"""Actual patched water renderer, native projection, vertex colors and fades.

Only texture binding / GPU command dispatch are stubbed. Never starts the game.
"""
import json,struct
from build_combat_patch import OUT,pefile,digest
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *

m=json.loads((OUT/'manifest.json').read_text());raw=(OUT/'GameNative.dll').read_bytes()
assert digest(raw)==m['patched_sha256'];pe=pefile.PE(data=raw)
info=m['standalone_teamups']['tidal_presentation'];results=[]
for base in (0x180000000,0x7ffb00000000):
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base,pe.OPTIONAL_HEADER.SizeOfImage)
    u.mem_write(base,pe.get_memory_mapped_image())
    fx,stack,vertices=0x40000000,0x50000000,0x60000000
    u.mem_map(fx,0x10000);u.mem_map(stack,0x10000);u.mem_map(vertices,0x2001000)
    sp=stack+0xff08;end=stack+0x100;binds=[];blends=[];quads=[];native_colors=[];layers=[]
    def put(a,f,*v):u.mem_write(a,struct.pack('<'+f,*v))
    def get(a,f):return struct.unpack('<'+f,u.mem_read(a,struct.calcsize('<'+f)))[0]
    def trace(emu,a,s,d):
        rv=a-base
        if rv==0x11f0aa:
            q=u.reg_read(UC_X86_REG_RBX)
            layers.append(get(base+info['layer'],'I'))
            native_colors.append([bytes(u.mem_read(q+j*16+4,4)) for j in range(4)])
            return
        if rv==0x11f0b1:
            quads.append(u.reg_read(UC_X86_REG_RBX));return
        if rv==0x11d1c0:
            binds.append((get(base+0x11ce6b2,'H'),get(base+0x11ce680,'H'),get(base+0x11ce6b8,'I')))
        elif rv==0x6fd70:
            blends.append(tuple(u.reg_read(r) for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8)))
        elif rv not in (0x6f440,0x60bf0,0x6c550,0x279670):return
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,(hex(rv),hex(rsp))
        u.reg_write(UC_X86_REG_RAX,1 if rv==0x11d1c0 else 0)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    u.hook_add(UC_HOOK_CODE,trace)
    put(base+0x8659e8,'9h',4096,0,0,0,4096,0,0,0,4096)
    put(base+0x8659fc,'iii',-240,32,1024)
    put(base+0x8c96f0,'i',512);put(base+0x8c9718,'i',160);put(base+0x8c92c4,'i',120)
    put(base+0x12cea68,'Q',fx+0x8000);put(fx+0x8000,'H',0x400)
    put(base+0x573c3e,'B',1);put(base+0x644a58,'Q',vertices);put(base+0x644a10,'Q',0)
    for facing in (-1,1):
        for tick in (0,1,12,24,96,167,179,190,191):
            binds.clear();blends.clear();quads.clear();native_colors.clear();layers.clear();put(vertices+0x2000008,'I',0)
            put(fx+0x30,'b',facing);put(fx+0x38,'H',tick)
            put(base+0x11ce6b2,'H',23);put(base+0x11ce6b4,'I',7)
            saved_draw=bytes(u.mem_read(base+0x11ce640,144))
            u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',end);u.reg_write(UC_X86_REG_RCX,fx)
            try:u.emu_start(base+info['render'],end,count=2000000)
            except Exception as ex:raise AssertionError((tick,facing,hex(u.reg_read(UC_X86_REG_RIP)-base))) from ex
            assert u.reg_read(UC_X86_REG_RIP)==end and u.reg_read(UC_X86_REG_RSP)==sp+8
            assert get(base+info['active'],'Q')==0
            assert bytes(u.mem_read(base+0x11ce640,144))==saved_draw, 'render input state leaked into later draws'
            count=len(quads)
            if tick in (0,191):assert not count
            else:
                assert count>0 and all(b[0]==52 for b in binds), (tick, facing, count, binds[:10], blends[:10])
                assert sum(b==(52,1,0) for b in binds)==count
                assert (0,2,10) in blends,'native additive texture blending not emitted'
                assert layers.count(0)==6, 'all three upper rectangles and three lower rain quads must be translucent'
                assert 1 in layers and (0,2,3) in blends, 'wave opacity path missing'
                for q,original,layer in zip(quads,native_colors,layers,strict=True):
                    alpha=(info['wave_alpha'] if layer else 255)*(min(tick,191-tick,24)*256//24)//256
                    assert [get(q+j*16+7,'B') for j in range(4)]==[alpha]*4
                    factor=min(tick,191-tick,24)*256//24
                    assert [bytes(u.mem_read(q+j*16+4,4)) for j in range(4)]==[
                        bytes(c*factor//256 for c in corner[:3])+bytes([alpha]) for corner in original
                    ],'fade must scale each native RGB corner, not replace its gradient'
                assert get(base+0x11ce6b2,'H')==23 and get(base+0x11ce6b4,'I')==7
            results.append(dict(base=hex(base),tick=tick,facing=facing,quads=count))
    # Unmarked calls still take the unmodified native path.
    put(vertices+0x2000008,'I',0);put(base+0x11ce6b4,'I',0);put(base+0x11ce6b8,'I',1)
    u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',end)
    u.emu_start(base+info['quad'],end,count=200000)
    assert get(base+0x11ce6b8,'I')==1
report=dict(passed=True,cases=len(results),sha256=m['patched_sha256'],native_vertices=True,
            native_projection=True,gpu_stubbed=True,visual_validation=False,results=results)
(OUT/'tidal-presentation-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
