"""Execute full native normal chains, including selector tables and descriptors."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_basic_mastery(u,base,m,actors,sp,reset,put,get,reg,regs):
    data=base+m['data_rva'];info=m['mastery_menu']['basic_attacks']
    choices=base+m['mastery_menu']['choices']['live_rva'];transient=base+info['state_rva']
    stop=data-16;master=actors+0xa000;cases=0
    saved=[]
    for table,targets in ((0x4e92b0,(0x112420,0x112560)),(0x4e93c0,(0x551bb0,0x551da8))):
        for char,target in enumerate(targets):
            p=base+table+char*8;saved.append((p,get(p,'Q')));put(p,'Q',base+target)
    def run(actor,direction):
        nonlocal cases
        cases+=1;reg('rcx',actor);reg('rdx',direction);reg('rsp',sp) if 'rsp' in regs else u.reg_write(UC_X86_REG_RSP,sp)
        put(sp,'Q',stop);reached=[]
        def boundary(_,address,size,user):
            if address==stop:reached.append(True);u.emu_stop()
            elif address-base in (0x7fe70,0x283090,0x11ace0,0x279670):
                rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
                reg('rax',0);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
        h=u.hook_add(UC_HOOK_CODE,boundary)
        try:u.emu_start(base+0x112720,stop+1,count=30000)
        finally:u.hook_del(h)
        assert reached and u.reg_read(UC_X86_REG_RSP)==sp+8
    def chain(char,direction,level,enabled=1,disabled=(),air=False,other=None):
        reset();u.mem_write(choices,b'\0'*224);u.mem_write(transient,b'\0'*32)
        # Set the other character's switch to the opposite value: no cross-talk.
        put(data+0x1a4f,'B',enabled if char==0 else 1-enabled)
        put(data+0x1a41,'B',enabled if char==1 else 1-enabled)
        put(base+0x12cea60,'Q',master)
        actor=actors+char*0x248
        put(actor+0x52,'B',4 if air else 0);put(actor+0x64,'B',4 if air else 0)
        put(actor+0x53,'B',1);put(actor+0x12,'h',-128 if air else 0)
        mapped=get(base+0x4e935c+direction,'B')
        family=get(base+(0x551bb0 if char==0 else 0x551da8)+mapped*5+4,'B')-1
        assert family in (0,1)
        # Both families are required by the shared branch.
        put(master+0xc08+char*16,'BB',level,0xa5)
        put(master+0xc10+char*16,'BB',level if other is None else other,0xa5)
        for tier in disabled:
            bit=char*256+134+tier
            p=choices+bit//8;put(p,'B',get(p,'B')|1<<(bit%8))
        count=0
        for i in range(10):
            put(actor+0x238,'H',get(actor+0x88,'H'))
            before=get(actor+0x6e,'B');run(actor,direction)
            if get(actor+0x6e,'B')==before:break
            count+=1
        else:raise AssertionError('unbounded normal chain')
        return count,actor
    try:
        for char in (0,1):
            for direction in (0,1,3):
                baseline,_=chain(char,direction,30,enabled=0)
                for level,extra in ((1,0),(14,0),(15,1),(29,1),(30,2)):
                    count,actor=chain(char,direction,level)
                    assert count==baseline+extra,(char,direction,level,baseline,count)
                    # No more attacks after the finite allowance, even on repeated presses.
                    run(actor,direction);assert get(actor+0x6e,'B')==count
                for a,b,extra in ((30,1,0),(30,14,0),(15,30,1),(30,15,1),(29,30,1)):
                    assert chain(char,direction,a,other=b)[0]==baseline+extra
                for disabled,extra in (((0,),2),((1,),1),((0,1),0)):
                    count,_=chain(char,direction,30,disabled=disabled)
                    assert count==baseline+extra,(char,direction,disabled,count)
                assert chain(char,direction,30,air=True)[0]==chain(char,direction,30,enabled=0,air=True)[0]
                _,actor=chain(char,direction,30)
                # A new grounded chain renews its allowance.
                put(actor+0x52,'B',0);put(actor+0x64,'B',0);run(actor,direction)
                assert get(transient+char*16+8,'I')==0
                # A terminal attack cannot be cancelled before its native window.
                put(actor+0x64,'B',15);put(actor+0x238,'H',0);put(actor+0x88,'H',20)
                before=get(actor+0x6e,'B');run(actor,direction);assert get(actor+0x6e,'B')==before
        return dict(cases=cases,finite_extensions=True,shared_family_requirement=True,individual_switches=True,
                    global_off_native=True,separate_character_groups=True,airborne_native=True,timing_preserved=True)
    finally:
        for p,value in saved:put(p,'Q',value)
        put(data+0x1a4f,'B',1)
        put(data+0x1a41,'B',1)
