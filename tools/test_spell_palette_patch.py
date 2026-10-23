"""Run the native CLUT loader and renderer, with only allocator/submit stubs.

Unlike a descriptor-copy test, this loads two palettes at the same VRAM
coordinates, then replays the first spell's already-queued palette command.
"""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_spell_palettes(u, base, m, sp, put, get, reg, regs):
    arena = 0x66000000
    u.mem_map(arena, 0x100000)
    manager, vector = arena, arena+0x1000
    allocator, avtable, allocfn = arena+0x100, arena+0x200, arena+0x300
    renderer, command = arena+0x3000, arena+0x4000
    heap = arena+0x10000
    sentinel = base+m['code_rva']-16
    # The shared harness maps raw PE sections without applying relocations.
    # Rebase the only native vtable entry exercised here, as the PE loader does.
    vtable_entry = base+0x51a5b8
    saved_get_type = get(vtable_entry, 'Q')
    calls = 0

    def ret(value=0):
        s = u.reg_read(UC_X86_REG_RSP)
        reg('rax', value)
        u.reg_write(UC_X86_REG_RIP, get(s, 'Q'))
        u.reg_write(UC_X86_REG_RSP, s+8)

    def stub(_, address, size, user):
        nonlocal heap
        if address == base+0x2655b0:
            ret(allocator)
        elif address in (base+0x261290, allocfn):
            length = u.reg_read(regs['rcx' if address == base+0x261290 else 'rdx'])
            result = heap
            heap += (length+15)&~15
            assert heap < arena+0x100000
            u.mem_write(result, b'\0'*length)
            ret(result)
        elif address == allocfn+0x10:
            ret()  # host allocator deallocation
        elif address == base+0x2a41e0:
            dst, src, length = [u.reg_read(regs[r]) for r in ('rcx', 'rdx', 'r8')]
            u.mem_write(dst, bytes(u.mem_read(src, length)))
            ret(dst)
        elif address == base+0x279670:
            ret()  # stack cookie runtime

    hook = u.hook_add(UC_HOOK_CODE, stub)

    def run(start, stop=None):
        nonlocal calls
        calls += 1
        put(sp, 'Q', sentinel)
        u.reg_write(UC_X86_REG_RSP, sp)
        target = sentinel if stop is None else base+stop
        def halt(_, address, size, user):
            if address == target:
                u.emu_stop()
        h = u.hook_add(UC_HOOK_CODE, halt)
        try:
            u.emu_start(base+start, sentinel+16, count=100000)
            assert u.reg_read(UC_X86_REG_RIP) == target
        finally:
            u.hook_del(h)

    def load(resource, part, x=0, y=500, w=16, h=1):
        reg('rcx', manager); reg('rdx', resource); reg('r8', part); reg('r9', x)
        # Windows x64 reserves eight bytes for each stack argument.
        for slot, value in enumerate((y, w, h, 0)):
            put(sp+0x28+8*slot, 'I', value)
        run(0x6acf0)
        return u.reg_read(regs['rax'])

    def select(resource, x=0, y=500):
        put(command, 'I', 0x31)
        put(command+8, 'IIiI', x, y, 0, resource)
        reg('rbx', renderer); reg('rdi', command); reg('r8', command)
        run(0x5f468, 0x5f52b)
        return get(renderer+0x270, 'Q')

    try:
        put(base+m['data_rva']+0x1a45,'B',1)
        put(vtable_entry, 'Q', base+0x670e0)
        put(allocator, 'Q', avtable); put(avtable+8, 'Q', allocfn)
        put(avtable+0x18, 'Q', allocfn+0x10)
        put(manager+0x20, 'QQQ', vector, vector, vector+0x1000)
        put(base+0x11c9e18, 'Q', manager)
        enemy = load(10, 1)
        # Air Thrust's template uses CLUT 0x7d00 (x=0, y=500).
        # Spread may use the same coordinates but a different part/extent.
        air = load(126, 2, w=16, h=4)
        saved = bytes(u.mem_read(air, 0x30))
        spread = load(188, 5, w=256)
        assert air != spread, 'Spread overwrites the live Air Thrust palette object'
        assert bytes(u.mem_read(air, 0x30)) == saved
        selected = select(126)
        assert selected == air, (
            'Air Thrust resolves wrong palette', hex(selected), hex(air), hex(spread),
            bytes(u.mem_read(air, 0x30)).hex(), bytes(u.mem_read(spread, 0x30)).hex())
        assert select(188) == spread
        # Opposite load order, a third spell, and cached/repeated loads.
        third = load(129, 7, w=32, h=2)
        assert select(126) == air and select(188) == spread and select(129) == third
        assert select(10) == enemy, 'Enemy palette borrowed a later party-spell palette'
        for resource, part, ptr, width in ((188, 5, spread, 256), (126, 2, air, 16)):
            for _ in range(4):
                assert load(resource, part, w=width) == ptr
                assert select(resource) == ptr
        assert (get(manager+0x28, 'Q')-vector)//8 == 4, 'repeat cast grows palette objects'
        # Boss-only large effects are outside the party overlap allowlist but
        # still upload into the same VRAM palette coordinates.
        boss_palettes={rid:load(rid,3,w=64) for rid in (160,165,199)}
        assert len(set(boss_palettes.values()))==3
        assert all(select(rid)==p for rid,p in boss_palettes.items())
        assert select(126)==air and select(188)==spread and select(10)==enemy
        assert all(load(rid,3,w=64)==p for rid,p in boss_palettes.items())
        assert (get(manager+0x28,'Q')-vector)//8==7
        # Non-spell uploads cannot overwrite retained spell palettes either.
        other = load(10, 1)
        assert other not in (air, spread, third)
        assert select(126) == air and select(188) == spread
        assert select(0xffffffff) == other  # unchanged unowned fallback
        assert load(11, 0) == other       # unrelated native reuse is unchanged
        assert select(147, x=15, y=511) == 0  # absent owned palette: never borrow another spell
        return calls
    finally:
        put(vtable_entry, 'Q', saved_get_type)
        u.hook_del(hook)
        u.mem_unmap(arena, 0x100000)
