"""Execute the real Spread extension gate and TP debit, including level edges."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_maelstrom_level(uc, base, manifest, actors, stats, impact, sp,
                         reset, put, get, reg, regs):
    master, config, options = actors+0xa000, actors+0xc100, actors+0xc200
    site, continuation, reject, success = 0xc0f0b, 0xc0f13, 0xc10aa, 0xc1002
    count = 0
    change = next(e for e in manifest['edits'] if e['rva'] == site)
    patched, original = bytes.fromhex(change['patched']), bytes.fromhex(change['original'])
    eligibility = next(e for e in manifest['edits'] if e['rva'] == 0xc0f19)
    assert original == bytes.fromhex('4180b8b90b00000f')

    def execute(start, stops):
        nonlocal count
        count += 1
        reached = []

        def step(emu, address, size, user):
            rva = address-base
            if rva in stops:
                reached.append(rva)
                emu.emu_stop()
            elif rva in (0x8d520, 0x1b5ca0):
                # Only HUD propagation and the insufficient-TP sound. The
                # actual cost table, discounts, affordability and debit execute.
                stack = emu.reg_read(UC_X86_REG_RSP)
                assert stack % 16 == 8, ('Native call alignment', hex(rva))
                destination = get(stack, 'Q')
                emu.reg_write(UC_X86_REG_RSP, stack+8)
                emu.reg_write(UC_X86_REG_RIP, destination)

        handle = uc.hook_add(UC_HOOK_CODE, step)
        try:
            uc.emu_start(base+start, base+manifest['data_rva'], count=5000)
        finally:
            uc.hook_del(handle)
        assert reached, ('No continuation', hex(uc.reg_read(UC_X86_REG_RIP)))
        assert uc.reg_read(UC_X86_REG_RSP) == sp-8
        return reached[0]

    def setup(char=2, side=0, level=10, resistance=10, vitality=0xa000,
              tp=100, timer=0x60, battle=6, action=7, difficulty=0,
              discount=0, boost=0, casts=50, bonus=0):
        reset()
        raw=base+manifest['artesphere']['usage']['live_rva']
        extra=base+manifest['artesphere']['usage']['catchup']['live_rva']
        put(raw+(char*128+71)*2,'H',casts)
        put(extra+(char*128+71)*2,'H',bonus)
        put(base+manifest['data_rva']+0x1a49,'B',1)
        uc.reg_write(UC_X86_REG_RSP, sp-8)  # mid-function call-site alignment
        actor = actors+char*0x248
        put(actor+0x51, 'B', side)
        put(actor+0x23a, 'B', action)
        put(actor+0x34, 'h', tp)
        put(stats+0x31, 'b', resistance)
        put(stats+0x4e, 'H', discount)
        put(master+0xbb9, 'BH', level, vitality)
        put(config+4, 'B', difficulty)
        put(options+0x2c, 'B', boost)
        put(base+0x12cea60, 'Q', master)
        put(base+0x12cea68, 'Q', config)
        put(base+0x12cea70, 'Q', base+0x562a50)
        put(base+0x6449e0, 'Q', options)
        put(base+0x644a70, 'Q', 0)  # no message renderer needed to test eligibility
        put(base+0x12d0ef7, 'B', battle)
        put(base+0x865610, 'I', 0)
        put(impact, 'Q', actor)
        put(impact+0x38, 'H', timer)
        reg('rbx', impact)
        reg('r9', actor)
        reg('r8', master)
        return actor

    # All valid Craymel levels: comparison preserves every GPR, stack, state and
    # the unsigned below/at-boundary branch. Unknown/nonparty sides stay native.
    for side in (0, 1, 2):
        for level in range(31):
            setup(side=side, level=level)
            before = {k: uc.reg_read(v) for k, v in regs.items()}
            state = bytes(uc.mem_read(master, 0x1000))
            execute(site, [continuation])
            assert before == {k: uc.reg_read(v) for k, v in regs.items()}
            assert state == bytes(uc.mem_read(master, 0x1000))
            # Execute the actual native JB, not a reimplemented flag test.
            destination = execute(continuation, [reject, 0xc0f19])
            assert (destination == 0xc0f19) == (level >= (10 if side == 0 else 15))

    raw_cost = get(base+0x562a50+71*24, 'B')
    assert raw_cost > 0

    def scenario(expected, *, native=False, disabled=False, **args):
        actor = setup(**args)
        if disabled:put(base+manifest['data_rva']+0x1a49,'B',0)
        tp = get(actor+0x34, 'h')
        vitality = get(master+0xbba, 'H')
        state = bytes(uc.mem_read(master, 0x1000))
        cost = raw_cost
        if args.get('boost', 0):
            cost //= 2
        if args.get('discount', 0) & 0x400:
            cost //= 2
        elif args.get('discount', 0) & 0x200:
            cost = cost*2//3
        uc.mem_write(base+site, original if native else patched)
        uc.mem_write(base+0xc0f19, bytes.fromhex(eligibility['original' if native else 'patched']))
        try:
            destination = execute(0xc0edb, [reject, success])
        finally:
            uc.mem_write(base+site, patched)
            uc.mem_write(base+0xc0f19, bytes.fromhex(eligibility['patched']))
        assert (destination == success) == expected, (args, native, hex(destination))
        assert get(base+0x865610, 'I') == int(expected), (args, 'extension mode')
        assert get(actor+0x34, 'h') == tp-(cost if expected and not args.get('side', 0) else 0)
        assert get(master+0xbba, 'H') == vitality
        assert bytes(uc.mem_read(master, 0x1000)) == state, 'No Craymel/save writes'

    for char in (2, 3):
        for casts,bonus in ((0,0),(49,0),(49,1),(17,33),(50,0)):
            scenario(casts+bonus>=50,char=char,casts=casts,bonus=bonus)
        for level in (9,10,14,15,30):
            for resistance in (0,10,30):
                for vitality in (0,0x7000,0xa000):
                    expected=level>=15 and resistance>0 and vitality>=(10-int(resistance/10))*4096
                    scenario(expected,char=char,level=level,resistance=resistance,vitality=vitality,disabled=True)
        for level in (9, 10, 14, 15, 30):
            for mode in ('native', 'patched'):
                threshold = 15 if mode == 'native' else 10
                scenario(level >= threshold, char=char, level=level, native=mode == 'native')
        for level in (10, 15):
            for resistance in (-10, 0, 1, 10, 30, 100):
                required = (10-int(resistance/10))*4096
                for vitality in sorted({0, 0x4fff, 0x5000, 0x5001, max(0, required-1), required, 0xa000}):
                    if not 0 <= vitality <= 0xffff:
                        continue
                    scenario(vitality >= 0x5000,
                             char=char, level=level, resistance=resistance, vitality=vitality)
            for discount in (0, 0x200, 0x400):
                for boost in (0, 1):
                    cost = raw_cost//2 if boost else raw_cost
                    cost = cost//2 if discount == 0x400 else cost*2//3 if discount == 0x200 else cost
                    for tp in sorted({0, cost-1, cost, 100}):
                        scenario(tp >= cost, char=char, level=level, tp=tp,
                                 discount=discount, boost=boost)
            for args in (dict(timer=0x5f), dict(timer=0x61), dict(battle=0), dict(action=6)):
                scenario(False, char=char, level=level, **args)

    # Enemy rule is deliberately identical to the original in every difficulty;
    # their TP and vitality bypasses remain native as well.
    for native in (False, True):
        for level in (9, 10, 14, 15, 30):
            for difficulty in range(4):
                scenario(level >= 15 and difficulty >= 1, native=native, side=1,
                         level=level, difficulty=difficulty, vitality=0, resistance=0, tp=0)

    return count
