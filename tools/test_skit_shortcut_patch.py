"""Execute shortcut, native eligibility/player and native playback lifecycle.

Only external audio/resource/input services are substituted. No game is run.
"""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_skit_shortcut(u, base, m, actors, sp, reset, put, get, reg, regs):
    sym = m['symbols']; info = m['skit_notice']['shortcut']; sp -= 0x2000
    end = base+m['code_rva']-16; inp = base+0x8c9180
    viewed = base+0x11cb0e8; table = base+0x599980
    config = actors+0x5000; audio = actors+0x5500
    manager = actors+0x6000; context = actors+0x2000
    original_table = bytes(u.mem_read(table, 264*8))
    original_offsets = bytes(u.mem_read(base+0x55ad2c, 0x600))
    original_record = get(base+0x59a620, 'I')
    calls = []; loads = []; count = 0; bridge = False; alias = False
    for rva, length in ((0x4f4710, 5), (0x4f9440, 16)):
        for i in range(length):
            p = base+rva+i*16; value = get(p, 'Q')
            if 0x180000000 <= value < 0x182000000:
                put(p, 'Q', value-0x180000000+base)

    def ret(value=0):
        s = u.reg_read(UC_X86_REG_RSP)
        assert s % 16 == 8, ('ABI alignment', hex(u.reg_read(UC_X86_REG_RIP)-base))
        for name in ('rcx','rdx','r8','r9','r10','r11'):reg(name,0xdead0000)
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(s,'Q'))
        u.reg_write(UC_X86_REG_RSP,s+8)

    def code(_, address, size, user):
        rva = address-base
        if rva == 0x13acc0:
            calls.append(u.reg_read(regs['rcx']))  # Run actual native player.
        elif rva == 0x259c10:
            assert u.reg_read(regs['rcx']) == 0xaf0
            assert u.reg_read(regs['rdx']) == base+0x867108
            assert u.reg_read(regs['r9']) > 0
            loads.append((u.reg_read(regs['r8']),u.reg_read(regs['r9'])))
            pending = get(u.reg_read(UC_X86_REG_RSP)+0x28,'Q')
            assert pending == base+0x866f84
            put(pending,'H',1);ret()
        elif rva in (0x6b8a0,0xf570,0xf5f0,0x1b4e30):ret()  # Engine/audio API.
        elif rva == 0x2a4880:
            dest,n=u.reg_read(regs['rcx']),u.reg_read(regs['r8'])
            assert n<0x100000,('memset size',hex(dest),hex(n),hex(get(u.reg_read(UC_X86_REG_RSP),'Q')-base))
            u.mem_write(dest,bytes([u.reg_read(regs['rdx'])&255])*n);ret(dest)
        elif rva == 0x2a41e0:
            dest,src,n=(u.reg_read(regs[x]) for x in ('rcx','rdx','r8'))
            u.mem_write(dest,bytes(u.mem_read(src,n)));ret(dest)
        elif rva == 0x1a5b80:ret()  # Native skit-count achievement boundary.
        elif rva == sym['artesphere_keyboard'] and bridge:
            if alias:put(inp,'I',get(inp,'I')|0x40000)
            ret()
        elif rva == 0x16ab39:
            raise AssertionError('Shortcut entered camp action')

    h = u.hook_add(UC_HOOK_CODE,code)

    def setup(mode=2,region=0,language=0):
        reset();calls.clear();loads.clear()
        u.mem_write(inp,b'\0'*0x144)
        u.mem_write(base+m['data_rva']+0x1a60,b'\0'*12)
        put(base+info['flag_rva'],'B',1)
        put(base+m['data_rva']+0x1a07,'B',1)
        u.mem_write(base+0x11ca700,b'\0'*0x1e00)
        u.mem_write(viewed,b'\xff'*44);put(viewed,'I',0xfffffffc)
        u.mem_write(table,struct.pack('<BBHhh',0,1 if mode==6 else 0,0,0,32767)*2)
        put(base+0x59a620,'I',1)
        put(base+0x119ea28,'H',mode);put(base+0x11cc542,'B',0x40)
        put(base+0x119ea49,'B',0);put(base+0x8c2a28,'B',0)
        for rva in (0x866f80,0x866f84,0x8c9f98,0x62ae30,0x62ae34,0x8c8a80,0x8c8a90):
            put(base+rva,'H',0)
        put(base+0x8ca0c0,'h',-1);put(base+0x8cab71,'B',0)
        put(base+0x11cc540,'B',0);put(base+0x8befb0,'I',0)
        for i in range(6):put(base+0x11a7b46+i*0x68,'H',0)
        put(base+0x8cdb08,'h',100);put(base+0x11cb354,'B',region)
        put(base+0x8befc0,'Q',actors);put(actors+4,'B',region)
        put(actors+8,'H',0);put(actors+0x13a0,'Q',context)
        put(context+0xc0,'Q',base+0x15ea90)
        for off,p in ((0x598,0x3000),(0x580,0x3500),(0x5a8,0x3800)):
            put(actors+off,'Q',actors+p)
        put(actors+0x5d0,'ii',65536,65536)
        put(actors+0x570,'B',12 if region==0 else 0x50)
        put(actors+0x22,'H',2400)
        put(base+0x11cad10,'6H',1,2,3,4,5,6)
        put(base+0x644a60,'Q',config);put(config+0x10,'I',language)
        put(base+0x644a28,'Q',audio);put(audio+8,'I',9)
        put(base+0x11c9e18,'Q',manager)
        put(base+0x644a48,'Q',actors+0x7000)
        put(base+0x644a10,'Q',0);put(base+0x644a58,'Q',0)
        # Deterministic existing-resource offsets for both voice packs.
        for index in (1,2,0x179,0x17a):
            put(base+0x55ad2c+index*4,'II',index*0x1000,(index+1)*0x1000)
        put(base+0x11cb356,'B',7)
        put(base+0x8cab78,'Q',0)
        put(base+0x8cb396,'H',1)  # Native event pool always reserves slot zero.
        put(base+0x8c9f94,'I',0);put(base+0x8c9f4e,'H',0)
        put(base+0x8ca0a0,'Q',actors+0x7800)
        put(base+0x8ca098,'Q',actors+0x7800)
        put(base+0x8ca0b4,'I',0);put(base+0x8ca0b8,'I',0)
        # Normal native defaults, not an invented L2-free configuration.
        defaults=(1,2,25,27,28,26,12,14,5,1,12,14)
        for i,value in enumerate(defaults):put(config+0x54+4*i,'I',value)

    def run(rva,entry=None,stop=None):
        nonlocal count
        count+=1;s=sp if entry is None else entry
        u.reg_write(UC_X86_REG_RSP,s);put(s,'Q',end)
        target=end if stop is None else base+stop;reached=[]
        saved={r:u.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
        def halt(_,a,size,user):
            if a==target:reached.append(a);u.emu_stop()
        hh=u.hook_add(UC_HOOK_CODE,halt)
        try:
            u.emu_start(base+(sym[rva] if isinstance(rva,str) else rva),end+16,count=2000000)
        except Exception as e:
            raise AssertionError((rva,hex(u.reg_read(UC_X86_REG_RIP)-base),str(e))) from e
        finally:u.hook_del(hh)
        assert reached,(rva,'did not return',hex(u.reg_read(UC_X86_REG_RIP)-base))
        if stop is None:
            assert u.reg_read(UC_X86_REG_RSP)==s+8,'stack imbalance'
            assert saved=={r:u.reg_read(regs[r]) for r in saved},'callee registers changed'

    def press(value,buffer=None):
        p=inp if buffer is None else buffer
        put(p,'4I',value,value,value,value);reg('rcx',p)
        run('skit_shortcut_input')

    def close_native():
        # Model a completed async read. Run actual native resource initialization
        # and script-context backup, then the real native end-of-skit cleanup.
        put(base+0x119e988+0x120,'Q',0)
        put(base+0x867108,'II',2,0x100)
        put(base+0x867104,'I',1)
        put(base+0x867208,'4H',4,0,0,0)  # Empty valid script, no event opcodes.
        put(base+0x8c9f94,'I',1)  # Native interpreter already busy: no opcodes.
        variables=bytearray((i*13+5)&255 for i in range(0x800))
        struct.pack_into('<h',variables,0x48,100)  # Current story checkpoint.
        variables=bytes(variables)
        u.mem_write(base+0x8cdac0,variables)
        run(0x13a200)
        assert get(base+0x866f84,'H')==0
        assert bytes(u.mem_read(base+0x11cde20,0x800))==variables,'script backup'
        u.mem_write(base+0x8cdac0,b'\0'*0x800)
        run(0x1395d0)
        assert get(base+0x866f80,'H')==0
        assert get(audio+8,'I')==9 and get(base+0x11cb356,'B')==7
        assert bytes(u.mem_read(base+0x8cdac0,0x800))==variables,'script restore'
        # Advance past the native exit fade before trying a new shortcut.
        put(base+0x62ae30,'H',0);put(base+0x62ae34,'H',0)

    try:
        for mode,region in ((2,0),(2,3),(6,0),(6,3)):
            for language in (0,1):
                setup(mode,region,language)
                before=bytes(u.mem_read(actors,0x2000))
                run('skit_exploration_context')
                assert u.reg_read(regs['rax'])==mode,('context',mode,region,u.reg_read(regs['rax']))
                run('skit_notice_probe')
                assert u.reg_read(regs['rax'])==1,('probe',mode,region,u.reg_read(regs['rax']))
                press(0x40000|0x100)
                assert calls==[1] and len(loads)==1,(mode,region,language,calls)
                assert get(viewed,'I')==0xfffffffd
                assert get(base+0x866f80,'H')==1 and get(audio+8,'I')==3
                assert all(get(inp+i,'I')==0x100 for i in (0,4,8,12))
                assert before==bytes(u.mem_read(actors,0x2000)),'party/world changed'
                close_native()
                # Held after native cleanup must not play the next skit.
                for _ in range(3):press(0x40000)
                assert calls==[1]
                press(0);press(0x40000)
                assert calls==[1,2],calls

        # A hidden notification does not disable this independent option.
        setup();put(base+m['data_rva']+0x1a07,'B',0);press(0x40000)
        assert calls==[1]
        setup(6);put(base+0x8befb0,'I',1);press(0x40000)
        assert calls==[1],'stale world pause must not block field'

        guards=[(info['flag_rva'],'B',0),(0x119ea28,'H',0),(0x119ea28,'H',7),
                (0x119ea49,'B',1),(0x11cc542,'B',0),(0x866f80,'H',1),
                (0x866f84,'H',1),(0x8c9f98,'H',1),(0x8ca0c0,'h',0),
                (0x8cab71,'B',4),(0x8cab71,'B',8),(0x11cc540,'B',0x10),
                (0x62ae30,'H',1),(0x62ae34,'H',1),(0x8c8a80,'H',1),
                (0x8c8a90,'H',1),(0x8befb0,'I',1),(0x644a60,'Q',0),
                (0x11c9e18,'Q',0),(0x8befc0,'Q',0)]
        guards += [(0x11a7b46+i*0x68,'H',1) for i in range(6)]
        for rva,fmt,value in guards:
            setup();old=get(base+rva,fmt);put(base+rva,fmt,value)
            before=bytes(u.mem_read(viewed,44));press(0x40000)
            assert not calls and before==bytes(u.mem_read(viewed,44)),hex(rva)
            assert get(inp,'I')==0x40000,('blocked input consumed',hex(rva))
            put(base+rva,fmt,old);press(0x40000)
            assert not calls,('late launch after guard clears',hex(rva))
        for key in (0,1,8,0x80000,0x20000):
            setup();press(key);assert not calls and get(inp,'I')==key
        setup();press(0x40000,actors+0x8000)
        assert not calls and get(actors+0x8000,'I')==0x40000
        setup();u.mem_write(viewed,b'\xff'*44);press(0x40000)
        assert not calls and not loads and bytes(u.mem_read(viewed,44))==b'\xff'*44

        # Every exploration action may be rebound. Require a chord, preserve
        # all other action banks and suppress the rebound native action.
        for action in range(13,25):
            for order in ('l2','select','together'):
                setup();put(config+0x20+4*action,'I',13)
                if order!='together':
                    first=0x40000 if order=='l2' else 1
                    press(first);assert not calls and get(inp,'I')==first
                for bank in (0xa4,0xc4,0xe4,0x104):u.mem_write(inp+bank,b'\1'*32)
                press(0x40001|0x100)
                assert calls==[1],(action,order)
                for bank in (0xa4,0xc4,0xe4,0x104):
                    expect=bytearray(b'\1'*32);expect[action]=0
                    assert bytes(u.mem_read(inp+bank,32))==bytes(expect)
                assert get(inp,'I')==0x100
                press(0x40000);press(1)
                assert calls==[1]  # Remains consumed until both released.
        # Combat-only L2 bindings do not require Select in exploration.
        setup();put(config+0x20,'I',13);press(0x40000);assert calls==[1]

        # Real poll-tail hook, real keyboard bridge, external key polling stub.
        # The alias is synthesized before the shortcut sees the input buffer.
        for alias in (False,True):
            setup();bridge=True
            put(inp,'I',0 if alias else 0x40000)
            entry=sp-8
            for offset,value in ((0x30,0x123),(0x38,0x234),(0x40,0x345),(0x48,0x456)):
                put(entry+offset,'Q',value)
            reg('rax',0x98765432);reg('rbx',inp)
            run(0x19df3d,entry=entry,stop=0x19df42)
            assert calls==[1] and u.reg_read(regs['rax'])==0x98765432
            assert u.reg_read(regs['rbx'])==0x123
            assert u.reg_read(UC_X86_REG_RSP)==entry
            bridge=False
    finally:
        u.hook_del(h);u.mem_write(table,original_table)
        u.mem_write(base+0x55ad2c,original_offsets);put(base+0x59a620,'I',original_record)
    return count
