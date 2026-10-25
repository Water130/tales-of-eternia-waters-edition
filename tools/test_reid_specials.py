"""Execute Reid's actual patched eligibility, input, dispatch and reset code."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_reid_specials(u,base,m,actors,stats,sp,reset,put,get,reg,regs):
    info=m['reid_specials'];counts=base+info['counters_rva'];flag=base+info['flag_rva']
    stop=base+m['data_rva']-16;cases=0;learned=1;result=0;calls=[]
    def setup(on=1):
        reset();put(flag,'B',on);put(counts,'I',0)
        put(stats+0x18,'I',1000);put(stats+0x1c,'H',999)
        put(base+0x12d0f02,'B',4);put(base+0x12d0fd2,'B',0)
    def ret(value):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('ABI',hex(u.reg_read(UC_X86_REG_RIP)),hex(rsp))
        reg('rax',value)
        for key in ('rcx','rdx','r8','r9','r10','r11'):reg(key,0xdead0000)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def stub(emu,address,size,user):
        if address==base+0x744d0:
            assert u.reg_read(UC_X86_REG_RDX)==22
            ret(learned)
        elif address==base+0x7fe70:
            ret(0)  # Animation setup, not admission, payment or allocation.
        elif address==base+0x114980:
            calls.append((u.reg_read(UC_X86_REG_RCX),u.reg_read(UC_X86_REG_RDX)))
            ret(result)
    handle=u.hook_add(UC_HOOK_CODE,stub)
    def run(start,end=None,aligned=False):
        nonlocal cases
        end=stop if end is None else base+end
        rsp=sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp)
        if end==stop:put(rsp,'Q',stop)
        u.ctl_remove_cache(end-16,end+16)
        u.emu_start(base+start,end,count=10000)
        assert u.reg_read(UC_X86_REG_RIP)==end,(hex(start),hex(u.reg_read(UC_X86_REG_RIP)))
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(8 if end==stop else 0)
        cases+=1
    try:
        # Whole native Aurora eligibility function; exact HP boundaries and
        # story/learned/cinematic/KO guards remain in force.
        for on in (0,1):
            for maximum in (100,999,1000,1001,9999):
                threshold=maximum//(4 if on else 8)
                for hp in (0,1,threshold,threshold+1,maximum):
                    setup(on);put(stats+0x18,'I',maximum);put(actors+0x2c,'I',hp)
                    reg('rcx',actors);run(0x111f40)
                    assert u.reg_read(UC_X86_REG_RAX)==int(0<hp<=threshold),(on,maximum,hp)
        for condition in ('unlearned','not_ready','ko','other_character','busy','large_effect'):
            setup();put(stats+0x18,'I',1000);put(actors+0x2c,'I',100)
            learned=int(condition!='unlearned')
            if condition=='not_ready':put(base+0x12d0f02,'B',0)
            if condition=='ko':put(actors+0x3c,'H',2)
            if condition=='other_character':put(actors+0x4f,'B',1)
            if condition=='busy':put(base+0x12d0efc,'B',1)
            if condition=='large_effect':put(base+0x12d0eaa,'H',5)
            reg('rcx',actors);run(0x111f40);assert u.reg_read(UC_X86_REG_RAX)==0,condition
        learned=1
        for site,length,key in ((0x11201d,9,'rcx'),(0xabf02,7,'rax'),(0xbddc5,6,'rcx')):
            for on in (0,1):
                for buttons in range(256):
                    setup(on);reg(key,buttons);run(site,site+length,True)
                    zf=bool(u.reg_read(UC_X86_REG_EFLAGS)&0x40)
                    mask=0x60 if on else 0xe0
                    assert zf==((buttons&mask)==mask),(site,on,buttons)
        # Infinity: execute all original initial criteria, including the level,
        # 50 uses and single surviving opponent. Only target HP is relaxed.
        master=base+0x11ca420;effect=actors+0x9000;enemy=actors+0x4000
        for on in (0,1):
            for uses,level,alive in ((49,50,1),(50,50,1),(51,51,1),(50,50,2)):
                for hp in (20000,20001,999999):
                    setup(on);put(base+0x12cea60,'Q',master);put(master+0xc52,'H',uses)
                    put(effect,'QQ',actors,enemy);put(enemy+0xe8,'Q',stats)
                    put(enemy+0x2c,'I',hp);put(stats+0x32,'B',level);put(base+0x12d0ef5,'B',alive)
                    reg('rcx',effect)
                    # Stop inside the native stack frame, before side effects.
                    u.reg_write(UC_X86_REG_RSP,sp)
                    u.emu_start(base+0xcf280,base+0xcf2d2,count=1000);cases+=1
                    assert u.reg_read(UC_X86_REG_R14)==int(uses>=50 and level<=50 and alive==1 and (on or hp<=20000))
        for on in (0,1):
            for char,side in ((0,0),(1,0),(0,1)):
                setup(on);put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                put(master+0xc4e,'H',200);reg('rdi',actors);reg('r9',master)
                dest=0xcdf44 if on and char==side==0 else 0xcdf37
                run(0xcdf2f,dest,True)
                if dest==0xcdf37:assert u.reg_read(UC_X86_REG_RAX)==200
        # Final Dragon Fang evaluates every live enemy, not just the target.
        # Execute that entire native loop with two enemies, on both sides of
        # the range boundary, and with chain-dependent use prerequisites.
        for on in (0,1):
            for uses,chain in ((159,0),(160,0),(69,3),(70,3),(0,6)):
                for second_hp in (2000+uses,2001+uses,999999):
                    for distance,alive in ((1599,1),(1600,1),(-1600,1),(1600,2)):
                        setup(on);put(base+0x12cea60,'Q',master)
                        put(master+0xc4e,'H',uses);put(actors+0x6e,'B',chain)
                        put(actors+0x10,'h',0);put(effect,'Q',actors)
                        put(base+0x12cece0,'Q',enemy);put(base+0x12cece9,'B',2)
                        put(enemy+0x3c,'H',1);put(enemy+0x10,'h',-100)
                        put(enemy+0x2c,'I',1)
                        put(enemy+0x248+0x3c,'H',alive)
                        put(enemy+0x248+0x10,'h',distance)
                        put(enemy+0x248+0x2c,'I',second_hp)
                        reg('rcx',effect);u.reg_write(UC_X86_REG_RSP,sp)
                        u.emu_start(base+0xcdeb0,base+0xcdf50,count=1000);cases+=1
                        assert u.reg_read(UC_X86_REG_RIP)==base+0xcdf50
                        eligible=uses>=160-chain*30 and (alive!=1 or
                            (abs(distance)<1600 and (on or second_hp<=2000+uses)))
                        assert u.reg_read(UC_X86_REG_R10)==int(eligible),(on,uses,chain,second_hp,distance,alive)
        input_state=actors+0xa000
        def held_setup(aid, tp=150, buttons=0x40, control=2, on=1):
            setup(on)
            put(actors+0xf0,'Q',input_state);put(input_state,'I',buttons)
            put(actors+0x57,'B',control);put(actors+0x6d,'B',aid)
            put(actors+0xac,'BBBB',aid,aid,aid,aid)
            put(actors+0x34,'h',tp)
            reg('rcx',actors);reg('rdx',aid);reg('r8',20 if aid==19 else 24)

        # Admission never pays. Held and fresh input are independent; a held
        # command through the entire precursor succeeds with no fresh edge.
        for aid in (19,21):
            for control in (0,1,2,3):
                for tp in (0,99,100,101,32767):
                    for buttons in (0,0x20,0x40,0x60,0xc0):
                        for fresh in (0,0x40):
                            held_setup(aid,tp,buttons,control)
                            put(input_state+4,'I',fresh)
                            saved={k:u.reg_read(regs[k]) for k in regs if k!='rax'}
                            run(0x114020)
                            assert u.reg_read(UC_X86_REG_RAX)==int(control in (1,2) and tp>=100 and buttons&0x40!=0)
                            assert saved=={k:u.reg_read(regs[k]) for k in saved}
                            assert get(actors+0x34,'h')==tp and get(counts,'I')==0
            for condition in ('used','phase','busy','ko','dead','other_arte','no_input'):
                held_setup(aid)
                if condition=='used':put(counts+(aid-19),'B',1)
                if condition=='phase':put(base+0x12d0ef7,'B',5)
                if condition=='busy':put(base+0x12d0eaa,'H',1)
                if condition=='ko':put(actors+0x3c,'H',2)
                if condition=='dead':put(actors+0x2c,'i',0)
                if condition=='other_arte':put(actors+0x6d,'B',1)
                if condition=='no_input':put(actors+0xf0,'Q',0)
                run(0x114020);assert u.reg_read(UC_X86_REG_RAX)==0,condition
                assert get(actors+0x34,'H')==150

        # The previous Phoenix quota, other actors and the OFF native path.
        for on in (0,1):
            for char,side in ((0,0),(1,0),(0,1)):
                for aid in (18,19,20,21,22):
                    for used in (0,1,2,3,255):
                        held_setup(aid,on=on)
                        put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                        u.mem_write(counts,bytes([used]*3))
                        modified=on and char==side==0 and aid in (19,21)
                        denied=on and char==side==0 and aid==20 and used>=3
                        run(0x114020,None if modified or denied else 0x114025)
                        if modified:assert u.reg_read(UC_X86_REG_RAX)==int(used<1)
                        if denied:assert u.reg_read(UC_X86_REG_RAX)==0
                        assert get(actors+0x34,'H')==150
                        assert bytes(u.mem_read(counts,3))==bytes([used]*3)
        # Run the whole original helper, including input, TP debit and chain
        # count. BP and OFF must still demand a NEW press and the native cost.
        for aid,on,cost in ((20,1,50),(19,0,20),(21,0,24)):
            for fresh in (0,0x40):
                held_setup(aid,on=on);put(input_state+4,'I',fresh);reg('r8',cost)
                run(0x114020)
                assert u.reg_read(UC_X86_REG_RAX)==int(bool(fresh))
                assert get(actors+0x34,'H')==150-(cost if fresh else 0)
                assert get(actors+0x6e,'B')==int(bool(fresh))

        # Actual dispatch call sites; allocator failure consumes neither TP nor
        # allowance. Run the native TP synchronizer, and verify callee ABI.
        for site,effect_id,index in ((0xcbd53,39,1),(0xce0e6,40,0),(0xcf807,41,2),(0xce01b,40,0)):
            for on in (0,1):
                for char,side in ((0,0),(1,0),(0,1)):
                    for result in (0,effect_id):
                        setup(on);put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                        put(actors+0x34,'H',150)
                        arg=actors
                        if site==0xce01b:put(enemy,'Q',actors);arg=enemy
                        reg('rcx',arg);reg('rdx',effect_id)
                        saved={k:u.reg_read(regs[k]) for k in ('rbx','rsi','rdi','rbp','r12','r13','r14','r15')}
                        run(site,site+5,True)
                        assert saved=={k:u.reg_read(regs[k]) for k in saved}
                        assert calls[-1]==(arg,effect_id)
                        expected=[0,0,0];success=char==side==0 and result==0
                        if success:expected[index]=1
                        assert list(u.mem_read(counts,3))==expected
                        assert u.reg_read(UC_X86_REG_RAX)==result
                        paid=success and on and effect_id!=39
                        assert get(actors+0x34,'H')==150-(100 if paid else 0)
                        assert get(actors+0x6e,'B')==int(paid)
                        assert get(actors+0x2c,'I')==1000

        # Success/failure/retry, independent allowances, no option-toggle reset.
        for aid,eid,site in ((19,40,0xce0e6),(21,41,0xcf807)):
            held_setup(aid,tp=250)
            for result in (eid,0):
                reg('rcx',actors);reg('rdx',aid);run(0x114020)
                assert u.reg_read(UC_X86_REG_RAX)==1
                reg('rcx',actors);reg('rdx',eid);run(site,site+5,True)
                assert get(actors+0x34,'H')==(250 if result else 150)
            for on in (0,1):
                put(flag,'B',on)
                # Opening/changing/scolling settings cannot overwrite quotas.
                put(base+m['data_rva']+0x1a12,'B',34)
                put(base+0x11c9ce8,'B',3)
                run(m['symbols']['settings_description_info'])
                assert get(counts+aid-19,'B')==1
            reg('rcx',actors);reg('rdx',aid);run(0x114020)
            assert u.reg_read(UC_X86_REG_RAX)==0 and get(actors+0x34,'H')==150
            other=21 if aid==19 else 19
            put(actors+0x6d,'B',other);reg('rcx',actors);reg('rdx',other)
            run(0x114020);assert u.reg_read(UC_X86_REG_RAX)==1

        # Execute the real late-frame trigger and dispatch path with Arte held
        # from frame zero. Timing and native geometric eligibility stay intact.
        result=0
        def segment(start,stops):
            nonlocal cases
            reached=[]
            def finish(emu,address,size,user):
                if address-base in stops:reached.append(address-base);emu.emu_stop()
            h=u.hook_add(UC_HOOK_CODE,finish)
            try:
                u.ctl_remove_cache(base+start,base+max(stops)+16)
                u.emu_start(base+start,stop,count=5000)
            finally:u.hook_del(h)
            cases+=1
            assert reached,(hex(start),hex(u.reg_read(UC_X86_REG_RIP)))
            assert u.reg_read(UC_X86_REG_RSP)==sp-8
            return reached[0]
        for aid,start,first,last,success_stop,failed_stops in (
                (19,0xcdf68,156,160,0xce0eb,(0xce1b3,)),
                (21,0xcf741,116,119,0xcf80c,(0xcf872,0xcf86b))):
            for tick in (0,first-1,first,first+1,last,last+1):
                for eligible in (0,1):
                    held_setup(aid);put(effect,'QQ',actors,enemy);put(effect+0x38,'H',tick)
                    put(actors+8,'Q',effect);put(actors+0x53,'b',-1);put(enemy+0x10,'h',100)
                    reg('rbx',effect);reg('rdi',effect);reg('r10',eligible);reg('r14',eligible)
                    reg('r11',0);reg('r12',0)
                    put(base+0x551f34,'i',-1)  # Disable portrait lookup during this path.
                    u.reg_write(UC_X86_REG_RSP,sp-8)
                    dest=segment(start,(success_stop,)+failed_stops)
                    succeeds=eligible and first<=tick<=last
                    assert (dest==success_stop)==bool(succeeds),(aid,tick,eligible,hex(dest))
                    assert get(actors+0x34,'H')==150-(100 if succeeds else 0)
                    assert get(counts+aid-19,'B')==int(bool(succeeds))

        # Real native damage mode switch, all six exact cinematic descriptors.
        # Check linear response to base damage and no effect on enemies, OFF,
        # other actors, or Burning Phoenix's existing 300% mixed-attack hit.
        config=actors+0xc100
        for row in info['impact_scaling']+[dict(descriptor_rva=0x584370,native_mode=2,native_power=300,slash_percent=300)]:
            ptr=base+row['descriptor_rva']+8
            assert get(ptr+2,'B')==row['native_mode'] and get(ptr+10,'h')==row['native_power']
            original=bytes(u.mem_read(ptr,14))
            for on in (0,1):
                for char,side in ((0,0),(1,0),(0,1)):
                    for amount in (0,1,99,100,333,1000,32767):
                        setup(on);put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                        put(base+0x12cea68,'Q',config);put(config+4,'B',0)
                        reg('rbp',actors);reg('r12',ptr);reg('rsi',amount)
                        saved={k:u.reg_read(regs[k]) for k in regs if k not in ('rax','rcx','rdx','rsi')}
                        run(0x8ecbc,0x8ed32)
                        if on and char==side==0:expected=amount*row['slash_percent']//100
                        elif row['native_mode']==3:expected=row['native_power']
                        else:expected=amount*row['native_power']//100
                        assert u.reg_read(UC_X86_REG_RSI)==expected,(row,on,char,side,amount)
                        assert saved=={k:u.reg_read(regs[k]) for k in saved}
                        assert bytes(u.mem_read(ptr,14))==original
        for on in (0,1):
            setup(on);put(counts,'I',0xffffffff)
            # Chained native battle initialization includes Craymel EXP reset.
            u.reg_write(UC_X86_REG_XMM0,0)
            saved={key:u.reg_read(value) for key,value in regs.items()}
            run(0x11c6ef,0x11c700,True)
            assert get(counts,'I')==0 and get(base+0x8c92c4,'I')==120
            assert saved=={key:u.reg_read(value) for key,value in regs.items()}
    finally:u.hook_del(handle)
    put(flag,'B',1)
    return cases
