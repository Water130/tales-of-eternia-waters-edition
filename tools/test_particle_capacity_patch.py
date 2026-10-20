"""Execute native constructors and updaters across saturation and pause states."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP
from particle_capacity_patch import TYPES, BANK_SIZE, BANKS


def check_particle_capacity(u, base, m, sp, reset, put, get, reg, regs):
    extra = base+m['particle_capacity']['state_rva']
    arena = 0x62000000
    u.mem_map(arena, 0x10000)
    source = arena+0x7000; dummy = arena+0x8000
    end = base+m['code_rva']-16; count = 0
    constructors = dict(sprite=0x8b540,line=0x8b5f0,quad=0x8b6a0,mesh=0x8b7e0)
    delays = dict(sprite=0x34,line=0xa,quad=0x56,mesh=0x1a)

    def setup():
        reset();u.mem_write(arena, b'\0'*0x10000)
        u.mem_write(extra, b'\0'*(BANK_SIZE*BANKS))
        put(base+0x12cecf0, 'Q', arena)
        put(base+0x12cec20, 'Q', dummy)

    def run(entry, stop=None):
        nonlocal count
        count+=1; saved={r:u.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
        u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',end)
        target=base+stop if stop else end; reached=[]
        def step(_,a,size,user):
            if a==target: reached.append(a);u.emu_stop()
            elif a==base+0x11e6f0:  # Native quad submission, no graphics device.
                s=u.reg_read(UC_X86_REG_RSP)
                assert s%16==8
                u.reg_write(UC_X86_REG_RIP,get(s,'Q'));u.reg_write(UC_X86_REG_RSP,s+8)
        h=u.hook_add(UC_HOOK_CODE,step)
        try:u.emu_start(base+entry,end+1,count=1000000)
        except Exception as e:
            raise AssertionError((hex(entry),hex(u.reg_read(UC_X86_REG_RIP)-base),str(e))) from e
        finally:u.hook_del(h)
        assert reached,hex(entry)
        assert saved=={r:u.reg_read(regs[r]) for r in saved}
        assert u.reg_read(UC_X86_REG_RSP)==sp+(0 if stop else 8)
        return u.reg_read(regs['rax'])

    try:
        for name,off,stride,capacity,active,flags,site,size,continuation,updater,*_ in TYPES:
            setup()
            put(source+active,'B',6 if name=='line' else 1)
            put(source+delays[name],'H',200)
            put(source,'hh',320,480)
            put(base+0x12ceb82,'hh',16,32)
            returned=[]
            for bank in [arena]+[extra+i*BANK_SIZE for i in range(BANKS)]:
                for i in range(capacity):
                    reg('rcx',source)
                    p=run(constructors[name]);returned.append(p)
                    assert p==bank+off+i*stride,(name,i,hex(p))
                    assert (get(p,'h'),get(p+2,'h'))==(336,512)
            assert len(set(returned))==capacity*4
            # One more request retains the native bounded dummy fallback.
            reg('rcx',source);assert run(constructors[name])==dummy
            # Full native pool used to lose all those extra particles. Execute
            # its original fallback bytes to demonstrate the old saturation.
            change=next(e for e in m['edits'] if e['rva']==site)
            patched=bytes(u.mem_read(base+site,len(bytes.fromhex(change['original']))))
            u.mem_write(base+site,bytes.fromhex(change['original']))
            u.ctl_remove_cache(base+site,base+site+len(patched))
            reg('rcx',source);assert run(constructors[name])==dummy
            u.mem_write(base+site,patched);u.ctl_remove_cache(base+site,base+site+len(patched))
            # Execute all four real native update passes. Their delay counters
            # allow the whole life-cycle loop to run without a graphics device.
            for pause in (0,1,0):
                put(base+0x12ceb7a,'B',pause)
                before=[get(p+delays[name],'H') for p in returned]
                run(updater)
                assert get(base+0x12cecf0,'Q')==arena, 'native pool pointer leaked'
                assert [get(p+delays[name],'H') for p in returned]==[v-(pause==0) for v in before],name
            # Pause blocks allocations even if overflow storage is free.
            put(returned[-1]+active,'B',0)
            put(base+0x12ceb7a,'B',1);reg('rcx',source)
            assert run(constructors[name])==dummy
            put(base+0x12ceb7a,'B',0);reg('rcx',source)
            assert run(constructors[name])==returned[-1], 'expired slot not reused'
            # Native clear preserves protected bit 8, and does not clear bytes
            # of other types or unrelated memory.
            for i,p in enumerate(returned[capacity:]):
                put(p+flags,'B',8 if i%2 else 0)
            run(m['symbols']['particle_clear_effects'],0x83231)
            for i,p in enumerate(returned[capacity:]):
                assert get(p+active,'B')==(6 if name=='line' else 1) if i%2 else get(p+active,'B')==0
            # Battle initialization clears all overflow slots, including ones
            # protected in the previous fight; the original pointer is kept.
            reg('rbx',arena)
            run(m['symbols']['particle_reset_battle'],0xd6512)
            assert bytes(u.mem_read(extra,BANK_SIZE*BANKS))==b'\0'*(BANK_SIZE*BANKS)
            assert get(base+0x12cecf0,'Q')==arena
    finally:
        put(base+0x12cecf0,'Q',0);put(base+0x12cec20,'Q',0)
        u.mem_unmap(arena,0x10000)
    return count
