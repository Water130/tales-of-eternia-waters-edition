"""Native atlas command construction, binding, resource lookup and UV conversion."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_XMM2, UC_X86_REG_XMM3


def check_spirit_icons(uc, base, manifest, sp, reset, put, get, reg, regs):
    data=base+manifest['data_rva'];sym=manifest['symbols']
    arena=0x50000000;context=arena;commands=arena+0x1000;state=arena+0x4000
    catalog=arena+0x6000;root=arena+0x6800;items=arena+0x7000;palettes=arena+0x8000
    uc.mem_map(arena,0x10000)
    vertices=0x51000000
    uc.mem_map(vertices,0x2001000)
    sentinel=base+manifest['data_rva']-0x10;count=0
    nonvolatile=['rbx','rbp','rsi','rdi','r12','r13','r14','r15']

    def setup():
        reset();uc.mem_write(arena,b'\0'*0x10000)
        put(base+0x644a10,'Q',context)
        put(context+0x4d0,'Q',commands);put(context+0x4d8,'Q',128)
        put(base+0x644a28,'Q',catalog);put(base+0x644a30,'Q',arena+0x9000)
        put(base+0x6449d0,'Q',arena+0xa000)
        put(base+0x644a58,'Q',vertices);put(vertices+0x2000008,'I',0)
        # Actual catalogue layout consumed by fb40: group/sub/item/palette.
        put(catalog+0x178,'Q',root)
        put(root,'QQQ',items,items+5*64,items+5*64)
        put(items+4*64,'Q',101)
        put(items+4*64+16,'QQQ',palettes,palettes+10*24,palettes+10*24)
        for element in range(1,10):
            entry=arena+0x8800+element*8
            put(entry,'Q',101+element)
            put(palettes+element*24,'QQQ',entry,entry+8,entry+8)

    def run(entry, stubs=(), intercept=None):
        nonlocal count
        count+=1;saved={r:uc.reg_read(regs[r]) for r in nonvolatile}
        uc.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',sentinel);done=[]
        def step(u,a,size,user):
            rva=a-base
            if a==sentinel:done.append(True);u.emu_stop()
            elif rva in stubs:
                rsp=u.reg_read(UC_X86_REG_RSP)
                assert rsp%16==8,('ABI',hex(rva),hex(rsp))
                if intercept:intercept(rva,rsp)
                u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
        h=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+entry,sentinel+1,count=20000)
        finally:uc.hook_del(h)
        assert done,('no return',hex(uc.reg_read(UC_X86_REG_RIP)))
        assert uc.reg_read(UC_X86_REG_RSP)==sp+8
        assert saved=={r:uc.reg_read(regs[r]) for r in nonvolatile},'nonvolatile changed'
        return uc.reg_read(regs['rax'])

    # Verify catalogue asset identity, palette count and all nine palette keys.
    assert get(base+0x4bd270,'I')==0x07010021
    assert get(base+0x4bd274,'I')==10
    for element in range(1,10):
        assert get(base+0x4c26b0+element*16,'I')==1
        pointer=get(base+0x4c26b8+element*16,'Q')
        # PE preferred-base pointers are not relocated in this emulator mapping.
        assert get(base+pointer-0x180000000,'I')==0x07010021+element

    for element in range(10):
        for slot in range(4):
            for tick in [0,7,8,16,24,32,40,48,56,63,64]:
                setup();x=slot*48-35+element*14;y=237
                put(base+0x12cea40,'I',tick)
                frame=[0,1,2,3,4,3,2,1][tick//8%8]
                u=element//5*120+frame*24;v=element%5*24
                u0,u1=(u+24,u) if tick//8%8>4 else (u,u+24)
                reg('rdi',element);reg('rsi',x&0xffffffff);reg('rbp',y)
                submitted=[]
                def capture(rva,rsp):
                    submitted.append(uc.reg_read(regs['rdx']))
                run(sym['ui_spirit_icon'],[0x60bf0],capture)
                assert len(submitted)==get(context+0x4e0,'I')
                ops=[get(p,'I') for p in submitted]
                assert ops[:2]==[0x14,0x22] and ops[-2:]==[12,8],ops
                assert get(submitted[0]+8,'I')==0xffffffff, 'atlas must not inherit transparent or tinted RGBA'
                bind=submitted[1];obj=data+0x1800+element*24
                assert get(bind+8,'Q')==obj and get(bind+24,'I')==4
                assert bytes(uc.mem_read(obj+8,16))==struct.pack('<4I',7,0,4,element)
                assert get(obj,'Q')==data+0x1900
                dims=submitted[-2];quad=submitted[-1]
                assert struct.unpack('<4f',uc.mem_read(dims+8,16))==(float(u1-u0),24.,8.,8.)
                assert struct.unpack('<5f',uc.mem_read(quad+8,20))==(float(x+83),float(y+17),509.,float(u0),float(v))
                assert x+83>=0 and x+91<=480 and y+17+8<=270
                # Run the actual deferred binding command. The special PSX group-8
                # remapping must not replace our native UI atlas group/sub/item.
                reg('rcx',context);reg('rdx',state);reg('r8',bind)
                run(0x5e710,[0x278db0])
                assert get(state+0x1b8,'Q')==obj
                assert (get(state+0x1d4,'I'),get(state+0x1d8,'I'))==(240,120), 'atlas dimensions missing from native binding'
                assert bytes(uc.mem_read(obj+8,16))==struct.pack('<4I',7,0,4,element)
                for command in [submitted[0]]+submitted[2:]:
                    reg('rcx',context);reg('rdx',state);reg('r8',command)
                    run(0x5e710,[0x62010])
                assert get(vertices+0x2000008,'I')==80
                actual_vertices=[struct.unpack('<5f',uc.mem_read(vertices+8+j*20,20)) for j in range(4)]
                assert actual_vertices==[(u0,v,x+83,y+17,509),(u1,v,x+91,y+17,509),
                                         (u0,v+24,x+83,y+25,509),(u1,v+24,x+91,y+25,509)],actual_vertices
                # Run the real renderer's vertex conversion, including its actual
                # state+8 ABI. This caught the old 1x1 binding that sampled outside
                # cage_pic despite apparently correct raw pixel coordinates.
                output=arena+0xb000
                put(state+0xc,'B',1)  # 62010 derives this from format bit 23.
                reg('rcx',state);reg('rdx',vertices+8);reg('r8',output);reg('r9',0x800183)
                put(sp+0x28,'I',4);put(sp+0x30,'Q',state+0x78)
                run(0x657f0)
                for j,(px,py,*_) in enumerate(actual_vertices):
                    uv=struct.unpack('<2f',uc.mem_read(output+j*48+40,8))
                    assert abs(uv[0]-px/240)<1e-6 and abs(uv[1]-(1-py/120))<1e-6,uv
                    assert all(0<=c<=1 for c in uv), 'UV outside real atlas'
                # Actual resolver, including palette vectors, then native handle
                # access stubbed only at the platform-owned resource boundary.
                reg('rcx',obj);handles=[]
                def resource(rva,rsp):
                    handles.append(uc.reg_read(regs['rdx']));reg('rax',901)
                assert run(sym['ui_spirit_texture_resource'],[0x5c170],resource)==101+element
                assert handles==[101+element]
                # Native UV method; float input pixels become normalized UVs.
                reg('rcx',obj);reg('rdx',arena+0x9800)
                # Native 657f0 passes state+8 to the UV method (65855/65943).
                # Do not fabricate dimensions as the old test did: use binding.
                put(sp+0x28,'Q',state+8)
                for register,value in [(UC_X86_REG_XMM2,float(element//5*120)),(UC_X86_REG_XMM3,float(element%5*24))]:
                    uc.reg_write(register,struct.unpack('<I',struct.pack('<f',value))[0])
                run(0x69120)
                actual=struct.unpack('<2f',uc.mem_read(arena+0x9800,8))
                expected=(element//5*.5,1-element%5*.2)
                assert all(abs(a-b)<1e-6 for a,b in zip(actual,expected))

    for exclusion in ['no_context','no_buffer','capacity','bad_spirit']:
        setup();reg('rdi',0);reg('rsi',0);reg('rbp',234)
        if exclusion=='no_context':put(base+0x644a10,'Q',0)
        if exclusion=='no_buffer':put(context+0x4d0,'Q',0)
        if exclusion=='capacity':put(context+0x4d8,'Q',9)
        if exclusion=='bad_spirit':reg('rdi',10)
        run(sym['ui_spirit_icon'])
        assert get(context+0x4e0,'I')==0,exclusion
    for missing in [0x644a28,0x644a30]:
        setup();put(base+missing,'Q',0);reg('rcx',data+0x1800)
        assert run(sym['ui_spirit_texture_resource'])==0
    put(base+0x644a10,'Q',0);put(base+0x644a28,'Q',0);put(base+0x644a30,'Q',0)
    put(base+0x6449d0,'Q',0);put(base+0x644a58,'Q',0)
    uc.mem_unmap(arena,0x10000)
    uc.mem_unmap(vertices,0x2001000)
    return count
