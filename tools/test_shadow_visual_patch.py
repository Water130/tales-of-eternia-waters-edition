"""Execute the native shadow layout fragment using projected sprite depths."""
from unicorn.x86_const import UC_X86_REG_RSP


def check_shadow(uc,base,data,actors,sp,reset,put,get,reg,regs):
    count=0
    for depth in [1,511,512,668,1024,1320,2048,4096,4097]:
        for phase,mode in [(6,1),(6,2),(5,1)]:
            reset();put(base+0x12d0ef7,'B',phase);put(data+0x20,'B',mode)
            put(base+0x12ceb8a,'h',160)
            put(sp+0xc0,'h',depth-512)
            uc.reg_write(UC_X86_REG_RSP,sp)
            reg('r14',140);reg('r15',180);reg('rdx',1)
            before=bytes(uc.mem_read(actors,0x5000))
            uc.emu_start(base+0x80615,base+0x8063e,count=300)
            eligible=phase==6 and mode==1 and 512<depth<=4096
            h=max(2,5120//depth) if eligible else 10
            offset=4096//depth if eligible else 8
            assert get(base+0x11ce666,'h')==h
            assert get(base+0x11ce662,'h')==160-offset
            assert get(base+0x11ce682,'h')==1
            assert uc.reg_read(regs['r15'])==40
            assert uc.reg_read(regs['rdx'])==1
            assert uc.reg_read(UC_X86_REG_RSP)==sp
            assert bytes(uc.mem_read(actors,0x5000))==before
            count+=1
    return count
