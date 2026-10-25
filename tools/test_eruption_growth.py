"""Run Eruption's native fireball loop and real collision allocation."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RIP, UC_X86_REG_RSP


def check_eruption(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['spell_mastery'];state=base+info['state_rva']
    tag=base+info['effects_rva'];context=base+info['context_rva']
    choices=base+info['usage']['preferences']['live_rva']
    flag=base+m['data_rva']+0x1a0c;effect=base+0x12cfca0
    collisions=base+0x12cee48;tags=base+info['projectiles_rva']
    attempts=[];sprites=[];fail=0;cases=0
    def ret(value):
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'))
        u.reg_write(UC_X86_REG_RSP,rsp+8)
    def boundary(_,address,size,user):
        if address==base+0x8b7e0:
            assert u.reg_read(regs['rcx'])==base+0x579dc0
            attempts.append(1)
            if fail and len(attempts)%fail==0:ret(0);return
            sprite=actors+0x5000+len(sprites)*0x80
            u.mem_write(sprite,bytes(0x80));sprites.append(sprite);ret(sprite)
        elif address==base+0x283090:ret(0x800)
    h=u.hook_add(UC_HOOK_CODE,boundary)
    try:
        for char,side in ((2,0),(3,0),(0,0),(2,1)):
            for uses in (0,55,56,111,112,166,167,222,223,277,278,333,334,388,389,444,445,499,500,999,65535):
                for enabled,disabled,wrong_tag in ((1,0,0),(0,0,0),(1,1,0),(1,0,1)):
                    for fail in (0,3):
                        reset();u.mem_write(state,bytes(info['size']));u.mem_write(choices,bytes(224))
                        actor=actors+char*0x248
                        put(actor+0x51,'B',side);put(actor,'Q',actors)
                        put(effect,'Q',actor);put(effect+0x38,'H',208)
                        put(tag,'QHHI',actor,75 if wrong_tag else 76,uses,0)
                        put(context,'Q',tag);put(flag,'B',enabled)
                        if disabled:put(choices+char*32+76//8,'B',1<<(76%8))
                        put(base+0x12ced28,'Q',actors+0x8000)
                        attempts.clear();sprites.clear()
                        rsp=sp-0x2b8;u.mem_write(rsp+0x268,b'\x5a'*32)
                        reg('r12',effect);reg('r14',0)
                        u.reg_write(UC_X86_REG_RSP,rsp)
                        u.emu_start(base+0x97d9f,base+0x97e80,count=100000)
                        assert u.reg_read(UC_X86_REG_RIP)==base+0x97e80
                        assert u.reg_read(UC_X86_REG_RSP)==rsp
                        extra=min(500,uses)*9//500 if enabled and not disabled and not wrong_tag and not side and char in (2,3) else 0
                        count=20+extra
                        assert len(attempts)==count and u.reg_read(regs['r14'])==count,(char,side,uses,enabled,disabled,wrong_tag,fail,len(attempts),count,get(rsp+0x270,'I'))
                        assert get(rsp+0x270,'I')==count
                        assert bytes(u.mem_read(rsp+0x268,8))==b'\x5a'*8
                        assert bytes(u.mem_read(rsp+0x274,20))==b'\x5a'*20
                        for i,sprite in enumerate(sprites):
                            collision=collisions+i*0x30
                            assert get(collision,'Q')==sprite
                            assert get(collision+8,'Q')==actor
                            assert get(collision+0x20,'B')==2
                            assert get(collision+0x18,'Q')==actors+0x8252
                            assert bytes(u.mem_read(tags+i*16,16))==bytes(u.mem_read(tag,16))
                        expected_delays=[(i+2)*4 for i in range(count) if not fail or (i+1)%fail]
                        assert [get(s+0x1a,'H') for s in sprites]==expected_delays
                        assert get(collisions+len(sprites)*0x30+0x20,'B')==0
                        assert get(effect+0x38,'H')==208
                        # The adjacent frames cannot emit another spray.
                        for tick in (207,209):
                            attempts.clear();put(effect+0x38,'H',tick)
                            u.emu_start(base+0x97d9f,base+0x97e80,count=1000)
                            assert not attempts
                        cases+=1
        return dict(cases=cases,native_fireballs=True,native_collisions=True,
                    allocation_failure_safe=True,immutable_cast_exp=True,additional_cap=9)
    finally:u.hook_del(h)
