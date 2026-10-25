"""Exercise gated combat events and the actual native normal/arte initializers."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

def check_fighters(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['mastery_menu']['fighter_faculties'];data=base+m['data_rva']
    state=base+info['state_rva'];choices=base+m['mastery_menu']['choices']['live_rva']
    master=actors+0xa000;stats=actors+0x8000;inputs=actors+0x9000;enemy=actors+0x4000
    stop=data-16;cases=0;saved=[];calls=[]
    for table,targets in ((0x4e92b0,(0x112420,0x112560)),(0x4e93c0,(0x551bb0,0x551da8))):
        for char,target in enumerate(targets):
            p=base+table+char*8;saved.append((p,get(p,'Q')));put(p,'Q',base+target)
    def setup(char=0,level=30):
        reset();u.mem_write(choices,bytes(224));u.mem_write(state,bytes(16));calls.clear()
        put(base+0x12cea60,'Q',master);put(data+0x1a4f,'B',1);put(data+0x1a41,'B',1)
        for offset in (0xc08,0xc10,0xc18,0xc20):put(master+offset,'B',level)
        a=actors+char*0x248
        put(a+0x52,'B',2);put(a+0x57,'B',2);put(a+0x53,'B',1);put(a+0xf0,'Q',inputs)
        put(a,'Q',enemy);put(enemy+0xe8,'Q',stats+0x200);put(enemy+0x10,'h',1500)
        put(base+0x12cea40,'I',100)
        put(base+0x12cea78,'Q',base+0x551780)
        put(base+0x12cea70,'Q',base+0x562a50)
        put(base+0x6449e0,'Q',actors+0x9800)
        return a
    def boundary(_,address,size,user):
        if address==stop:u.emu_stop();return
        if address-base in (0x7fe70,0x283090,0x11ace0,0x279670,0xc7210,0x8d520,0x712e0,0x114980,0x114dd0,0x1b5ca0):
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8,(hex(address-base),hex(rsp))
            calls.append(address-base);reg('rax',0)
            u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,boundary)
    def run(name,end=None):
        nonlocal cases
        cases+=1;rsp=sp-8 if end else sp
        u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        dest=base+end if end else stop
        u.emu_start(base+m['symbols'][name],dest,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==dest,(name,hex(u.reg_read(UC_X86_REG_RIP)))
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if end else 8)
    def enabled(a,id):
        reg('rcx',a);reg('rdx',id);run('fighter_faculty_enabled');return u.reg_read(regs['rax'])
    def block(a):reg('rcx',a);run('fighter_block_record')
    def action(a):reg('rcx',a);run('fighter_guard_action')
    def impact(a):reg('rcx',a);reg('rdx',enemy);run('fighter_heavy_impact')
    try:
        for id,char,threshold in ((138,0,20),(139,0,25),(140,0,20),(141,1,20)):
            for level in (threshold-1,threshold,30):
                a=setup(char,level);assert enabled(a,id)==int(level>=threshold)
            bit=char*256+id;p=choices+bit//8;put(p,'B',1<<(bit%8));assert not enabled(a,id)
            put(p,'B',0);assert enabled(a,id)
            for offset,fmt,value in ((0x51,'B',1),(0x3c,'H',0),(0x2c,'i',0),(0x4f,'B',3)):
                a=setup(char);put(a+offset,fmt,value);assert not enabled(a,id)
            a=setup(char);put(data+(0x1a4f if char==0 else 0x1a41),'B',0);assert not enabled(a,id)
            a=setup(char);put(base+0x12d0ef7,'B',0);assert not enabled(a,id)
        # Actual native first thrust from guard, one accepted block => one action.
        for dt in (0,24,25,0xffffffff):
            a=setup();block(a);put(base+0x12cea40,'I',(100+dt)&0xffffffff)
            put(inputs+4,'B',0x20);action(a)
            if dt<=24:
                assert get(a+0x52,'B')==8 and get(a+0x6e,'B')==1
                assert get(a+0xab,'B')==1
                assert get(state+12,'B')==0
                action(a);assert get(a+0x6e,'B')==1
            else:assert get(a+0x52,'B')==2 and get(state+12,'B')==0
        for offset,fmt,value in ((0x57,'B',0),(0x57,'B',3),(0x44,'H',1),(0x74,'B',1),(0x12,'h',-1),(0x30,'I',0x4000)):
            a=setup();block(a);put(inputs+4,'B',0x20);put(a+offset,fmt,value);action(a)
            assert get(a+0x52,'B')==2
        a=setup();put(inputs+4,'B',0x20);action(a);assert get(a+0x52,'B')==2
        # Native input mapping, native cost check/debit and native arte initializer.
        for aid in range(1,8):
            for tp in (0,100):
                a=setup();put(a+0xac,'B',aid);put(inputs+4,'B',0x40);put(a+0x34,'H',tp)
                block(a);action(a)
                started=aid<=6 and tp==100
                assert (get(a+0x52,'B')==8)==started,(aid,tp,get(a+0x52,'B'))
                cost=get(base+0x562a50+aid*24,'B')
                assert get(a+0x34,'H')==tp-(cost if started else 0)
                if started:
                    assert get(a+0x64,'B')>=16 and get(a+0x6e,'B')==1
                    assert get(state+12,'B')==0
        # Terminal grounded hits only; protected targets are unchanged.
        for ticks in (1,10,30,32760):
            a=setup();put(a+0x52,'B',8);put(a+0x64,'B',15);put(enemy+0x44,'h',ticks)
            impact(a);expected=min(32767,(ticks*110+99)//100);assert get(enemy+0x44,'h')==expected
            impact(a);assert get(enemy+0x44,'h')==expected
            put(a+0x52,'B',0);action(a);assert get(state+13,'B')==0
        for ptr,offset,fmt,value in ((actors,0x64,'B',1),(actors,0x12,'h',-1),(enemy,0x12,'h',-1),(stats+0x200,0x2e,'B',5),(stats+0x200,0x4e,'H',4),(stats+0x200,0x4e,'H',16)):
            a=setup();put(a+0x52,'B',8);put(a+0x64,'B',15);put(enemy+0x44,'h',30)
            put(ptr+offset,fmt,value);impact(a);assert get(enemy+0x44,'h')==30
        # Execute both native incoming paths, including the fast-landing branch
        # to d623b. Calling only the trampoline missed a branch into its old
        # overwritten span and let the 0.14.20 crash escape this suite.
        for char in range(4):
            for speed,threshold in [(v,t) for t in (48,64) for v in (-65,-64,-48,0,48,64,65)]:
                for level in (19,20,30):
                    a=setup(char,level)
                    put(a+0x64,'B',16);put(a+0x18,'h',speed);put(a+0x42,'h',threshold)
                    put(a+0x44,'H',4)
                    reg('rbx',a);reg('r10',8);reg('r8',4);reg('r9',0)
                    reg('r12',0);reg('rsi',8)
                    rsp=sp-8;u.reg_write(UC_X86_REG_RSP,rsp)
                    cases+=1
                    u.emu_start(base+0xd61f7,base+0xd624f,count=100000)
                    assert u.reg_read(UC_X86_REG_RIP)==base+0xd624f
                    fast=abs(speed)>threshold
                    expected=4 if fast else (8 if char==1 and level>=20 else 16)
                    assert get(a+0x44,'H')==expected,(char,speed,level,get(a+0x44,'H'))
                    assert get(a+0x52,'B')==(5 if fast else 6)
                    assert get(a+0x18,'h')==(speed if fast else 0)
                    assert get(a+0x64,'B')==15 and get(a+0x88,'H')==2 and get(a+0x66,'B')==8
                    assert u.reg_read(UC_X86_REG_RSP)==rsp
        # Landing hook retains native state/flags/registers except the requested SI timer.
        for char,old,selector,level,expected in ((1,8,16,20,7),(1,8,15,30,13),(1,0,16,30,13),(0,8,16,30,13),(1,8,16,19,13)):
            a=setup(char,level);put(a+0x64,'B',selector);reg('rbx',a);reg('r10',old);reg('rsi',13);reg('rax',6);reg('r8',0)
            before={r:u.reg_read(v) for r,v in regs.items()}
            run('fighter_landing_hook',0xd623e)
            before['rsi']=expected
            assert before=={r:u.reg_read(v) for r,v in regs.items()}
            assert get(a+0x44,'H')==expected and get(a+0x52,'B')==6
        return dict(cases=cases,native_thrust=True,block_expiry=True,individual_gates=True,protected_targets=True,landing_abi=True,native_fast_landing_branch=True)
    finally:
        u.hook_del(h)
        for p,v in saved:put(p,'Q',v)
        put(data+0x1a4f,'B',1);put(data+0x1a41,'B',1)
