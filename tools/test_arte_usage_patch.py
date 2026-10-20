"""Execute usage hooks, native UI block and save lifecycle under ASLR."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS


def check_arte_usage(u, base, m, actors, sp, reset, put, get, reg, regs):
    sym = m['symbols']
    info = m['artesphere']['usage']
    state = base + m['artesphere']['state_rva']
    live = base + info['live_rva']
    size = info['size']
    data = base + m['data_rva']
    api = 0x65000000
    u.mem_map(api, 0x1000)
    stop = base + m['data_rva'] - 32
    records = {}
    width = 40
    draws = []
    failed = False
    native_save = True
    runs = 0

    def text(ptr, wide=False):
        raw = bytearray()
        step = 2 if wide else 1
        for i in range(2048):
            b = bytes(u.mem_read(ptr+i*step, step))
            if b == b'\0'*step:
                return raw.decode('utf-16-le' if wide else 'utf8')
            raw.extend(b)
        raise AssertionError('unterminated')

    def ret(value=0):
        rsp = u.reg_read(UC_X86_REG_RSP)
        assert rsp % 16 == 8, (hex(u.reg_read(UC_X86_REG_RIP)-base), hex(rsp))
        reg('rax', value)
        for r in ('rcx', 'rdx', 'r8', 'r9', 'r10', 'r11'):
            reg(r, 0xdead0000)
        u.reg_write(UC_X86_REG_RIP, get(rsp, 'Q'))
        u.reg_write(UC_X86_REG_RSP, rsp+8)

    def stub(emu, address, length, _):
        a = address-base
        rcx, rdx, r8, r9 = [u.reg_read(regs[r]) for r in ('rcx','rdx','r8','r9')]
        rsp = u.reg_read(UC_X86_REG_RSP)
        if address == api:
            assert text(rcx) == 'kernel32.dll'
            ret(1)
        elif address == api+0x10:
            ret(api+(0x20 if text(rdx)=='GetPrivateProfileStructW' else 0x30))
        elif address in (api+0x20, api+0x30):
            section = text(rcx, True)
            assert (section, r9) in (('ArteUsage-v1',size+8),('Artesphere-v1',104),('Artesphere-v2',104))
            key = (section, text(rdx,True))
            if address == api+0x30:
                if not failed:
                    records[key] = bytes(u.mem_read(r8,r9))
                ret(int(not failed))
            else:
                if not failed and key in records:
                    u.mem_write(r8, records[key])
                ret(int(not failed and key in records))
        elif a == 0x594d0:
            ret(int(native_save))
        elif a == 0x2a41e0:
            u.mem_write(rcx,bytes(u.mem_read(rdx,r8)))
            ret(rcx)
        elif a == 0xd180:
            ret(width)
        elif a == 0xceb0:
            draws.append(('number',rcx,rdx,get(rsp+0x40,'I')))
            ret()
        elif a == 0xb480:
            draws.append(('label',))
            ret()
        elif a in (0x25aaa0,0x25a090):
            draws.append(('box',rcx,rdx,r9))
            ret()
        elif a == 0x2518a0:
            draws.append(('element',rcx,rdx,r9,get(rsp+0x28,'B')))
            ret()
        elif a == 0x251390:
            draws.append(('vitality',rcx,rdx))
            ret()
    hook = u.hook_add(UC_HOOK_CODE,stub)

    def setup():
        reset()
        u.mem_write(live,b'\0'*size)
        put(base+0x2a9058,'Q',api)
        put(base+0x2a9060,'Q',api+0x10)
        put(data+0x1a10,'B',1)
        put(base+0x644a70,'Q',0)
        put(base+0x11cc540,'B',0)
        draws.clear()

    def run(entry, ends=None, aligned=False):
        nonlocal runs
        runs += 1
        entry = sym[entry] if isinstance(entry,str) else entry
        rsp = sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp)
        put(rsp,'Q',stop)
        targets = {base+x for x in ends} if ends else {stop}
        reached = []
        def end(emu,address,length,_):
            if address in targets:
                reached.append(address)
                emu.emu_stop()
        h = u.hook_add(UC_HOOK_CODE,end)
        try:
            u.emu_start(base+entry,stop+1,count=500000)
            assert reached,('no continuation',hex(u.reg_read(UC_X86_REG_RIP)-base))
            if not ends:
                assert u.reg_read(UC_X86_REG_RSP)==rsp+8
        finally:
            u.hook_del(h)

    def addr(char, arte):
        return live+(char*128+arte)*2

    def cast(char, arte, result=0, enemy=0):
        reg('rax',result)
        reg('rbx',actors)
        put(actors+0x4f,'B',char)
        put(actors+0x51,'B',enemy)
        put(actors+0x6d,'B',arte)
        run(0xd554e,[0xd5555],True)
        assert u.reg_read(regs['rax'])==result

    try:
        setup()
        # Every castable arte, both shared casters; do not infer counts from hits.
        for char in (2,3):
            for arte in range(43,114):
                cast(char,arte,1)
                assert get(addr(char,arte),'H')==0
                cast(char,arte)
                assert get(addr(char,arte),'H')==1
        for arte in (39,40,41):
            cast(1,arte)
            assert get(addr(1,arte),'H')==1
        for char,arte,enemy in ((2,71,1),(255,71,0),(2,255,0),(2,0,0),(0,1,0),(1,42,0)):
            before=bytes(u.mem_read(live,size))
            cast(char,arte,enemy=enemy)
            assert bytes(u.mem_read(live,size))==before
        put(addr(2,71),'H',9999)
        cast(2,71)
        assert get(addr(2,71),'H')==9999
        # Successful menu use, then the original epilogue; never count previews.
        reg('rdi',3);reg('rbp',54)
        run(0x224643,[0x224648],True)
        assert get(addr(3,54),'H')==2
        # Non-casting extra physical artes at the native first-hit latch.
        reg('rdi',actors)
        put(actors+0x4f,'B',4);put(actors+0x51,'B',0);put(actors+0x6d,'B',108)
        run(0x8e418,[0x8e41f],True)
        assert get(addr(4,108),'H')==1
        assert u.reg_read(regs['rcx'])==108

        # Execute the native frame, number, label, single/dual element layout.
        for width in (25,45,80):
            for arte in (2,8,39,41,42,43,54,71,73,87,93,108,113):
                for char in (2,3):
                    for elements in (0,1,2):
                        reg('rbp',arte);reg('r15',char);reg('rsi',0);reg('r13',128)
                        put(sp-8+0x60,'B',128);put(sp-8+0x68,'I',char)
                        put(base+0x11cb048+arte*2,'H',123)
                        put(addr(char,arte),'H',456+char)
                        if elements:
                            put(actors+0x3000,'5B',arte,1,1 if elements==1 else 5,0,0)
                            reg('r14',actors+0x3000)
                        else:
                            reg('r14',0)
                        draws.clear()
                        run(0x226fab,[0x2272aa],True)
                        native = arte < 39 or arte == 42
                        number = [d for d in draws if d[0]=='number']
                        assert number==[('number',123 if native else 456+char,5,0x80fffdfa)],number
                        assert len([d for d in draws if d[0]=='label'])==1
                        frame=[d for d in draws if d[0]=='box'][0]
                        icons=[d for d in draws if d[0]=='element']
                        expected=elements or int(43<=arte<=52)
                        assert len(icons)==expected,(arte,elements,icons)
                        for i,icon in enumerate(icons):
                            assert icon[1]==frame[1]-22-19*i,(frame,icons)
                            assert icon[4]==128
                        assert u.reg_read(regs['r15'])==char
        # The entire new counter block is cleared on new game, including end.
        u.mem_write(live,b'\x01'*size)
        run('arte_usage_new_game')
        assert bytes(u.mem_read(live,size))==b'\0'*size

        # Save lifecycle uses immutable per-slot snapshots and an exact native
        # fingerprint. Preview reads must not modify the active character counts.
        setup()
        raw=actors+0x4000
        u.mem_write(raw,bytes(i%251 for i in range(0x12d4)))
        put(addr(2,71),'H',19);put(addr(3,71),'H',5)
        run('artesphere_save_snapshot',[0x24db28],True)
        put(addr(2,71),'H',20)
        reg('rsi',0x12d4);reg('r12',2);reg('rbp',actors)
        run('artesphere_queue_profile',[0x3f3a8],True)
        put(addr(2,71),'H',21)
        reg('r12',2);reg('r15',raw);put(sp+0x58,'Q',0x12d4)
        run('artesphere_save_commit')
        record=records[('ArteUsage-v1','Slot02')]
        assert len(record)==size+8
        assert struct.unpack_from('<H',record,8+(2*128+71)*2)[0]==19
        assert struct.unpack_from('<H',record,8+(3*128+71)*2)[0]==5
        # Reading another slot cannot inherit this slot's counts.
        for slot,matching,expected in ((2,True,19),(3,True,0),(2,False,0)):
            put(addr(2,71),'H',77)
            if not matching:
                put(raw+1,'B',253)
            dest=actors+0x6000
            reg('rcx',dest);reg('rdx',raw);reg('r8',0x12d4)
            reg('r14',0x12d4);reg('r15',dest);reg('rbx',raw);reg('r12',slot)
            run('artesphere_read_stage',[0x40172],True)
            assert get(addr(2,71),'H')==77
            native=bytes(u.mem_read(dest,0x12d4))
            reg('rcx',dest)
            run('artesphere_import_profile',[0x24db46])
            assert get(addr(2,71),'H')==expected
            assert bytes(u.mem_read(dest,0x12d4))==native
        # Failed native save never updates either sidecar; INI errors surfaced.
        before=dict(records);native_save=False
        reg('r12',2);reg('r15',raw);put(sp+0x58,'Q',0x12d4)
        run('artesphere_save_commit')
        assert records==before
        native_save=True;failed=True
        reg('r12',2);reg('r15',raw);put(sp+0x58,'Q',0x12d4)
        run('artesphere_save_commit')
        assert records==before and get(state+7,'B')==1
        return dict(cases=runs,per_character=True,save_isolation=True,
                    interrupted_or_refused_casts_ignored=True,
                    native_localized_panel=True,element_layouts_checked=234,
                    native_save_bytes_preserved=True)
    finally:
        u.hook_del(hook)
