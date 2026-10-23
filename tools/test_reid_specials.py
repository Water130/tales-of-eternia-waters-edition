"""Execute Reid's actual patched eligibility, input, dispatch and reset code."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_reid_specials(u,base,m,actors,stats,sp,reset,put,get,reg,regs):
    info=m['reid_specials'];counts=base+info['counters_rva'];flag=base+info['flag_rva']
    stop=base+m['data_rva']-16;cases=0;learned=1;result=0;calls=[]
    def setup(on=1):
        reset();put(flag,'B',on);put(counts,'I',0)
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
        # Quotas are checked before input handling / native TP debit. Other
        # actors, arte IDs and OFF all reach the original function unchanged.
        for on in (0,1):
            for char,side in ((0,0),(1,0),(0,1)):
                for aid in (18,19,20,21,22):
                    for used in (0,1,2,3,255):
                        setup(on);put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                        u.mem_write(counts,bytes([used]*3));reg('rcx',actors);reg('rdx',aid);reg('r8',20)
                        denied=on and char==side==0 and 19<=aid<=21 and used>=3
                        run(0x114020,None if denied else 0x114025)
                        if denied:assert u.reg_read(UC_X86_REG_RAX)==0
                        assert get(actors+0x34,'H')==10
                        assert bytes(u.mem_read(counts,3))==bytes([used]*3)
        # Execute all three actual initial call sites, with successful and
        # failed allocator returns. Stub only the renderer/resource allocator.
        for site,effect_id,index in ((0xcbd53,39,1),(0xce0e6,40,0),(0xcf807,41,2)):
            for on in (0,1):
                for char,side in ((0,0),(1,0),(0,1)):
                    for result in (0,effect_id):
                        setup(on);put(actors+0x4f,'B',char);put(actors+0x51,'B',side)
                        for repeat in range(5):
                            reg('rcx',actors);reg('rdx',effect_id)
                            saved={key:u.reg_read(regs[key]) for key in ('rbx','rsi','rdi','rbp','r12','r13','r14','r15')}
                            run(site,site+5,True)
                            assert saved=={key:u.reg_read(regs[key]) for key in saved}
                            assert calls[-1]==(actors,effect_id)
                            expected=[0,0,0]
                            if char==side==0 and result==0:expected[index]=min(3,repeat+1)
                            assert list(u.mem_read(counts,3))==expected
                            assert u.reg_read(UC_X86_REG_RAX)==result
        # A saturated technique does not spend or reset the other allowances.
        setup();u.mem_write(counts,bytes([3,1,2]))
        for aid in (19,20,21):
            reg('rcx',actors);reg('rdx',aid)
            run(0x114020,None if aid==19 else 0x114025)
        assert list(u.mem_read(counts,3))==[3,1,2]
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
