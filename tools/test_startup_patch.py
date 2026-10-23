"""Exercise original boot/movie paths with only I/O/cookie calls stubbed."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP

def check_startup(uc, base, manifest, sp, reset, put, get, reg, regs):
    sentinel=manifest['data_rva']-0x10
    data=base+manifest['data_rva']
    initialized=data+0x1a10
    flag=data+0x1a4c
    count=0
    def execute(start,stops=None,stubs=(),capture=None):
        nonlocal count
        count+=1
        rsp=sp-8 if start in (0x2528fb,0x253395,0x259340) else sp
        uc.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',base+sentinel)
        reached=[]
        def step(u,address,size,user):
            r=address-base
            if r in (stops or [sentinel]):reached.append(r);u.emu_stop()
            elif r in stubs:
                p=u.reg_read(UC_X86_REG_RSP)
                assert p%16==8,('ABI',hex(r))
                if capture:capture(r)
                u.reg_write(UC_X86_REG_RIP,get(p,'Q'));u.reg_write(UC_X86_REG_RSP,p+8)
        h=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+start,base+sentinel+1,count=10000)
        finally:uc.hook_del(h)
        assert reached,hex(uc.reg_read(UC_X86_REG_RIP))
        return reached[0]

    for stage in range(6):
        reset();put(initialized,'B',1);put(flag,'B',1)
        put(base+0x119ea68,'I',stage);reg('rbx',0)
        destination=execute(0x2528fb,[0x252d58,0x252d68])
        assert destination==(0x252d58 if stage==1 else 0x252d68)
    # Only reached after the native resource initialization block has finished.
    reset();put(base+0x119ea68,'I',2);put(base+0x119ea60,'I',1)
    execute(0x253395,[0x2533c7])
    assert get(base+0x119ea68,'I')==5 and get(base+0x119ea60,'I')==0
    assert get(base+0x119ea2a,'H')==7 and uc.reg_read(regs['rax'])==30
    # Native options loader state 4 bypasses presentation, requests movie 1.
    reset();put(base+0x119db04,'I',4);put(base+0x119ea21,'B',0)
    execute(0x259040,stubs=[0x279670])
    assert get(base+0x119db04,'I')==6 and get(base+0x119ea21,'B')==1
    assert get(base+0x119ea2a,'H')==7
    # Original movie handler passes index zero to the actual opening player.
    for r in (0x10e1c48,0x10e1c4c,0x10e1c50,0x10e1c54):put(base+r,'I',0)
    movies=[]
    execute(0x253f70,stubs=[0x19da70],capture=lambda r:movies.append((uc.reg_read(regs['rcx']),uc.reg_read(regs['rdx']))))
    assert movies==[(0,0)] and get(base+0x119ea21,'B')==0
    assert uc.reg_read(regs['rax'])==7
    # Error acknowledgement and asynchronous options-loading states stay native.
    for state,stop in [(1,0x2590a7),(2,0x2591a8),(3,0x2592a2)]:
        put(base+0x119db04,'I',state)
        execute(0x259040,[stop])
    # OFF reproduces the overwritten native instructions, including the
    # original resource state (ea60, not ea68) and renderer pointer.
    put(flag,'B',0);put(initialized,'B',1)
    for stage in range(6):
        put(base+0x119ea68,'I',stage)
        assert execute(0x2528fb,[0x252901])==0x252901
        assert uc.reg_read(regs['rcx'])==stage
    put(base+0x119ea68,'I',1);put(base+0x119ea60,'I',0)
    execute(0x253395,[0x25339f])
    assert get(base+0x119ea60,'I')==2 and get(base+0x119ea68,'I')==1
    put(base+0x644a70,'Q',0x12345678)
    execute(0x259340,[0x259347]);assert uc.reg_read(regs['rcx'])==0x12345678
    # Settings must be consulted before the very first update or draw decision.
    # The full Unicode INI loader is separately executed by the settings suite.
    for site,end in [(0x2528fb,0x252901),(0x253395,0x25339f),(0x259340,0x259347)]:
        loaded=[];put(initialized,'B',0);put(flag,'B',1)
        def load(_):
            assert get(initialized,'B')==0
            loaded.append(True);put(initialized,'B',1);put(flag,'B',0)
        execute(site,[end],stubs=[manifest['symbols']['settings_initialize']],capture=load)
        assert loaded==[True]
    put(flag,'B',1)
    return count
