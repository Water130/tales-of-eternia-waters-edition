"""Native PNG registration/loading/cleanup, deferred draw, UVs and failure cases."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from title_logo_patch import PNG

def check_title_logo(u,base,m,sp,reset,put,get,reg,regs):
    arena=0x54000000;vertices=0x55000000
    u.mem_map(arena,0x10000);u.mem_map(vertices,0x2001000)
    sym=m['symbols'];data=base+m['data_rva'];cache=data+0x1c00
    manager=arena;pool=arena+0x400;array=arena+0x800;native=arena+0x1000
    context=arena+0x2000;commands=arena+0x3000;state=arena+0x8000
    api=arena+0xe000;sentinel=base+m['data_rva']-16
    count=0;calls=[];submitted=[];no_alloc=False;png_handle=701
    def return_(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('ABI',hex(u.reg_read(UC_X86_REG_RIP)))
        for name in ('rcx','rdx','r8','r9','r10','r11'):reg(name,0xdead0000)
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def step(_,a,size,user):
        rcx=u.reg_read(regs['rcx']);rdx=u.reg_read(regs['rdx'])
        if a in (api,api+0x10):calls.append(('lock' if a==api else 'unlock',rcx));return_()
        elif a==base+0x261290:
            assert (rcx,rdx,u.reg_read(regs['r8']))==(0x30,1,8)
            calls.append(('allocate',rcx));return_(0 if no_alloc else native)
        elif a==base+0x2655b0:return_(arena+0xd000)
        elif a==api+0x20:calls.append(('free_node',rdx));return_()
        elif a==api+0x30:
            assert rdx==24;return_(arena+0xc000)
        elif a==api+0x40:
            assert bytes(u.mem_read(rcx,rdx))==PNG.read_bytes()
            calls.append(('png',rdx));return_(png_handle&0xffffffff)
        elif a==api+0x50:calls.append(('release_png',rcx));return_()
        elif a==base+0x279690:calls.append(('free_object',rcx));return_()
        elif a==base+0x60bf0:submitted.append(rdx);return_()
        elif a in (base+0x278db0,base+0x62010):return_()
    hook=u.hook_add(UC_HOOK_CODE,step)
    def setup():
        reset();u.mem_write(arena,b'\0'*0x10000);u.mem_write(cache,b'\0'*0xc0)
        calls.clear();submitted.clear()
        put(base+0x644a30,'Q',manager);put(manager+8,'Q',arena+0xd100)
        put(arena+0xd100,'QQQ',api,0,api+0x10)
        put(manager+0x60,'Q',pool);put(manager+0x68,'Q',array)
        put(pool+8,'QQQ',arena+0xa000,1,array)
        put(arena+0xa000,'QQQ',arena+0xa000,arena+0xa000,5)
        put(manager+0x90,'QQ',arena+0xb000,0)
        put(arena+0xb000,'QQ',arena+0xb000,arena+0xb000)
        put(arena+0xd000,'Q',arena+0xd080)
        put(arena+0xd080+8,'Q',api+0x30);put(arena+0xd080+24,'Q',api+0x20)
        put(base+0x8602e8,'Q',api+0x40);put(base+0x8602c0,'Q',api+0x50)
        put(base+0x644a10,'Q',context);put(context+0x4d0,'Q',commands);put(context+0x4d8,'Q',240)
        put(base+0x6449d0,'Q',arena+0xd800);put(base+0x644a58,'Q',vertices)
        put(vertices+0x2000008,'I',0)
    def run(name):
        nonlocal count
        count+=1;saved={k:u.reg_read(regs[k]) for k in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
        u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',sentinel);done=[]
        def stop(_,a,size,user):
            if a==sentinel:done.append(True);u.emu_stop()
        h=u.hook_add(UC_HOOK_CODE,stop)
        try:u.emu_start(base+(sym[name] if isinstance(name,str) else name),sentinel+1,count=30000)
        finally:u.hook_del(h)
        assert done,(name,hex(u.reg_read(UC_X86_REG_RIP)-base))
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        assert saved=={k:u.reg_read(regs[k]) for k in saved}
        return u.reg_read(regs['rax'])
    try:
        setup();assert run('title_logo_initialize')==0
        assert get(array+4*8,'Q')==native and get(native+0x10,'Q')==5
        assert get(manager+0x98,'Q')==1 and get(arena+0xc010,'Q')==native
        assert get(cache+8,'Q')==5 and get(native+0x18,'I')==0xffffffff
        before=list(calls);assert run('title_logo_initialize')==0 and calls==before
        # Execute the actual queued PNG object's loader, then cache reuse.
        reg('rcx',native);assert run(0x5b820)&255==1
        assert get(native+0x18,'I')==701
        before=list(calls)
        for _ in range(5):assert run('title_logo_initialize')==5 and calls==before
        assert run('title_logo_draw')==1
        ops=[get(p,'I') for p in submitted]
        assert ops[:2]==[20,34] and ops[-2:]==[12,8],ops
        bind=submitted[1];dims=submitted[-2];quad=submitted[-1]
        assert (get(bind+16,'I'),get(bind+20,'I'))==(2149,732)
        assert get(quad+8,'f')==293 and get(quad+12,'f')==160
        assert get(dims+16,'f')==124
        assert ops.count(8)==17
        colors=[get(p+8,'I') for p in submitted if get(p,'I')==20]
        assert colors==[0x12ffd080]*8+[0x24ffd080]*8+[0xffffffff],colors
        assert get(cache+0x30,'B')==0
        assert get(context+0x4e0,'I')<180
        # Consume the real native deferred command and pixel-to-UV conversion.
        for command in submitted:
            reg('rcx',context);reg('rdx',state);reg('r8',command);run(0x5e710)
        assert get(vertices+0x2000008,'I')==17*80
        put(state+12,'B',1)
        reg('rcx',state);reg('rdx',vertices+8);reg('r8',arena+0x9000);reg('r9',0x800183)
        put(sp+0x28,'I',4);put(sp+0x30,'Q',state+0x78);run(0x657f0)
        for j,(px,py) in enumerate(((36,153),(2113,153),(36,596),(2113,596))):
            uv=struct.unpack('<2f',u.mem_read(arena+0x9000+j*48+40,8))
            assert abs(uv[0]-px/2149)<1e-6 and abs(uv[1]-(1-py/732))<1e-6,uv
        reg('rcx',data+0x1c40);assert run('title_logo_resource')==5
        # Native owner destructor releases the managed texture and heap object.
        reg('rcx',native);reg('rdx',1);run(0x5b7d0)
        assert ('release_png',701) in calls and ('free_object',native) in calls
        for missing in (0x644a30,0x8602e8):
            setup();put(base+missing,'Q',0);assert run('title_logo_initialize')==0 and not calls
        setup();put(manager+0x60,'Q',0);assert run('title_logo_initialize')==0 and not calls
        setup();no_alloc=True;assert run('title_logo_initialize')==0
        assert [v[0] for v in calls]==['lock','allocate','unlock'];no_alloc=False
        setup();put(pool+0x10,'Q',0);assert run('title_logo_initialize')==0
        assert ('free_object',native) in calls and not any(k=='release_png' for k,v in calls)
        setup();run('title_logo_initialize');png_handle=-1;reg('rcx',native)
        assert run(0x5b820)&255==0 and run('title_logo_initialize')==0;png_handle=701
        for missing in ('context','buffer','capacity'):
            setup()
            if missing=='context':put(base+0x644a10,'Q',0)
            elif missing=='buffer':put(context+0x4d0,'Q',0)
            else:put(context+0x4d8,'Q',10)
            assert run('title_logo_draw')==0 and not calls and not submitted
    finally:
        for addr in (0x644a30,0x644a10,0x644a58,0x6449d0,0x8602e8,0x8602c0):put(base+addr,'Q',0)
        u.mem_write(cache,b'\0'*0xc0)
        u.hook_del(hook);u.mem_unmap(arena,0x10000);u.mem_unmap(vertices,0x2001000)
    return count
