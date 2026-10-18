"""Exercise original boot/movie paths with only I/O/cookie calls stubbed."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP

def check_startup(uc, base, manifest, sp, reset, put, get, reg, regs):
    sentinel=manifest['data_rva']-0x10
    count=0
    def execute(start,stops=None,stubs=(),capture=None):
        nonlocal count
        count+=1;uc.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',base+sentinel)
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
        reset();put(base+0x119ea68,'I',stage);reg('rbx',0)
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
    return count
