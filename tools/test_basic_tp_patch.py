"""Replay native normal-attack initialization before testing TP attribution."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS


def check_basic_tp(uc, base, manifest, actors, enemies, stats, impact, sp,
                   reset, put, get, reg, regs):
    data = base + manifest['data_rva']
    flags = base + manifest['mod_settings']['flags_rva']
    projectiles = base + 0x12cee48
    sentinel = data - 16
    cases = 0
    # These native tables contain absolute pointers; relocate them as the PE
    # loader does, so the native initializer also runs at the second ASLR base.
    tables = [(0x4e92b0, 0x112420, 0x112560, 0x112560, 0x1125e0),
              (0x4e93c0, 0x551bb0, 0x551da8, 0x551d68, 0x551e70)]
    saved_tables = []
    for table, *targets in tables:
        for char, target in [*enumerate(targets),
                             (11, 0x112560 if table == 0x4e92b0 else 0x551df8)]:
            address = base + table + char * 8
            saved_tables.append((address, get(address, 'Q')))
            put(address, 'Q', base + target)
    saved_flag = get(flags + 2, 'B')

    def execute(start, stop=None, caller=None, stubs=()):
        nonlocal cases
        cases += 1
        reached = []
        uc.reg_write(UC_X86_REG_RSP, sp)
        put(sp, 'Q', sentinel if caller is None else base + caller)
        target = sentinel if stop is None else base + stop

        def step(emu, address, size, user):
            if address == target:
                reached.append(address)
                emu.emu_stop()
            elif address - base in stubs:
                rsp = emu.reg_read(UC_X86_REG_RSP)
                reg('rax', 0)
                emu.reg_write(UC_X86_REG_RIP, get(rsp, 'Q'))
                emu.reg_write(UC_X86_REG_RSP, rsp + 8)

        hook = uc.hook_add(UC_HOOK_CODE, step)
        try:
            uc.emu_start(base + start, sentinel + 1, count=20000)
        finally:
            uc.hook_del(hook)
        assert reached, (hex(start), hex(uc.reg_read(UC_X86_REG_RIP) - base))
        assert uc.reg_read(UC_X86_REG_RSP) == sp + (8 if stop is None else 0)

    def setup(char, action, enabled=1):
        reset()
        put(flags + 2, 'B', enabled)
        actor = actors + (4 if char == 11 else char) * 0x248
        put(actor + 0x52, 'B', 4 if action == 4 else 0)
        put(actor + 0x64, 'B', action)
        put(actor + 0x53, 'B', 1)
        put(actor + 0x12, 'h', -128 if action == 4 else 0)
        put(base + 0x12cea60, 'Q', actors + 0xa000)
        # Meredy's native command delegates to Quickie when he is ready.
        put(actors + 4 * 0x248 + 0x75, 'B', 3)
        if char == 3:
            put(actors + 4 * 0x248 + 0x52, 'B', 0)
        return actor

    def initialize(actor, direction):
        reg('rcx', actor)
        reg('rdx', direction)
        # Only animation-resource/sound/random/security-cookie callees are
        # stubbed. The character selector and attack descriptors run natively.
        execute(0x112720, stubs=(0x7fe70, 0x283090, 0x11ace0, 0x279670))
        assert get(actor + 0x52, 'B') == 8

    def hit(actor, owner, gain, enabled=1, ranged=False, damage=30, commit=True):
        reg('rcx', actor)
        reg('rdx', enemies)
        reg('r9', impact if ranged else actor + 0xd8)
        reg('rsi', projectiles + 5 * 0x30)
        saved = {r: uc.reg_read(v) for r, v in regs.items()}
        execute(0x8e910, 0x8e915, 0x1164e3 if ranged else 0x822cd)
        assert saved == {r: uc.reg_read(v) for r, v in regs.items()}
        before_hp, before_tp = get(enemies + 0x2c, 'i'), get(owner + 0x34, 'h')
        reg('rdi', enemies)
        reg('rsi', damage)
        uc.reg_write(UC_X86_REG_EFLAGS, 0x242 if commit else 0x202)
        saved = {r: uc.reg_read(v) for r, v in regs.items()}
        execute(0x8f099, 0x8f0a1)
        assert saved == {r: uc.reg_read(v) for r, v in regs.items()}
        expected = min(before_tp + gain, get(stats + 0x1c, 'h')) \
            if enabled and commit and damage > 0 else before_tp
        assert get(owner + 0x34, 'h') == expected, (
            'native basic hit TP', get(actor + 0x4f, 'B'),
            get(actor + 0x64, 'B'), get(owner + 0x34, 'h'), expected)
        assert get(enemies + 0x2c, 'i') == before_hp - (damage if commit else 0)

    try:
        # Ground combos, running attacks and aerial attacks, all three native
        # directional variants. Quickie's hits must credit Meredy, never him.
        for char in (0, 1, 2, 3, 11):
            for action in ((0, 1) if char == 3 else (0, 1, 4, 5)):
                for direction in (0, 1, 3):
                    for enabled in (0, 1):
                        actor = setup(char, action, enabled)
                        initialize(actor, direction)
                        if action == 4:
                            assert get(actor + 0x64, 'B') == 0x0f
                        owner = actors + 3 * 0x248 if char == 11 else actor
                        hit(actor, owner, 2 if char in (2, 3, 11) else 1, enabled)
                        if char == 11:
                            assert get(actor + 0x34, 'h') == 10

        # Meredy has no separate native airborne command; keep that behavior.
        actor = setup(3, 4)
        reg('rcx', actor)
        reg('rdx', 0)
        execute(0x112720, stubs=(0x279670,))
        assert get(actor + 0x52, 'B') == 4
        assert get(actor + 0x64, 'B') == 4
        assert get(actor + 0x34, 'h') == 10

        # Aerial projectile provenance survives a subsequent arte/cast.
        for char in (0, 1, 2, 11):
            for caller in (0x70d3e, 0x70ef7):
                actor = setup(char, 4)
                initialize(actor, 0)
                reg('rax', projectiles + 5 * 0x30)
                reg('r8', actor)
                reg('rdx', impact)
                reg('r11', 5)
                execute(0x116602, 0x116609, caller)
                assert get(data + 0x105, 'B') == 1
                put(actor + 0x64, 'B', 0xff)
                put(actor + 0x52, 'B', 10)
                owner = actors + 3 * 0x248 if char == 11 else actor
                hit(actor, owner, 2 if char in (2, 11) else 1, ranged=True)

        # Audit every usable physical descriptor, then execute the native
        # special-attack initializer's class encoding, not a synthetic list.
        physical = 0
        for arte in range(1, 114):
            descriptor = base + 0x551780 + arte * 8
            if get(descriptor, 'B') == 0 or get(descriptor + 1, 'B') > 1:
                continue
            physical += 1
            actor = setup(0, 0)
            reg('rbx', actor)
            reg('rdi', descriptor)
            reg('rbp', 0)
            reg('r14', 0)
            execute(0x112c58, 0x112c6f)
            assert get(actor + 0x64, 'B') >= 0x10, arte
            hit(actor, actor, 0)
        assert physical > 30

        # Class 0x0f at landing is not an attack; magic, enemy and non-native
        # impact paths still cannot generate credit or keep a previous one.
        for state, side, magic, caller in (
            (4, 0, 0, 0x822cd), (5, 0, 0, 0x822cd), (6, 0, 0, 0x822cd),
            (8, 1, 0, 0x822cd), (8, 0, 0x80, 0x822cd),
            (8, 0, 0, 0x976a9),
        ):
            actor = setup(0, 4)
            put(actor + 0x64, 'B', 0x0f)
            put(actor + 0x52, 'B', state)
            put(actor + 0x51, 'B', side)
            put(actor + 0xd8, 'B', magic)
            put(data, 'Q', actor)
            reg('rcx', actor)
            reg('rdx', enemies)
            reg('r9', actor + 0xd8)
            execute(0x8e910, 0x8e915, caller)
            assert get(data, 'Q') == 0

        for char in (0, 1, 2, 11):
            for initial, damage, commit in (
                (99, 30, True), (100, 30, True), (10, 0, True),
                (10, -30, True), (10, 30, False),
            ):
                actor = setup(char, 4)
                initialize(actor, 0)
                owner = actors + 3 * 0x248 if char == 11 else actor
                put(owner + 0x34, 'h', initial)
                hit(actor, owner, 2 if char in (2, 11) else 1,
                    damage=damage, commit=commit)
    finally:
        put(flags + 2, 'B', saved_flag)
        for address, value in saved_tables:
            put(address, 'Q', value)
    return cases
