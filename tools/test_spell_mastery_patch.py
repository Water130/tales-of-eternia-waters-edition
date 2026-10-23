"""Execute emitted mastery and native allocation/callback/damage code under ASLR.

Rendering/audio/CRT boundaries are stubbed; gameplay state and damage queue are
native. These tests do not claim to validate the live game's rendering.
"""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS


def check_spell_mastery(u, base, m, actors, enemies, impact, sp,
                       reset, put, get, reg, regs):
    info = m['spell_mastery']
    sym = m['symbols']
    state = base+info['state_rva']
    context = base+info['context_rva']
    effects = base+info['effects_rva']
    tags = base+info['projectiles_rva']
    roots = base+info['current_roots_rva']
    live = base+info['usage']['live_rva']
    preferences = base+info['usage']['preferences']['live_rva']
    flag = base+m['data_rva']+0x1a00+info['option_flag']
    pool, projectiles = base+0x12cfca0, base+0x12cee48
    sentinel = base+m['data_rva']-16
    stub_callback = actors+0xf000
    callback_kind = 'plain'
    callbacks = []
    raw_damage = None
    rng_roll = 99
    rng_calls = []
    execute_scripts = False
    script_hits = []
    script_sprites = []
    star_active = False
    star_sprites = []
    star_impacts = []
    damage_owner = actors+2*0x248
    cases = 0
    saved_tables = {}
    for table, index, target in ((0x4e9420,1,stub_callback),
                                 (0x4e9900,4,stub_callback),
                                 (0x4e9690,6,stub_callback)):
        p = base+table+index*8
        saved_tables[p] = bytes(u.mem_read(p,8))
        put(p,'Q',target)
    for index, target in ((19,0xcab90),(20,0xcac50),(21,0xcad00),(22,0xcada0)):
        p = base+0x4e9690+index*8
        saved_tables[p] = bytes(u.mem_read(p,8))
        put(p,'Q',base+target)

    def ret(value=0):
        rsp = u.reg_read(UC_X86_REG_RSP)
        assert rsp % 16 == 8, ('ABI',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rsp))
        reg('rax',value)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'))
        u.reg_write(UC_X86_REG_RSP,rsp+8)

    def boundary(emu, address, size, _):
        a = address-base
        if a == 0x283090:
            rng_calls.append(rng_roll)
            ret(rng_roll)
        elif a == 0x2a4880:
            dest, val, n = [u.reg_read(regs[r]) for r in ('rcx','rdx','r8')]
            u.mem_write(dest,bytes([val&255])*n)
            ret(dest)
        elif a == 0x114640:  # Native buff sound only.
            ret()
        elif star_active and a == 0x114e60:
            command=u.reg_read(regs['rdx'])
            assert command==base+0x58a650
            assert get(command+2,'h')==1 and get(command+4,'H')==0
            star_sprites.append(command)
            ret(actors+0x9000)
        elif star_active and a == 0x8f6e0:
            star_impacts.append(bytes(u.mem_read(u.reg_read(regs['rdx']),8)))
            ret()
        elif star_active and a == 0x116260:
            ret(0)
        elif execute_scripts and a == 0x116260:
            script_hits.append(get(pool+0x38,'H'))
            ret(0)
        elif execute_scripts and a == 0x114e60:
            command=u.reg_read(regs['rdx'])
            script_sprites.append((get(pool+0x38,'H'),get(command+2,'h')))
            ret(0)
        elif address == stub_callback or (a == 0x114f50 and not execute_scripts):
            callbacks.append((get(context,'Q'),u.reg_read(regs['rcx'])))
            if callback_kind == 'projectile':
                # Tail-call the real projectile allocator within the scope.
                reg('rcx',5)
                reg('rdx',impact)
                reg('r8',damage_owner)
                reg('r9',impact+0x40)
                u.reg_write(UC_X86_REG_RIP,base+0x116580)
            else:
                ret(0x1234)
        elif a == 0x8e929 and raw_damage is not None:
            # Run the original damage prologue (including saved RSI and native
            # caller return address). Supply post-resistance damage, then run
            # the original cap, number queue and HP commit without mocks.
            reg('rbp',damage_owner);reg('rdi',enemies)
            reg('rsi',raw_damage & 0xffffffffffffffff)
            reg('r8',impact)
            reg('r12',impact)
            for r in ('r14','r13','r15','rbx'):
                reg(r,0)
            u.reg_write(UC_X86_REG_RIP,base+0x8effc)
    h = u.hook_add(UC_HOOK_CODE,boundary)

    def setup():
        reset()
        u.mem_write(state,b'\0'*info['size'])
        u.mem_write(live,b'\0'*info['usage']['size'])
        u.mem_write(preferences,b'\0'*224)
        put(flag,'B',1)
        callbacks.clear()

    def run(entry, end=None, rsp=None, call_return=None):
        nonlocal cases
        cases += 1
        rsp = sp if rsp is None else rsp
        u.reg_write(UC_X86_REG_RSP,rsp)
        if call_return is not None:
            put(rsp,'Q',base+call_return)
        elif end is None:
            put(rsp,'Q',sentinel)
        target = sentinel if end is None else base+end
        reached = []
        def stop(emu,address,size,_):
            if address == target:
                reached.append(address);emu.emu_stop()
        stop_hook=u.hook_add(UC_HOOK_CODE,stop)
        try:
            start = sym[entry] if isinstance(entry,str) else entry
            u.emu_start(base+start,target+1,count=10000)
            assert reached,('No end',entry,hex(u.reg_read(UC_X86_REG_RIP)-base))
        finally:
            u.hook_del(stop_hook)
        expected = rsp+8 if end is None else rsp
        # Damage deliberately stops inside its native stack frame.
        if entry == 0x8e910: expected = rsp-0x68
        assert u.reg_read(UC_X86_REG_RSP)==expected,('stack',entry)

    def capture(char, arte, uses, slot=0, side=0, effect=None, caller=0xd554e):
        actor = actors+char*0x248
        effect_id = get(base+0x551780+arte*8,'B') if effect is None else effect
        put(actor+0x6d,'B',arte);put(actor+0x51,'B',side)
        put(actor,'Q',actors)
        put(live+(char*128+arte)*2,'H',uses)
        put(pool+slot*0x120,'QQ',actor,actors)
        reg('r12',actor);reg('r14',pool+slot*0x120);reg('rbp',effect_id)
        put(sp-8+0x58,'Q',base+caller)
        before={r:u.reg_read(v) for r,v in regs.items() if r!='rax'}
        u.reg_write(UC_X86_REG_EFLAGS,0x246)
        run(0x114a45,0x114a4f,rsp=sp-8)
        assert before=={r:u.reg_read(regs[r]) for r in before}
        assert u.reg_read(UC_X86_REG_EFLAGS)==0x246
        assert get(pool+slot*0x120+0x36,'B')==effect_id & 255
        assert get(live+(char*128+arte)*2,'H')==uses, 'allocation counts twice'
        return effects+slot*16, actor

    def projectile(actor, slot=5):
        reg('rax',projectiles+slot*0x30)
        reg('r8',actor);reg('rdx',impact);reg('r11',5)
        before={r:u.reg_read(v) for r,v in regs.items() if r!='rcx'}
        u.reg_write(UC_X86_REG_EFLAGS,0x246)
        run(0x116609,0x116610)
        assert before=={r:u.reg_read(regs[r]) for r in before}
        assert u.reg_read(UC_X86_REG_EFLAGS)==0x246
        assert get(projectiles+slot*0x30+8,'Q')==actor
        return tags+slot*16

    def damage(amount, expected, caller=0x1164e3, slot=5, immediate=False):
        nonlocal raw_damage
        raw_damage=amount
        put(enemies+0x2c,'i',100000)
        put(base+0x865a08,'I',0)  # native damage ring write cursor
        reg('rcx',damage_owner);reg('rdx',enemies)
        reg('r9',impact);reg('rsi',base+0x12cf988 if immediate else projectiles+slot*0x30)
        put(impact,'B',0x80)
        run(0x8e910,0x8f0a1,call_return=caller)
        assert get(enemies+0x2c,'i')==100000-expected,(amount,expected,get(enemies+0x2c,'i'))
        assert get(base+0x12d0f46,'h')==expected, 'display does not match HP'
        raw_damage=None

    try:
        extra=base+info['usage']['catchup']['live_rva']
        for char in (2,3):
            setup()
            put(live+((char^1)*128+73)*2,'H',500)
            put(extra+(char*128+73)*2,'H',20)
            rec,actor=capture(char,73,98)
            assert get(rec+10,'H')==121
            assert get(rec+12,'I')==6
            assert get(extra+(char*128+73)*2,'H')==20
            reg('rcx',actor);reg('rdx',73);run('mastery_actor_uses')
            assert u.reg_read(regs['rax'])==118
            # Accepted cast then commits exactly the predicted EXP.
            reg('rcx',char);reg('rdx',73);run('arte_usage_increment')
            assert get(live+(char*128+73)*2,'H')==99
            assert get(extra+(char*128+73)*2,'H')==22
        from spell_growth import PROJECTILE_CAPS
        import struct
        # Summons snapshot native Craymel levels, not use counts. Independent
        # toggle, exact level-one/native behavior and no spell critical stacking.
        from summon_growth import bonus
        summon_flag=base+m['data_rva']+0x1a43
        # A summon released while a previous spell callback is scoped must
        # snapshot its own Craymel level, never inherit that spell's mastery.
        for char in (2,3):
            for spirit in range(10):
                setup()
                master=actors+0xa000
                put(base+0x12cea60,'Q',master)
                put(master+0xbb8+spirit*8,'BB',3,10)
                previous,actor=capture(char,73,998)
                put(context,'Q',previous)
                rec,_=capture(char,43+spirit,9999,slot=1)
                assert get(rec+8,'H')==43+spirit
                assert get(rec+10,'H')==10
                assert get(rec+12,'I')==bonus(spirit,10)
                put(context,'Q',rec)
                child,_=capture(char,43+spirit,0,slot=2,caller=0xc0000)
                assert bytes(u.mem_read(child,16))==bytes(u.mem_read(rec,16))
        for char in (2,3):
            for spirit in range(10):
                for level in (1,2,10,20,29,30,255):
                    for enabled in (0,1):
                        setup()
                        master=actors+0xa000
                        put(base+0x12cea60,'Q',master)
                        put(master+0xbb8+spirit*8,'BB',3,level)
                        rec,actor=capture(char,43+spirit,9999)
                        damage_owner=actor
                        assert get(rec,'Q')==actor
                        assert get(rec+8,'H')==43+spirit
                        assert get(rec+10,'H')==min(level,30)
                        assert get(rec+12,'I')==bonus(spirit,level)
                        put(context,'Q',rec)
                        projectile(actor)
                        put(master+0xbb9+spirit*8,'B',1)
                        put(summon_flag,'B',enabled)
                        put(flag,'B',0)
                        rng_roll=0
                        rng_calls.clear()
                        damage(100,100+(bonus(spirit,level) if enabled else 0))
                        assert not rng_calls
                        put(flag,'B',1)
                        damage(100,100+(bonus(spirit,level) if enabled else 0))
                        assert not rng_calls
                        # Both native scratch and persistent collisions use the
                        # same frozen level, and do not mutate their rectangle.
                        for immediate in (False,True):
                            obj=base+0x12cf988 if immediate else projectiles+5*0x30
                            put(obj+8,'Q',actor)
                            for _ in range(2):
                                reg('rsi',obj)
                                packed=int.from_bytes(struct.pack('<4h',-100,-80,100,0),'little')
                                reg('rbx',packed)
                                run(0x1162b5,0x1162ba,rsp=sp-8)
                                lv=min(level,30)-1 if enabled else 0
                                dx=(720-200)*lv//58
                                dy=80*(lv*50//29)//200
                                expected=(-100-dx,-80-dy,100+dx,dy)
                                got=struct.unpack('<4h',u.reg_read(regs['rbx']).to_bytes(8,'little'))
                                assert got==expected,(spirit,level,enabled,got,expected)
        rng_roll=99
        put(summon_flag,'B',0)
        for uses in (0,165,166,498,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,94,uses,side=side)
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+94//8,'B',1<<(94%8))
                extra=min(999,uses+1)*6//999 if enabled and not disabled and not side else 0
                star_active=True
                try:
                    for tick in range(40,128):
                        star_sprites.clear();star_impacts.clear()
                        put(pool+0x38,'H',tick);reg('rdi',pool)
                        reg('rax',tick%8);reg('rdx',0);reg('rbp',0)
                        run(0xbce35,0xbcec4,rsp=sp-8)
                        added=tick in (44,52,60,68,76,84)[:extra]
                        assert len(star_impacts)==(2 if tick%8==0 else 1 if added else 0),(uses,tick,star_impacts)
                        assert len(star_sprites)==int(added)
                        if added:assert bytes(u.mem_read(actors+0x9000,8))==star_impacts[0]
                finally:
                    star_active=False
        for uses in (0,165,166,498,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,91,uses,side=side)
                put(pool+0x10,'Q',base+0x5785d0)
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+91//8,'B',1<<(91%8))
                extra=min(999,uses+1)*6//999 if enabled and not disabled and not side else 0
                reg('rcx',pool);run('mastery_dark_force_script')
                script=get(pool+0x10,'Q')
                assert script==(state+0x5000 if extra else base+0x5785d0),(uses,enabled,disabled,side,extra,hex(script),hex(state),get(pool+0x38,'H'),bytes(u.mem_read(rec,16)).hex())
                for offset in (52,76,100,148):assert get(script+offset,'H')==5+extra
                # Execute the real native script interpreter for the impact
                # stage: every added orb gets its own scheduled hit; native
                # repeat/fade/completion timing is retained or shifted intact.
                put(pool+0x78,'Q',base+0x578430)
                put(pool+0x35,'B',24)
                execute_scripts=True;script_hits.clear();script_sprites.clear()
                try:
                    for tick in range(90,145+extra*6):
                        put(pool+0x38,'H',tick);reg('rcx',pool)
                        run(0x114f50)
                    assert script_hits==list(range(92,117+extra*6,6)),(extra,script_hits)
                    assert get(pool+0x10,'Q')==0
                    assert (128+extra*6,8) in script_sprites
                finally:
                    execute_scripts=False
        for uses in (0,165,166,498,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,89,uses,slot=13,side=side)
                effect=pool+13*0x120
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+89//8,'B',1<<(89%8))
                extra=min(999,uses+1)*6//999 if enabled and not disabled and not side else 0
                reg('rsi',effect);put(effect+0x38,'H',0)
                run(0x947f5,0x947fb,rsp=sp-8)
                record=state+0x4010+13*4
                assert get(record,'B')==extra
                for tick in range(32,113):
                    put(effect+0x38,'H',tick);reg('rsi',effect)
                    added=tick in (42,50,58,66,74,82)[:extra]
                    run(0x94d05,0x9498f if added else 0x94d0c,rsp=sp-8)
                    assert get(effect+0x38,'H')==tick+(2 if added else 0)
                    if added:
                        assert get(effect+0x38,'H')%4==0
                        run(0x94d05,0x94d0c,rsp=sp-8)
                        assert get(effect+0x38,'H')==tick
                        # Never loop on the extra beam or retrigger in a
                        # repeated update for the same native tick.
                        run(0x94d05,0x94d0c,rsp=sp-8)
        phases=[]
        def aqua_phase(emu,address,size,_):
            if address==base+sym['mastery_aqua_edge_native']:
                effect=u.reg_read(regs['rcx'])
                phases.append(get(effect+0x38,'H'))
                ret()
        aqua_hook=u.hook_add(UC_HOOK_CODE,aqua_phase)
        try:
            for uses in (0,331,332,665,998):
                for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                    setup();rec,actor=capture(2,70,uses,slot=14,side=side)
                    effect=pool+14*0x120
                    put(effect+0x10,'Q',impact)
                    put(context,'Q',rec);put(flag,'B',enabled)
                    if disabled:put(preferences+2*32+70//8,'B',1<<(70%8))
                    extra=min(999,uses+1)*3//999 if enabled and not disabled and not side else 0
                    for tick in range(113):
                        phases.clear();put(effect+0x38,'H',tick);reg('rcx',effect)
                        run(0xcefa0)
                        assert phases==[tick+i*8 for i in range(extra+1) if tick+i*8<=112]
                        assert get(effect+0x38,'H')==tick
                    # Native completion/free is called once, regardless of
                    # the previous number of extra projectile phases.
                    phases.clear();put(effect+0x10,'Q',0);reg('rcx',effect)
                    run(0xcefa0)
                    assert phases==[112]
        finally:
            u.hook_del(aqua_hook)
        for uses in (0,331,332,665,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,90,uses,slot=15,side=side)
                effect=pool+15*0x120
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+90//8,'B',1<<(90%8))
                extra=min(999,uses+1)*3//999 if enabled and not disabled and not side else 0
                array=state+0x3000+15*256
                put(effect+0x38,'H',0);reg('r14',effect)
                run(0x9bacd,0x9bad4,rsp=sp-8)
                assert u.reg_read(regs['rbp'])==array
                assert get(array+0xf8,'I')==16+2*extra
                for tick in range(16,80):
                    for phase in (0,4,7):
                        reg('rcx',tick);reg('rbp',array);reg('r15',impact)
                        put(base+0x12ceb40,'I',phase)
                        dest=0x9bb00 if phase==0 else 0x9bb10 if phase==4 and (tick-16)//8<extra else 0x9bc71
                        run(0x9baf3,dest,rsp=sp-8)
                        if dest==0x9bb10:
                            assert u.reg_read(regs['rax'])==8+(tick-16)//8
                            assert u.reg_read(regs['rcx'])==impact+0x6a
                for index in (15,16,21,22):
                    reg('r14',effect);reg('r12',index)
                    run(0x9bf67,0x9bc93 if index<16+2*extra else 0x9bf71,rsp=sp-8)
                for i in range(22):
                    sprite=actors+0x8000+i*0x80
                    put(array+i*8,'Q',sprite)
                    put(sprite+0x5a,'hh',4,100)
                reg('r14',effect);run(0x9c116,0x9c26d,rsp=sp-8)
                assert get(effect+0x38,'H')==126
                for i in range(22):
                    values=struct.unpack('<hh',u.mem_read(actors+0x8000+i*0x80+0x5a,4))
                    assert values==((3,36) if i<16+2*extra else (4,100)),(uses,enabled,disabled,side,i,values)
        for uses in (0,165,498,998):
            for enabled in (0,1):
                setup();rec,actor=capture(2,93,uses)
                put(context,'Q',rec);put(flag,'B',enabled);reg('rbp',pool)
                put(pool+0x38,'H',0)
                run(0x9cb8d,0x9cb94,rsp=sp-8)
                array=state+0x2000
                extra=min(999,uses+1)*6//999 if enabled else 0
                assert u.reg_read(regs['rsi'])==array
                assert get(array+0x78,'I')==8+extra
                for tick in range(192):
                    quotient=tick//24
                    reg('r8',tick);reg('rax',quotient*24);reg('rbx',quotient);reg('rsi',array)
                    dest=0x9cbca if tick%24==0 else 0x9cbd0 if tick%24==12 and quotient<extra else 0x9cc4e
                    run(0x9cbc1,dest,rsp=sp-8)
                    if dest==0x9cbd0:assert u.reg_read(regs['rbx'])==8+quotient
                reg('rsi',array);run(0x9cc4e,0x9cc55,rsp=sp-8)
                assert u.reg_read(regs['r13'])==array+(8+extra)*8
                # A setting change mid-flight keeps the allocated slot count.
                put(flag,'B',not enabled);put(pool+0x38,'H',1);reg('rbp',pool)
                run(0x9cb8d,0x9cb94,rsp=sp-8)
                assert get(array+0x78,'I')==8+extra
        for uses in (0,331,332,665,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,72,uses,side=side)
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+72//8,'B',1<<(72%8))
                extra=min(999,uses+1)*3//999 if enabled and not disabled and not side else 0
                for site,native,ticks,yes,no in ((0xca2c5,12,(24,40,56),0xca2cb,0xca329),(0xca333,32,(44,60,76),0xca33d,0xca3f8)):
                    for tick in range(1,88):
                        put(pool+0x38,'H',tick);reg('rbx',pool);reg('rcx',pool);reg('rax',tick)
                        expected=tick==native or tick in ticks[:extra]
                        saved={r:u.reg_read(regs[r]) for r in regs}
                        run(site,yes if expected else no,rsp=sp-8)
                        assert saved=={r:u.reg_read(regs[r]) for r in saved}
        # Freeze Lancer's native emission branch creates both a real lance
        # sprite and its collision object. No fixed VFX array is extended.
        for uses in (0,165,166,498,998):
            for enabled,disabled,side in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                setup();rec,actor=capture(2,83,uses,side=side)
                put(context,'Q',rec);put(flag,'B',enabled)
                if disabled:put(preferences+2*32+83//8,'B',1<<(83%8))
                extra=min(999,uses+1)*6//999 if enabled and not disabled and not side else 0
                for tick in range(64):
                    put(pool+0x38,'H',tick)
                    reg('rdi',pool);reg('rcx',pool);reg('rax',tick%4)
                    expected=tick%4==0 or (tick%4==2 and tick//4<extra)
                    saved={r:u.reg_read(regs[r]) for r in regs if r!='rax'}
                    run(0x931c1,0x931c9 if expected else 0x932f7,rsp=sp-8)
                    assert saved=={r:u.reg_read(regs[r]) for r in saved}
        for arte in info['offensive_arte_ids']:
            for uses in (0,18,19,498,998):
                for enabled in (0,1):
                    setup();rec,actor=capture(2,arte,uses)
                    put(context,'Q',rec);projectile(actor)
                    put(flag,'B',enabled)
                    original=(-100,-50,100,50)
                    packed=int.from_bytes(struct.pack('<4h',*original),'little')
                    reg('rsi',projectiles+5*0x30);reg('rbx',packed)
                    before={r:u.reg_read(v) for r,v in regs.items() if r!='rbx'}
                    put(projectiles+5*0x30+0x28,'Q',packed)
                    run(0x1162b5,0x1162ba,rsp=sp-8)
                    pct=(min(999,uses+1)*50//999) if enabled and arte not in PROJECTILE_CAPS else 0
                    expected=(-100-pct,-50-pct//2,100+pct,50+pct//2)
                    got=struct.unpack('<4h',u.reg_read(regs['rbx']).to_bytes(8,'little'))
                    assert got==expected,(arte,uses,enabled,got,expected)
                    assert get(sp-8+0x38,'Q')==u.reg_read(regs['rbx'])
                    assert get(projectiles+5*0x30+0x28,'Q')==packed
                    assert before=={r:u.reg_read(regs[r]) for r in before}
        # Timing hooks retain the native even-frame mask, character boundaries,
        # preferences and global opt-out. Cancellation never adds a cast.
        for char, side, arte in ((2,0,71),(3,0,73),(0,0,71),(2,1,71),(2,0,54)):
            for uses in (0,33,34,99,100,499,500,999,9999):
                for enabled in (0,1):
                    setup()
                    actor=actors+char*0x248
                    put(actor+0x51,'B',side)
                    put(live+(char*128+arte)*2,'H',uses)
                    put(flag,'B',enabled)
                    reg('rbx',actor);reg('rbp',arte);reg('rdx',400)
                    before={r:u.reg_read(v) for r,v in regs.items() if r not in ('rax','rdx')}
                    run(0x112fe9,0x112fee,rsp=sp-8)
                    reduction=min(15,uses*15//500) if enabled and char in (2,3) and side==0 and arte>=70 else 0
                    assert u.reg_read(regs['rdx'])==(400*(100-reduction)+99)//100
                    assert before=={r:u.reg_read(regs[r]) for r in before}
                    assert get(live+(char*128+arte)*2,'H')==uses

        # Every possible percentile verifies the exact critical threshold,
        # doubled native damage, final cap and display flag. No roll when OFF.
        for uses in (0,32,33,99,499,998):
            setup();rec,actor=capture(2,71,uses)
            damage_owner=actor
            put(context,'Q',rec);projectile(actor)
            chance=min(15,(uses+1)*15//500)
            power=min(25,(uses+1)//20)
            for roll in range(100):
                rng_roll=roll
                damage(100,(100+power)*(2 if roll<chance else 1))
                assert bool(u.reg_read(regs['r15'])&2)==(roll<chance)
            put(flag,'B',0)
            prior=len(rng_calls)
            damage(100,100)
            assert len(rng_calls)==prior
        rng_roll=99

        # Earlier release leaves the complete effect untouched. Test the
        # absolute script clock and exact rounding around every threshold.
        script=base+0x550000
        saved_script=bytes(u.mem_read(script,32))
        try:
            for uses in (0,32,33,99,499,998):
                for enabled in (0,1):
                    for tick in (0,84,85,86,94,95,96,99,100):
                        setup();rec,actor=capture(2,73,uses)
                        put(flag,'B',enabled);put(context,'Q',rec)
                        put(script,'HhI',0,-3,4);put(script+8,'HhI',100,-1,0)
                        put(pool+0x10,'Q',script);put(pool+0x38,'H',tick)
                        put(actor+0x52,'B',10);put(actor+0x77,'B',1)
                        put(actor+0x8c,'H',0);put(actor+0x23a,'B',7)
                        put(actor+0x23d,'B',4)
                        fx=bytes(u.mem_read(pool,0x120))
                        reg('rcx',pool)
                        before={r:u.reg_read(v) for r,v in regs.items()}
                        run('mastery_spell_recovery')
                        reduction=min(15,(uses+1)*15//500)
                        released=bool(enabled and reduction and tick>=100-reduction)
                        assert get(actor+0x77,'B')==(0 if released else 1)
                        assert get(actor+0x23d,'B')==(255 if released else 4)
                        assert bytes(u.mem_read(pool,0x120))==fx
                        assert before=={r:u.reg_read(regs[r]) for r in before}
            for mode in ('preference','casting','stagger','different_arte','not_latest','enemy','no_scope'):
                setup();rec,actor=capture(2,73,499)
                put(context,'Q',rec);put(pool+0x10,'Q',script);put(pool+0x38,'H',99)
                put(actor+0x52,'B',10);put(actor+0x77,'B',1);put(actor+0x8c,'H',0)
                if mode=='preference':put(preferences+2*32+73//8,'B',1<<(73%8))
                elif mode=='casting':put(actor+0x8c,'H',10)
                elif mode=='stagger':put(actor+0x52,'B',7)
                elif mode=='different_arte':put(actor+0x6d,'B',75)
                elif mode=='not_latest':put(roots+2*8,'Q',pool+0x120)
                elif mode=='enemy':put(actor+0x51,'B',1)
                elif mode=='no_scope':put(context,'Q',0)
                reg('rcx',pool);run('mastery_spell_recovery')
                assert get(actor+0x77,'B')==1,mode
            for arte,duration in ((75,80),(79,36),(82,100)):
                setup();rec,actor=capture(2,arte,499)
                put(context,'Q',rec);put(pool+0x10,'Q',0)
                put(actor+0x52,'B',10);put(actor+0x77,'B',1);put(actor+0x8c,'H',0)
                threshold=(duration*85+99)//100
                put(pool+0x38,'H',threshold-1);reg('rcx',pool);run('mastery_spell_recovery')
                assert get(actor+0x77,'B')==1
                put(pool+0x38,'H',threshold);reg('rcx',pool);run('mastery_spell_recovery')
                assert get(actor+0x77,'B')==0
            # Old cleanup is ignored even when the following spell has the
            # same native ID. Its own cleanup still follows the original path.
            setup();rec,actor=capture(2,73,499)
            newer,_=capture(2,73,500,slot=1)
            assert get(roots+2*8,'Q')==pool+0x120
            put(actor+0x8e,'H',4)
            reg('rcx',actor);reg('rbx',pool);reg('rax',4)
            run(0x115ef4,0x115f14,rsp=sp-8)
            reg('rcx',actor);reg('rbx',pool+0x120);reg('rax',4)
            run(0x115ef4,0x115efd,rsp=sp-8)
        finally:
            u.mem_write(script,saved_script)

        # Native immediate collisions inherit only the active effect scope.
        # A different mage, an absent scope, a buff or a stale scratch owner
        # must never borrow another spell's power or critical chance.
        for arte in (71,73,74,79,85,63):
            setup();rec,actor=capture(2,arte,499)
            damage_owner=actor
            put(base+0x12cf990,'Q',actor)
            put(context,'Q',rec)
            damage(100,125 if arte>=70 else 100,immediate=True)
            rng_roll=0
            damage(100,250 if arte>=70 else 100,immediate=True)
            rng_roll=99
            put(context,'Q',0);damage(100,100,immediate=True)
            put(context,'Q',rec);put(base+0x12cf990,'Q',actors+3*0x248)
            damage(100,100,immediate=True)
            put(base+0x12cf990,'Q',actor);put(rec,'Q',actors+3*0x248)
            damage(100,100,immediate=True)

        # Real Air Thrust loop storage, maximum count and option boundaries.
        # Each simultaneous effect receives a disjoint ten-projectile array.
        air=info['projectile_growth'][0]
        arrays=base+air['arrays_rva']
        for slot in range(16):
            for uses in (0,165,166,332,499,665,831,998,9999):
                for enabled in (0,1):
                    setup();rec,actor=capture(2,73,uses,slot=slot)
                    put(flag,'B',enabled)
                    fx=pool+slot*0x120
                    reg('rsi',fx)
                    before={r:u.reg_read(v) for r,v in regs.items() if r!='r14'}
                    run(0x94234,0x9423b,rsp=sp-8)
                    count=4+(min(999,uses+1)*6//999 if enabled else 0)
                    assert get(arrays+slot*128+0x70,'I')==count
                    assert u.reg_read(regs['r14'])==arrays+slot*128+2
                    assert before=={r:u.reg_read(regs[r]) for r in before}
                    run(0x9423f,0x94246,rsp=sp-8)
                    assert u.reg_read(regs['r15'])==arrays+slot*128+0x50
                    # A later option/counter change cannot add uninitialized
                    # projectiles to an already running effect.
                    put(fx+0x38,'H',1);put(flag,'B',1-enabled)
                    put(rec+10,'H',9999)
                    run(0x94234,0x9423b,rsp=sp-8)
                    assert get(arrays+slot*128+0x70,'I')==count
                    for i in (count-1,count):
                        reg('rbp',i)
                        run(0x94515,0x94251 if i<count else 0x9451e,rsp=sp-8)
                    for other in range(16):
                        if other!=slot:
                            assert get(arrays+other*128+0x70,'I')==0
        for arte,site,end,countreg in ((75,0xc9ba3,0xc9ba8,'rbp'),(82,0xce252,0xce259,'rdi')):
            for uses in (0,331,332,665,998,9999):
                for enabled in (0,1):
                    for native_count in (3,4):
                        setup();rec,actor=capture(2,arte,uses)
                        put(flag,'B',enabled);put(context,'Q',rec)
                        reg('rbx',pool);reg(countreg,native_count)
                        run(site,end,rsp=sp-8)
                        assert u.reg_read(regs[countreg])==native_count+(min(999,uses+1)*3//999 if enabled else 0)

        # Thresholds, every ordinary offensive arte, both mages, capped and
        # non-castable/excluded data; records replace stale allocations.
        for char in (2,3):
            for arte in info['offensive_arte_ids']:
                for uses in (0,23,24,25,49,624,625,9999):
                    setup()
                    rec,actor=capture(char,arte,uses)
                    assert get(rec,'Q')==actor,(char,arte)
                    assert get(rec+8,'H')==arte
                    assert get(rec+10,'H')==min(9999,uses+1)
                    assert get(rec+12,'I')==min(25,(uses+1)//20)
        for arte in range(54,63):
            setup();rec,actor=capture(2,arte,0)
            assert get(rec,'Q')==actor and get(rec+8,'H')==arte
        for arte in list(range(43,54))+list(range(67,70))+list(range(102,112)):
            setup()
            u.mem_write(effects,b'\xff'*16)
            rec,_=capture(2,arte,9999)
            assert bytes(u.mem_read(rec,16))==b'\0'*16, arte
        for char,side,effect,caller in ((0,0,None,0xd554e),(1,0,None,0xd554e),
                                      (2,1,None,0xd554e),(3,0,26,0xd554e),
                                      (2,0,999,0xd554e),(2,0,None,0x115cef)):
            setup();rec,_=capture(char,71,625,side=side,effect=effect,caller=caller)
            assert get(rec,'Q')==0

        # Two casters, overlapping casts and later counter changes: launched
        # projectiles keep their own percentage. Child effects inherit it.
        setup()
        a,meredy=capture(3,73,624)
        put(context,'Q',a);ta=projectile(meredy,5)
        put(context,'Q',0)
        b,keele=capture(2,71,49,slot=1)
        put(context,'Q',b);tb=projectile(keele,6)
        put(meredy+0x6d,'B',75);put(keele+0x6d,'B',54)
        put(live+(3*128+73)*2,'H',0)
        put(context,'Q',a)
        child,_=capture(3,75,0,slot=2,effect=150,caller=0xc0000)
        assert bytes(u.mem_read(child,16))==bytes(u.mem_read(a,16))
        assert get(ta+12,'I')==25 and get(tb+12,'I')==2
        for owner,slot,pct in ((meredy,5,25),(keele,6,2)):
            damage_owner=owner
            for amount in (1,99,100,101,1234,29999,30000,2_000_000_000):
                damage(amount,min(30000,amount*(100+pct)//100),slot=slot)
            put(flag,'B',0);damage(100,100,slot=slot);put(flag,'B',1)
            damage(100,100,caller=0x822cd,slot=slot)
            damage(100,100,caller=0x976a9,slot=slot)
            put(enemies+0x51,'B',0);damage(100,100,slot=slot);put(enemies+0x51,'B',1)
        # Allocation without scope clears an old projectile's bonus, even if
        # the same mage is still present or is casting another spell.
        put(context,'Q',0);projectile(keele,6)
        assert get(tb,'Q')==0
        damage_owner=keele;damage(100,100,slot=6)
        put(context,'Q',a);projectile(keele,6) # mismatched owner
        assert get(tb,'Q')==0

        # Execute each real callback callsite. It must scope only this effect,
        # retain all incoming arguments, restore a prior context and return ABI.
        for kind,site,end,index in (('init',0x1159c7,0x1159d4,1),
                                   ('script',0x1159fc,0x115a01,0),
                                   ('large',0x115a33,0x115a3d,4),
                                   ('small',0x115d1c,0x115d26,6)):
            setup();rec,damage_owner=capture(2,75,624)
            put(context,'Q',effects+0xf0)
            reg('rax',index);reg('rsi',pool)
            reg('rcx',base if kind=='init' else pool);reg('rdx',base)
            before={r:u.reg_read(v) for r,v in regs.items() if r not in ('rax','rcx','rdx','r8','r9','r10','r11')}
            callback_kind='projectile'
            run(site,end,rsp=sp-8)
            assert callbacks==[(rec,pool)],kind
            assert get(context,'Q')==effects+0xf0
            assert get(tags,'Q')==damage_owner and get(tags+12,'I')==25,kind
            assert before=={r:u.reg_read(regs[r]) for r in before},kind
        callback_kind='plain'

        # Real small-effect allocation runs through its CRT memset, our capture,
        # all original script/target setup, and successful cast usage increment.
        for arte in (63,64,65,66,70,75,86):
            setup()
            actor=actors+2*0x248
            put(actor,'Q',actors);put(actor+0x6d,'B',arte)
            put(live+(2*128+arte)*2,'H',99)
            reg('rcx',actor);reg('rdx',get(base+0x551780+arte*8,'B'))
            # Native cast continuation is the stop, but allocation returns +8.
            u.reg_write(UC_X86_REG_RSP,sp)
            put(sp,'Q',base+0xd554e)
            hit=[]
            def halt(emu,address,size,_):
                if address==base+0xd554e:hit.append(1);emu.emu_stop()
            hh=u.hook_add(UC_HOOK_CODE,halt)
            try:u.emu_start(base+0x114980,base+0xd554e,count=10000)
            finally:u.hook_del(hh)
            assert u.reg_read(UC_X86_REG_RIP)==base+0xd554e
            assert u.reg_read(UC_X86_REG_RSP)==sp+8
            assert get(effects,'Q')==actor and get(effects+10,'H')==100
            assert get(pool+8,'Q')==actors, (arte,'target',hex(get(pool+8,'Q')))
            effect_id=get(base+0x551780+arte*8,'B')
            assert get(pool+0x10,'Q')==get(base+0x4e89a0+(effect_id%100)*8,'Q')
            reg('rbx',actor);reg('rax',0);reg('r12',0)
            run(0xd554e,0xd5555,rsp=sp-8)
            assert get(live+(2*128+arte)*2,'H')==100
            cases+=1

        # A large spell is reallocated after loading its resources. The native
        # continuation occurs outside callbacks, with R15 pointing at old+0x3a.
        setup();rec,actor=capture(2,71,624)
        put(context,'Q',0);reg('r15',pool+0x3a)
        loaded,_=capture(2,71,0,slot=1,caller=0x115cef)
        assert bytes(u.mem_read(loaded,16))==bytes(u.mem_read(rec,16))
        put(context,'Q',loaded);projectile(actor,5)
        damage_owner=actor;damage(100,125)

        # Buffs: exact native mask/value and palette; primary native callback,
        # 0/1/2/3 additional living party members; no extra TP or usage debit.
        for arte,bit,palette in ((63,2,4),(64,16,7),(65,4,5),(66,8,6)):
            for uses,extra in ((0,0),(98,0),(99,1),(100,1),(248,1),(249,2),(498,2),(499,3),(9999,3)):
                for enabled in (0,1):
                    setup();rec,actor=capture(2,arte,uses)
                    # The native callback must retain its script so it doesn't
                    # try to destroy the test's effect at the end of the frame.
                    put(pool+0x10,'Q',1);put(pool+0x38,'H',0)
                    put(pool+8,'Q',actors+3*0x248)
                    put(flag,'B',enabled)
                    for c in range(4):
                        put(actors+c*0x248+0x30,'I',0x4000 | (8 if bit!=8 else 2))
                    before_usage=bytes(u.mem_read(live,info['usage']['size']))
                    reg('rcx',pool);reg('rdx',base)
                    reg('rax',get(pool+0x36,'B')-99)
                    run(0x115d1c,0x115d26,rsp=sp-8)
                    expected_extra=extra if enabled else 0
                    for c in range(4):
                        expected=0x4000 | (bit if c==3 or c<expected_extra else (8 if bit!=8 else 2))
                        assert get(actors+c*0x248+0x30,'I')==expected,(arte,uses,enabled,c)
                        assert get(actors+c*0x248+0x34,'h')==10
                    assert bytes(u.mem_read(live,info['usage']['size']))==before_usage
                    auras=[base+0x12ced48+i*0x20 for i in range(8)]
                    assert sum(get(p+0x18,'B')==0x18 for p in auras)==1+expected_extra
                    assert all(get(p+0x19,'B')==palette for p in auras if get(p+0x18,'B'))
                    # Second update cannot re-apply state (or buff a new actor).
                    put(actors+0x30,'I',0x4000)
                    put(pool+0x38,'H',1)
                    reg('rcx',pool);reg('rdx',base);reg('rax',get(pool+0x36,'B')-99)
                    run(0x115d1c,0x115d26,rsp=sp-8)
                    assert get(actors+0x30,'I')==0x4000
            for mode in ('same_buff','dead','inactive','enemy','quickie','full_aura','no_pool','bad_count','zero_count'):
                setup();rec,actor=capture(2,arte,499)
                put(context,'Q',rec);put(pool+8,'Q',actors+3*0x248)
                put(pool+0x38,'H',0)
                if mode=='same_buff':put(actors+0x30,'I',bit)
                elif mode=='dead':put(actors+0x2c,'i',0)
                elif mode=='inactive':put(actors+0x3c,'H',0)
                elif mode=='enemy':put(actors+0x51,'B',1)
                elif mode=='quickie':put(actors+0x4f,'B',11)
                elif mode=='full_aura':
                    for i in range(8):put(base+0x12ced48+i*0x20+0x18,'B',1)
                elif mode=='no_pool':put(base+0x12cecd8,'Q',0)
                elif mode=='bad_count':put(base+0x12cece8,'B',255)
                elif mode=='zero_count':put(base+0x12cece8,'B',0)
                snapshot=bytes(u.mem_read(actors,0x248))
                reg('rcx',pool)
                run('mastery_buff_share')
                if mode not in ('full_aura',):
                    assert bytes(u.mem_read(actors,0x248))==snapshot,mode
                else:
                    assert get(actors+0x30,'I')==bit
                assert get(actors+4*0x248+0x30,'I')==0, 'Quickie receives party buffs'
                # Re-entry at tick zero remains idempotent.
                all_actors=bytes(u.mem_read(actors,0x248*5))
                reg('rcx',pool);run('mastery_buff_share')
                assert bytes(u.mem_read(actors,0x248*5))==all_actors
        # Disable only the chosen character/spell; keep counters and other
        # spells/casters intact. Primary native buffs must still be applied.
        for char in (2,3):
            for selected in (63,64,65,66,71,73):
                for caster in (2,3):
                    for arte in (63,64,65,66,71,73):
                        setup();rec,actor=capture(caster,arte,624)
                        put(preferences+char*32+selected//8,'B',1<<(selected%8))
                        unchanged=bytes(u.mem_read(live,info['usage']['size']))
                        disabled=char==caster and selected==arte
                        if arte>=70:
                            put(context,'Q',rec);projectile(actor)
                            damage_owner=actor;damage(100,100 if disabled else 125)
                        else:
                            bit={63:2,64:16,65:4,66:8}[arte]
                            put(pool+0x10,'Q',1);put(pool+0x38,'H',0)
                            put(pool+8,'Q',actors+3*0x248)
                            reg('rcx',pool);reg('rdx',base)
                            reg('rax',get(pool+0x36,'B')-99)
                            run(0x115d1c,0x115d26,rsp=sp-8)
                            assert get(actors+3*0x248+0x30,'I')&bit
                            assert sum(bool(get(actors+c*0x248+0x30,'I')&bit) for c in range(4))==(1 if disabled else 4)
                        assert bytes(u.mem_read(live,info['usage']['size']))==unchanged
        return cases
    finally:
        u.hook_del(h)
        for addr,payload in saved_tables.items():u.mem_write(addr,payload)
        put(flag,'B',1)
        u.mem_write(state,b'\0'*info['size'])
        u.mem_write(preferences,b'\0'*224)
