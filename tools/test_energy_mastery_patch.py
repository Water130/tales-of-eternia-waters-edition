"""Execute Energy hooks, native heal/cap/number queue and field-menu casts."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RIP, UC_X86_REG_RSP


def check_energy(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['energy_mastery'];sym=m['symbols'];flag=base+info['flag_rva']
    choices=base+m['artesphere']['usage']['preferences']['live_rva']
    usage=base+m['artesphere']['usage']['live_rva'];master=base+0x11ca420
    effect=actors+0x6000;stats=actors+0x7000;stop=base+m['code_rva']-16
    count=0
    nonvolatile=('rbx','rbp','rsi','rdi','r12','r13','r14','r15')
    def boundary(_,address,length,user):
        # Rendering/audio and animation assets only; HP/state/cost/counters
        # execute the actual game and injected instructions.
        if address not in {base+a for a in (0x1b5ca0,0x1b5a30,0x7fe70,0x8b9d0,0x283090)}:return
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('alignment',hex(address-base),hex(rsp))
        reg('rax',0)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,boundary)
    def setup(level=30,disabled=0,on=1):
        reset();u.mem_write(choices,b'\0'*224);u.mem_write(usage,b'\0'*1792)
        u.mem_write(master,b'\0'*0x1070)
        put(flag,'B',on);put(choices+48,'B',disabled)
        put(base+0x11cb038,'B',level);put(base+0x11cb040,'B',level)
        put(base+0x11cad10,'6H',1,2,3,4,5,6)
        put(base+0x12cece8,'B',6);put(base+0x865a08,'I',0)
        put(base+0x12d0fcc,'B',0);put(base+0x12d0ef7,'B',6)
        put(base+0x6449e0,'Q',actors+0x8000)
        for i in range(7):
            a=actors+i*0x248;s=stats+i*0x100;p=master+i*0xd0
            put(a+0x3c,'H',1);put(a+0x4f,'BB',i,0);put(a+0x51,'B',0)
            put(a+0xe8,'Q',s);put(a+0x2c,'i',500);put(a+0x34,'h',100)
            put(s+0x18,'ih',2000,200)
            put(p+0x36,'HH',2000,500);put(p+0x3c,'HH',200,100)
        put(effect,'QQ',actors+0x248,actors)
        put(effect+0x10,'Q',1);put(effect+0x38,'H',32)
    def run(entry,ends=None,aligned=False):
        nonlocal count
        count+=1;rsp=sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        targets={base+x for x in ends} if ends else {stop};reached=[]
        saved={r:u.reg_read(regs[r]) for r in nonvolatile}
        def halt(_,address,length,user):
            if address in targets:reached.append(address);u.emu_stop()
        hh=u.hook_add(UC_HOOK_CODE,halt)
        try:
            u.emu_start(base+(sym[entry] if isinstance(entry,str) else entry),stop+1,count=200000)
            assert reached,(entry,'did not return',hex(u.reg_read(UC_X86_REG_RIP)-base))
            assert saved=={r:u.reg_read(regs[r]) for r in nonvolatile},('ABI',entry)
            assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if ends else 8),('stack',entry)
        except Exception as ex:
            raise AssertionError((entry,hex(u.reg_read(UC_X86_REG_RIP)-base),
                                  {r:hex(u.reg_read(regs[r])) for r in regs})) from ex
        finally:u.hook_del(hh)
    def targets(mode,values):
        for i,(hp,maximum,alive) in enumerate(values):
            a=actors+i*0x248;p=master+i*0xd0
            put(a+0x2c,'i',hp);put(stats+i*0x100+0x18,'i',maximum)
            put(a+0x3c,'H',1 if alive else 2)
            put(p+0x36,'HH',maximum,hp);put(p+0x5b,'B',0 if alive else 8)
    def hp(mode,i):return get(master+i*0xd0+0x38,'H') if mode else get(actors+i*0x248+0x2c,'i')
    def cast(mode,arte):
        if mode:
            reg('rcx',1);reg('rdx',0);reg('r8',arte);run(0x224530)
        else:
            reg('rcx',effect);run({39:0xcbe00,40:0xcce20,41:0xccb40}[arte])
    try:
        # Every threshold combination, independently disabled, including
        # mismatched Punch/Kick and corrupt out-of-range levels.
        for punch in (0,9,10,14,15,19,20,24,25,29,30,255):
            for kick in (9,15,20,25,30,255):
                for disabled in (0,1,2,4,8,16,32,63):
                    setup(punch,disabled);put(base+0x11cb040,'B',kick)
                    run('energy_enabled_faculties')
                    level=min(punch,kick)
                    expected=sum(1<<i for i,l in enumerate((10,20,30,15,25,30))
                                 if level<=30 and level>=l and not disabled&(1<<i))
                    assert u.reg_read(regs['rax'])==expected,(punch,kick,disabled)
        # Same actual target choice and nominal amounts in menu and battle.
        # Primary almost full, second and third differ in max HP and ratio.
        values=[(1950,2000,True),(500,2000,True),(40,1000,True),
                (200,4000,True),(0,2000,False),(2000,2000,True)]
        for mode in (0,1):
            for level in (9,10,14,15,19,20,24,25,29,30):
                for disabled in (0,1,2,4,6,63):
                    setup(level,disabled);targets(mode,values)
                    cast(mode,39)
                    main=800 if level>=10 and not disabled&1 else 600
                    second=level>=20 and not disabled&2
                    third=level>=30 and not disabled&4
                    expected=[2000,500,40,200,0,2000]
                    if second:expected[2]+=main//2
                    if third:expected[3 if second else 2]+=main//4
                    assert [hp(mode,i) for i in range(6)]==expected,(mode,level,disabled,expected,[hp(mode,i) for i in range(6)])
                    assert get(usage+(128+39)*2,'H')==int(bool(mode)), 'extra heal counted as a cast'
                    if mode:assert get(master+0xd0+0x3e,'H')==88,'Healer charged more than 12 TP'
                    else:
                        assert get(actors+0x248+0x34,'h')==100
                        n=1+int(second)+int(third)
                        assert get(base+0x865a08,'I')==n, 'missing/duplicate native heal numbers'
                        queue=base+0x8d69e+get(base+0x8d69a,'i')
                        assert [get(queue+i*8+4,'H') for i in range(n)]==[main]+([main//2] if second else [])+([main//4] if third else [])
            # Global off retains native amount and exactly one primary target.
            setup(30,on=0);targets(mode,values);cast(mode,39)
            assert [hp(mode,i) for i in range(6)]==[2000,500,40,200,0,2000]
            # Multiple injured targets near max: each gain caps independently.
            setup();targets(mode,[(900,1000,True),(990,1000,True),(995,1000,True),
                                 (1000,1000,True),(0,1000,False),(1000,1000,True)])
            cast(mode,39);assert [hp(mode,i) for i in range(6)]==[1000,1000,1000,1000,0,1000]
            # Detoxify keeps rare flags/KO; level 25 matches native Recover.
            for level in (14,15,24,25,30):
                for disabled in (0,8,16,24,63):
                    setup(level,disabled)
                    if mode:put(master+0x5b,'B',0xf7)
                    else:put(actors+0x30,'I',0xefffffff)
                    cast(mode,40)
                    heal=level>=15 and not disabled&8
                    purify=level>=25 and not disabled&16
                    assert hp(mode,0)==500+(500 if heal else 0),(mode,level,disabled)
                    if mode:
                        assert get(master+0x5b,'B')==0xf7 & (0xe8 if purify else 0xfa)
                        assert get(master+0xd0+0x3e,'H')==96
                    else:
                        want=0xefffffff & (0xfdff99fe if purify else 0xfffffbfe)
                        assert get(actors+0x30,'I')==want
            for level in (29,30):
                for disabled in (0,32):
                    setup(level,disabled)
                    put(actors+0x3c,'H',2);put(actors+0x2c,'i',0)
                    put(master+0x5b,'B',8);put(master+0x38,'H',0)
                    cast(mode,41)
                    assert hp(mode,0)==(700 if level==30 and not disabled else 400),(mode,level,disabled,hp(mode,0))
                    if mode:assert get(master+0xd0+0x3e,'H')==50 and get(master+0x5b,'B')&8==0
                    else:assert get(actors+0x3c,'H')==1
        # Owner guards: enemy Farah and other characters keep native Healer.
        for character,side in ((0,0),(2,0),(3,0),(1,1)):
            setup();put(actors+0x248+0x4f,'B',character);put(actors+0x248+0x51,'B',side)
            cast(0,39);assert hp(0,0)==1100 and hp(0,1)==500
        # Real menu target eligibility: injured with no ailment, extended
        # ailment, KO, full health, global and per-faculty toggles.
        for level in (14,15,24,25,30):
            for disabled in (0,8,16,24):
                for on in (0,1):
                    for status in (0,1,2,4,8,16,32,128):
                        for current in (500,2000):
                            setup(level,disabled,on);put(master+0x5b,'B',status);put(master+0x38,'H',current)
                            reg('rcx',0);reg('rdx',40);run(0x224400)
                            want=not status&8 and (bool(status&5) or (on and level>=25 and not disabled&16 and bool(status&0x17))
                                 or (on and level>=15 and not disabled&8 and current<2000))
                            assert bool(u.reg_read(regs['rax']))==bool(want),(level,disabled,on,status,current)
        # Companion and enemy objects must not be secondary allies.
        setup();put(actors+2*0x248+0x4f,'B',11);put(actors+3*0x248+0x51,'B',1)
        put(actors+4*0x248+0x3c,'H',2);put(actors+5*0x248+0x2c,'i',0)
        cast(0,39);assert [hp(0,i) for i in range(6)]==[1300,900,500,500,500,0]
        # Exact percentage ordering even where integer percentage would tie.
        setup();targets(0,[(500,2000,True),(1001,10000,True),(1000,9999,True),
                           (0,1000,False),(1000,1000,True),(1000,1000,True)])
        reg('rcx',actors);reg('rdx',0);run('energy_secondary_targets')
        assert u.reg_read(regs['rax'])==actors+2*0x248 and u.reg_read(regs['rdx'])==actors+0x248
    finally:u.hook_del(h)
    return count
