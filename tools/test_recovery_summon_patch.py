"""Execute modified dispatchers and native recovery/vitality/cost instructions."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_recovery_summon(uc, base, manifest, actors, enemies, stats, impact, sp,
                          reset, put, get, reg, regs):
    master, inputs, config, options = actors+0xa000, actors+0xc000, actors+0xc100, actors+0xc200
    sentinel = manifest['data_rva']-0x10
    checks = []
    count = 0

    def execute(start, stops=None, stubs=(), stack=None):
        nonlocal count
        count += 1
        if stack is not None:
            uc.reg_write(UC_X86_REG_RSP, stack)
        if stops is None:
            stops = [sentinel]
            put(uc.reg_read(UC_X86_REG_RSP), 'Q', base+sentinel)
        reached = []
        def step(emu, address, size, user):
            rva = address-base
            if rva in stops:
                reached.append(rva)
                emu.emu_stop()
            elif rva in stubs:
                # Only presentation/animation routines are stubbed, never cost,
                # access, targeting, selection or vitality calculations.
                current = emu.reg_read(UC_X86_REG_RSP)
                assert current % 16 == 8, ('Windows call alignment', hex(rva), hex(current))
                destination = get(current, 'Q')
                emu.reg_write(UC_X86_REG_RSP, current+8)
                emu.reg_write(UC_X86_REG_RIP, destination)
        handle = uc.hook_add(UC_HOOK_CODE, step)
        try:
            uc.emu_start(base+start, base+sentinel+1, count=30000)
        finally:
            uc.hook_del(handle)
        assert reached, ('No continuation', hex(start), hex(uc.reg_read(UC_X86_REG_RIP)))
        return reached[0]

    def setup(char=2, held=0x80, vitality=0xa000, owner=None, learned=True):
        reset()
        actor = actors+char*0x248 if char < 4 else actors
        put(actor+0x4f, 'B', char)
        put(actor+0x57, 'B', 2)
        put(actor+0x52, 'B', 0)
        put(actor+0x6b, 'B', 3)
        put(actor, 'Q', enemies)
        put(actor+0xf0, 'Q', inputs)
        put(actor+0x34, 'H', 500)
        put(inputs, 'II', held, 0x40)
        put(base+0x12cea60, 'Q', master)
        put(base+0x12cea68, 'Q', config)
        put(base+0x12cea70, 'Q', base+0x562a50)
        put(base+0x12cea78, 'Q', base+0x551780)
        put(base+0x6449e0, 'Q', options)
        for element in range(10):
            put(master+0xbb8+element*8, 'BBH', char+1 if owner is None else owner, 15, vitality)
            if learned:
                put(master+char*0xd0+0x7a+element, 'B', 43+element)
        return actor

    if 'victory_tp' in manifest['features']:
        # Enter before the original state/ailment/difficulty tests, execute through
        # our hook and native division/minimum. R9 points to the result TP field.
        for difficulty, percent in enumerate([8, 9, 10, 13]):
            for bonus in [0, 1]:
                for maximum in [1, 30, 99, 100, 139, 178, 999, 9999]:
                    for state, ailment in [(1, 0), (1, 0x4000), (2, 0)]:
                        setup()
                        put(config+4, 'B', difficulty)
                        put(base+0x12d0ef0, 'I', bonus)
                        put(stats+0x1c, 'h', maximum)
                        put(actors+0x3c, 'H', state)
                        put(actors+0x30, 'I', ailment)
                        reg('r8', actors); reg('r9', impact)
                        reg('r14', 1); reg('r11', 5); reg('rsi', 10)
                        execute(0x118afb, [0x118b57])
                        expected = max(10, maximum*(percent+bonus)//100) if state == 1 and not ailment else 0
                        assert get(impact, 'H') == expected, (difficulty, bonus, maximum, state, ailment)
        checks.append('192 native victory TP calculations: four difficulties, bonus, floor, minimum, KO/status exclusions')

    if 'summon_modifier' not in manifest['features']:
        return checks, count

    for char in [2, 3]:
        for arte in range(116):
            for held in [0, 0x80]:
                actor = setup(char, held)
                reg('rax', arte); reg('rcx', actor); reg('rdx', inputs)
                saved = {k:uc.reg_read(v) for k,v in regs.items() if k != 'rax'}
                before = bytes(uc.mem_read(master, 0x1000))
                execute(manifest['symbols']['choose_elemental_summon'])
                family = get(base+0x551780+arte*8+2, 'B') & 15
                expected = 42+family if held and 70 <= arte <= 95 else arte
                assert uc.reg_read(regs['rax']) == expected, (char, arte, held, expected)
                assert saved == {k:uc.reg_read(v) for k,v in regs.items() if k != 'rax'}
                assert bytes(uc.mem_read(master, 0x1000)) == before
                assert uc.reg_read(UC_X86_REG_RSP) == sp+8
    for args in [dict(vitality=0x9800), dict(vitality=0x9000), dict(owner=4),
                 dict(owner=0), dict(learned=False), dict(char=0), dict(char=1), dict(char=6)]:
        actor = setup(**args)
        reg('rax', 71); reg('rcx', actor); reg('rdx', inputs)
        execute(manifest['symbols']['choose_elemental_summon'])
        assert uc.reg_read(regs['rax']) == 71, args
    for missing in ['actor', 'input', 'master', 'table', 'level', 'enemy']:
        actor = setup()
        reg('rax', 71); reg('rcx', actor); reg('rdx', inputs)
        if missing == 'actor': reg('rcx', 0)
        if missing == 'input': reg('rdx', 0)
        if missing == 'master': put(base+0x12cea60, 'Q', 0)
        if missing == 'table': put(base+0x12cea78, 'Q', 0)
        if missing == 'level': put(master+0xbb9, 'B', 0)
        if missing == 'enemy': put(actor+0x51, 'B', 1)
        execute(manifest['symbols']['choose_elemental_summon'])
        assert uc.reg_read(regs['rax']) == 71, missing
    checks.append('All 116 arte IDs for both mages, with/without Guard; ownership, learned access, gauge and null-pointer exclusions; no state writes')

    # Actual patched entry and native command reader, four preset directions,
    # including query-only mode used during combat transitions.
    for char in [2, 3]:
        for direction, slot in [(0,0xac), (1,0xad), (2,0xae), (4,0xaf)]:
            for held in [0, 0x80]:
                actor = setup(char, held)
                put(actor+slot, 'B', 71)
                put(inputs+0x10, 'B', direction)
                reg('rcx', actor); reg('rdx', 0)
                execute(0x1140f0)
                assert uc.reg_read(regs['rax']) == (43 if held else 71)
                assert get(actor+slot, 'B') == 71, 'Binding must never change'
    checks.append('Native player reader: four directions and query mode capture the chosen action without changing bindings')

    for char in [2, 3]:
        for mode in [0, 1, 2]:
            for held in [0, 0x80]:
                actor = setup(char, 0)
                put(actor+0x57, 'B', mode)
                # Issuer and recipient have different inputs. Only issuer counts.
                put(actors+0xf0, 'Q', inputs+0x20)
                put(inputs+0x20, 'I', held)
                reg('r14', actors); reg('rbx', actor); reg('rbp', 71)
                execute(0x1134c7, [0x1134cc])
                assert uc.reg_read(regs['rdx']) == (43 if held else 71)
                assert uc.reg_read(regs['rbp']) == (43 if held else 71)
                assert uc.reg_read(regs['rcx']) == actor
                assert uc.reg_read(UC_X86_REG_RSP) == sp
    checks.append('Explicit ally shortcuts use issuer input and update the action before native validation, including AI recipients')

    # Full native start-cast execution; stub animation setup and casting graphic
    # only. Autonomous AI enters the original launch directly and is not replaced.
    presentation = [0x7fe70, 0x114980, 0x1b5ca0]
    for char in [2, 3]:
        for arte in [71, 73, 78, 81, 85, 88, 90, 92, 94, 95]:
            for held in [0, 0x80]:
                actor = setup(char, held)
                put(actor+0xac, 'B', arte)
                reg('rcx', actor); reg('rdx', 1)
                execute(0x1140f0, stubs=presentation)
                family = get(base+0x551780+arte*8+2, 'B') & 15
                result = 42+family if held else arte
                assert get(actor+0x6d, 'B') == result
                assert get(actor+0x8e, 'H') == get(base+0x551780+result*8, 'B')
                assert get(actor+0x34, 'H') == 500, 'No debit or double debit during selection/start'
                assert get(master+0xbba+(family-1)*8, 'H') == 0xa000
                assert get(actor, 'Q') == enemies, 'Native target route retained'
        actor = setup(char)
        put(actor+0x57, 'B', 0)
        reg('rcx', actor); reg('rdx', 71)
        execute(0x112d10, stubs=presentation)
        assert get(actor+0x6d, 'B') == 71, 'Autonomous spell must not change'

    for char in [2,3]:
        for tp in [0, 29, 30, 500]:
            actor = setup(char)
            put(actor+0xac, 'B', 71); put(actor+0x34, 'H', tp)
            reg('rcx', actor); reg('rdx', 1)
            execute(0x1140f0, stubs=presentation)
            assert get(actor+0x6d, 'B') == (43 if tp >= 30 else 0)
            assert get(actor+0x34, 'H') == tp
            assert get(master+0xbba, 'H') == 0xa000
    checks.append('Full native cast starts for ten families and both mages; costs checked, insufficient TP refuses invocation, AI unaffected')

    # Guard hook runs within a function (stack aligned to 16), not at its entry.
    for char in [2,3]:
        for held, pressed, stunned, expected in [(0x80,0x40,0,43),(0x80,0,0,0),
                                                 (0,0x40,0,0),(0x280,0x40,0,0),(0x80,0x40,1,0)]:
            actor = setup(char, held)
            put(inputs+4, 'I', pressed); put(actor+0x44, 'H', stunned)
            put(actor+0xac, 'B', 71); put(actor+0x52, 'B', 2)
            reg('rbx', actor)
            execute(0x72723, [0x72627,0x7272a], stubs=presentation, stack=sp-8)
            assert get(actor+0x6d, 'B') == expected
            assert uc.reg_read(UC_X86_REG_RSP) == sp-8
    checks.append('Already-held Guard invokes once on new Arte press; target selection, stun and no press keep native guard behavior')

    for char in [2,3]:
        for element in range(10):
            for initial, expected in [(0xa000,0xa000),(0x9000,0x9800),(0x9800,0xa000)]:
                setup(char)
                put(master+0xbba+element*8, 'H', initial)
                reg('rcx', char); reg('rdx', element); reg('r8', 0x800); reg('r9', 0)
                execute(0x90380)
                assert get(master+0xbba+element*8, 'H') == expected, (char, element, initial)
            # Spell cast by the other mage also must not lower full gauge to five.
            setup(char, owner=4 if char == 2 else 3)
            reg('rcx', char); reg('rdx', element); reg('r8', 0x800); reg('r9', 0)
            execute(0x90380)
            assert get(master+0xbba+element*8, 'H') == 0xa000
    checks.append('Native vitality routine: full stays full for both mages; ordinary charging still reaches ten')

    for element in range(10):
        for level in [1, 15, 30]:
            actor = setup()
            put(master+0xbb9+element*8, 'B', level)
            put(actor+0x8e, 'H', 26+element)
            reg('rbx', actor); reg('rdi', actor+0x8e); reg('r12',0); reg('r14',base)
            execute(0xd55c3, [0xd569d])
            assert get(master+0xbba+element*8, 'H') == level*4096//10
    checks.append('Actual invocation consumption is unchanged: ten families, levels 1/15/30 return to level/10 vitality')

    for arte in range(43,53):
        for discount in [0, 0x400, 0x200]:
            actor = setup()
            put(stats+0x4e,'H',discount)
            reg('rcx', actor); reg('rdx', arte); reg('r8', 1)
            # Stop immediately after the native debit, before HUD propagation.
            execute(0x8fe50, [0x8fec2])
            cost = get(base+0x562a50+arte*24,'B')
            if discount == 0x400: cost //= 2
            if discount == 0x200: cost = cost*2//3
            assert get(actor+0x34,'H') == 500-cost
    checks.append('Native debit uses only the invocation cost, retaining half/two-thirds cost equipment reductions')
    return checks, count
