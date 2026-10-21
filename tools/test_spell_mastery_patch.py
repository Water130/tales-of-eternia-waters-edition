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
    live = base+info['usage']['live_rva']
    preferences = base+info['usage']['preferences']['live_rva']
    flag = base+m['data_rva']+0x1a00+info['option_flag']
    pool, projectiles = base+0x12cfca0, base+0x12cee48
    sentinel = base+m['data_rva']-16
    stub_callback = actors+0xf000
    callback_kind = 'plain'
    callbacks = []
    raw_damage = None
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
        if a == 0x2a4880:
            dest, val, n = [u.reg_read(regs[r]) for r in ('rcx','rdx','r8')]
            u.mem_write(dest,bytes([val&255])*n)
            ret(dest)
        elif a == 0x114640:  # Native buff sound only.
            ret()
        elif address == stub_callback or a == 0x114f50:
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
        put(sp+0x58,'Q',base+caller)
        before={r:u.reg_read(v) for r,v in regs.items() if r!='rax'}
        u.reg_write(UC_X86_REG_EFLAGS,0x246)
        run(0x114a45,0x114a4f)
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

    def damage(amount, expected, caller=0x1164e3, slot=5):
        nonlocal raw_damage
        raw_damage=amount
        put(enemies+0x2c,'i',100000)
        put(base+0x865a08,'I',0)  # native damage ring write cursor
        reg('rcx',damage_owner);reg('rdx',enemies)
        reg('r9',impact);reg('rsi',projectiles+slot*0x30)
        put(impact,'B',0x80)
        run(0x8e910,0x8f0a1,call_return=caller)
        assert get(enemies+0x2c,'i')==100000-expected,(amount,expected,get(enemies+0x2c,'i'))
        assert get(base+0x12d0f46,'h')==expected, 'display does not match HP'
        raw_damage=None

    try:
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
                    assert get(rec+12,'I')==min(25,(uses+1)//25)
        for arte in list(range(43,63))+list(range(67,70))+list(range(102,112)):
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
