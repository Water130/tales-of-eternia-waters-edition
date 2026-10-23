"""Execute injected EXP collection, original victory loop and both gauge reads."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_craymel_exp(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['craymel_experience'];sym=m['symbols'];master=base+0x11ca420
    entries=master+0xbb8;pending=base+info['pending_rva'];flag=base+info['flag_rva']
    stop=base+m['data_rva']-16;cases=0;calls=[]
    def setup():
        reset();u.mem_write(master,b'\0'*0xd00)
        u.mem_write(pending,b'\0'*40)
        put(base+0x12cea60,'Q',master);put(flag,'B',1)
        for i in range(10):put(entries+i*8,'BBHI',3 if i%2==0 else 4,1,0,0)
    def run(start,end=stop,aligned=False):
        nonlocal cases
        rsp=sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp)
        if not aligned:put(rsp,'Q',stop)
        u.emu_start(base+start,end,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==end,(hex(start),hex(u.reg_read(UC_X86_REG_RIP)))
        assert u.reg_read(UC_X86_REG_RSP)==(rsp if aligned else rsp+8)
        cases+=1
    def cast(aid,char=2,result=None):
        actor=actors+char*0x248
        put(actor+0x6d,'B',aid)
        if result is None:
            reg('rcx',actor);reg('rdx',aid);run(info['cast'])
        else:
            reg('rbx',actor);reg('rax',result)
            saved={k:u.reg_read(v) for k,v in regs.items()}
            run(0xd554e,base+0xd5555,True)
            assert saved=={k:u.reg_read(v) for k,v in regs.items()}
    def award(owner=3,base_exp=12345,ko=False):
        rsp=sp-8
        for key,val in [('r15',owner-1),('rbx',owner),('r12',master+4),('rbp',base_exp),('r13',0)]:reg(key,val)
        for off,val in [(0x50,owner),(0x54,base_exp),(0x60,owner-1),(0x58,0x58)]:put(rsp+off,'I',val)
        start=0x119bf7
        if ko:
            actor=actors+(owner-1)*0x248
            put(actor+0x3c,'H',2);reg('r13',actor);start=0x119a01
        run(start,base+0x119e30,True)
    def threshold(level):
        if level==1:return 0
        return sum(min(100000+i,((i+40)*i*i)//10+3*i+3) for i in range(1,2*level+3))

    # Verify native rank, rather than low unlock-level recipes, controls EXP.
    for aid,spirit,amount in [(70,0,50),(71,0,200),(73,1,200),(74,1,500),
                              (84,4,200),(88,5,500),(93,8,200),(94,8,500),
                              (54,0,50),(58,0,500),(65,1,50),(112,5,200),(113,6,500)]:
        for char in (2,3):
            setup();cast(aid,char,result=0)
            assert get(pending+spirit*4,'I')==amount,(aid,char)
            assert sum(get(pending+i*4,'I') for i in range(10))==amount
            assert get(entries+spirit*8+4,'I')==0,'EXP credited before victory'
            cast(aid,char,result=1)
            assert get(pending+spirit*4,'I')==amount,'Rejected cast was credited'
    for char in (0,1,4,5,6):
        setup();cast(70,char);assert get(pending,'I')==0
    for condition in ('off','enemy','unknown','max','not_battle'):
        setup();actor=actors+2*0x248
        if condition=='off':put(flag,'B',0)
        if condition=='enemy':put(actor+0x51,'B',1)
        if condition=='unknown':put(entries,'B',0)
        if condition=='max':put(entries+1,'B',30)
        if condition=='not_battle':put(base+0x12d0ef7,'B',0)
        cast(70);assert get(pending,'I')==0,condition
    for aid in (0,39,43,53,102,111,114,127):
        setup();cast(aid);assert bytes(u.mem_read(pending,40))==bytes(40),aid

    setup();cast(70);cast(70,3);cast(71);cast(73,3)
    # 300 water EXP and 200 wind EXP, independent of cage owner/caster.
    award(4);award(3)
    assert get(entries+4,'I')==300 and get(entries+12,'I')==200
    assert all(get(entries+i*8+4,'I')==0 for i in range(2,10)),'Free EXP survived'
    assert bytes(u.mem_read(pending,40))==bytes(40)
    award(3);award(4)
    assert get(entries+4,'I')==300 and get(entries+12,'I')==200,'EXP paid twice'

    # Original level loop, overflows/cap and KO owner's reward notifications.
    for amount in (485,486,1073,1074,29561,712938,800000):
        setup();put(pending,'I',amount);award(3,ko=True)
        expected=min(amount,712938)
        level=max(lv for lv in range(1,31) if threshold(lv)<=expected)
        assert get(entries+4,'I')==expected
        assert get(entries+1,'B')==level,(amount,level,get(entries+1,'B'))
        assert bool(get(actors+2*0x248+0xa0,'H')&64)==(level>1)

    setup();put(flag,'B',0);award(3,base_exp=100)
    assert [get(entries+i*8+4,'I') for i in range(10)]==[60 if i%2==0 else 0 for i in range(10)]
    # A fled/abandoned fight cannot fund a subsequent victory. Reset preserves
    # all registers and the native clock reset including the caller's XMM0.
    setup();cast(71);u.mem_write(base+info['state_rva'],b'\xff'*0x800)
    u.reg_write(UC_X86_REG_XMM0,0)
    saved={k:u.reg_read(v) for k,v in regs.items()}
    run(0x11c6ef,base+0x11c6f6,True)
    assert saved=={k:u.reg_read(v) for k,v in regs.items()}
    assert bytes(u.mem_read(base+info['state_rva'],0x830))==bytes(0x830)
    award(3);assert get(entries+4,'I')==0

    for progress in (info['cage']['progress'],sym['craymel_exp_progress_tree']):
        for spirit in range(10):
            for level in range(1,31):
                floor=threshold(level)
                needed=threshold(level+1)-floor if level<30 else 0
                for gained in sorted({0,needed//2,max(0,needed-1),needed}):
                    setup();put(entries+spirit*8,'BBHI',3,level,0,floor+gained)
                    reg('rcx',spirit);run(progress)
                    assert u.reg_read(UC_X86_REG_RAX)==(gained*10000//needed if needed else 10000)
                    assert u.reg_read(UC_X86_REG_RDX)==(gained if needed else 0)
                    assert u.reg_read(UC_X86_REG_R8)==needed
                    assert u.reg_read(UC_X86_REG_R9)==level
        for sid in (0,9,10,0xffffffff):
            setup();put(entries,'B',0);put(entries+9*8,'B',0)
            reg('rcx',sid);run(progress)
            assert all(u.reg_read(r)==0 for r in (UC_X86_REG_RAX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9))

    def render(emu,address,size,user):
        if address!=base+0x251390:return
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,'Cage gauge ABI'
        calls.append((u.reg_read(UC_X86_REG_RCX),u.reg_read(UC_X86_REG_RDX),
                      u.reg_read(UC_X86_REG_R8),u.reg_read(UC_X86_REG_R9),
                      get(rsp+0x28,'I'),get(rsp+0x30,'I'),get(rsp+0x38,'I'),get(rsp+0x40,'I')))
        # Test renderer may clobber every volatile register.
        dest=get(rsp,'Q')
        for key in ('rax','rcx','rdx','r8','r9','r10','r11'):reg(key,0xdead)
        u.reg_write(UC_X86_REG_RIP,dest);u.reg_write(UC_X86_REG_RSP,rsp+8)
    positions=[]
    def level_position(_,address,size,user):
        if address!=base+0xceb0:return
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
        positions.append(u.reg_read(UC_X86_REG_XMM2)&0xffffffff)
        dest=get(rsp,'Q');u.reg_write(UC_X86_REG_RIP,dest);u.reg_write(UC_X86_REG_RSP,rsp+8)
    level_hook=u.hook_add(UC_HOOK_CODE,level_position)
    hook=u.hook_add(UC_HOOK_CODE,render)
    try:
        for amount,width in ((0,0),(243,24),(485,48)):
            for alpha in (0,128,255):
                setup();calls.clear();put(entries+4,'I',amount)
                reg('r14',0);reg('r15',alpha);put(sp-8+0xb0,'I',123)
                run(0x243e8a,base+0x243e91,True)
                assert calls[0]==(170,64,0x601,128,128,128,49,alpha),calls
                assert len(calls)==(2 if width else 1)
                if width:assert calls[1]==(170,64,0x601,192,192,48,width,alpha),calls
        setup();put(flag,'B',0);calls.clear()
        run(0x243e8a,base+0x243e91,True);assert not calls
        for enabled in (0,1):
            setup();put(flag,'B',enabled);positions.clear()
            u.reg_write(UC_X86_REG_XMM2,0x437f0000)
            run(0x243d62,base+0x243d67,True)
            assert positions==[0x436a0000 if enabled else 0x437f0000]
    finally:
        u.hook_del(hook);u.hook_del(level_hook)
    return cases
