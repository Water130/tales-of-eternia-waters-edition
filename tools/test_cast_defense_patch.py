"""Exercise native cleanup, command readers and guard/jump state transitions."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_cast_defense(uc, base, manifest, actors, enemies, stats, sp,
                       reset, put, get, reg, regs):
    flags = base+manifest['mod_settings']['flags_rva']
    master, inputs = actors+0xa000, actors+0xc000
    sentinel = base+manifest['data_rva']-16
    actor = actors+2*0x248
    cases = 0

    def setup(char=2, state=10, timer=100, control=2, guard=True, press=True,
              up=False, duration=2, cancel=1, jump=1, pending=0):
        reset()
        put(flags+10,'BB',cancel,jump)
        put(base+0x12cea60,'Q',master)
        put(base+0x12cea68,'Q',actors+0xc100)
        put(base+0x12cea70,'Q',base+0x562a50)
        put(base+0x12cea78,'Q',base+0x551780)
        put(base+0x6449e0,'Q',actors+0xc200)
        put(actor+0x4f,'B',char)
        put(actor+0x52,'BB',state,0xff)
        put(actor+0x57,'B',control)
        put(actor+0xf0,'Q',inputs)
        put(actor+0xe8,'Q',stats)
        put(actor,'Q',enemies)
        put(actor+0x8c,'HHH',timer,2,pending)
        put(actor+0xa2,'HH',0,0x40)
        put(actor+0x6c,'BB',4,71)
        put(actor+0xba,'B',3)
        put(actor+0x34,'H',500)
        put(actor+0x42,'H',64)
        put(inputs,'II',(0x80 if guard else 0)|(1 if up else 0),0x80 if press else 0)
        put(inputs+0xd,'B',duration)
        put(inputs+0x10,'B',int(up))
        put(base+0x8c9180,'I',0x100)  # Cast cancellation must win over L1 hold.
        put(base+0x8c922f,'BB',1,1)
        for i in range(10):
            put(master+0xbb8+8*i,'BBH',char+1,15,0xa000)

    def execute(start, stops=None, entry_sp=sp, stubs=()):
        nonlocal cases
        cases += 1
        reached = []
        targets = {base+x for x in stops} if stops else {sentinel}
        uc.reg_write(UC_X86_REG_RSP,entry_sp)
        put(entry_sp,'Q',sentinel)
        def step(emu,address,size,user):
            if address in targets:
                reached.append(address-base)
                emu.emu_stop()
            elif address-base in stubs:
                current=emu.reg_read(UC_X86_REG_RSP)
                assert current%16 == 8, ('ABI',hex(address-base))
                reg('rax',0)
                emu.reg_write(UC_X86_REG_RIP,get(current,'Q'))
                emu.reg_write(UC_X86_REG_RSP,current+8)
        hook=uc.hook_add(UC_HOOK_CODE,step)
        for target in targets:uc.ctl_remove_cache(target-16,target+16)
        try:
            uc.emu_start(base+start,sentinel+1,count=20000)
        finally:
            uc.hook_del(hook)
        assert reached, (hex(start),hex(uc.reg_read(UC_X86_REG_RIP)-base))
        stack_delta = 8 if stops is None else (-0x68 if start == 0xd51f0 else 0)
        assert uc.reg_read(UC_X86_REG_RSP) == entry_sp+stack_delta
        return reached[0]

    def controls():
        reg('rcx',actor)
        before={r:uc.reg_read(v) for r,v in regs.items() if r!='r13'}
        input_before=bytes(uc.mem_read(inputs,0x20))
        master_before=bytes(uc.mem_read(master,0x1000))
        execute(0xd520c,[0xd5214],sp-0x68)
        assert before == {r:uc.reg_read(regs[r]) for r in before}
        assert uc.reg_read(regs['r13']) == get(actor+0x90,'H')
        assert bytes(uc.mem_read(inputs,0x20)) == input_before
        assert bytes(uc.mem_read(master,0x1000)) == master_before
        assert get(actor+0x34,'H') == 500

    try:
        # Compare with actual native interruption, not a recreated cleanup.
        for char in (0,1,2,3,4,5,6):
            for control in (1,2):
                for timer in (1,2,4,30,500):
                    for mask in (0,0x40,0x400,0x800,0x100,0x2000):
                        setup(char=char,control=control,timer=timer,up=True)
                        put(actor+0xa4,'H',mask)
                        before=bytes(uc.mem_read(actor,0x248))
                        reg('rcx',actor);execute(0x712e0)
                        put(actor+0x52,'B',0)
                        put(actor+0x75,'B',0)
                        put(actor+0x90,'H',6)
                        expected=bytes(uc.mem_read(actor,0x248))
                        uc.mem_write(actor,before)
                        controls()
                        assert bytes(uc.mem_read(actor,0x248)) == expected
                        assert get(actor+0x8c,'I') == 0
                        assert get(actor+0xa4,'H') == 0

        # Exclusions leave every actor field unchanged, including pending input.
        exclusions = [
            (flags+10,'B',0),(actor+0x51,'B',1),(actor+0x3c,'H',2),
            (actor+0x57,'B',0),(actor+0x57,'B',3),(actor+0x2c,'i',0),
            (actor+0x44,'H',1),(actor+0x74,'B',1),(actor+0x30,'I',0x4000),
            (actor+0x12,'h',-1),(actor+0xf0,'Q',0),(inputs,'I',0x280),
            (inputs+4,'I',0),(inputs,'I',0),(actor+0x8c,'h',0),
            (actor+0x8c,'h',-1),(base+0x12d0ef7,'B',1),
            (actor+0xe8,'Q',0),(base+0x12cea60,'Q',0),
        ]
        for address,fmt,value in exclusions:
            setup()
            put(address,fmt,value)
            before=bytes(uc.mem_read(actor,0x248))
            controls()
            assert bytes(uc.mem_read(actor,0x248)) == before, hex(address)

        # Jump option is independent, and never touches spells, attacks,
        # other characters, airborne motion, or autonomous AI.
        for enabled in (0,1):
            for char in range(7):
                for state in (0,1,2,3,4,8,9,10):
                    for guard in (False,True):
                        for up,duration in ((False,2),(True,1),(True,2)):
                            setup(char=char,state=state,guard=guard,up=up,
                                  duration=duration,press=False,cancel=0,jump=enabled,pending=3)
                            before=bytearray(uc.mem_read(actor,0x248))
                            affected=enabled and char in (2,3) and state<=3
                            if affected:
                                if guard and up and duration>=2:
                                    if state==2:before[0x52]=0
                                else:
                                    before[0x90:0x92]=b'\0\0'
                            controls()
                            assert bytes(uc.mem_read(actor,0x248)) == bytes(before), (enabled,char,state,guard,up,duration)

        for changes in (
            [(actor+0x57,'B',0)],[(actor+0x51,'B',1)],
            [(actor+0x44,'H',4)],[(actor+0x12,'h',-32)],
            [(inputs,'I',0x281)],[(base+0x12d0ef7,'B',1)],
        ):
            setup(state=0,up=True,press=False)
            for address,fmt,value in changes:put(address,fmt,value)
            before=bytes(uc.mem_read(actor,0x248))
            controls()
            assert bytes(uc.mem_read(actor,0x248)) == before

        # Real manual and semi-auto command readers, followed by the complete
        # update through its native guard/jump state initialization.
        for reader,control in ((0x114300,2),(0x72490,1)):
            for enabled in (0,1):
                for char in (2,3):
                    for state in (0,1,2,3):
                        for guard,up in ((False,True),(True,True),(True,False)):
                            setup(char=char,state=state,timer=0,control=control,
                                  guard=guard,up=up,press=False,jump=enabled)
                            put(actor+0x64,'B',0)
                            reg('rcx',actor)
                            execute(reader,stubs=(0x111fe0,0x1140f0,0x8fa90))
                            requested=get(actor+0x90,'H')
                            reg('rcx',actor)
                            # Stop before animation submission; simulation and
                            # native guard/jump initialization have executed.
                            execute(0xd51f0,[0xd6081],sp,
                                    stubs=(0x8fa90,0x8bac0))
                            if enabled:
                                assert (get(actor+0x52,'B')==4) == (guard and up), (reader,char,state,guard,up)
                            elif requested==3:
                                assert get(actor+0x52,'B')==4
                            if get(actor+0x52,'B')==4:
                                assert get(actor+0x1a,'h') == -192
                                assert get(actor+0x22,'H') == 16
                                assert get(actor+0x90,'H') == 0
                            assert get(actor+0x34,'H')==500

        # An upward diagonal without Guard keeps native horizontal movement
        # and dash braking. Compare complete native transitions with the same
        # inputs lacking only Up, using real direction readers in both modes.
        for reader,control in ((0x114300,2),(0x72490,1)):
            for char in (2,3):
                for state in (0,1,3):
                    for facing in (-1,1):
                        for horizontal in (2,8):
                            outcomes=[]
                            for up in (False,True):
                                setup(char=char,state=state,timer=0,control=control,
                                      guard=False,up=up,press=False)
                                put(actor+0x53,'b',facing)
                                put(actor+0x64,'B',0)
                                put(actor+0x56,'B',1)
                                put(inputs,'I',horizontal|int(up))
                                put(inputs+0x10,'B',horizontal|int(up))
                                reg('rcx',actor)
                                execute(reader,stubs=(0x111fe0,0x1140f0,0x8fa90))
                                reg('rcx',actor)
                                execute(0xd51f0,[0xd6081,0xd6088],sp,
                                        stubs=(0x8fa90,0x8bac0))
                                outcomes.append(tuple(get(actor+offset,fmt) for offset,fmt in
                                    ((0x52,'B'),(0x53,'b'),(0x18,'h'),(0x1a,'h'),
                                     (0x22,'H'),(0x44,'H'),(0x90,'H'))))
                            assert outcomes[0]==outcomes[1], (reader,char,state,facing,horizontal,outcomes)

        # Guard cancellation reaches native guard (state 2, animation 2)
        # before any spell cost or effect dispatch, even in a ready/held cast.
        for char in (2,3):
            for control in (1,2):
                for timer in (1,2,4,30,500):
                    setup(char=char,control=control,timer=timer,up=True)
                    before=bytes(uc.mem_read(master,0x1000))
                    reg('rcx',actor)
                    execute(0xd51f0,[0xd6081])
                    assert get(actor+0x52,'B')==2
                    assert uc.reg_read(regs['rbp'])==2
                    assert get(actor+0x90,'H')==6
                    assert get(actor+0x8c,'I')==0 and get(actor+0xa4,'H')==0
                    assert get(actor+0x34,'H')==500
                    assert bytes(uc.mem_read(master,0x1000))==before
                    # Releasing Guard follows the original control transition.
                    put(inputs,'II',0,0);put(inputs+0x10,'B',0)
                    reg('rcx',actor)
                    execute(0x114300 if control==2 else 0x72490,
                            stubs=(0x111fe0,0x1140f0,0x8fa90))
                    assert get(actor+0x90,'H')==0
                    # Native spell initialization can start a fresh cast.
                    put(actor+0x52,'B',0)
                    reg('rcx',actor);reg('rdx',71)
                    execute(0x112d10,stubs=(0x7fe70,0x114980,0x1b5ca0))
                    assert get(actor+0xa4,'H')==0x40 and get(actor+0x6d,'B')==71
                    assert get(actor+0x8c,'H')>0
    finally:
        put(flags+10,'BB',1,1)
    return cases
