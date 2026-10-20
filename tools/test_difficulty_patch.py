"""Native enemy record and fixed-hit calculations, with the option on and off."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_difficulty(uc, base, manifest, actors, stats, impact, sp,
                     reset, put, get, reg, regs):
    config = actors+0xc100
    flag = base+manifest['mod_settings']['flags_rva']+8
    count = 0

    def setup(enabled, difficulty):
        reset()
        put(flag, 'B', enabled)
        put(config+4, 'B', difficulty)
        put(base+0x12cea68, 'Q', config)

    def run(start, end):
        nonlocal count
        count += 1
        hit = []
        def stop(emu, address, size, user):
            if address == base+end:
                hit.append(True)
                emu.emu_stop()
        hook = uc.hook_add(UC_HOOK_CODE, stop)
        try:
            uc.emu_start(base+start, base+manifest['data_rva'], count=2000)
        finally:
            uc.hook_del(hook)
        assert hit, ('No continuation', hex(uc.reg_read(UC_X86_REG_RIP)))
        assert uc.reg_read(UC_X86_REG_RSP) == sp

    for enabled in (0, 1):
        for difficulty in (0, 1, 2, 3, 4, 255):
            for hp, attack, defense, intelligence, accuracy in (
                (1000, 100, 100, 100, 100),
                (101, 101, 101, 101, 71),
                (1, 1, 1, 1, 0),
                (999999, 9999, 9999, 9999, 999),
                (12345, 71, 0, 83, 37),
                (67891, 71, 30000, 83, 37),
            ):
                setup(enabled, difficulty)
                record = bytearray(b'\x31'*0x100)
                for offset, fmt, value in (
                    (0x18, 'i', hp), (0x1e, 'h', attack), (0x22, 'h', defense),
                    (0x24, 'h', intelligence), (0x26, 'h', accuracy),
                ):
                    struct.pack_into('<'+fmt, record, offset, value)
                uc.mem_write(stats, bytes(record))
                reg('rdi', stats)
                put(sp+0x40, 'QQ', 0x12340000, 0x56780000)
                saved = {r: uc.reg_read(regs[r]) for r in regs if r not in ('rax','rcx','rdx','rsi','rbp')}
                run(0x82a2e, 0x82b3f)
                expected = bytearray(record)
                d = difficulty if difficulty <= 3 else 0
                hp_multiplier = (10, 15, 30, 50)[d] if enabled else (10, 12, 15, 18)[d]
                def_multiplier = (10+d) if enabled else 10
                for offset, fmt, value in (
                    (0x18, 'i', hp*hp_multiplier//10),
                    (0x1e, 'h', attack*(10,11,12,13)[d]//10),
                    (0x22, 'h', min(32767, defense*def_multiplier//10)),
                    (0x24, 'h', intelligence*(10,11,13,15)[d]//10),
                    (0x26, 'h', accuracy+d*10),
                ):
                    struct.pack_into('<'+fmt, expected, offset, value)
                assert bytes(uc.mem_read(stats, 0x100)) == bytes(expected), (enabled, difficulty, hp, defense)
                assert saved == {r: uc.reg_read(regs[r]) for r in saved}, 'Register corruption'
                assert uc.reg_read(regs['rbp']) == 0x12340000
                assert uc.reg_read(regs['rsi']) == 0x56780000
                assert get(flag, 'B') == enabled

    # HP scaling uses wide intermediates and cannot wrap a large boss HP field.
    for difficulty in (1,2,3):
        setup(1, difficulty)
        put(stats+0x18, 'i', 2_000_000_000)
        reg('rdi', stats)
        run(0x82a2e, 0x82b3f)
        assert get(stats+0x18, 'i') == 0x7fffffff

    # Execute the original attack-mode switch too. Only enemy mode 3 changes.
    for enabled in (0,1):
        for difficulty in (0,1,2,3,4,255):
            for side in (0,1):
                for mode in range(4):
                    for amount in (0,1,7,100,101,32767):
                        setup(enabled, difficulty)
                        put(actors+0x51, 'B', side)
                        put(impact+2, 'B', mode)
                        put(impact+10, 'h', amount)
                        reg('rbp', actors)
                        reg('r12', impact)
                        reg('r15', 40)
                        reg('rsi', 1234)
                        saved = {r: uc.reg_read(regs[r]) for r in regs if r not in ('rax','rcx','rdx','rsi')}
                        run(0x8ecbc, 0x8ed32)
                        if mode == 0:
                            expected = 1234+amount
                        elif mode == 1:
                            expected = 1234+amount-40
                        elif mode == 2:
                            expected = 1234*amount//100
                        else:
                            expected = amount
                            if side == 1:
                                if enabled and difficulty in (1,2):
                                    expected += amount*difficulty//10
                                elif difficulty == 1:
                                    expected += amount//4
                                elif 2 <= difficulty < 128:
                                    expected += amount//2
                        assert uc.reg_read(regs['rsi']) == expected, (enabled,difficulty,side,mode,amount)
                        assert saved == {r: uc.reg_read(regs[r]) for r in saved}
                        assert get(flag, 'B') == enabled

    put(flag, 'B', 1)
    return count
