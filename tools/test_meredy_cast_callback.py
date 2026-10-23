"""Exercise Meredy's entire native casting callback, including shared branches.

Regression for the two dumps ending at GameNative+0xcc8be. Testing only the
particle callsites misses native jumps into the middle of an option gate.
"""
from unicorn import UC_HOOK_CODE, UcError
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP
from mod_settings_patch import FLAG_OFFSETS


def check_meredy_cast_callback(uc, base, manifest, actors, sp, reset, put, get, reg, regs):
    pool, effect = 0x21000000, actors+0x9000
    ends = (0xcc570, 0x115ee0, manifest['data_rva']-0x10)
    flag = base+manifest['data_rva']+FLAG_OFFSETS[22]
    saved_flag = get(flag, 'B')
    uc.mem_map(pool, 0x10000)
    count = 0
    try:
        # Phase 1 follows the exact JNE -> shared continuation seen in the dumps.
        for enabled in (1, 0):
            for timer in (1, *range(32), -1, -4, -8, -16):
                for null_first in (False, True):
                    for casting in (0, 3):
                        reset()
                        actor = actors+3*0x248
                        put(actor+0x6c, 'B', 6*4)  # Lightning / Volt
                        put(actor+0x8c, 'H', casting)
                        put(effect, 'Q', actor)
                        put(effect+0x38, 'h', timer)
                        put(effect+0x48, 'Q', base+0x591a68-0x17b8)
                        put(effect+0x58, 'Q', base+0x592f38-0x1158)
                        put(effect+0x60, 'Q', base+0x58ff54-0x424)
                        uc.mem_write(pool, bytes(0x10000))
                        put(base+0x12cecf0, 'Q', pool)
                        put(base+0x12cec20, 'Q', pool+0x6000)
                        put(flag, 'B', enabled)
                        put(sp, 'Q', base+ends[2])
                        reg('rcx', effect)
                        uc.reg_write(UC_X86_REG_RSP, sp)
                        nonvolatile = {r: uc.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
                        reached, shared, first = [], [], [True]

                        def step(emu, address, size, user):
                            rva = address-base
                            if rva in ends:
                                reached.append(rva); emu.emu_stop()
                            if rva == 0xcc8b9:
                                shared.append(rva)
                            stub_value = None
                            if rva == 0x8b7e0 and first[0]:
                                first[0] = False
                                if null_first: stub_value = 0
                            elif rva == 0x283090: stub_value = 1
                            elif rva in (0x19eea0, 0x19ee60): stub_value = 0
                            if stub_value is not None:
                                rsp = emu.reg_read(UC_X86_REG_RSP)
                                assert rsp % 16 == 8, ('Native ABI alignment', hex(rva))
                                reg('rax', stub_value)
                                emu.reg_write(UC_X86_REG_RIP, get(rsp, 'Q'))
                                emu.reg_write(UC_X86_REG_RSP, rsp+8)

                        hook = uc.hook_add(UC_HOOK_CODE, step)
                        try:
                            uc.emu_start(base+0xcc820, base+ends[2]+1, count=40000)
                        except UcError as exc:
                            raise AssertionError(dict(error=str(exc), rva=hex(uc.reg_read(UC_X86_REG_RIP)-base),
                                                      rax=hex(uc.reg_read(regs['rax'])),
                                                      enabled=enabled,timer=timer,null_first=null_first,casting=casting)) from exc
                        finally:
                            uc.hook_del(hook)
                        assert reached == [0xcc570 if casting else 0x115ee0], (enabled,timer,null_first,casting,reached)
                        assert shared == [0xcc8b9]
                        assert uc.reg_read(UC_X86_REG_RSP) == sp
                        assert nonvolatile == {r:uc.reg_read(regs[r]) for r in nonvolatile}
                        assert get(effect+0x31,'B') == 4
                        count += 1
        # Both incoming native jumps must target intact instructions, never the
        # displacement/padding of a generated five-byte gate.
        for branch_target in (0xcc8b9, 0xcc8df, 0xcc93b):
            for edit in manifest['edits']:
                start, length = edit['rva'], len(bytes.fromhex(edit['patched']))
                assert not start < branch_target < start+length, (edit['name'],hex(branch_target))
    finally:
        put(flag, 'B', saved_flag)
        uc.mem_unmap(pool, 0x10000)
    return count
