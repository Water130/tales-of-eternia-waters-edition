"""Execute catch-up EXP, successful-cast admission and preserved real counters."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP
from spell_catchup import ELIGIBLE


def check_spell_catchup(u,base,m,actors,sp,reset,put,get,reg,regs):
    sym=m['symbols'];usage=m['artesphere']['usage'];info=usage['catchup']
    raw=base+usage['live_rva'];extra=base+info['live_rva']
    prefs=base+usage['preferences']['live_rva'];data=base+m['data_rva']
    stop=data-24;cases=0
    address=lambda table,c,a:table+(c*128+a)*2
    def setup():
        reset();u.mem_write(raw,bytes(1792));u.mem_write(extra,bytes(1792))
        u.mem_write(prefs,bytes(224));put(data+0x1a0c,'B',1)
        put(data+0x1ac0,'I',0)
    def run(name,end=None):
        nonlocal cases
        cases+=1;rsp=sp-8 if end else sp
        u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        dest=base+end if end else stop
        u.emu_start(base+sym[name],dest,count=10000)
        assert u.reg_read(UC_X86_REG_RIP)==dest,name
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if end else 8),name
        return u.reg_read(regs['rax'])
    entries={base+sym[n] for n in ('spell_exp_read','spell_exp_next','spell_exp_award')}
    def abi(_,addr,size,user):
        if addr in entries:assert u.reg_read(UC_X86_REG_RSP)%16==8,hex(addr-base)
    h=u.hook_add(UC_HOOK_CODE,abi)
    try:
        for c in (2,3):
            for a in (a for a in range(39,114) if a!=42):
                for current,credit,peer,peer_credit in ((0,0,100,0),(10,20,29,0),
                        (10,20,30,0),(10,20,31,0),(10,20,32,0),(10,20,33,0),
                        (100,100,0,999),(497,0,9999,0),(498,0,9999,0),(499,0,9999,0),(500,0,9999,0),(997,0,9999,0),(999,0,9999,0),(9999,50,9999,0)):
                    setup()
                    put(address(raw,c,a),'H',current);put(address(extra,c,a),'H',credit)
                    put(address(raw,c^1,a),'H',peer);put(address(extra,c^1,a),'H',peer_credit)
                    cap=500
                    bonus=max(0,min(2,min(cap,peer+peer_credit)-(current+credit+1))) if a in ELIGIBLE else 0
                    expected=current+credit+1+bonus
                    before=bytes(u.mem_read(raw,1792))+bytes(u.mem_read(extra,1792))
                    reg('rcx',c);reg('rdx',a)
                    assert run('spell_exp_next')==expected,(c,a,current,credit,peer,peer_credit)
                    assert before==bytes(u.mem_read(raw,1792))+bytes(u.mem_read(extra,1792))
                    # Run the real post-admission hook and preserve its native inputs.
                    reg('rax',0);reg('rbx',actors)
                    put(actors+0x4f,'B',c);put(actors+0x51,'B',0);put(actors+0x6d,'B',a)
                    saved={r:u.reg_read(v) for r,v in regs.items()}
                    run('arte_usage_cast_completed',0xd5555)
                    assert saved=={r:u.reg_read(v) for r,v in regs.items()}
                    assert get(address(raw,c,a),'H')==min(9999,current+1),(c,a)
                    assert get(address(extra,c,a),'H')==credit+bonus,(c,a)
                    assert get(address(raw,c^1,a),'H')==peer
                    reg('rcx',c);reg('rdx',a)
                    assert run('spell_exp_read')==min(9999,current+1)+credit+bonus
        # No credit for an interrupted/refused spell, enemy, unrelated character,
        # disabled group or disabled faculty. Native counts still behave as before.
        for result,enemy,c,enabled,disabled in ((1,0,2,1,0),(0,1,2,1,0),
                (0,0,1,1,0),(0,0,2,0,0),(0,0,2,1,1)):
            setup();put(address(raw,3,73),'H',500)
            put(data+0x1a0c,'B',enabled)
            if disabled:put(prefs+(2*256+73)//8,'B',1<<(73%8))
            reg('rax',result);reg('rbx',actors)
            put(actors+0x4f,'B',c);put(actors+0x51,'B',enemy);put(actors+0x6d,'B',73)
            run('arte_usage_cast_completed',0xd5555)
            assert get(address(extra,c,73),'H')==0
            assert get(address(raw,c,73),'H')==int(not result and not enemy)
        # Actual use requirements cannot be met by catch-up credit.
        setup();put(address(raw,3,73),'H',500)
        for _ in range(20):
            reg('rcx',2);reg('rdx',73);run('arte_usage_increment')
        assert get(address(raw,2,73),'H')==20
        assert get(address(extra,2,73),'H')==40
        # Earned credit survives disabling/re-enabling and switching the leader.
        put(data+0x1a0c,'B',0);reg('rcx',2);reg('rdx',73);run('arte_usage_increment')
        assert get(address(extra,2,73),'H')==40
        put(data+0x1a0c,'B',1);put(address(raw,3,73),'H',20)
        reg('rcx',3);reg('rdx',73);run('arte_usage_increment')
        assert get(address(extra,3,73),'H')==2
        return cases
    finally:u.hook_del(h)
