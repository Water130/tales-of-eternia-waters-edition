"""Execute native casting, patched controls and per-instance particle constructors."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP
from casting_color_patch import COLORS, NEUTRAL_CAST


def check_cast_hold(uc, base, manifest, actors, enemies, stats, impact, sp,
                    reset, put, get, reg, regs):
    master, options = actors+0xa000, actors+0xc200
    sentinel = manifest['data_rva']-0x10
    count = 0
    checks = []

    def execute(start, stops=None, stubs=()):
        nonlocal count
        count += 1
        uc.reg_write(UC_X86_REG_RSP, sp)
        if stops is None:
            stops = [sentinel]
            put(sp, 'Q', base+sentinel)
        reached = []
        def step(emu, address, size, user):
            rva = address-base
            if rva in stops:
                reached.append(rva); emu.emu_stop()
            elif rva in stubs:
                current = emu.reg_read(UC_X86_REG_RSP)
                assert current % 16 == 8, ('Native ABI alignment', hex(rva))
                emu.reg_write(UC_X86_REG_RIP, get(current, 'Q'))
                emu.reg_write(UC_X86_REG_RSP, current+8)
        handle = uc.hook_add(UC_HOOK_CODE, step)
        try:
            uc.emu_start(base+start, base+sentinel+1, count=40000)
        finally:
            uc.hook_del(handle)
        assert reached, ('No continuation', hex(start), hex(uc.reg_read(UC_X86_REG_RIP)))
        return reached[0]

    def setup(char=2, arte=71, held=True, l1=False, mask=0x40, issuer=0, gauge=0xa000):
        reset()
        put(base+0x8c9180, 'I', 0x100 if l1 else 0)
        put(base+0x8c922f, 'BB', int(held), int(held))
        actor = actors+char*0x248
        put(actor+0x52, 'B', 10); put(actor+0x57, 'B', 2)
        put(actor+0x6b, 'B', 3); put(actor+0x6d, 'B', arte)
        put(actor+0x6c, 'B', (get(base+0x551780+arte*8+2, 'B') & 15)*4)
        put(actor+0x8c, 'H', 3)
        put(actor+0x8e, 'H', get(base+0x551780+arte*8, 'B'))
        put(actor+0xa2, 'HH', issuer, mask)
        put(actor+0x34, 'H', 500); put(actor, 'Q', enemies)
        put(actor+0xf0, 'Q', base+0x12ceba0)
        put(base+0x12cea60, 'Q', master)
        put(base+0x12cea68, 'Q', actors+0xc100)
        put(base+0x12cea70, 'Q', base+0x562a50)
        put(base+0x12cea78, 'Q', base+0x551780)
        put(base+0x6449e0, 'Q', options)
        for family in range(10):
            put(master+0xbb8+family*8, 'BBH', char+1, 15, gauge)
            put(master+char*0xd0+0x7a+family, 'B', 43+family)
        return actor

    def tick(actor, stops=None):
        reg('rcx', actor)
        return execute(0xd51f0, stops or [0xd571d], [0x8d520, 0x1b5ca0])

    if 'summon_hold' in manifest['features']:
        for char in [2, 3]:
            for arte in range(116):
                actor = setup(char, arte)
                reg('rcx', actor); reg('rax', arte)
                before = bytes(uc.mem_read(master, 0x1000))
                execute(manifest['symbols']['held_summon_choice'])
                family = get(base+0x551780+arte*8+2, 'B') & 15
                assert uc.reg_read(regs['rax']) == (42+family if 70 <= arte <= 95 else arte)
                assert bytes(uc.mem_read(master, 0x1000)) == before
        checks.append('232 arte/family/character choices; healing and support stay unchanged')

        spells = [71,73,78,81,85,88,90,92,94,95]
        for char in [2,3]:
            for arte in spells+[54]:
                for mask in [0x40,0x400,0x800]:
                    for held in [False,True]:
                        for l1 in [False,True]:
                            actor = setup(char, arte, held, l1, mask)
                            tick(actor)
                            family = get(base+0x551780+arte*8+2, 'B') & 15
                            expected = 42+family if held and not l1 and arte>=70 else arte
                            assert get(actor+0x6d,'B') == expected, (char,arte,mask,held,l1)
                            assert get(actor+0x8c,'H') == (4 if l1 else 2)
                            assert get(actor+0x34,'H') == 500
                            assert get(master+0xbba+(family-1)*8,'H') == 0xa000
        checks.append('Native cast ticks: L1 priority, release, ten elements, healing, direct and both shortcut buttons')
        if 'artesphere' in manifest['features']:
            for char in [2,3,6]:
                for held in [False,True]:
                    for l1 in [False,True]:
                        actor=setup(char,71,held,l1,0x100)
                        put(base+0x8c9180,'I',(0x80000 if held else 0)|(0x100 if l1 else 0))
                        tick(actor)
                        assert get(actor+0x6d,'B')==(43 if char in (2,3) and held and not l1 else 71)
                        assert get(actor+0x8c,'H')==(4 if l1 or (char==6 and held) else 2)
            # Native release path must also retarget ally healing for R2.
            for source in (0x400,0x800,0x100):
                actor=setup(2,55,False,False,source);reg('rbx',actor);reg('rdx',source)
                execute(0xd53f0,[0x90690])
            checks.append('R2 casts: release/hold/invocation, L1 priority and native ally-healing target branch')

        for exclusion in ['low_gauge','owner','unlearned','enemy','autonomous','other_controller']:
            actor = setup()
            if exclusion=='low_gauge':put(master+0xbba,'H',0x9000)
            if exclusion=='owner':put(master+0xbb8,'B',4)
            if exclusion=='unlearned':put(master+2*0xd0+0x7a,'B',0)
            if exclusion=='enemy':put(actor+0x51,'B',1)
            if exclusion=='autonomous':put(actor+0xa4,'H',0)
            if exclusion=='other_controller':put(actor+0xa2,'H',1)
            tick(actor)
            assert get(actor+0x6d,'B')==71,exclusion
        # Down no longer holds; Guard and LT/RT must not hold or select a summon.
        for raw, logical in [(0,4),(0x8000,0x80),(0x40000,0),(0x80000,0)]:
            actor=setup(held=False);put(base+0x8c9180,'I',raw);put(base+0x12ceba0,'I',logical)
            tick(actor);assert get(actor+0x8c,'H')==2 and get(actor+0x6d,'B')==71
        checks.append('Ownership, learning, gauge, autonomous AI, enemy and controller exclusions; Down/Guard/L2/R2 do not hold')

        for char in [2,3]:
            for arte in spells:
                for discount in [0,0x400,0x200]:
                    actor=setup(char,arte,l1=True)
                    # Repeated ready-state ticks with L1 consume nothing.
                    for _ in range(3):
                        put(actor+0x8c,'H',3);tick(actor)
                        assert get(actor+0x34,'H')==500
                    put(base+0x8c9180,'I',0);put(actor+0x8c,'H',3);tick(actor)
                    summon=get(actor+0x6d,'B');assert 43<=summon<=52
                    assert get(actor+0xa4,'H')==0x2000
                    put(stats+0x4e,'H',discount)
                    # Another large effect is still running: repeated retries do
                    # not charge TP, consume a gauge or discard the chosen summon.
                    pool=base+0x12cfca0
                    put(pool,'Q',enemies);put(pool+0x33,'B',1);put(pool+0x36,'B',1)
                    for _ in range(3):
                        put(actor+0x8c,'H',1);tick(actor)
                        assert get(actor+0x34,'H')==500
                        assert get(master+0xbba+(summon-43)*8,'H')==0xa000
                        assert get(actor+0xa4,'H')==0x2000
                    put(pool,'Q',0);put(actor+0x8c,'H',1)
                    tick(actor,[0xd5549])
                    cost=get(base+0x562a50+summon*24,'B')
                    if discount==0x400:cost//=2
                    if discount==0x200:cost=cost*2//3
                    assert get(actor+0x34,'H')==500-cost
                    assert get(actor+0xa4,'H')==0
                    assert get(actor+0x4c,'H')==get(base+0x551780+summon*8+4,'H')+(0x9c if char==3 else 0)
                    # Actual native invocation vitality write (level 15 => 1.5).
                    reg('rbx',actor);reg('rdi',actor+0x8e);reg('r12',0);reg('r14',base)
                    execute(0xd55c3,[0xd569d])
                    assert get(master+0xbba+(summon-43)*8,'H')==15*4096//10
        checks.append('Native multi-tick casts, L1 release, serialized summon retries, one TP debit, discounts, voice IDs and native vitality consumption')

        for event in ['gauge_lost','owner_lost','no_tp']:
            actor=setup();tick(actor);put(actor+0x8c,'H',1)
            if event=='gauge_lost':put(master+0xbba,'H',0x9000)
            if event=='owner_lost':put(master+0xbb8,'B',4)
            if event=='no_tp':put(actor+0x34,'H',0)
            tick(actor)
            assert get(actor+0x52,'B')==0,event
            assert get(actor+0x34,'H')==(0 if event=='no_tp' else 500)
        checks.append('Invalidated summon and insufficient TP cancel before dispatch without spending vitality')

        actor=setup();tick(actor)
        reg('rcx',actor);execute(0x712e0)
        assert get(actor+0xa4,'H')==0 and get(actor+0x8c,'H')==0
        # Subsequent casting initializes a fresh input latch through native code.
        put(actor+0x52,'B',0);reg('rcx',actor);reg('rdx',71)
        execute(0x112d10,stubs=[0x7fe70,0x114980,0x1b5ca0])
        assert get(actor+0xa4,'H')==0x40 and get(actor+0x6d,'B')==71
        checks.append('Real native interruption clears the pending choice; the next cast initializes its own command')

        ready=manifest['symbols']['cast_dispatch_ready']
        allowed=manifest['concurrent_effect_allowlist']
        for new in allowed+[26,34]:
            for active in allowed+[26,34,58,70]:
                setup();pool=base+0x12cfca0
                put(pool,'Q',enemies);put(pool+0x33,'B',1);put(pool+0x36,'B',active)
                put(base+0x12d0eaa,'H',0xffff);reg('rdx',new)
                execute(ready)
                expected=int(new in allowed and active in allowed and new!=active)
                assert uc.reg_read(regs['rax'])==expected,(new,active)
        for state,init in [(2,0),(1,1)]:
            setup();pool=base+0x12cfca0
            put(pool,'Q',enemies);put(pool+0x33,'B',1);put(pool+0x36,'B',1)
            put(pool+0x3a,'H',state);put(pool+0x3e,'H',init)
            reg('rdx',2);execute(ready);assert uc.reg_read(regs['rax'])==0
        for effect_id in [1,26,161]:
            setup()
            for slot in range(16):put(base+0x12cfca0+slot*0x120,'Q',enemies)
            reg('rdx',effect_id);execute(ready);assert uc.reg_read(regs['rax'])==0
        checks.append('Pre-debit admission matches supported overlap pairs; loading and exhausted pools wait without charging')

        for char in [2,3]:
            for family in range(10):
                actor=setup(char)
                reg('rcx',char);reg('rdx',family);reg('r8',0x800);reg('r9',0)
                execute(0x90380)
                assert get(master+0xbba+family*8,'H')==0xa000
        checks.append('Ordinary same-element spells still preserve full vitality')

    if 'casting_colors' in manifest['features']:
        effect,particle=impact,impact+0x200
        for char in [2,3]:
            for family,rgb in enumerate([NEUTRAL_CAST]+list(COLORS.values())):
                for offset in [0x10,0x22,0xa]:
                    for intensity in [0,64,128,255]:
                        actor=setup(char)
                        put(actor+0x6c,'B',family*4);put(effect,'Q',actor)
                        uc.mem_write(particle,bytes([0x6b])*0x80)
                        put(particle+offset,'BBBB',intensity,intensity//2,intensity//3,0x91)
                        before=bytes(uc.mem_read(particle,0x80))
                        reg('rax',particle);reg('rdi',effect);reg('rdx',offset)
                        saved={k:uc.reg_read(v) for k,v in regs.items()}
                        execute(manifest['symbols']['tint_cast_particle'])
                        expected=bytearray(before);expected[offset:offset+3]=bytes(x*intensity//255 for x in rgb)
                        assert bytes(uc.mem_read(particle,0x80))==expected
                        assert saved=={k:uc.reg_read(v) for k,v in regs.items()}
        checks.append('264 particle tints: neutral plus ten families and both mages; RGB only, intensity/phase/geometry/register preservation')

        particle_pool=0x21000000
        uc.mem_map(particle_pool,0x10000)
        # All nine hooked callsites, executing their real native constructors.
        sites=[(0xcc6f4,0,0x10),(0xcc73e,0,0x10),(0xcc78e,0x19c8,0x22),
               (0xcc7c3,0x19c8,0x22),(0xcc7f6,0x19c8,0x22),(0xcc860,0x19c8,0x22),
               (0xcc8da,0,0x10),(0xcc900,0x19c8,0x22),(0xcc92a,0x36b0,0xa)]
        for site,pooloff,offset in sites:
            actor=setup();put(actor+0x6c,'B',12);put(effect,'Q',actor)
            uc.mem_write(particle_pool,b'\0'*0x10000)
            put(base+0x12cecf0,'Q',particle_pool);put(base+0x12cec20,'Q',particle_pool+0x6000)
            put(base+0x12ceb7a,'B',0)
            source=particle
            uc.mem_write(source,b'\0'*0x80)
            put(source+offset,'BBBB',128,128,128,0x91)
            before=bytes(uc.mem_read(source,0x80))
            reg('rcx',source);reg('rdi',effect)
            # Hook sits at a call instruction: native caller RSP is 16 aligned.
            old_sp=sp;sp=old_sp-8
            try:execute(site,[site+5])
            finally:sp=old_sp
            result=uc.reg_read(regs['rax'])
            assert result==particle_pool+pooloff,(hex(site),hex(result))
            from casting_color_patch import PROFILES
            if site in PROFILES:
                for off,value in PROFILES[site]:
                    expected=bytes(((x*abs(value)//255)*(1 if value>=0 else -1))&255 for x in COLORS['fire'])
                    assert bytes(uc.mem_read(result+off,3))==expected,(hex(site),off)
            else:
                assert bytes(uc.mem_read(result+offset,3))==bytes(x*128//255 for x in COLORS['fire'])
            assert get(result+offset+3,'B')==0x91
            assert bytes(uc.mem_read(source,0x80))==before
        from casting_color_patch import PROFILES
        real_templates={0xcc73e:(0x590db0,0x58),0xcc860:(0x592f38,0x4a),
                        0xcc8da:(0x591a68,0x58),0xcc900:(0x592bc0,0x4a),0xcc92a:(0x58ff54,0x6a)}
        for char in [2,3]:
            for family,rgb in enumerate([NEUTRAL_CAST]+list(COLORS.values())):
                for profile_index,(site,records) in enumerate(PROFILES.items()):
                    actor=setup(char);put(actor+0x6c,'B',family*4);put(effect,'Q',actor)
                    template,length=real_templates[site]
                    before=bytes(uc.mem_read(base+template,length))
                    uc.mem_write(particle,before)
                    reg('rax',particle);reg('rdi',effect);reg('rdx',profile_index)
                    saved={k:uc.reg_read(v) for k,v in regs.items()}
                    execute(manifest['symbols']['tint_cast_profile'])
                    expected=bytearray(before)
                    if site in (0xcc73e,0xcc92a):
                        blend=0x38 if site==0xcc73e else 0x5a
                        mode=int.from_bytes(expected[blend:blend+2],'little')
                        expected[blend:blend+2]=((mode&~0x60)|0x20).to_bytes(2,'little')
                        assert ((mode>>5)&3)==2
                    for offset,value in records:
                        expected[offset:offset+3]=bytes(((v*abs(value)//255)*(1 if value>=0 else -1))&255 for v in rgb)
                    assert bytes(uc.mem_read(particle,length))==expected,(char,family,site)
                    assert bytes(uc.mem_read(base+template,length))==before
                    assert saved=={k:uc.reg_read(v) for k,v in regs.items()}
                    # Native RGB evolution, including its two-phase delay counters.
                    # A completely faded zero is allowed, a foreign dominant hue is not.
                    color_offset=records[0][0];delta_offset=records[-1][0]
                    for frame in range(12):
                        reg('rcx',particle+color_offset);reg('rdx',particle+delta_offset)
                        execute(0x8bbe0)
                        live=list(uc.mem_read(particle+color_offset,3))
                        strongest=max(range(3),key=lambda j:rgb[j])
                        assert all(abs(live[j]*rgb[strongest]-live[strongest]*rgb[j])<=20*255 for j in range(3)),(site,family,frame,live)
        checks.append('100 real casting templates: both gradients/evolution; 12 native ticks; subtractive hand/energy glyphs switched to additive; geometry, lifetime, CLUT and phase preserved')
        checks.append('Nine real particle-constructor callsites preserve shared templates and native particle placement')
        uc.mem_unmap(particle_pool,0x10000)
    return checks,count
