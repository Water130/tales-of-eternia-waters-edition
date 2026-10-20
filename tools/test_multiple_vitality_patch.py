"""Execute the complete native vitality routine, including consumption and counters."""
import struct
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RAX, UC_X86_REG_RIP


def check_multiple_vitality(uc, base, manifest, actors, sp, reset, put, get, reg, regs):
    master = actors+0xa000
    flag = base+manifest['mod_settings']['flags_rva']+9
    sentinel = base+manifest['data_rva']-16
    opposites = [5, 3, 4, 1, 2, 0, 7, 6, 9, 8]
    assert list(uc.mem_read(base+0x4e8748, 10)) == [x+1 for x in opposites]
    cases = 0

    def setup(enabled, caster, owner, gauges, level=10, counter=0):
        reset()
        put(flag, 'B', enabled)
        put(base+0x12cea60, 'Q', master)
        block = bytearray(b'\x55'*0x1000)
        for family, gauge in enumerate(gauges):
            struct.pack_into('<BBH', block, 0xbb8+8*family, owner, level, gauge)
        uc.mem_write(master, bytes(block))
        for family in range(10):
            put(base+0x12cecba+2*family, 'H', counter)
        return bytes(block)

    def call(caster, family, gain=0x800, mode=0):
        nonlocal cases
        cases += 1
        uc.reg_write(UC_X86_REG_RSP, sp)
        put(sp, 'Q', sentinel)
        reg('rcx', caster)
        reg('rdx', family & 0xffffffff)
        reg('r8', gain)
        reg('r9', mode)
        saved = {r: uc.reg_read(regs[r]) for r in
                 ('rbx','rbp','rdi','rsi','r12','r13','r14','r15','r8','r9')}
        uc.emu_start(base+0x90380, sentinel, count=2000)
        assert uc.reg_read(UC_X86_REG_RIP) == sentinel
        assert uc.reg_read(UC_X86_REG_RSP) == sp+8
        assert saved == {r: uc.reg_read(regs[r]) for r in saved}
        return uc.reg_read(UC_X86_REG_RAX)

    def expect(block, gauges, counter, family):
        expected = bytearray(block)
        for i, value in enumerate(gauges):
            struct.pack_into('<H', expected, 0xbba+8*i, value)
        assert bytes(uc.mem_read(master, 0x1000)) == bytes(expected), (
            gauges, [get(master+0xbba+i*8, 'H') for i in range(10)])
        actual = [get(base+0x12cecba+2*i, 'H') for i in range(10)]
        assert actual == [min(100,counter+1) if i == family else counter for i in range(10)]

    try:
        # Mixed MAX/partial gauges, all ten families, both mages and ownership.
        # Verify the complete master block: no level, owner or adjacent save writes.
        for enabled in (0,1):
            for caster in (2,3):
                for owned in (False,True):
                    owner = caster+1 if owned else 4 if caster == 2 else 3
                    for family, opposite in enumerate(opposites):
                        for initial in (0,0x9000,0x9800,0xa000):
                            for opposing in (0,0x5000,0xa000):
                                for gain in (1,0x800,0x1000):
                                    gauges = [0xa000 if i%2 == 0 else 0x7000 for i in range(10)]
                                    gauges[family], gauges[opposite] = initial, opposing
                                    counter = (0,99,100)[(initial//0x800)%3]
                                    block = setup(enabled, caster, owner, gauges, counter=counter)
                                    expected = gauges.copy()
                                    if not (enabled and opposing == 0xa000):
                                        expected[opposite] = max(0, opposing-gain//2)
                                    result = 0
                                    if initial == 0xa000:
                                        expected[family] = 0xa000 if enabled else 0x5000
                                    elif initial+gain < 0xa000:
                                        expected[family] = initial+gain
                                    elif not owned:
                                        expected[family] = 0x9800
                                    else:
                                        if not enabled:
                                            expected = [0x9000 if x == 0xa000 else x for x in expected]
                                        expected[family] = 0xa000
                                        result = 1
                                    assert call(caster,family,gain) == result
                                    expect(block,expected,counter,family)
                                    assert get(flag,'B') == enabled

        # Actual invocation mode consumes only its own gauge; it is never
        # intercepted by the ordinary-cast protection, regardless of the switch.
        for enabled in (0,1):
            for caster in (2,3):
                for family in range(10):
                    for level in (1,10,15,30):
                        gauges = [0xa000]*10
                        block = setup(enabled,caster,caster+1,gauges,level=level,counter=99)
                        assert call(caster,family,mode=1) == 0
                        gauges[family] = (level*0x1000)//10
                        expect(block,gauges,99,family)

        # No-op modes and invalid family inputs retain native bounds behavior.
        for enabled in (0,1):
            for family, mode in ((0,2),(9,255),(10,0),(-1,0)):
                gauges = [0xa000]*10
                block = setup(enabled,2,3,gauges)
                assert call(2,family,mode=mode) == 0
                expect(block,gauges,0,family)

        # Long-lived sequence: charge every family, including opposing pairs.
        # Start below MAX; no gauge is artificially filled by toggling the option.
        for caster in (2,3):
            setup(1,caster,caster+1,[0x9800]*10)
            for family in range(10):
                for _ in range(3):
                    if get(master+0xbba+8*family,'H') == 0xa000:
                        break
                    call(caster,family)
                assert all(get(master+0xbba+8*i,'H') == 0xa000 for i in range(family+1))
            assert [get(master+0xbba+8*i,'H') for i in range(10)] == [0xa000]*10
            call(caster,0,mode=1)
            assert get(master+0xbba,'H') == 0x1000
            assert all(get(master+0xbba+8*i,'H') == 0xa000 for i in range(1,10))
            put(flag,'B',0)
            call(caster,1)
            assert get(master+0xbba+8,'H') == 0x5000
            assert get(master+0xbba+8*opposites[1],'H') == 0x9c00
    finally:
        put(flag,'B',1)
    return cases
