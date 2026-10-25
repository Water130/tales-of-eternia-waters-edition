"""Execute approved faculties at both module bases, including adverse inputs."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_expansion(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['craymel_faculties']['fighter_expansion']; data=base+m['data_rva']
    state=base+info['state_rva']; prefs=base+m['mastery_menu']['choices']['live_rva']
    master=actors+0xa000; stats=actors+0x8000; inputs=actors+0x9000; enemy=actors+0x4000
    stop=data-16; cases=0; calls=[]
    def setup(char=0,level=30):
        reset();u.mem_write(state,bytes(info['size']));u.mem_write(prefs,bytes(224));calls.clear()
        put(data+0x1a41,'B',1);put(data+0x1a4f,'B',1);put(base+0x12cea60,'Q',master)
        for off in (0xc08,0xc10,0xc18,0xc20):put(master+off,'B',level)
        put(base+0x12cea40,'I',100);put(stats+0x18,'I',4000)
        a=actors+char*0x248
        put(a+0xf0,'Q',inputs);put(a+0x57,'B',2);put(a+0x52,'B',0)
        put(a,'Q',enemy);put(enemy+0x10,'h',2000)
        put(enemy+0xe8,'Q',stats+0x200)
        put(base+0x12cea78,'Q',base+0x551780)
        return a
    def disabled(char,pref):put(prefs+char*32+pref//8,'B',1<<(pref%8))
    def boundary(_,address,size,user):
        if address==stop:u.emu_stop();return
        if address in (base+0x7fe70,base+0x112720):
            calls.append(('motion' if address==base+0x7fe70 else 'attack',u.reg_read(regs['rdx'])))
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
            u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
        if address==base+0x8fbf0:
            a=u.reg_read(regs['rcx']);n=u.reg_read(regs['rdx'])
            calls.append(('tp',a,n));put(a+0x34,'H',get(a+0x34,'H')+n)
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
            u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    handle=u.hook_add(UC_HOOK_CODE,boundary)
    def run(name,*args):
        nonlocal cases
        for key,val in zip(('rcx','rdx','r8','r9'),args):reg(key,val)
        keep={k:u.reg_read(regs[k]) for k in ('rbx','rsi','rdi','rbp','r12','r13','r14','r15')}
        u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop);cases+=1
        try:u.emu_start(base+m['symbols'][name],stop,count=100000)
        except Exception as exc:raise AssertionError((name,hex(u.reg_read(UC_X86_REG_RIP)-base))) from exc
        assert u.reg_read(UC_X86_REG_RIP)==stop,name
        assert u.reg_read(UC_X86_REG_RSP)==sp+8,name
        assert keep=={k:u.reg_read(regs[k]) for k in keep},name
        return u.reg_read(regs['rax'])
    try:
        for key,(pref,char,family,level) in info['gates'].items():
            for lv in (level-1,level,30,31):
                a=setup(char,lv);assert run('fighter_expansion_enabled',a,pref)==int(level<=lv<=30),(key,lv)
            a=setup(char);disabled(char,pref);assert run('fighter_expansion_enabled',a,pref)==0
            for off,fmt,val in ((0x51,'B',1),(0x3c,'H',0),(0x2c,'i',0),(0x4f,'B',3)):
                a=setup(char);put(a+off,fmt,val);assert not run('fighter_expansion_enabled',a,pref)
        # Strict <25%, emergency cooldown; martial bonus supersedes emergency.
        for hp in (0,999,1000,1001,4000):
            a=setup(1);put(a+0x2c,'i',hp)
            assert run('fighter_expansion_cast',a,39,112)==(56 if hp==999 else 112),hp
        a=setup(1);put(a+0x2c,'i',500);s=run('fighter_expansion_slot',a)
        put(s+24,'B',1);assert run('fighter_expansion_cast',a,39,112)==28
        assert get(s+24,'B')==1,'query consumed preparation'
        put(a+0x52,'B',10);put(a+0x6d,'B',39);put(a+0x6e,'B',5)
        run('fighter_expansion_action',a);assert get(s+24,'B')==0
        assert get(s+28,'I')==0,'martial should not also spend emergency'
        run('fighter_expansion_action',a);assert get(s+28,'I')==0
        put(a+0x6e,'B',6);run('fighter_expansion_action',a)
        assert get(s+28,'I')==1000
        assert run('fighter_expansion_cast',a,39,112)==112
        put(base+0x12cea40,'I',1000);assert run('fighter_expansion_cast',a,39,112)==56
        # Whole arcane ward; other actions and a disabled switch do not protect.
        for aid,kind,expected in ((13,8,1),(21,8,1),(12,8,0),(22,8,0),(13,6,0)):
            a=setup();put(a+0x52,'B',kind);put(a+0x65,'B',2);put(a+0x6d,'B',aid)
            assert run('fighter_expansion_ward',a,0)==expected
        a=setup();put(a+0x52,'B',8);put(a+0x65,'B',2);put(a+0x6d,'B',13)
        disabled(0,163);assert not run('fighter_expansion_ward',a,0)
        # Actual heal only, one nonstacking discount, no effect on spells.
        a=setup(1);s=run('fighter_expansion_slot',a)
        run('fighter_expansion_healed',a,actors,0);assert not get(s+32,'B')
        run('fighter_expansion_healed',a,actors,50);assert get(s+32,'B')==1
        assert run('fighter_expansion_cost',a,25,19)==16
        assert run('fighter_expansion_cost',a,39,19)==19
        run('fighter_expansion_healed',a,actors,50);assert run('fighter_expansion_cost',a,25,19)==16
        run('fighter_expansion_commit',a,25);assert not get(s+32,'B')
        # Prepared punch only one light interruption, tied to the admitted arte.
        a=setup(1);put(a+0x52,'B',2);put(inputs,'H',0x80)
        run('fighter_expansion_action',a);put(base+0x12cea40,'I',120);run('fighter_expansion_action',a)
        s=run('fighter_expansion_slot',a);assert get(s+16,'I')==300
        run('fighter_expansion_commit',a,25)
        put(a+0x52,'B',8);put(a+0x6e,'B',1)
        assert run('fighter_expansion_ward',a,0)==1
        assert run('fighter_expansion_ward',a,0)==0
        # Guard timing, one reward per attacker/action, clamped TP.
        a=setup();put(a+0x52,'B',2);put(inputs,'H',0x80)
        run('fighter_expansion_action',a);run('fighter_expansion_block',a,enemy)
        assert get(a+0x34,'H')==13
        run('fighter_expansion_block',a,enemy);assert get(a+0x34,'H')==13
        put(enemy+0x6e,'B',1);put(base+0x12cea40,'I',109)
        run('fighter_expansion_block',a,enemy);assert get(a+0x34,'H')==13
        # Step-in: only toward target, release required, Guard+Up untouched.
        for direction,expected in ((8,5),(2,2),(9,2),(0,2)):
            a=setup();put(a+0x52,'B',2);put(inputs,'H',0x80);put(inputs+0x10,'B',direction)
            run('fighter_expansion_action',a);assert get(a+0x52,'B')==expected,(direction,get(a+0x52,'B'))
            if expected==5:
                assert get(a+0x18,'h')==48
                put(a+0x52,'B',2);put(a+0x18,'h',0);put(a+0x44,'H',0)
                run('fighter_expansion_action',a);assert get(a+0x52,'B')==2
        # Revival protection and Rempart multiply; exclude magic and self aura.
        farah=setup(1);victim=actors+2*0x248
        run('fighter_expansion_revived',farah,victim)
        assert run('fighter_expansion_defense',victim,100,1)==75
        put(actors+0x52,'B',2)
        assert run('fighter_expansion_defense',victim,100,0)==68
        assert run('fighter_expansion_defense',actors,100,0)==100
        put(base+0x12cea40,'I',400);assert run('fighter_expansion_defense',victim,100,1)==100
        # Temporary immunity only the condition that Detoxify actually removed.
        a=setup(1);run('fighter_expansion_purified',a,actors,1)
        assert run('fighter_expansion_immunity',actors,3)==1
        assert run('fighter_expansion_immunity',actors,6)==0
        put(base+0x12cea40,'I',700);assert run('fighter_expansion_immunity',actors,3)==0
        # Serial wraps at 255 in the native actor; preparations follow it.
        a=setup(1);s=run('fighter_expansion_slot',a);put(s+16,'I',300)
        put(a+0x6e,'B',255);run('fighter_expansion_commit',a,25)
        put(a+0x52,'B',8);put(a+0x6e,'B',0)
        assert run('fighter_expansion_ward',a,0)==1
        # Step latch survives native slide/recovery frames; released input resets it.
        a=setup();put(a+0x52,'B',2);put(inputs,'H',0x80);put(inputs+0x10,'B',8)
        run('fighter_expansion_action',a);run('fighter_expansion_action',a)
        s=run('fighter_expansion_slot',a);assert get(s+12,'B')==1
        put(inputs+0x10,'B',0);run('fighter_expansion_action',a);assert not get(s+12,'B')
        # A completed full-HP heal permits recovery cancellation, no TP rebate.
        a=setup(1);s=run('fighter_expansion_slot',a)
        run('fighter_expansion_healed',a,actors,0)
        assert get(s+36,'I')==280 and not get(s+32,'B')
        put(a+0x52,'B',6);put(a+0x44,'H',30);put(inputs+4,'B',0x20)
        run('fighter_expansion_action',a);assert get(a+0x44,'H')==0
        assert ('attack',0) in calls
        # Three successful normal actions, not three hits from one action.
        a=setup();s=run('fighter_expansion_slot',a)
        put(a+0x52,'B',8);put(a+0x64,'B',15)
        for serial in (1,1,2,3):
            put(a+0x6e,'B',serial);run('fighter_expansion_hit',a,enemy,100,0)
        assert get(s+108,'I')==3
        run('fighter_expansion_commit',a,1);put(a+0x6e,'B',4);put(a+0x64,'B',16)
        put(enemy+0x52,'B',2)
        assert run('fighter_expansion_guard_break',a,enemy)==1
        assert not run('fighter_expansion_guard_break',a,enemy)
        # Ordinary guarded hits and zero damage never award a preparation.
        for damage,flags in ((0,0),(100,1)):
            a=setup();s=run('fighter_expansion_slot',a)
            put(a+0x52,'B',8);put(a+0x64,'B',15)
            run('fighter_expansion_hit',a,enemy,damage,flags);assert not get(s+108,'I')
        # Three different successful Punch artes refund once; repeated target hits don't.
        a=setup(1);s=run('fighter_expansion_slot',a)
        for aid in (25,27,31):
            run('fighter_expansion_paid',a,aid,20);run('fighter_expansion_commit',a,aid)
            put(a+0x52,'B',8);put(a+0x64,'B',16);put(a+0x6d,'B',aid)
            put(a+0x6e,'B',get(a+0x6e,'B')+1)
            run('fighter_expansion_hit',a,enemy,100,0)
            run('fighter_expansion_hit',a,enemy,100,0)
        assert get(a+0x34,'H')==16 and get(s+104,'B')==1
        # Alternating successful families, not merely admitted attacks, prepare F8.
        a=setup(1);s=run('fighter_expansion_slot',a)
        for aid in (25,26,27):
            run('fighter_expansion_commit',a,aid);put(a+0x52,'B',8);put(a+0x64,'B',16)
            put(a+0x6d,'B',aid);put(a+0x6e,'B',get(a+0x6e,'B')+1)
            run('fighter_expansion_hit',a,enemy,100,0)
        assert get(s+24,'B')==1
        # Final palm only, once a chain; heavy targets and launch trajectories untouched.
        a=setup(1);put(a+0x52,'B',8);put(a+0x6d,'B',31);put(a+0xe1,'B',16)
        put(a+0x23c,'B',2);put(enemy+0x44,'h',20)
        run('fighter_expansion_reaction',a,enemy);assert get(enemy+0x44,'h')==26
        run('fighter_expansion_reaction',a,enemy);assert get(enemy+0x44,'h')==26
        a=setup();put(a+0x52,'B',8);put(a+0x6d,'B',2);put(enemy+0x18,'h',120)
        run('fighter_expansion_reaction',a,enemy);assert get(enemy+0x18,'h')==60
        put(enemy+0x1a,'h',-20);run('fighter_expansion_reaction',a,enemy)
        assert get(enemy+0x18,'h')==60
        # Six additional frames with the original minimum aerial height.
        a=setup(1);put(a+0x52,'B',8);put(a+0x65,'B',2);put(a+0x88,'H',10)
        put(a+0x66,'B',4);put(a+0x12,'h',-641)
        for frame,want in ((9,0),(14,1),(19,1),(20,0)):
            put(a+0x238,'H',frame);assert run('fighter_expansion_window',a)==want
        put(a+0x12,'h',-640);put(a+0x238,'H',15);assert not run('fighter_expansion_window',a)
        # Sonic Blade changes dissipation only, no speed, power or target edits.
        a=setup();particle=enemy+0x1000;put(a+0x6d,'B',1)
        u.mem_write(particle,bytes(0x50));put(particle+0x3a,'h',512)
        put(particle+0x3e,'h',-10);put(particle+0x40,'h',-10);put(particle+0xc,'h',80)
        put(particle+0x1c,'h',128);run('fighter_expansion_sonic',a,particle)
        assert get(particle+0x3e,'h')==-8 and get(particle+0x40,'h')==-8
        assert get(particle+0xc,'h')==100 and get(particle+0x1c,'h')==128
        # Reinitializing a character's actor clears all transient bonuses.
        a=setup(1);s=run('fighter_expansion_slot',a);put(s+24,'B',1)
        other=actors+0x1800;put(other+0x4f,'B',1)
        assert run('fighter_expansion_slot',other)==s and not get(s+24,'B')
        return {'cases':cases,'gates':len(info['gates']),'native_abi':True}
    finally:u.hook_del(handle)
