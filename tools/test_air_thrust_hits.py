"""Air Thrust's native collision loop, hit writes and HP commit under ASLR.

Graphics/audio and damage *calculation* are isolated: use a fixed post-defense
174 damage. Collision geometry, cooldown decisions, number queue and HP
subtraction execute the patched native instructions, not a Python hit model.
"""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP


def check_air_hits(u, base, m, actors, enemies, impact, sp, reset, put, get, reg, regs):
    air=m['spell_mastery']['projectile_growth'][0]
    info=air['independent_hits']
    ledger=base+info['ledger_rva'];scope=base+info['scope_rva']
    pool=base+0x12cfca0;scratch=base+0x12cf988
    flag=base+m['mod_settings']['flag_rvas'][29]
    saved_flags={base+addr:get(base+addr,'B') for addr in m['mod_settings']['flag_rvas']}
    desc=base+0x577e98
    interval=get(desc+11,'B')
    assert interval>0
    sprite=impact+0x100
    cases=0;hits=[];damage_saved=None;response_saved=None

    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('ABI',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rsp))
        reg('rax',value)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'))
        u.reg_write(UC_X86_REG_RSP,rsp+8)

    def boundary(emu,address,size,_):
        nonlocal damage_saved,response_saved
        a=address-base
        if a in (0xc7550,0x279670,0x1b5ca0):ret()  # particle, stack cookie, audio
        elif a==0x283090:ret(99)  # deterministic non-critical roll
        elif a==0x8e910:
            damage_saved=({r:u.reg_read(v) for r,v in regs.items()},u.reg_read(UC_X86_REG_RSP))
            hits.append((u.reg_read(regs['rcx']),u.reg_read(regs['rdx'])))
        elif a==0x8e929 and damage_saved:
            saved,_=damage_saved
            reg('rbp',saved['rcx']);reg('rdi',saved['rdx'])
            reg('rsi',174);reg('r8',impact)
            reg('r12',saved['r9'])
            for r in ('r14','r13','r15','rbx'):reg(r,0)
            u.reg_write(UC_X86_REG_RIP,base+0x8effc)
        elif a==0x8f0a1 and damage_saved:
            saved,rsp=damage_saved;damage_saved=None
            for r,v in saved.items():reg(r,v)
            u.reg_write(UC_X86_REG_RSP,rsp);ret()
        elif a==0x8e320:
            # Execute the genuine response's cooldown write; omit its unrelated
            # actor animation, combo award and sound work in this fixture.
            rsp=u.reg_read(UC_X86_REG_RSP)
            response_saved=({r:u.reg_read(v) for r,v in regs.items()},rsp)
            reg('rbx',get(rsp+0x28,'Q'));reg('rdi',u.reg_read(regs['r9']))
            reg('rsi',u.reg_read(regs['r8']))
            u.reg_write(UC_X86_REG_RIP,base+0x8e69f)
        elif a==0x8e6b2 and response_saved:
            saved,rsp=response_saved;response_saved=None
            for r,v in saved.items():reg(r,v)
            u.reg_write(UC_X86_REG_RSP,rsp);ret()

    h=u.hook_add(UC_HOOK_CODE,boundary)
    def run(start,end,frame_sp=sp-8):
        nonlocal cases
        cases+=1
        u.reg_write(UC_X86_REG_RSP,frame_sp)
        def stop(emu,address,size,_):
            if address==base+end:emu.emu_stop()
        hh=u.hook_add(UC_HOOK_CODE,stop)
        try:u.emu_start(base+start,base+end+1,count=15000)
        except Exception as exc:
            raise AssertionError((hex(start),hex(end),hex(u.reg_read(UC_X86_REG_RIP)-base),
                                  {r:hex(u.reg_read(v)) for r,v in regs.items()})) from exc
        finally:u.hook_del(hh)
        assert u.reg_read(UC_X86_REG_RIP)==base+end,('end',hex(start),hex(u.reg_read(UC_X86_REG_RIP)-base))
        assert u.reg_read(UC_X86_REG_RSP)==frame_sp,('stack',hex(start))

    def setup(enabled=1,targets=1,side=0):
        reset();hits.clear()
        u.mem_write(ledger,b'\0'*info['size'])
        u.mem_write(base+m['spell_mastery']['state_rva'],b'\0'*0x7000)
        for addr in m['mod_settings']['flag_rvas']:put(base+addr,'B',0)
        put(flag,'B',enabled)
        put(base+0x12cece8+1-side,'B',targets)
        owner=actors+2*0x248 if not side else enemies+7*0x248
        put(owner+0x51,'B',side)
        target=actors if side else enemies
        for t in range(targets):
            p=target+t*0x248
            put(p+0x4e,'B',t);put(p+0x3c,'H',1);put(p+0x58,'BB',0,0)
            put(p+0x51,'B',1-side);put(p+0x52,'B',8);put(p+0x2c,'I',10000)
            put(p+0x140,'4h',590,-40,610,0);put(p+0x240,'B',1)
        put(sprite,'3h',600*16,-20*16,0)
        return owner,target

    def collision(owner,slot,projectile,tick=40):
        fx=pool+slot*0x120
        put(fx,'Q',owner);put(fx+0x38,'H',tick);put(fx+0x78,'Q',desc)
        reg('rsi',fx);reg('rdi',sprite);reg('rbp',projectile)
        keep={r:u.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
        previous=bytes(u.mem_read(scope,24))
        run(0x94484,0x9449f)
        assert previous==bytes(u.mem_read(scope,24)),'scope leaked'
        assert keep=={r:u.reg_read(regs[r]) for r in keep},'nonvolatile register changed'

    try:
        # Same-frame impacts on the distant target. OFF reproduces the single
        # hit; ON commits four separate HP losses and keeps per-projectile delay.
        for side in (0,1):
            for enabled in (0,1):
                owner,target=setup(enabled,side=side)
                for i in range(4):collision(owner,0,i)
                assert len(hits)==(4 if enabled else 1),(enabled,side,hits)
                assert get(target+0x2c,'I')==10000-174*(4 if enabled else 1)
                for i in range(4):collision(owner,0,i,41)
                assert len(hits)==(4 if enabled else 1),'repeat every frame'
                if enabled:
                    for i in range(4):collision(owner,0,i,40+interval)
                    assert len(hits)==8,'native repeat interval lost'
        # Different casts and all ten mastery projectiles have independent rows.
        owner,target=setup()
        for slot in (0,1,15):
            for projectile in range(10):collision(owner,slot,projectile)
        assert len(hits)==30 and get(target+0x2c,'I')==10000-30*174
        # Actual scratch object from 8f6e0 also receives the frozen mastery tag.
        # A stale or mismatched owner must not inherit another mage's bonus.
        for matching in (True,False):
            owner,target=setup()
            tag=base+m['spell_mastery']['effects_rva']
            put(base+m['spell_mastery']['context_rva'],'Q',tag)
            put(tag,'QHHI',owner if matching else owner+0x248,73,500,25)
            put(base+m['mod_settings']['flag_rvas'][12],'B',1)
            u.mem_write(base+m['spell_mastery']['usage']['preferences']['live_rva'],b'\0'*224)
            for i in range(4):collision(owner,0,i)
            assert get(target+0x2c,'I')==10000-4*(217 if matching else 174)
        # Multiple target slots, genuine miss, native immunity and blocked-hit
        # cooldown. No synthetic hit is added for a projectile outside the box.
        owner,target=setup(targets=8)
        put(target+0x140,'4h',0,-40,20,0)
        put(target+0x248+0x58,'B',1)
        put(target+2*0x248+0x59,'B',1)
        for i in range(4):collision(owner,0,i)
        assert len(hits)==20 and all(p>=target+3*0x248 for _,p in hits)
        for i in range(4):
            assert get(ledger+i*16+2*2,'H')==72,'blocked-hit delay must remain 32'
            assert get(ledger+i*16,'H')==0,'miss must not consume a hit'
            assert get(ledger+i*16+2,'H')==0,'immune target must remain immune'
        # Reuse every effect slot through the real first-frame storage hook.
        for slot in range(16):
            u.mem_write(ledger,b'\x55'*0x1000)
            fx=pool+slot*0x120;put(fx+0x38,'H',0);reg('rsi',fx)
            run(0x94234,0x9423b)
            assert bytes(u.mem_read(ledger+slot*256,256))==b'\0'*256
            for other in range(16):
                if other!=slot:assert bytes(u.mem_read(ledger+other*256,256))==b'\x55'*256
        # Both native damage/guard response writes mirror their exact byte value
        # and retain registers; unrelated owners/descriptors cannot borrow scope.
        owner,target=setup()
        for site,end in ((0x8e525,0x8e52d),(0x8e6a7,0x8e6b2)):
            for delay in (0,1,16,32,255):
                for valid in (True,False):
                    put(scope,'QQQ',ledger,owner,100)
                    put(scratch+0x18,'Q',desc)
                    reg('rsi',desc+8+(0 if valid else 2));reg('rdi',owner)
                    reg('rcx',7);reg('rax',delay);reg('rbx',target);reg('r15',0)
                    put(ledger+14,'H',0)
                    before={r:u.reg_read(v) for r,v in regs.items()}
                    run(site,end)
                    assert before=={r:u.reg_read(v) for r,v in regs.items()}
                    assert get(owner+0x5a+7,'B')==delay
                    assert get(ledger+14,'H')==(100+delay if valid else 0)
        # Outside the Air Thrust call, the native shared gate still applies.
        owner,target=setup()
        put(scope,'Q',0);reg('rsi',scratch);reg('rax',owner);reg('rcx',0)
        put(owner+0x5a,'B',16)
        run(0x11630e,0x11652e)
    finally:
        u.hook_del(h)
        put(scope,'QQQ',0,0,0)
        for addr,value in saved_flags.items():put(addr,'B',value)
    return f'{cases} cases; native repeat interval {interval} ticks; independent 4/10-projectile HP commits, OFF baseline, 16 slots, 8 targets, both sides, misses, immunity, guard, reuse and ABI'
