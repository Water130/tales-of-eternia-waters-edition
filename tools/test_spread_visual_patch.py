"""Compare original/patched Spread through native projection and quad emission."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_spread(uc,base,manifest,actors,sp,reset,put,get,reg,regs):
    data=base+manifest['data_rva'];count=0
    change=next(e for e in manifest['edits'] if e['name']=='Close Spread upper rim while preserving the complete vanilla column')
    original=bytes.fromhex(change['original']);patched=bytes.fromhex(change['patched'])
    allocation=0x52000000;context=0x55000000
    uc.mem_map(allocation,0x2001000);uc.mem_map(context,0x10000)
    def mesh(depth,mode=1,phase=6,adaptive=1,age=80,pitch=True,enabled=True,missing=None):
        nonlocal count
        count+=1;reset();uc.mem_write(base+0xc0ca6,patched if enabled else original)
        put(base+0x12d0ef7,'B',phase);put(data+0x20,'B',adaptive)
        put(base+0x12cea9c,'h',depth);put(base+0x12ceb82,'h',240*16)
        matrix=[4096,0,0,0,4076,-401,0,401,4076] if pitch else [4096,0,0,0,4096,0,0,0,4096]
        put(base+0x8659e8,'9h',*matrix);put(base+0x8659fc,'iii',-240,32,depth)
        uc.mem_write(base+0x11ce620,b'\0'*0xa0)
        put(base+0x8c96f0,'i',512);put(base+0x8c9718,'i',160);put(base+0x8c92c4,'i',120)
        put(base+0x644a58,'Q',0 if missing=='vertices' else allocation)
        put(allocation+0x2000008,'I',0x2000000 if missing=='vertex_full' else 0)
        put(base+0x644a10,'Q',0 if missing=='context' else context)
        put(context+0x4d0,'Q',0 if missing=='commands' else context+0x1000)
        put(context+0x4d8,'Q',159 if missing=='command_full' else 256)
        put(context+0x4e0,'I',0)
        put(base+0x12cea68,'Q',actors+0xc100);put(actors+0xc100,'H',0x400)
        put(base+0x573c3e,'B',1)
        effect=actors+0x9000;put(effect+0x38,'H',age)
        before=bytes(uc.mem_read(actors,0x10000))
        reg('rcx',effect);reg('rdx',mode);uc.reg_write(UC_X86_REG_RSP,sp)
        world=[];screen=[];body=[];caps=[];draws=[];done=[];cap=False;scratch=None;projection=None;nv=None
        def step(u,a,size,user):
            nonlocal cap,scratch,projection,nv
            rva=a-base
            rsp=u.reg_read(UC_X86_REG_RSP)
            def ret():
                u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
            if rva==0xc0cb2:
                done.append(True);u.emu_stop()
            elif rva==0xc0ca6:
                scratch=bytes(u.mem_read(base+0x11ce620,0xa0))
                projection=bytes(u.mem_read(base+0x8c9720,24))
                nv={r:u.reg_read(regs[r]) for r in ['rbx','rbp','rsi','rdi','r12','r13','r14','r15']}
            elif rva==manifest['symbols']['spread_column_cap']:cap=True
            elif rva==0x1a07d0:world.append(struct.unpack('<3h',u.mem_read(base+0x8c9730,6)))
            elif rva in [0xc08e1,0xc0a0b]:screen.append(struct.unpack('<2i',u.mem_read(base+0x8c9720,8)))
            elif rva==0x11ed60:
                assert rsp%16==8
                record=(struct.unpack('<8h',u.mem_read(base+0x11ce640,16)),bytes(u.mem_read(base+0x11ce670,36)))
                (caps if cap else body).append(record)
                if not cap:ret()  # body checked byte-for-byte; execute real cap builder
            elif rva in [0x11d1c0,0x11ded0]:
                # Platform texture resolution only; native vertices/commands run.
                if rva==0x11d1c0:reg('rax',1)
                ret()
            elif rva==0x60bf0:
                command=u.reg_read(regs['rdx'])
                if get(command,'I')==5:
                    assert get(command+0xc,'I')==0x80011e, 'cap lost water texture vertex format'
                    ptr=get(command+0x20,'Q');draws.append(bytes(u.mem_read(ptr,64)))
                ret()
        h=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+0xc0780,base+0xc0cb3,count=100000)
        finally:uc.hook_del(h)
        assert done,hex(uc.reg_read(UC_X86_REG_RIP))
        assert len(screen)==(80 if mode==1 else 112)
        assert before==bytes(uc.mem_read(actors,0x10000)),'Spread gameplay/effect state changed'
        expected=bytearray(scratch);struct.pack_into('<I',expected,0x44,0x00400040)
        assert bytes(expected)==bytes(uc.mem_read(base+0x11ce620,0xa0)), 'render scratch leaked'
        assert projection==bytes(uc.mem_read(base+0x8c9720,24)), 'projection scratch leaked'
        assert nv=={r:uc.reg_read(regs[r]) for r in nv}, 'nonvolatile register changed'
        assert len(caps)==len(draws), 'cap was not submitted by native builder'
        if caps:
            assert len(caps)==16 and world[-1]==(0,-204,0)
            apex=caps[0][0][4:6]
            for i,(q,material) in enumerate(caps):
                assert q[:2]==screen[i] and q[2:4]==screen[(i+1)%16], 'rim gap'
                assert q[4:6]==q[6:8]==apex
                assert material[16:26]==body[0][1][16:26], 'water texture identity/depth changed'
                vertices=[struct.unpack('<8h',draws[i][j*16:j*16+16]) for j in range(4)]
                assert vertices[2][4:7]==vertices[3][4:7], 'triangle apex not closed'
                assert vertices[1][0]-vertices[0][0]==32, 'new cap stretched texture tile'
                assert vertices[2][1]-vertices[0][1]==32
        return world[:len(screen)],screen,body,len(caps)
    try:
        for depth in [512,640,1024,1276,2048,4096]:
            for pitch in [False,True]:
                for age in [16,80,150]:
                    old=mesh(depth,age=age,pitch=pitch,enabled=False)
                    new=mesh(depth,age=age,pitch=pitch)
                    assert old[:3]==new[:3], 'vanilla column geometry, projection, UVs or colors changed'
                    assert old[3]==0 and new[3]==16
        for depth in [512,1276,4096]:
            assert mesh(depth,mode=0,enabled=False)==mesh(depth,mode=0),'flat wave changed'
        for phase,adaptive in [(5,1),(6,0),(6,2)]:
            assert mesh(1276,phase=phase,adaptive=adaptive,enabled=False)==mesh(1276,phase=phase,adaptive=adaptive)
        for missing in ['vertices','vertex_full','context','commands','command_full']:
            assert mesh(1276,missing=missing)[3]==0,missing
    finally:
        uc.mem_write(base+0xc0ca6,patched)
        put(base+0x644a10,'Q',0);put(base+0x644a58,'Q',0)
        uc.mem_unmap(allocation,0x2001000);uc.mem_unmap(context,0x10000)
    return count
