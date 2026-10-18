"""Run Ondine's original water-decor mesh and draw loop with its real projection."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_ondine(uc,base,manifest,actors,sp,reset,put,get,reg,regs):
    edit=next(e for e in manifest['edits'] if e['rva']==0xa07d8)
    old=bytes.fromhex(edit['original']);new=bytes.fromhex(edit['patched'])
    count=0
    def draw(depth,center,height,age,enabled=True,phase=6):
        nonlocal count
        count+=1;reset();uc.mem_write(base+0xa07d8,new if enabled else old)
        put(base+0x12d0ef7,'B',phase)
        put(base+0x12cea98,'hhh',-center,height,depth)
        put(base+0x8659e8,'9h',4096,0,0,0,4076,-401,0,401,4076)
        put(base+0x8659fc,'iii',-center,height,depth)
        put(base+0x8c96f0,'i',512);put(base+0x8c9718,'i',160);put(base+0x8c92c4,'i',120)
        uc.mem_write(base+0x11ce6a0,b'\0'*8)
        effect=actors+0x9000;put(effect+0x38,'H',age)
        before=bytes(uc.mem_read(actors,0x10000))
        reg('rcx',effect);uc.reg_write(UC_X86_REG_RSP,sp)
        world=[];grid=[];quads=[];done=[]
        def step(u,a,size,user):
            rva=a-base
            if rva==0xa0aa9:done.append(True);u.emu_stop()
            elif rva==0x1a07d0:
                world.append(struct.unpack('<3h',u.mem_read(base+0x8c9730,6)))
            elif rva==0xa07ef:
                grid.append(struct.unpack('<2h',u.mem_read(u.reg_read(regs['rsi']),4)))
            elif rva in [0x11e4d0,0x11f170,0x11e6f0,0x120f70,0x283090]:
                if rva==0x283090:reg('rax',17)  # platform rand(); decor scroll only
                if rva==0x11e6f0:quads.append(struct.unpack('<8h',u.mem_read(base+0x11ce640,16)))
                rsp=u.reg_read(UC_X86_REG_RSP)
                u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
        h=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+0xa0460,base+0xa0aaa,count=100000)
        finally:uc.hook_del(h)
        assert done,hex(uc.reg_read(UC_X86_REG_RIP))
        assert len(grid)==70 and len(world)==72
        assert before==bytes(uc.mem_read(actors,0x10000))
        assert get(base+0x12cea98,'h')==-center
        return world,grid,quads
    try:
        for depth in [512,668,960,1321]:
            for center,height in [(0,32),(300,64),(-160,48)]:
                for age in [16,80,128]:
                    ow,og,oq=draw(depth,center,height,age,False)
                    nw,ng,nq=draw(depth,center,height,age)
                    assert ow==nw,'water world mesh altered'
                    for row in range(7):
                        assert ng[row*10][0]<=-16 and ng[row*10+9][0]>=336
                        for col in range(1,9):
                            assert ng[row*10+col][0]==og[row*10+col][0]
                            if row<6:assert ng[row*10+col]==og[row*10+col]
                    assert all(y>=224 for x,y in ng[-10:])
                    assert nq, 'water surface not submitted'
                    # The actual submitted edge polygons reach both overscan
                    # borders. This catches a correct grid followed by culling.
                    assert min(q[i] for q in nq for i in [0,2,4,6])<=-16
                    assert max(q[i] for q in nq for i in [0,2,4,6])>=336
        assert draw(512,300,64,80,False,5)==draw(512,300,64,80,True,5)
    finally:uc.mem_write(base+0xa07d8,new)
    return count
