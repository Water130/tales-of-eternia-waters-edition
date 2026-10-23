"""Native descriptor capture, binding, and UV scaling across overlapping loads."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_spell_textures(u, base, m, actors, sp, reset, put, get, reg, regs):
    info=m['spell_textures'];sym=m['symbols'];state=base+info['state_rva']
    area=0x65000000;u.mem_map(area,0x20000)
    manager=area;head=area+0x100;nodes=area+0x200;objects=area+0x1000
    renderer=area+0x2000;commands=area+0x3000;output=area+0x8000
    end=base+m['code_rva']-16;count=0;submitted=[]
    def step(_,a,size,user):
        if a==base+0x60bf0:
            submitted.append(u.reg_read(regs['rdx']))
            s=u.reg_read(UC_X86_REG_RSP)
            u.reg_write(UC_X86_REG_RIP,get(s,'Q'));u.reg_write(UC_X86_REG_RSP,s+8)
    h=u.hook_add(UC_HOOK_CODE,step)
    def run(target,stop=None,entry=None):
        nonlocal count
        count+=1;s=sp if entry is None else entry
        put(s,'Q',end);u.reg_write(UC_X86_REG_RSP,s)
        dest=end if stop is None else base+stop
        def stop_at(_,a,size,user):
            if a==dest:u.emu_stop()
        stop_hook=u.hook_add(UC_HOOK_CODE,stop_at)
        try:u.emu_start(base+(sym[target] if isinstance(target,str) else target),end+16,count=1000000)
        finally:u.hook_del(stop_hook)
        assert u.reg_read(UC_X86_REG_RIP)==dest,(target,hex(u.reg_read(UC_X86_REG_RIP)-base))
        if stop is None:assert u.reg_read(UC_X86_REG_RSP)==s+8
    def load(effect,width,height):
        # Two linked parts plus a foreign asset at a different VRAM key.
        u.mem_write(area,b'\0'*0x2000)
        put(base+0x11c9e18,'Q',manager);put(manager+0x48,'Q',head)
        put(head,'QQQ',nodes,nodes, nodes+0x100);put(head+0x19,'B',1)
        for i in range(3):
            node=nodes+i*0x80;p=objects+i*0x100
            put(node,'QQQ',head,head if i==0 else node-0x80,
                head if i==2 else node+0x80)
            put(node+0x20,'QQ',0x70000000+i*0x100,p)
            put(p,'Q',base+0x51a700)
            put(p+8,'III',4,effect+122 if i<2 else 999,i)
            put(p+0x1c,'IIIII',i*64,0,width,height,4)
            put(p+0x30,'Q',0x70000000+i*0x100)
        put(objects+0x40,'Q',objects+0x100)
        put(objects+0x50,'Q',objects+0x200)  # must not retain foreign links
        put(base+0x12d0efa,'B',effect);reg('rcx',effect)
        native_before=bytes(u.mem_read(area,0x2000))
        run('spell_texture_capture')
        assert bytes(u.mem_read(area,0x2000))==native_before
        bank=state+effect*info['bank_size']
        assert get(bank,'I')==2
        first=bank+0x20;second=first+info['stride']
        assert get(first+0x40,'Q')==second and get(first+0x50,'Q')==0
        assert get(first+0x24,'I')==width
        return first
    try:
        reset()
        put(base+m['data_rva']+0x1a45,'B',1)
        # Spell A remains intact after B overwrites the very same native objects.
        for a,b in ((66,4),(4,66),(61,62),(1,25),(38,4),(4,38),(43,66),(77,1),(30,38)):
            first=load(a,32,128)
            saved=bytes(u.mem_read(first,0x68))
            second=load(b,64,256)
            assert bytes(u.mem_read(first,0x68))==saved
            assert first!=second
            for effect,expected,w,hgt in ((a,first,32,128),(b,second,64,256)):
                put(base+0x59431c,'i',effect+122)
                put(base+0x594300,'i',-1);put(base+0x865a20,'Q',0)
                put(base+0x865a2c,'I',1)
                put(base+0x594308,'I',64);put(base+0x594310,'I',64)
                put(base+0x644a10,'Q',renderer)
                put(renderer+0x4d0,'QQI',commands,64,0)
                put(renderer+0x4e0,'I',0);submitted.clear()
                reg('rcx',16);reg('rdx',0x70000000)
                run(0x11cfc0)
                binds=[p for p in submitted if get(p,'I')==0x26]
                assert len(binds)==1
                assert get(binds[0]+8,'Q')==expected
                assert get(binds[0]+0x24,'I')==effect+122
                # Execute original UV-scale method with the selected descriptor.
                put(output+0x1ec,'B',1)
                put(output+0x1f0,'II',64,64)
                reg('rcx',expected);reg('rdx',output+0x400);reg('r8',output)
                run(0x68e80)
                assert get(output+0x400,'f')==64/(w*4)
                assert get(output+0x404,'f')==64/hgt
            # Native latest descriptor now demonstrably has different UV scaling.
            reg('rcx',objects);reg('rdx',output+0x400);reg('r8',output)
            run(0x68e80)
            assert get(output+0x400,'f')!=64/(32*4)
        # Missing texture/unknown asset use the unmodified native fallback.
        for effect,key in ((0,0x70000000),(999,0x70000000),(66,0xdeadbeef)):
            reg('rsi',objects);reg('rdi',key);put(base+0x59431c,'i',effect+122)
            run('spell_texture_lookup',0x11d03e)
            assert u.reg_read(regs['rsi'])==objects
        # Capture wrapper preserves live volatile registers and replays RSI load.
        put(base+0x12d0efa,'B',0);reg('r12',122);put(base+0x8659d8,'Q',0x12345678)
        before={r:u.reg_read(regs[r]) for r in ('rax','rcx','rdx','r8','r9','r10','r11')}
        run(0x115747,0x11574e,sp-8)
        assert before=={r:u.reg_read(regs[r]) for r in before}
        assert u.reg_read(regs['rsi'])==0x12345678
        reg('r13',66);reg('r12',188);put(sp-8+0x40,'Q',0xfeed4321)
        run(0x75f17,0x75f1c,sp-8)
        assert u.reg_read(regs['r15'])==0xfeed4321
        assert get(state+66*info['bank_size'],'I')==0, 'cached path must refresh stale descriptors'
        # Replay the native type-5 branch which resets R13: the texture
        # resource still lives in R12. Capture must not depend on R13/pending ID.
        for effect in (1,4,38,43,61,62,66,77):
            first=load(effect,48,160)
            put(state+effect*info['bank_size'],'I',0)
            reg('r12',effect+122);reg('r13',effect)
            run(0x75e74,0x75e7c,sp-8)
            assert u.reg_read(regs['r13'])==0
            put(sp-8+0x40,'Q',0xfeed4321)
            run(0x75f17,0x75f1c,sp-8)
            assert get(state+effect*info['bank_size'],'I')==2
            assert get(first+0x24,'I')==48
            put(state+effect*info['bank_size'],'I',0)
            put(base+0x12d0efa,'B',25 if effect!=25 else 1)
            run(0x115747,0x11574e,sp-8)
            assert get(state+effect*info['bank_size'],'I')==2
            # Continuation uploads bypass the other two loader hooks.
            put(state+effect*info['bank_size'],'I',0)
            reg('r13',effect+122);put(base+0x12d0efb,'B',9)
            run(0x115cd4,0x115cdb,sp-8)
            assert get(state+effect*info['bank_size'],'I')==2
            assert u.reg_read(regs['rdx'])==9
        # Empty/malformed/oversized traversal cannot leave a partial cache valid.
        put(base+0x12d0efa,'B',66);reg('rcx',66);put(base+0x11c9e18,'Q',0)
        run('spell_texture_capture')
        assert get(state+66*info['bank_size'],'I')==0
        # A malformed tree is bounded and cannot publish a partial snapshot.
        load(66,32,128)
        put(nodes+8,'Q',nodes);put(nodes+0x10,'Q',head)
        reg('rcx',66);run('spell_texture_capture')
        assert get(state+66*info['bank_size'],'I')==0
        before=bytes(u.mem_read(state+30*info['bank_size'],info['bank_size']))
        reg('rcx',78);run('spell_texture_capture')
        assert bytes(u.mem_read(state+30*info['bank_size'],info['bank_size']))==before
    finally:
        u.hook_del(h);u.mem_unmap(area,0x20000)
        put(base+0x11c9e18,'Q',0);put(base+0x644a10,'Q',0)
    return count
