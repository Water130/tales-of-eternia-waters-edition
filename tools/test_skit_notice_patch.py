"""Native selector differential tests and actual queued window/font rendering."""
import random
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *


def check_skit_notice(u, base, m, actors, sp, reset, put, get, reg, regs):
    sym = m['symbols']; info = m['skit_notice']; sp -= 0x2000
    state = base + info['state_rva']; table = base + info['camp_table_rva']
    viewed = base + info['viewed_rva']; end = base + m['code_rva'] - 16
    world = actors; context = actors + 0x2000
    arena = 0x61000000; manager = arena + 0x1000; commands = arena + 0x10000
    u.mem_map(arena, 0x2001000)
    count = 0; texts = []; submitted = []; probes = []; native_hud = []
    stub_hud = False
    # These are actual relocated native pointer tables, as loaded by Windows.
    for rva, length in ((0x4f4710, 5), (0x4f9440, 16)):
        for i in range(length):
            p = base + rva + 16*i
            value = get(p, 'Q')
            if 0x180000000 <= value < 0x182000000:
                put(p, 'Q', value - 0x180000000 + base)

    def ret(value=0):
        s = u.reg_read(UC_X86_REG_RSP)
        assert s % 16 == 8, ('alignment', hex(u.reg_read(UC_X86_REG_RIP)), hex(s))
        for r in ('rcx', 'rdx', 'r8', 'r9', 'r10', 'r11'):reg(r, 0xdead0000)
        reg('rax', value)
        u.reg_write(UC_X86_REG_RIP, get(s, 'Q')); u.reg_write(UC_X86_REG_RSP, s+8)

    def cstring(p):
        out = bytearray()
        for i in range(256):
            c = bytes(u.mem_read(p+i, 1))
            if c == b'\0':return out.decode('utf-8')
            out += c
        raise AssertionError('Unterminated text')

    def code(_, a, size, user):
        if a == base+0x21c460:
            raise AssertionError('Skit notice must not initialize/darken the full menu backdrop')
        if a == base+0x13acc0:raise AssertionError('Notification attempted to play/mark a skit')
        if a == base+sym['skit_notice_probe']:probes.append(True)
        if a == base+0xb480:
            s = u.reg_read(UC_X86_REG_RSP)
            texts.append((cstring(u.reg_read(regs['rcx'])), get(s+0x30, 'I')))
            # Run the actual native UTF-8 font/layout routine.
        elif a == base+0x6a320:ret(123)  # UI atlas provider only.
        elif a == base+0x52f10:  # Font provider boundary, same as existing suite.
            p = u.reg_read(regs['r9']);u.mem_write(p, b'\0'*0x70)
            put(p, 'fffff', 6., 12., 0., 0., 7.);ret()
        elif a == base+0x60bf0:
            submitted.append(u.reg_read(regs['rdx']));ret()
        elif a == base+0x62010:ret()  # Actual device submission stays outside test.
        elif a == base+0x25c490 and stub_hud:
            native_hud.append(u.reg_read(regs['rcx']));ret(0x76543210)

    hook = u.hook_add(UC_HOOK_CODE, code)

    def setup(region=0, story=100):
        reset();u.reg_write(UC_X86_REG_RSP, sp)
        put(base+m['data_rva']+0x1a07,'B',1)
        u.mem_write(state, b'\0'*0x40)
        u.mem_write(viewed, b'\0'*44)
        u.mem_write(base+0x11ca700, b'\0'*0x1e00)
        put(base+0x119ea28, 'H', 2);put(base+0x11cc542, 'B', 0x40)
        put(base+0x119ea49,'B',0)
        put(base+0x866f80, 'H', 0);put(base+0x8c9f98, 'H', 0)
        put(base+0x8ca0c0, 'h', -1);put(base+0x8cab71, 'B', 0)
        put(base+0x8c2a28,'B',0)
        for i in range(6):put(base+0x11a7b46+i*0x68,'H',0)
        put(base+0x11cc540, 'B', 0)
        for addr in (0x62ae30,0x62ae34):put(base+addr,'H',0)
        put(base+0x8cdb08, 'h', story);put(base+0x11cb354, 'B', region)
        put(base+0x8befc0, 'Q', world);put(world+4, 'B', region)
        put(world+0x13a0, 'Q', context);put(context+0xc0, 'Q', base+0x15ea90)
        put(world+0x598, 'Q', actors+0x3000)
        put(world+0x580, 'Q', actors+0x3500);put(world+0x5a8, 'Q', actors+0x3800)
        put(world+0x5d0, 'i', 65536);put(world+0x5d4, 'i', 65536)
        put(world+0x570, 'B', 12 if region == 0 else 0x50)
        put(world+0x22, 'H', 2400)
        put(base+0x11cad10, '6H', 1, 2, 3, 4, 5, 6)
        put(base+0x644a10, 'Q', 0);put(base+0x644a58, 'Q', 0)
        put(base+0x11c9e18, 'Q', 0);put(base+0x12cea68, 'Q', 0)
        put(base+0x11c9ce8, 'B', 3)
        texts.clear();submitted.clear();probes.clear()

    def run(name, stop=None, native=False, audit=False, entry_sp=None):
        nonlocal count
        count += 1;entry = entry_sp if entry_sp is not None else (sp-8 if native else sp)
        u.reg_write(UC_X86_REG_RSP, entry);put(entry, 'Q', end)
        target = base+stop if stop is not None else end
        reached = []; writes = []
        def stop_at(_, a, size, user):
            if a == target:reached.append(a);u.emu_stop()
        def writing(_, access, a, size, value, user):
            if not (0x30000000 <= a and a+size <= 0x30010000):writes.append((a, size))
        h = u.hook_add(UC_HOOK_CODE, stop_at)
        hw = u.hook_add(UC_HOOK_MEM_WRITE, writing) if audit else None
        u.ctl_remove_cache(target-16, target+16)
        try:
            u.emu_start(base+(sym[name] if isinstance(name, str) else name), end+16, count=2000000)
        except Exception as e:
            raise AssertionError((name, hex(u.reg_read(UC_X86_REG_RIP)-base), str(e))) from e
        finally:
            u.hook_del(h)
            if hw is not None:u.hook_del(hw)
        assert reached, (name, 'did not return')
        if stop is None:assert u.reg_read(UC_X86_REG_RSP) == entry+8, 'stack balance'
        if audit:
            assert all(base+0x644b40 <= a and a+s <= base+0x644c40 for a, s in writes), writes
        return u.reg_read(regs['rax'])

    def original():
        reg('r12', 0)
        run(0x16ab39, stop=0x16abdd, native=True)
        return u.reg_read(regs['rdi'])

    def render_ready():
        u.mem_write(manager, b'\0'*0x9000)
        put(base+0x644a10, 'Q', manager)
        put(manager+0x4d0, 'Q', commands);put(manager+0x4d8, 'Q', 4096)
        put(base+0x644a58, 'Q', arena);put(arena+0x2000008, 'I', 0)
        put(base+0x11c9e18, 'Q', arena+0x9000)
        put(base+0x644a18, 'Q', arena+0x9000);put(base+0x644a20, 'Q', arena+0x9000)
        put(arena+0x9008, 'f', 12.)
        put(base+0x11cc57c, 'I', 0xffcca060)

    try:
        # Original native loop vs new read-only loop, including both continents,
        # seen bits, story cutoffs, missing party members and extra skit rules.
        rng = random.Random(25190541)
        for mode,region in ((2,0),(2,3),(6,0),(6,3)):
            for story in (-1, 0, 1, 30, 100, 200, 400, 650, 1000, 2000, 8000, 32767):
                setup(region, story)
                put(base+0x119ea28,'H',mode)
                if story % 3 == 1:
                    u.mem_write(viewed, rng.randbytes(44))
                    put(base+0x11cad10, '6H', 1, 3, 4, 0, 0, 0)
                before = bytes(u.mem_read(base+0x11ca700, 0x1e00))
                expected = original()
                scratch = rng.randbytes(0x100);u.mem_write(base+0x644b40, scratch)
                saved = {r:u.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
                actual = run('skit_notice_probe', audit=True)
                assert actual == expected, (mode, region, story, actual, expected)
                assert before == bytes(u.mem_read(base+0x11ca700, 0x1e00)), 'save data changed'
                assert scratch == bytes(u.mem_read(base+0x644b40, 0x100)), 'query scratch changed'
                assert saved == {r:u.reg_read(regs[r]) for r in saved}, 'nonvolatile register changed'

        # Walk every camp slot, especially bitset word boundaries and final 264.
        # A fully viewed slot must never trigger; hints after 264 are excluded.
        setup();u.mem_write(viewed, b'\xff'*33+b'\0'*11)
        assert run('skit_notice_probe') == 0
        for index in range(264):
            row = table+index*8;lo=get(row+4,'h');hi=get(row+6,'h')
            put(base+0x8cdb08,'h',lo)
            u.mem_write(viewed, b'\xff'*44)
            word=viewed+4*(index//32);put(word,'I',0xffffffff^(1<<(index%32)))
            got=run('skit_notice_probe',audit=True)
            assert got in (0,index+1), (index,got)
            put(base+0x8cdb08,'h',hi)
            assert run('skit_notice_probe')==0, ('exclusive end',index)

        # Force a harmless first-table entry only in emulator memory, then run
        # the real predicates/renderer to make availability deterministic.
        original_table=bytes(u.mem_read(table,264*8))
        setup();u.mem_write(viewed,b'\xff'*44);put(viewed,'I',0xfffffffe)
        u.mem_write(table,struct.pack('<BBHhh',0,0,0,0,32767))
        assert run('skit_notice_context')==2
        put(base+0x119ea28,'H',6)
        assert run('skit_notice_context')==6
        put(base+0x119ea28,'H',2)
        for addr,fmt,value in [(0x119ea28,'H',0),(0x119ea28,'H',1),
                                (0x119ea28,'H',7),(0x119ea28,'H',16),(0x11cc542,'B',0),
                                (0x866f80,'H',1),(0x8c9f98,'H',1),(0x11cb354,'B',1),
                                (0x8befc0,'Q',0),(0x8ca0c0,'h',0),(0x8cab71,'B',4),
                                (0x8cab71,'B',8),(0x11cc540,'B',0x10),
                                (0x62ae30,'H',1),(0x62ae34,'H',1),(0x119ea49,'B',1)]:
            old=get(base+addr,fmt);put(base+addr,fmt,value)
            put(state,'II',12,1);assert run('skit_notice_context')==0
            run('skit_notice_frame');assert get(state,'Q')==0
            put(base+addr,fmt,old)
        # Field-only state must not suppress the overworld notification.
        for mode in (2,6):
            put(base+0x119ea28,'H',mode)
            for value in (1,8):
                put(base+0x8c2a28,'B',value)
                assert run('skit_notice_context')==(2 if mode==2 else 0)
        put(base+0x8c2a28,'B',0)
        put(base+m['data_rva']+0x1a07,'B',0)
        before=len(probes)
        run('skit_notice_frame')
        assert len(probes)==before and get(state,'Q')==0, 'disabled notice must not query skits'
        put(base+m['data_rva']+0x1a07,'B',1)
        for mode in (2,6):
            put(base+0x119ea28,'H',mode)
            for i in range(6):
                for value in (1,2,4,0x80,0xffff):
                    addr=base+0x11a7b46+i*0x68
                    put(addr,'H',value)
                    assert run('skit_notice_context')==0,(mode,i,value)
                    run('skit_notice_frame')
                    put(addr,'H',0)
                    for _ in range(30):
                        run('skit_notice_frame');assert get(state,'Q')==0, 'bubble flashed between messages'
        put(base+0x119ea28,'H',2)
        for addr in (world+0x13a0,context+0xc0,world+0x598,world+0x580,world+0x5a8):
            old=get(addr,'Q');put(addr,'Q',0);assert run('skit_notice_context')==0;put(addr,'Q',old)
        put(world+8,'H',1);assert run('skit_notice_context')==0;put(world+8,'H',0)

        run('skit_notice_frame');assert get(state+4,'I')==1 and not submitted
        initial=len(probes)
        for _ in range(29):run('skit_notice_frame')
        assert len(probes)==initial
        run('skit_notice_frame');assert len(probes)==initial+1
        put(viewed,'I',0xffffffff);run('skit_notice_frame');assert get(state+4,'I')==0
        put(viewed,'I',0xfffffffe);put(state,'I',0)
        render_ready()
        for language in range(8):
            put(base+0x11c9ce8,'B',language)
            texts.clear();submitted.clear();put(manager+0x4e0,'I',0);put(arena+0x2000008,'I',0)
            scratch=bytes(u.mem_read(base+0x11ce620,0xa0))
            font_scratch=rng.randbytes(0x70);u.mem_write(base+0x862350,font_scratch)
            flags=get(manager+8,'I')
            run('skit_notice_frame')
            assert [t[0] for t in texts]==(['Saynète','Disponible'] if language==3 else ['Skit','Available'])
            assert texts[0][1]==0xffffd090 and texts[1][1]==0xffffffff
            assert bytes(u.mem_read(base+0x11ce620,0xa0))==scratch
            assert bytes(u.mem_read(base+0x862350,0x70))==font_scratch
            assert get(manager+8,'I')==flags, 'render flags changed'
            assert not {get(p,'I') for p in submitted}&{0x2a,0x0b,0x07}, 'scene/projection reset'
            assert get(base+0x12cea68,'Q')==0, 'no battle renderer dependency'
            windows=[p for p in submitted if get(p,'I')==5 and get(p+12,'I')==0x80011e]
            assert len(windows)==9
            vertices=[get(p+32,'Q')+i*16 for p in windows for i in range(4)]
            bounds=(min(get(v+8,'h') for v in vertices),max(get(v+8,'h') for v in vertices),
                    min(get(v+10,'h') for v in vertices),max(get(v+10,'h') for v in vertices))
            assert bounds==(5,75,242,267),bounds
            glyphs=[p for p in submitted if get(p,'I')==9]
            assert len(glyphs)>=13, (language,len(glyphs),texts)
            assert all(5<=get(p+8,'f')<75 and 242<=get(p+12,'f')<267 for p in glyphs)
            assert submitted.index(windows[-1])<submitted.index(glyphs[0]), 'text behind window'

        # Populate the actual native command array, not a stubbed collision
        # result. Reserve one corner at a time with real UI primitive layouts.
        corners=[(5,242),(405,242),(5,5),(405,5)]
        def seed(rects, kind='glyph'):
            render_ready();texts.clear();submitted.clear()
            idx=0;vertex_pos=arena+0x80000
            def command(tag):
                nonlocal idx
                p=commands+idx*80;idx+=1
                u.mem_write(p,b'\0'*80);put(p,'I',tag)
                return p
            for x,y,w,h in rects:
                if kind in ('glyph','sprite'):
                    p=command(12);put(p+16,'ff',float(w),float(h))
                    p=command(9 if kind=='glyph' else 8)
                    put(p+8,'ff',float(x),float(y))
                else:
                    fmt,stride,offset={
                        'window':(0x80011e,16,8),'flat':(0x800100,6,0),
                        'rotated':(0x800183,20,8),'float':(0x800180,12,0),
                        '3d':(0x183,20,8),'unknown':(0x800999,20,8)
                    }[kind]
                    p=command(5);put(p+12,'II',fmt,2);put(p+32,'Q',vertex_pos)
                    u.mem_write(vertex_pos,b'\0'*(stride*2))
                    coord='hh' if kind in ('window','flat') else 'ff'
                    put(vertex_pos+offset,coord,x,y)
                    put(vertex_pos+stride+offset,coord,x+w,y+h)
                    vertex_pos+=stride*2
            put(manager+0x4e0,'I',idx)
            put(arena+0x2000008,'I',vertex_pos-arena-8 if rects else 0)
            return idx

        for mode,points in ((2,[(5,242),(205,242),(253,242),(5,204),(5,5),(405,5),(205,5)]),
                            (6,[(405,242),(5,242),(205,242),(253,242),(405,5),(5,5),(5,204),(405,204)])):
            put(base+0x119ea28,'H',mode)
            for used in range(len(points)+1):
                rects=[(*p,70,25) for p in points[:used]]
                seed(rects)
                # Make the fake first camp entry location compatible with the
                # native field predicate. Actual native eligibility is used.
                put(table+1,'B',1 if mode==6 else 0);put(state,'I',0)
                run('skit_notice_frame')
                # Nearby fallback candidates overlap, so calculate the first
                # genuinely free rectangle rather than assuming list indices.
                expected=next((p for p in points if all(
                    p[0]+74<=x or p[0]-4>=x+w or p[1]+29<=y or p[1]-4>=y+h
                    for x,y,w,h in rects)),None)
                if expected is not None:
                    assert (get(state+12,'I'),get(state+16,'I'))==expected,(mode,used)
                    assert len(texts)==2,(mode,used,'bubble missing')
                    windows=[p for p in submitted if get(p,'I')==5 and get(p+12,'I')==0x80011e]
                    vertices=[get(p+32,'Q')+i*16 for p in windows for i in range(4)]
                    assert min(get(v+8,'h') for v in vertices)==expected[0]
                    assert min(get(v+10,'h') for v in vertices)==expected[1]
                else:
                    assert not texts, 'no unoccupied candidate'
            seed([]);run('skit_notice_draw')
            assert (get(state+12,'I'),get(state+16,'I'))==points[0], 'preferred corner freed'

        # Every supported 2D shape reserves its true footprint. 3D scene
        # geometry and screen-sized background planes do not reserve all UI.
        put(base+0x119ea28,'H',2)
        for kind in ('glyph','sprite','window','flat','rotated','float'):
            seed([(10,225,130,40)],kind)
            saved={r:u.reg_read(regs[r]) for r in ('rbx','rsi','rdi','r12','r13','r14','r15')}
            simd={r:rng.getrandbits(128) for r in (UC_X86_REG_XMM6,UC_X86_REG_XMM7)}
            for r,v in simd.items():u.reg_write(r,v)
            assert run('skit_notice_placement')==1
            assert (get(state+12,'I'),get(state+16,'I'))==(205,242),kind
            assert saved=={r:u.reg_read(regs[r]) for r in saved}
            assert simd=={r:u.reg_read(r) for r in simd}
        for kind in ('3d','flat','float'):
            seed([(0,0,480,272)],kind)
            assert run('skit_notice_placement')==1
            assert (get(state+12,'I'),get(state+16,'I'))==(5,242),kind
        # Minimap protection does not depend on its earlier render commands.
        seed([])
        put(state+12,'II',405,242)
        assert run('skit_notice_occupied')==1
        seed([(8,230,48,28)])
        run('skit_notice_placement')
        assert (get(state+12,'I'),get(state+16,'I'))==(205,242)
        seed([(16,232,40,20)],'unknown')
        assert run('skit_notice_placement')==1, 'skip unknown 2D buffer without dereferencing or hiding every corner'
        put(commands+16,'I',5000);put(commands+32,'Q',1)
        assert run('skit_notice_placement')==1, 'unknown geometry does not globally reserve the HUD'
        seed([(16,232,40,20)],'flat');put(commands+32,'Q',0x77777777)
        assert run('skit_notice_placement')==0, 'vertex pointer outside arena'
        seed([]);put(manager+0x4e0,'i',-1)
        assert run('skit_notice_placement')==0, 'invalid command count'

        # Camera-dependent scene geometry precedes the native world HUD entry.
        # It must not reserve all corners, while later HUD primitives still do.
        put(base+0x119ea28,'H',2)
        seed([(*p,100,24) for p in corners])
        reg('rbx',0x123456);reg('rax',0x987654)
        run(0x157e60,stop=0x157e66)
        assert get(state+28,'I')==8 and get(state+32,'Q')==manager
        assert u.reg_read(regs['rax'])==0x987654
        assert u.reg_read(UC_X86_REG_RSP)==sp-0x28
        assert get(sp-8,'Q')==0x123456
        assert run('skit_notice_placement')==1
        assert (get(state+12,'I'),get(state+16,'I'))==corners[0]
        # Add an actual HUD obstacle after the remembered boundary.
        u.mem_write(commands+8*80,bytes(u.mem_read(commands,160)))
        put(manager+0x4e0,'I',10)
        assert run('skit_notice_placement')==1
        assert (get(state+12,'I'),get(state+16,'I'))==(205,242)
        put(state+32,'Q',0);put(state+28,'I',0)

        # Restored GPU commands must be the most recent value of each changed
        # state, in their ORIGINAL order (font and texture bindings interact).
        for flags in (0,0x10,0x200,0x210,0x5555):
            seed([]);put(manager+8,'I',flags)
            kinds=[0x21,0x14,0x23,0x0c,0x39,0x1d,0x22,0x2e,0x1b,0x21,0x14]
            for i,tag in enumerate(kinds):
                p=commands+i*80;u.mem_write(p,b'\0'*80);put(p,'II',tag,0xfeed0000+i)
            put(manager+0x4e0,'I',len(kinds))
            before=bytes(u.mem_read(commands,80*len(kinds)))
            run('skit_notice_draw')
            replay=[p for p in submitted if commands<=p<commands+80*len(kinds)]
            expected=[commands+i*80 for i,tag in enumerate(kinds) if tag not in kinds[i+1:]]
            assert replay==expected, 'GPU restoration changed original ordering'
            assert bytes(u.mem_read(commands,80*len(kinds)))==before, 'existing commands changed'
            assert get(manager+8,'I')==flags, 'native GPU flags not restored'
        seed([])

        for addr,fmt,value in [(base+0x644a10,'Q',0),(manager+0x4d0,'Q',0),
                                (manager+0x4d8,'Q',1),(base+0x644a58,'Q',0),
                                (arena+0x2000008,'I',0x1fffff0),(base+0x11c9e18,'Q',0)]:
            old=get(addr,fmt);put(addr,fmt,value);texts.clear();submitted.clear()
            run('skit_notice_draw');assert not submitted and not texts
            put(addr,fmt,old)
        # Native global submission stays untouched, including its prologue.
        # Even if exploration eligibility is stale during a loader submission,
        # the entire original submission function must not query/draw a notice.
        setup();before_probes=len(probes)
        put(base+0x11c9f18,'Q',0);put(base+0x11c9f20,'Q',0)
        run(0x6f070)
        assert len(probes)==before_probes and not submitted and not texts
        put(base+0x119ea28,'H',7);reg('rbx',0xabcdef)
        assert bytes(u.mem_read(base+0x6f070,6))==bytes.fromhex('40534883ec20')
        run(0x6f070,stop=0x6f076)
        assert u.reg_read(UC_X86_REG_RSP)==sp-0x28
        assert get(sp-8,'Q')==0xabcdef
        # World epilogue preserves native result/RBX and caller stack exactly.
        reg('rax',0x76543210);reg('rbx',0x123456)
        put(sp-8,'Q',0xabcdef);put(sp,'Q',end)
        run(0x157f1f,stop=end-base,entry_sp=sp-0x28)
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        assert u.reg_read(regs['rbx'])==0xabcdef
        assert u.reg_read(regs['rax'])==0x76543210
        # Field replacement calls the displaced native HUD once, before our
        # callback, and returns to its original continuation with the same RSP.
        stub_hud=True;reg('rcx',1)
        run(0x198a54,stop=0x198a59,entry_sp=sp-8)
        assert native_hud==[1]
        assert u.reg_read(UC_X86_REG_RSP)==sp-8
        assert u.reg_read(regs['rax'])==0x76543210
        u.mem_write(table,original_table)
    finally:
        u.hook_del(hook);u.mem_unmap(arena,0x2001000)
    return count
