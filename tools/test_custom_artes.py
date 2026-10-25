"""Level-one roster and native execution of the new player adaptations."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from custom_test_artes import TEST_ROSTER, MAGE_ROSTER, RECIPES, NAMES, FLAG_OFFSET

def check_custom_artes(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['standalone_teamups'];data=base+m['data_rva'];master=base+0x11ca420
    fx=base+0x12cfca0;state=base+info['state_rva'];stop=data-16
    calls=[];mocks=set();cases=0;particle=actors+0x7000
    from collections import deque
    recent=deque(maxlen=48)
    def trace(_,addr,size,user):
        rv=addr-base
        recent.append(rv)
        if rv not in mocks:return
        if rv==0x114b22:  # Audio-name hash lookup; no effect or caster writes.
            u.reg_write(UC_X86_REG_RIP,base+0x114be6);return
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8,('ABI',hex(rv),hex(rsp))
        value=99 if rv==0x283090 else 0
        if rv==0x7fe70:
            a=u.reg_read(regs['rcx']);motion=u.reg_read(regs['rdx'])
            calls.append(('motion',motion));put(a+0x23a,'B',motion);put(a+0x23c,'B',0);put(a+0x238,'H',0)
        elif rv==0x114980:calls.append(('launch',u.reg_read(regs['rdx'])))
        elif rv==0x2506e0:calls.append(('announcement',u.reg_read(regs['rcx'])))
        elif rv==0xb7460:calls.append(('water',))
        elif rv==0x8f770:
            calls.append(('impact',u.reg_read(regs['rcx']),u.reg_read(regs['rdx']),u.reg_read(regs['r8'])))
        elif rv==0x8b7e0:value=particle
        elif rv==0x11ed60:calls.append(('water_quad',))
        elif rv==m['symbols']['spell_label_texture_initialize']:value=actors+0xc800
        elif rv==0x121b50:
            calls.append(('managed_quad',u.reg_read(regs['rdx']),u.reg_read(regs['r8']),u.reg_read(regs['r9'])))
        elif rv==0x11e6f0:calls.append(('native_quad',))
        elif rv==0x116580:
            calls.append(('projectile',u.reg_read(regs['r8']),u.reg_read(regs['r9'])))
            return # Exercise the real bounded native projectile allocator.
        elif rv==0x116260:
            calls.append(('area',u.reg_read(regs['rcx'])))
            return
        elif rv==0x115ee0:
            calls.append(('release',));put(u.reg_read(regs['rcx']),'Q',0)
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,trace)
    def run(rv,*args):
        nonlocal cases
        for k,v in zip(('rcx','rdx','r8','r9'),args):reg(k,v)
        u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop)
        keep={k:u.reg_read(regs[k]) for k in ('rbx','rsi','rdi','rbp','r12','r13','r14','r15')}
        try:u.emu_start(base+rv,stop,count=200000)
        except Exception as ex:raise AssertionError(('at',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rv),'recent',[hex(x) for x in recent])) from ex
        assert u.reg_read(UC_X86_REG_RIP)==stop,('did not return',hex(rv))
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        assert keep=={k:u.reg_read(regs[k]) for k in keep},('nonvolatile',hex(rv))
        cases+=1;return u.reg_read(regs['rax'])
    def fragment(start,end):
        nonlocal cases
        u.reg_write(UC_X86_REG_RSP,sp-8)
        u.ctl_remove_cache(base+end-16,base+end+16)
        try:u.emu_start(base+start,base+end,count=200000)
        except Exception as ex:raise AssertionError(('fragment',hex(start),hex(u.reg_read(UC_X86_REG_RIP)-base))) from ex
        assert u.reg_read(UC_X86_REG_RIP)==base+end
        assert u.reg_read(UC_X86_REG_RSP)==sp-8
        cases+=1
    def setup(owner=3,aid=136,enabled=1):
        reset();calls.clear();mocks.clear();u.mem_write(master,bytes(0x1000))
        u.mem_write(state+0x5400,bytes(0x210))
        put(data+FLAG_OFFSET,'B',enabled)
        for off in (0x1a41,0x1a42,0x1a63):put(data+off,'B',0)
        put(base+0x12cea60,'Q',master);put(base+0x6449e0,'Q',actors+0xc200)
        put(base+0x12cea70,'Q',base+info['metadata']);put(base+0x12cea78,'Q',base+info['launch'])
        run(info['initialize'])
        a=actors+owner*0x248
        put(a+0x34,'H',200);put(a+0x6d,'B',aid);put(a+0x6e,'B',7)
        put(a+0x8e,'H',124);put(a+0x52,'B',0);put(a+0x64,'B',0);put(a+0x65,'B',0)
        put(a+0xf0,'Q',actors+0x9000);put(a,'Q',actors+0x4000);put(a+0x53,'b',1)
        put(a+0xe8,'Q',actors+0x8000);put(actors+0x802f,'B',1)
        return a
    try:
        # The resource loader may finish after the actor's selected spell has
        # changed. Test the actual capture detour and its continuation ABI.
        for owner in (2,3):
            for aid,effect in ((112,24),(136,52),(137,19),(139,60),(140,57),(144,24),(145,24)):
                a=setup(owner,aid);tags=base+info['identity']['tags']
                for slot,parent,selected in ((0,False,aid),(1,True,70)):
                    put(a+0x6d,'B',selected)
                    reg('r14',fx+slot*0x120);reg('r12',a);reg('rbp',effect)
                    reg('rdi',0);reg('rax',1);reg('r15',fx+0x3a)
                    put(fx+slot*0x120,'Q',a)
                    put(sp-8+0x58,'Q',base+(0x115cef if parent else 0x11304e))
                    fragment(0x114a4f,0x114a57)
                    assert get(tags+slot*16,'Q')==a and get(tags+slot*16+8,'I')==aid,(owner,aid,'identity capture',slot)
                    assert run(info['identity']['lookup'],fx+slot*0x120)==aid
        # Reusing a slot for an enemy clears player identity, including an
        # asynchronous continuation and a colliding arte/character byte.
        for owner in (2,3):
            for aid,effect in ((112,24),(136,52),(137,19),(139,60),(140,57),(141,63),(142,67),(143,16),(144,24),(145,24)):
                for parent in (False,True):
                    a=setup(owner,aid);tags=base+info['identity']['tags']
                    put(a+0x51,'B',1)
                    for slot in (0,1):
                        put(tags+slot*16,'QII',a,aid,0)
                        put(fx+slot*0x120,'Q',a)
                    reg('r14',fx+0x120);reg('r12',a);reg('rbp',effect)
                    reg('rdi',0);reg('rax',1);reg('r15',fx+0x3a)
                    put(sp-8+0x58,'Q',base+(0x115cef if parent else 0x11304e))
                    fragment(0x114a4f,0x114a57)
                    assert bytes(u.mem_read(tags+16,16))==bytes(16)
                    assert run(info['identity']['lookup'],fx+0x120)==0
        # Approved spells require the actual spirit in this mage's cage in
        # both editions, even when an old test INI/save contains their IDs.
        prototype_ids={113,136,139,140,141,142,143,144,145}
        for aid,spirit,minimum in ((112,5,5),(137,2,10)):
            for owner in (2,3):
                for cage in (0,3,4):
                    for level in (0,minimum-1,minimum,30):
                        for enabled in (0,1):
                            a=setup(owner,aid,enabled)
                            put(master+0xbb8+spirit*8,'BB',cage,level)
                            # Deliberately retain an old learned test entry.
                            put(master+0x7a+owner*0xd0,'3B',aid,113,136)
                            expected=int(cage==owner+1 and level>=minimum)
                            before=bytes(u.mem_read(master,0x1000))
                            assert run(info['unlocked'],owner,aid,master)==expected,(aid,owner,cage,level,enabled)
                            run(m['fringe']['refresh'],master)
                            rows=bytes(u.mem_read(base+m['fringe']['state_rva']+owner*0xd0,128))
                            assert (aid in rows)==bool(expected),('approved list',aid,rows)
                            assert run(m['symbols']['artesphere_learned'],owner,aid)==expected
                            if not MAGE_ROSTER:
                                assert not (set(rows)&prototype_ids),('release leaked test spell',rows)
                                for test_id in prototype_ids:
                                    assert run(info['unlocked'],owner,test_id,master)==0
                                    assert run(m['symbols']['artesphere_learned'],owner,test_id)==0
                            assert bytes(u.mem_read(master,0x1000))==before
                            mocks.update({0x283090,0x712e0,0x8d520,0x114980,0x114dd0,0x1b5ca0,0x2506e0,0x7fe70})
                            put(a+0x8c,'H',0)
                            run(0x112d10,a,aid)
                            assert bool(get(a+0x8c,'H'))==bool(expected),('approved admission',aid,expected)
        # Native Spark Wave initialization remains intact for enemies;
        # only the player instance receives the private damage/script pair.
        for owner in (2,3):
            for enemy in (False,True):
                a=setup(owner,112);put(a+0x51,'B',int(enemy));put(fx,'Q',a)
                if not enemy:put(base+info['identity']['tags'],'QII',a,112,0)
                run(info['spirit_magic_runtime']['native_initialize'],fx)
                spark=info['approved_spark']
                assert get(fx+0x10,'Q')==base+(0x57dbf0 if enemy else spark['script'])
                assert get(fx+0x78,'Q')==base+(0x57d968 if enemy else spark['impact'])
                powers=[]
                for i in range(35):
                    at=get(fx+0x10,'Q')+i*8
                    if get(at+2,'h')==-7:
                        powers.append(get(get(fx+0x78,'Q')+22*get(at+6,'h')+18,'H'))
                assert len(powers)==6 and sum(powers)==(600 if enemy else 1400),powers
        # Integration: admit an arte with no pre-seeded selected ID, allocate
        # its real native container and dispatch the actual native table entry.
        # This catches initialization/event ordering that direct callback tests
        # cannot cover. Relocate original table pointers, not expected handlers.
        import struct
        from build_combat_patch import BACKUP, pefile
        original=pefile.PE(str(BACKUP));original_base=original.OPTIONAL_HEADER.ImageBase
        # Scripts, impact descriptors and casting templates shared by enemies
        # remain byte-for-byte native in the staged DLL, before pointer relocation.
        from extra_test_magic import SPELLS
        from build_combat_patch import OUT
        patched=pefile.PE(str(OUT/'GameNative.dll'))
        native_ranges=[(row[8],row[9]) for row in SPELLS]+[(row[10],44) for row in SPELLS]
        native_ranges += [(0x57d968,22),(0x57dbf0,280),(0x590db0,0x58),(0x592f38,0x4a),(0x591a68,0x58),
                          (0x592bc0,0x4a),(0x58ff54,0x6a)]
        for address,length in native_ranges:
            assert patched.get_data(address,length)==original.get_data(address,length),('shared native data modified',hex(address))
        for table,n in ((0x4e9690,78),(0x4e89a0,78),(0x4e9420,78),(0x4e9900,78),(0x4e9b70,78)):
            for ix in range(n):
                value=struct.unpack('<Q',original.get_data(table+ix*8,8))[0]
                if original_base<=value<original_base+original.OPTIONAL_HEADER.SizeOfImage:
                    put(base+table+ix*8,'Q',base+value-original_base)
        # The OS relocates original input-sequence pointers before our table
        # initializer runs. Virtual entries must copy those live pointers.
        for ix in range(126):
            value=struct.unpack('<Q',original.get_data(0x562a50+ix*24+16,8))[0]
            if original_base<=value<original_base+original.OPTIONAL_HEADER.SizeOfImage:
                put(base+0x562a50+ix*24+16,'Q',base+value-original_base)
        put(state+0x1ff0,'B',0)
        setup()
        for row in info['recipes']:
            aid,template=row['id'],row['physical']
            expected=get(base+0x562a50+template*24+16,'Q')
            assert get(base+info['metadata']+aid*24+16,'Q')==expected,('ASLR input sequence',aid)
            if expected:
                a=setup(2,aid);put(a+0xba,'B',0)
                reg('rcx',a);reg('rbx',a);reg('r9',actors+0x8000)
                fragment(0xd52e4,0xd5316)
                assert u.reg_read(regs['rdi'])==get(expected,'H'),('Keele casting input',aid)
        # Admission -> allocation -> initializer. Never seed the private
        # identity or script: these must survive the real caller chain.
        for owner in (2,3):
            for aid in (136,137,139,140,141,142,143,144,145):
                a=setup(owner,aid)
                mocks.update({0x71600,0x1b5ca0,0x1b6180,0x1b4e30,0x75c40,0x259a90,0x259c10,0x114b22})
                effect=get(base+info['launch']+aid*8,'B')
                run(0x114980,a,effect)
                assert get(fx,'Q')==a
                assert run(info['identity']['lookup'],fx)==aid,('allocated identity',owner,aid)
                put(fx+0x3a,'H',1)  # Only the external resource IO is completed by the fixture.
                callback=struct.unpack('<Q',original.get_data(0x4e9420+effect*8,8))[0]-original_base
                run(callback,fx)
                wanted={136:state+0x3300,137:state+0x3360,139:state+0x5100}
                if aid not in wanted:
                    wanted[aid]=base+next(r for r in info['extra_magic']+info['spirit_magic'] if r['id']==aid)['script']
                assert get(fx+0x10,'Q')==wanted[aid],('allocated script',owner,aid,hex(get(fx+0x10,'Q')))
        # Both endpoints of the background lightning follow the target zone.
        # Native enemy Night retains its original fixed origin and registers.
        for private in (False,True):
            for x in (-6400,0,4800):
                setup(3,142)
                night=next(r for r in info['extra_magic'] if r['id']==142)
                put(fx+0x10,'Q',base+(night['script'] if private else 0x58ceb0))
                put(fx+0x20,'h',x)
                for site,end in ((0xc16df,0xc16e4),(0xc1748,0xc174e)):
                    reg('rsi',fx);reg('r8',actors+0x7000);reg('rdx',0x12345678);reg('rax',0xabcdef)
                    fragment(site,end)
                    expected=x if private else 0xac0
                    if site==0xc16df:
                        assert u.reg_read(regs['rax'])==expected&0xffffffff
                    else:
                        assert get(actors+0x7000,'h')==expected
                        assert u.reg_read(regs['rax'])==0xabcdef
                    assert u.reg_read(regs['rdx'])==0x12345678
        # Suspended prototypes cannot consume TP, enter a physical action or
        # allocate effects, even with the level-one test option enabled.
        suspended={130,131,132,133,134,135,138}
        for aid,owner in ((130,1),(131,1),(132,1),(133,1),(134,0),(135,0),(138,1)):
            a=setup(owner,aid);put(a+0x6d,'B',0);put(a+0x8e,'H',0)
            mocks.update({0x712e0,0x8d520,0x114dd0,0x1b5ca0,0x2506e0,0x7fe70})
            before=bytes(u.mem_read(a,0x248))
            run(0x112d10,a,aid)
            assert not calls and get(fx,'Q')==0,('suspended admission',aid,calls)
            assert bytes(u.mem_read(a,0x248))==before
        # No changes to native learned entries, levels or counters at all.
        allids=set(sum((list(v) for v in TEST_ROSTER.values()),[]))
        for enabled in (0,1):
            setup(enabled=enabled)
            before=bytes(u.mem_read(master,0x1000))
            for char in range(7):
                for aid in sorted(allids|suspended|{0,74,125,140,255}):
                    assert run(info['unlocked'],char,aid,master)==int(enabled and aid in TEST_ROSTER.get(char,())),(char,aid,enabled)
            assert bytes(u.mem_read(master,0x1000))==before
            run(m['fringe']['refresh'],master)
            for char,ids in TEST_ROSTER.items():
                rows=bytes(u.mem_read(base+m['fringe']['state_rva']+char*0xd0,128)).rstrip(b'\0')
                assert not rows.count(0),('holes',char,rows)
                assert not (set(rows)&suspended), ('suspended rows',char,rows)
                assert set(rows)&allids==(set(ids) if enabled else set()),(char,enabled,rows)
                for aid in ids:assert run(m['symbols']['artesphere_learned'],char,aid)==enabled
            assert bytes(u.mem_read(master,0x1000))==before
        for aid,owner,template,_,effect,msg,tp,name in RECIPES:
            for enabled in (0,1):
                for enough in (False,True):
                    a=setup(owner,aid,enabled);put(a+0x34,'H',tp if enough else tp-1)
                    mocks.update({0x283090,0x712e0,0x8d520,0x114980,0x114dd0,0x1b5ca0,0x2506e0,0x7fe70})
                    before=bytes(u.mem_read(master,0x1000));run(0x112d10,a,aid)
                    assert bytes(u.mem_read(master,0x1000))==before
                    # Physical admission pays immediately; spells begin casting.
                    if owner in (0,1):
                        assert not calls,(aid,enabled,enough,calls)
                        assert get(a+0x34,'H')==tp-int(not enough)
                    elif enabled and enough and aid in MAGE_ROSTER:
                        assert get(a+0x6d,'B')==aid
                        assert get(a+0x8c,'H')>0,('cast timer',aid)
            # Sidecar counter slots must not touch Auto bitfield or native save.
            a=setup(owner,aid);usage=base+info['usage_rva'];u.mem_write(usage,bytes(1792))
            put(usage+8,'H',0xa55a);run(m['symbols']['arte_usage_increment'],owner,aid)
            assert get(usage+8,'H')==0xa55a
            assert get(usage+(owner*128+aid-122)*2,'H')==1
        for aid in MAGE_ROSTER:
            for owner in (2,3):
                for language in (1,3):
                    a=setup(owner,aid);put(base+0x11c9ce8,'B',language)
                    mocks.update({0x283090,0x712e0,0x8d520,0x114980,0x114dd0,0x1b5ca0,0x2506e0,0x7fe70})
                    run(0x112d10,a,aid)
                    assert get(a+0x8c,'H')>0
                    effect=get(base+info['launch']+aid*8,'B');assert get(a+0x8e,'H')==effect
                    calls.clear();put(a+0x8c,'H',0)
                    reg('rbx',a);reg('r12',0);reg('r15',1);reg('r14',base)
                    fragment(0xd5430,0xd571d)
                    assert ('launch',effect) in calls,(owner,aid,calls)
                    if aid>=136:
                        row=next(r for r in info['custom_artes'] if r['id']==aid)
                        assert ('announcement',base+row['names'][language==1]) in calls,(owner,aid,calls)
            if aid>=126:
                setup(2,aid);usage=base+info['usage_rva'];u.mem_write(usage,bytes(1792))
                run(m['symbols']['arte_usage_increment'],2,aid)
                run(m['symbols']['arte_usage_increment'],3,aid)
                run(m['symbols']['arte_usage_increment'],3,aid)
                assert get(usage+(2*128+aid-122)*2,'H')==1
                assert get(usage+(3*128+aid-122)*2,'H')==2
                # IDs 142..145 use bits above the old 16-bit preference word.
                for expected in (1<<(aid-126),0):
                    reg('r8',aid);fragment(0x22b67b,0x22b6c9)
                    assert get(usage+8,'I')==expected
        # Voice selection must preserve native side flags and enemy voices.
        for owner in (2,3):
            for side in (0,1):
                for aid in (70,)+MAGE_ROSTER:
                    a=setup(owner,aid);put(a+0x51,'B',side)
                    reg('rbx',a);reg('rbp',aid)
                    fragment(0x113084,0x113097)
                    expected=(0x19c if owner==3 else 273) if side==0 and aid!=70 else get(base+info['launch']+aid*8+4,'H')
                    assert u.reg_read(regs['rdx'])==expected,(owner,side,aid)
                    assert bool(u.reg_read(UC_X86_REG_EFLAGS)&64)==(side==1)
        for aid,element in ((136,1),(137,3),(138,0),(139,8)):
            setup(3,aid)
            assert get(base+info['launch']+aid*8+2,'B')==element
        for aid in (134,135):
            a=setup(0,aid);row=next(r for r in info['custom_artes'] if r['id']==aid)
            put(fx,'Q',a);put(fx+0x36,'B',124);mocks.update({0x7fe70,0x115ee0})
            for tick in range(180):
                put(fx+0x38,'H',tick);run(0xcaf30,fx)
                if not get(fx,'Q'):break
                # The engine executes its event VM as well as the actor script.
                # No private flags may occupy its ten scheduled-event records.
                put(fx+0x10,'Q',state+0x3300);put(fx+0x35,'B',0)
                run(0x114f50,fx)
                assert base+row['script']<=get(a+0x230,'Q')<base+row['script']+0xc0
                run(0x708e0,a)
                if get(a+0x230,'Q'):put(a+0x23c,'B',get(a+0x23c,'B')+1)
            else:raise AssertionError(('Reid script did not finish',aid))
            assert [c[1] for c in calls if c[0]=='motion']==({134:[21,23,21,23],135:[21,23]}[aid])
            assert get(a+0x230,'Q')==0
        # Run native init and event VM, including native resource binding.
        a=setup();put(fx,'Q',a);put(fx+0x3e,'H',77)
        before=bytes(u.mem_read(a,0x248));run(0xb7330,fx)
        assert get(fx+0x10,'Q')==state+0x3300
        assert bytes(u.mem_read(a,0x248))==before
        for phase in (0,32,191,192,512):
            put(fx+0x35,'B',0);put(fx+0x38,'H',phase);put(fx+0x10,'Q',state+0x3300)
            assert run(0x114f50,fx)==int(phase==512)
        for ready in (0,1,2):
            for frozen in (0,1):
                for phase in (0,31,32,33,64,96,128,160,161,191,192):
                    a=setup();put(fx,'Q',a);put(fx+0x30,'b',1);put(fx+0x38,'H',phase)
                    put(fx+0x10,'Q',state+0x3300);put(fx+0x3a,'H',ready);put(base+0x12ceb74,'B',frozen)
                    before=bytes(u.mem_read(a,0x248));mocks.update({0xb7460,0x116260,0x115ee0})
                    run(0xb7c90,fx,ready)
                    active=ready!=2 and not frozen
                    expected=[('water',)] if ready!=2 and 0<phase<191 else []
                    if active:
                        if phase>=192:expected=[('release',)]
                        if 32<=phase<=160 and phase%32==0:expected.append(('area',base+0x12cf988))
                    assert calls==expected,(ready,frozen,phase,calls)
                    assert bytes(u.mem_read(a,0x248))==before
        # Actual native dispatcher callsite (EDX is image base, not a ready flag).
        for aid,effect in ((136,52),(137,19)):
            a=setup(3,aid);put(fx,'Q',a);put(fx+0x36,'B',effect);put(fx+0x40,'H',effect)
            # Emulate the loader's relocation of the original absolute table.
            put(base+0x4e9900+effect*8,'Q',base+(0xb7c90 if aid==136 else 0x9d630))
            run(0xb7330 if aid==136 else 0x9d590,fx)
            put(fx+0x38,'H',32 if aid==136 else 36)
            mocks.update({0xb7460,0x116260,0x8b7e0,0x283090,0x116580})
            reg('rdi',1);reg('r15',fx+0x3a);fragment(0x115a1c,0x115a3d)
            assert any(c[0]==('area' if aid==136 else 'projectile') for c in calls),(aid,calls)
            calls.clear();put(base+0x12ceb74,'B',0x20)
            reg('rdi',0);reg('r15',fx+0x3a);fragment(0x115a1c,0x115a3d)
            assert calls==([('water',)] if aid==136 else []),('paused frame produced an impact',aid,calls)
            assert get(state+0x5600,'Q')==0
        # A delayed lifetime sentinel must never re-enter Chat's full arte.
        a=setup(3,136);put(fx,'Q',a);put(fx+0x38,'H',512)
        put(state+0x5400,'Q',a);put(state+0x5408,'I',136)
        put(fx+0x10,'Q',0);put(fx+0x3a,'H',1);mocks.add(0x115ee0)
        before=bytes(u.mem_read(a,0x248));run(0xb7c90,fx,base)
        assert calls==[('release',)] and bytes(u.mem_read(a,0x248))==before
        for owned in (False,True):
            a=setup(3,137 if owned else 75);put(fx,'Q',a);put(fx+0x3e,'H',88)
            run(0x9d590,fx)
            assert (get(fx+0x10,'Q')==state+0x3360)==owned
            assert get(fx+0x78,'Q')!=state+0x3340
            for occupied in (0,59,60):
                for ready in (0,1,2):
                    calls.clear();pool=base+0x12cee48
                    u.mem_write(pool,bytes(60*48));put(base+0x12ced28,'Q',actors+0x7400)
                    for i in range(occupied):put(pool+i*48+32,'B',5)
                    old=bytes(u.mem_read(pool,occupied*48));put(base+0x12cec20,'Q',actors+0x7600)
                    put(fx+0x38,'H',36);put(fx+0x3a,'H',ready);mocks.update({0x8b7e0,0x283090,0x116580})
                    run(0x9d630,fx,base)
                    assert get(base+0x12ced28,'Q')==actors+0x7400
                    assert bytes(u.mem_read(pool,occupied*48))==old
                    if ready!=2 or not owned:
                        impact=state+0x3340 if owned else actors+0x7400
                        assert calls==[('projectile',a,impact)],calls
                        if occupied<60:assert get(pool+occupied*48+24,'Q')==impact
                    else:assert calls==[]
        # Consecutive native event/frame/release cycles, with the real particle
        # allocator. Only sound, GPU submission and target damage are stubs.
        pool_area=0x66000000;u.mem_map(pool_area,0x10000)
        from test_fear_alignment import check_fear_alignment
        check_fear_alignment(u,base,m,actors,pool_area,setup,run,put,get,mocks)
        for aid,effect,init,frame,end in ((136,52,0xb7330,0xb7c90,192),(137,19,0x9d590,0x9d630,161),(139,60,0xbd7a0,0xbd8b0,48)):
            a=setup(3,aid)
            u.mem_write(pool_area,bytes(0x10000))
            put(base+0x12cecf0,'Q',pool_area);put(base+0x12cec20,'Q',pool_area+0xf000)
            put(fx,'Q',a);put(fx+8,'Q',actors+0x4000)
            put(fx+0x36,'B',effect);put(fx+0x3e,'H',effect);put(fx+0x30,'b',1)
            put(a+0x8e,'H',effect);put(a+0x77,'B',1);put(a+0x23a,'B',7)
            put(base+m['spell_mastery']['current_roots_rva']+3*8,'Q',fx)
            put(fx+0x33,'B',1);put(fx+0x3a,'H',1);put(fx+0x40,'H',effect)
            put(base+0x4e9420+effect*8,'Q',base+init)
            put(base+0x4e9900+effect*8,'Q',base+frame)
            put(base+0x12d0ea0,'Q',fx)
            banks=None
            mocks.update({0x11cb80,0x1a07d0,0x11e4d0,0x11ed60,0x279670,0x8f770,0x283090,0x116580,0x116260})
            for tick in range(end+1):
                assert get(fx+0x38,'H')==tick,('native clock',aid,tick)
                # The dispatcher admits this effect during a visual transition,
                # then changes the shared byte from 0x30 to 0x20 before calling
                # its frame. A nonzero byte does not mean this effect is paused.
                put(fx+0x32,'B',1);put(base+0x12ceb74,'B',0x30)
                run(0x1158a0)
                if banks is None:banks=bytes(u.mem_read(fx+0x48,0x38))
                if tick<end:
                    assert get(fx,'Q')==a,(aid,tick,'premature release')
                    assert bytes(u.mem_read(fx+0x48,0x38))==banks
            assert get(fx,'Q')==0,(aid,'effect not released')
            assert get(a+0x77,'B')==0 and get(a+0x23d,'B')==255,(aid,'casting motion not released')
            if aid==136:
                assert sum(c[0]=='area' for c in calls)==5
                assert any(c[0]=='water_quad' for c in calls)
            elif aid==137:
                assert any(c[0]=='projectile' for c in calls)
                assert any(get(pool_area+0x19c8+i*74+8,'B') for i in range(100))
            else:
                assert sum(c[0]=='impact' for c in calls)==1
                assert not get(pool_area+0x19c8+8,'B'),'dark blade survived effect release'
        from test_hyades_finality import check_prototypes
        check_prototypes(u,base,m,actors,pool_area,setup,run,fragment,put,get,reg,regs,calls,mocks)
        from test_extra_magic import check_extra_magic
        check_extra_magic(u,base,m,actors,pool_area,setup,run,put,get,calls,mocks)
        u.mem_unmap(pool_area,0x10000)
    finally:u.hook_del(h)
    return cases
