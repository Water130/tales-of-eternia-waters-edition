"""Native area intersection and recoil-table selection, with damage/audio isolated."""
import json,struct
from build_combat_patch import OUT,pefile,digest
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *

m=json.loads((OUT/'manifest.json').read_text());raw=(OUT/'GameNative.dll').read_bytes()
assert digest(raw)==m['patched_sha256'];pe=pefile.PE(data=raw);results=[]
for base in (0x180000000,0x7ffb00000000):
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base,pe.OPTIONAL_HEADER.SizeOfImage)
    u.mem_write(base,pe.get_memory_mapped_image())
    arena,stack=0x40000000,0x50000000;u.mem_map(arena,0x10000);u.mem_map(stack,0x10000)
    fx=base+0x12cfca0;state=base+m['standalone_teamups']['state_rva'];sp=stack+0xff08;end=stack+0x100
    def put(a,f,*v):u.mem_write(a,struct.pack('<'+f,*v))
    def get(a,f):return struct.unpack('<'+f,u.mem_read(a,struct.calcsize('<'+f)))[0]
    recoil_entry={};hits=[]
    def trace(emu,a,s,d):
        rv=a-base
        if rv==0x8e320:
            recoil_entry.update({r:u.reg_read(r) for r in (UC_X86_REG_RSP,UC_X86_REG_RBX,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R14,UC_X86_REG_RBP,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R15)})
            return
        if rv==0x8e3a0:
            victim=u.reg_read(UC_X86_REG_RBX)
            hits.append((get(victim+0x53,'b'),get(victim+0x18,'h'),get(victim+0x1a,'h')))
            for r,v in recoil_entry.items():u.reg_write(r,v)
        elif rv not in (0xb7460,0xc7550,0x8e910,0x279670):return
        rsp=u.reg_read(UC_X86_REG_RSP)
        u.reg_write(UC_X86_REG_RAX,0);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    u.hook_add(UC_HOOK_CODE,trace)
    for caster_x in (-2400,2400):
        facing=1 if caster_x>0 else -1
        for target_x in (-1000,0,1000):
            u.mem_write(arena,bytes(0x10000));u.mem_write(fx,bytes(0x120));hits.clear()
            put(arena+0x10,'h',caster_x);put(arena+0x53,'b',facing)
            victim=arena+0x1000;put(victim+0x3c,'H',1);put(victim+0x51,'B',1)
            put(victim+0x10,'h',target_x);put(victim+0x240,'B',1)
            put(victim+0x140,'4h',target_x//16-10,-32,target_x//16+10,0)
            put(base+0x12cece0,'Q',victim);put(base+0x12cece9,'B',1)
            put(base+0x12ceb74,'B',0);put(base+0x12ceb7a,'B',0)
            put(fx,'Q',arena);put(fx+0x10,'Q',state+0x3300);put(fx+0x38,'H',32)
            put(fx+0x3a,'H',1);put(fx+0x30,'b',facing)
            u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',end);u.reg_write(UC_X86_REG_RCX,fx)
            u.emu_start(base+0xb7c90,end,count=200000)
            assert u.reg_read(UC_X86_REG_RIP)==end and u.reg_read(UC_X86_REG_RSP)==sp+8
            assert len(hits)==1 and hits[0][1]*(target_x-caster_x)>0,(caster_x,target_x,hits)
            results.append(dict(base=hex(base),caster_x=caster_x,target_x=target_x,recoil=hits[0]))
report=dict(passed=True,cases=len(results),sha256=m['patched_sha256'],native_intersection=True,native_initial_recoil=True,damage_stubbed=True,results=results)
(OUT/'tidal-recoil-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
