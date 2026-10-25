"""Execute native arte admission, payment and commit across successive artes."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

def check_fighter_chains(u,base,m,actors,sp,reset,put,get,reg,regs):
    data=base+m['data_rva'];info=m['mastery_menu']['fighter_chains']
    state=base+info['state_rva'];choices=base+m['mastery_menu']['choices']['live_rva']
    master=base+0x11ca420;stop=data-16;cases=0
    def setup(char=1,level=30,technical_return=False):
        reset();u.mem_write(state,bytes(64));u.mem_write(choices,bytes(224))
        u.mem_write(base+m['craymel_faculties']['fighter_expansion']['state_rva'],bytes(0x800))
        # Isolate sequencing from rebates (covered by the expansion suite).
        disable(0,160)
        if not technical_return:disable(0,162)
        put(base+0x12cea60,'Q',master)
        put(base+0x12cea78,'Q',base+0x551780);put(base+0x12cea70,'Q',base+0x562a50)
        put(base+0x6449e0,'Q',actors+0x9800)
        put(data+0x1a41,'B',1);put(data+0x1a4f,'B',1)
        for o in (0xc08,0xc10,0xc18,0xc20):put(master+o,'B',level)
        a=actors+char*0x248;put(a+0x52,'B',0);put(a+0x64,'B',0)
        put(a+0x34,'H',1000);put(a,'Q',actors+0x4000)
        return a
    def boundary(_,address,size,user):
        if address==stop:u.emu_stop();return
        if address-base in (0x712e0,0x114980,0x114dd0,0x1b5ca0,0x8d520):
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
            reg('rax',0);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,boundary)
    def run(entry):
        nonlocal cases
        cases+=1;put(sp,'Q',stop);u.reg_write(UC_X86_REG_RSP,sp)
        before={r:u.reg_read(regs[r]) for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}
        u.emu_start(base+(m['symbols'][entry] if isinstance(entry,str) else entry),stop,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==stop,(entry,hex(u.reg_read(UC_X86_REG_RIP)-base))
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        assert before=={r:u.reg_read(regs[r]) for r in before},entry
    def cast(a,aid,accept=True):
        old=get(a+0x6e,'B');tp=get(a+0x34,'H')
        reg('rcx',a);reg('rdx',aid);run(0x112d10)
        assert (get(a+0x6e,'B')!=old)==accept,(aid,accept,get(a+0x65,'B'),get(state+32+8,'B'))
        cost=get(base+0x562a50+aid*24,'B')
        assert get(a+0x34,'H')==tp-(cost if accept else 0),(aid,'cost')
    def disable(char,id):
        bit=char*256+id;p=choices+bit//8;put(p,'B',get(p,'B')|1<<(bit%8))
    try:
        # Punch-only, Kick-only and mixed chains. A seventh/eighth press cannot extend.
        for level,limit in ((14,1),(15,5),(29,5),(30,6)):
            for seq in ((25,27),(26,36),(25,26)):
                a=setup(level=level)
                for i in range(limit):cast(a,seq[i%2])
                for i in range(3):cast(a,seq[limit%2],False)
                assert get(state+32+8,'B')==limit
                # Recovery/new chain is tracked independently, without clearing preference bits.
                put(a+0x64,'B',0);put(a+0x65,'B',0);put(a+0x52,'B',0)
                cast(a,seq[0]);assert get(state+32+8,'B')==1
        for first,seq in ((142,(25,27)),(144,(26,36)),(146,(25,26))):
            a=setup();disable(1,first+1)
            for i in range(5):cast(a,seq[i%2])
            cast(a,seq[1],False)
            a=setup();disable(1,first);disable(1,first+1)
            cast(a,seq[0]);cast(a,seq[1],False)
        # Mixed requirements, global toggles and insufficient TP.
        a=setup();put(master+0xc20,'B',14);cast(a,25);cast(a,26,False)
        a=setup();put(data+0x1a41,'B',0);cast(a,25);cast(a,27,False)
        a=setup();cast(a,25);put(a+0x34,'H',0);cast(a,27,False)
        assert get(state+32+8,'B')==1
        # A rising arte can still only link to a dive above native minimum height.
        a=setup();cast(a,30);cast(a,31,False);cast(a,29,False)
        put(a+0x12,'h',-641);cast(a,29);cast(a,31,False)
        put(a+0x12,'h',0);cast(a,31);cast(a,25)
        # Same-family basics, mixed basics, and no basic after an arcane.
        for seq,pref in (((1,4),151),((2,3),152),((1,2),153)):
            for lv in (9,10,30):
                a=setup(0,lv);cast(a,seq[0]);cast(a,seq[1],lv>=10)
                cast(a,seq[0],False)
            a=setup(0);disable(0,pref);cast(a,seq[0]);cast(a,seq[1],False)
        # Arcane families: 19 Slash, 20 Thrust, 13 mixed. Exactly two arcanes.
        for seq in ((19,19),(20,20),(13,14),(19,20)):
            for lv in (29,30):
                a=setup(0,lv);cast(a,seq[0]);cast(a,seq[1],lv==30)
                cast(a,seq[0],False);cast(a,1,False)
        for aid,pref in ((19,148),(20,149)):
            a=setup(0);disable(0,pref);cast(a,aid);cast(a,aid,False)
        a=setup(0);put(master+0xc10,'B',29);cast(a,19);cast(a,19)
        a=setup(0);put(master+0xc10,'B',29);cast(a,19);cast(a,20,False)
        a=setup(0);cast(a,1);cast(a,4);cast(a,19);cast(a,19);cast(a,19,False)
        # Technical Return: one arcane -> basic transition, keeping both quotas.
        for lv in (24,25,30):
            a=setup(0,lv,True);cast(a,19);cast(a,1,lv>=25)
            if lv>=25:
                cast(a,19,lv==30)
                if lv==30:cast(a,4,False)
        a=setup(0,30,True);cast(a,19);cast(a,19);cast(a,1);cast(a,19,False)
        a=setup(0,30,True);cast(a,1);cast(a,4);cast(a,19);cast(a,1,False)
        a=setup(0,30,True);cast(a,19);put(a+0x34,'H',0);cast(a,1,False)
        assert get(state+13,'B')==0,'failed admission consumed Technical Return'
        put(a+0x34,'H',1000);cast(a,1);assert get(state+13,'B')==1
        # Healing ward covers precisely Farah's three heals, not attacks or dead actors.
        for lv in (29,30,31):
            for aid in range(38,43):
                a=setup(1,lv);put(a+0x52,'B',10);put(a+0x8c,'H',20);put(a+0x6d,'B',aid)
                reg('rcx',a);reg('rdx',1);run('craymel_interruption_ward')
                assert u.reg_read(regs['rax'])==int(lv==30 and 39<=aid<=41)
        for offset,fmt,value in ((0x4f,'B',0),(0x51,'B',1),(0x52,'B',8),(0x8c,'H',0),(0x3c,'H',2),(0x2c,'i',0)):
            a=setup();put(a+0x52,'B',10);put(a+0x8c,'H',20);put(a+0x6d,'B',39)
            put(a+offset,fmt,value);reg('rcx',a);run('energy_healing_ward');assert u.reg_read(regs['rax'])==0
        a=setup();put(a+0x52,'B',10);put(a+0x8c,'H',20);put(a+0x6d,'B',39)
        disable(1,150);reg('rcx',a);run('energy_healing_ward');assert u.reg_read(regs['rax'])==0
        return dict(cases=cases,finite_chains=True,native_tp=True,aerial_constraints=True,healing_ward=True)
    finally:u.hook_del(h)
