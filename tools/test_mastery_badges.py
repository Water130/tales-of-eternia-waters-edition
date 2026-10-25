"""Execute native badge rendering through its real texture/label calls."""
import json, struct
from build_combat_patch import OUT, pefile, digest
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

manifest=json.loads((OUT/'manifest.json').read_text())
binary=(OUT/'GameNative.dll').read_bytes()
assert digest(binary)==manifest['patched_sha256']
pe=pefile.PE(data=binary)
checks=[]
for base in (0x180000000,0x7ffb00000000):
    u=Uc(UC_ARCH_X86,UC_MODE_64)
    u.mem_map(base,(pe.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff)
    u.mem_write(base,pe.get_memory_mapped_image())
    arena=0x30000000;u.mem_map(arena,0x40000)
    sp=arena+0xff08;stop=base+manifest['data_rva']-16
    def put(p,fmt,*v):u.mem_write(p,struct.pack('<'+fmt,*v))
    def get(p,fmt):return struct.unpack('<'+fmt,u.mem_read(p,struct.calcsize(fmt)))[0]
    def f(r):return struct.unpack('<f',(u.reg_read(r)&0xffffffff).to_bytes(4,'little'))[0]
    colors=[];quads=[];labels=[]
    def boundary(_,addr,size,user):
        if addr-base not in (0x6c550,0x12cb0,0xcb90):return
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
        if addr-base==0x6c550:colors.append(u.reg_read(UC_X86_REG_RCX))
        elif addr-base==0x12cb0:
            quads.append((f(UC_X86_REG_XMM1),f(UC_X86_REG_XMM2),
                          get(rsp+0x28,'f'),get(rsp+0x30,'f'),
                          tuple(get(rsp+off,'f') for off in (0x38,0x40,0x48,0x50))))
        else:labels.append((u.reg_read(UC_X86_REG_RCX),f(UC_X86_REG_XMM1),f(UC_X86_REG_XMM2),
                            get(rsp+0x28,'f'),get(rsp+0x30,'I'),get(rsp+0x40,'f')))
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    u.hook_add(UC_HOOK_CODE,boundary)
    cases=0
    for lang in (1,3):
        put(base+0x11c9ce8,'B',lang)
        for element in range(11):
            for opacity in (128,255):
                colors.clear();quads.clear();labels.clear()
                u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop)
                for r,v in ((UC_X86_REG_RCX,element),(UC_X86_REG_RDX,280),(UC_X86_REG_R8,33),(UC_X86_REG_R9,opacity)):u.reg_write(r,v)
                u.emu_start(base+manifest['symbols']['mastery_element_badge'],stop,count=10000)
                assert u.reg_read(UC_X86_REG_RIP)==stop
                assert len(quads)==1 and quads[0][:2]==(280.,33.),quads
                assert quads[0][2:4]==(14.,14.),quads
                rgb=get(base+0x50ff58+element*4,'I')&0xffffff
                assert colors==[rgb|(opacity<<24)],colors
                assert len(labels)==1
                cases+=1
                original=quads[0];original_label=labels[0]
                colors.clear();quads.clear();labels.clear()
                u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop)
                for r,v in ((UC_X86_REG_RCX,element),(UC_X86_REG_RDX,280),(UC_X86_REG_R8,33),(UC_X86_REG_R9,opacity)):u.reg_write(r,v)
                u.emu_start(base+manifest['symbols']['mastery_compact_element_badge'],stop,count=10000)
                assert u.reg_read(UC_X86_REG_RIP)==stop
                assert len(quads)==1 and quads[0][:4]==(280.,33.,10.,10.),quads
                assert quads[0][4]==original[4],quads
                assert colors==[rgb|(opacity<<24)],colors
                assert len(labels)==1 and labels[0][0]==original_label[0]
                assert labels[0][4]==original_label[4],('native label color/opacity',labels)
                assert abs(labels[0][1]-(280.+7.1*10/14))<0.0001
                assert abs(labels[0][2]-(33.+4.*10/14))<0.0001
                assert abs(labels[0][3]-6.*10/14)<0.0001
                assert abs(labels[0][5]-13.5*10/14)<0.0001
                cases+=1
        for aid in (54,55,56,57,58,59,60,67):
            colors.clear();quads.clear();labels.clear()
            u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop)
            for r,v in ((UC_X86_REG_RCX,aid),(UC_X86_REG_RDX,37),(UC_X86_REG_R8,81),(UC_X86_REG_R9,255)):u.reg_write(r,v)
            u.emu_start(base+manifest['symbols']['mastery_spell_badge'],stop,count=10000)
            assert u.reg_read(UC_X86_REG_RIP)==stop
            assert len(quads)==1 and quads[0][:4]==(37.,81.,10.,10.),(aid,quads)
            assert quads[0][4]==(0.875,0.53125,1.0,0.65625),('native green heal glyph',aid,quads)
            assert not labels
            cases+=1
    checks.append(f'{base:x}: {cases} native elemental discs and healing glyphs, UVs/coordinates/opacity/ABI')
report=dict(passed=True,patched_sha256=digest(binary),checks=checks,runtime_validated=False)
(OUT/'mastery-badges-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
