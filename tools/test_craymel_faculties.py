"""Actual x64 faculty entry points, native heal/cost operations, two ASLR bases."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP,UC_X86_REG_RIP,UC_X86_REG_XMM0,UC_X86_REG_EFLAGS
from craymel_milestones import LEVELS, BASE_LEVELS, TIERS, faculty_id


def check_faculties(u,base,m,actors,sp,reset,put,get,reg,regs):
    f=m['craymel_faculties'];sy=m['symbols'];state=base+f['state_rva']
    choices=base+f['choices'];flag=base+f['flag_rva']
    live=actors+0xa000;stats=actors+0x8000;record=actors+0x9000
    caster=actors+2*0x248;target=actors;stop=base+m['code_rva']-16
    nonvolatile=('rbx','rbp','rsi','rdi','r12','r13','r14','r15')
    count=0;roll=99;item_deltas=None
    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8,('alignment',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rsp))
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def boundary(_,address,length,user):
        if address==base+0x283090:ret(roll)
        elif address in {base+a for a in (0x1b5ca0,0x1b5a30,0x7fe70,0x8b9d0)}:ret()
        elif address==base+0x91600 and item_deltas is not None:
            for i,(hp_gain,tp_gain) in enumerate(item_deltas):
                a=actors+i*0x248
                put(a+0x2c,'I',get(a+0x2c,'I')+hp_gain)
                put(a+0x34,'H',get(a+0x34,'H')+tp_gain)
            ret(1)
    h=u.hook_add(UC_HOOK_CODE,boundary)
    def setup(level=30,on=1):
        reset();u.mem_write(state,bytes(f['size']));u.mem_write(choices,bytes(224))
        u.mem_write(live,bytes(0x2000));put(base+0x12cea60,'Q',live)
        put(flag,'B',on);put(base+0x12cece8,'B',4);put(base+0x6449e0,'Q',actors+0x7000)
        put(base+0x865a08,'I',0);put(base+0x12d0fcc,'B',0)
        put(base+m['spell_mastery']['context_rva'],'Q',0)
        for spirit in range(10):put(live+0xbb8+spirit*8,'BB',1,level)
        for i in range(4):
            a=actors+i*0x248;s=stats+i*0x100
            put(a+0x4f,'B',i);put(a+0x51,'B',0);put(a+0x2c,'I',1000);put(a+0x34,'H',100)
            put(a+0x3c,'H',1);put(a+0xe8,'Q',s);put(s+0x18,'IH',2000,200)
        put(record,'QHHI',caster,70,1,0)
    def run(name,rcx=0,rdx=0,r8=0,r9=0,end=None,aligned=False):
        nonlocal count
        count+=1;reg('rcx',rcx);reg('rdx',rdx);reg('r8',r8);reg('r9',r9)
        rsp=sp-8 if aligned else sp;u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        saved={r:u.reg_read(regs[r]) for r in nonvolatile};reached=[]
        def halt(_,address,length,user):
            if address==(base+end if end else stop):reached.append(1);u.emu_stop()
        hh=u.hook_add(UC_HOOK_CODE,halt)
        try:
            u.emu_start(base+(sy[name] if isinstance(name,str) else name),stop+1,count=200000)
            assert reached,(name,'no return',hex(u.reg_read(UC_X86_REG_RIP)-base))
            assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if end else 8),(name,'stack')
            assert saved=={r:u.reg_read(regs[r]) for r in nonvolatile},(name,'nonvolatile')
            return u.reg_read(regs['rax'])
        finally:u.hook_del(hh)
    def disable(spirit,node,char=2):
        bit=char*256+faculty_id(spirit,node);p=choices+bit//8
        put(p,'B',get(p,'B')|1<<(bit%8))
    def slot(a):return run('craymel_actor_state',a)
    def hp(a):return get(a+0x2c,'I')
    try:
        assert all(levels[:len(old)]==old for old,levels in zip(BASE_LEVELS,LEVELS))
        assert faculty_id(3,8)==220  # Gnome overflow cannot alias Celsius ID 160.
        expected_tiers={
            'cost':(0,5,10,10,15,15,20), 'prepared':(0,0,0,5,10,15,15),
            'recovery':(0,5,10,10,20,25,30), 'dodge':(0,0,0,5,5,5,10),
            'power':(0,3,5,5,10,10,15), 'fervor':(0,0,0,5,10,15,15),
            'cast_defense':(0,10,15,15,20,20,25), 'light_ward':(0,0,0,1500,1200,900,600),
            'magic_defense':(0,5,10,10,15,15,20), 'stun_reduction':(0,0,0,15,15,30,30),
            'critical':(0,2,5,7,10,12,15), 'heal_share':(0,15,30,50,50,50,50),
            'hp_drain':(0,10,25,50,50,50,50), 'mana_share':(0,5,5,6,6,8,8),
            'haste':(0,5,5,5,5,10,15)
        }
        for char in (2,3):
            a=actors+char*0x248
            for tier,expected in expected_tiers.items():
                spirit,nodes=TIERS[tier]
                for level,want in zip((4,5,10,15,20,25,30),expected):
                    setup(level)
                    assert run('craymel_'+tier,a)==want,(char,tier,level)
                    put(flag,'B',0);assert run('craymel_'+tier,a)==0
                # Disabling a higher rank falls back to the next enabled one;
                # no tiers add together and the other mage's choices stay intact.
                setup()
                for i,value in reversed(nodes):
                    assert run('craymel_'+tier,a)==value,(tier,i)
                    disable(spirit,i,char)
                assert run('craymel_'+tier,a)==0
                assert run('craymel_'+tier,actors+(char^1)*0x248)==nodes[-1][1]
            # Pre-existing OFF choices keep their original byte positions.
            setup()
            for spirit,levels in enumerate(BASE_LEVELS):
                for i in range(len(levels)):disable(spirit,i,char)
            before=bytes(u.mem_read(choices,224))
            for spirit,levels in enumerate(LEVELS):
                for i in range(len(levels)):
                    assert run('craymel_faculty_enabled',a,spirit,i)==int(i>=len(BASE_LEVELS[spirit]))
                for invalid in range(len(levels),13):
                    assert run('craymel_faculty_enabled',a,spirit,invalid)==0
            assert bytes(u.mem_read(choices,224))==before
        # Actual native stun write: thresholds, independent opt-outs, and all
        # volatile GPR/SIMD/flags preserved at the overwritten instruction.
        for level,duration in ((14,240),(15,204),(24,204),(25,168),(30,168)):
            for on in (0,1):
                setup(level,on);reg('rbx',caster)
                put(record+32,'H',999)
                reg('rcx',record+32);reg('rdx',0);reg('r8',0);reg('r9',0)
                saved_gpr={r:u.reg_read(register) for r,register in regs.items()}
                vectors={UC_X86_REG_XMM0+i:0x123456789abcdef0123456789abcdef0+i for i in range(6)}
                for register,value in vectors.items():u.reg_write(register,value)
                u.reg_write(UC_X86_REG_EFLAGS,0x246)
                run('craymel_stun_duration',record+32,end=0x8e66d,aligned=True)
                assert get(record+32,'H')==(duration if on else 240)
                assert saved_gpr=={r:u.reg_read(register) for r,register in regs.items()}
                assert vectors=={register:u.reg_read(register) for register in vectors}
                assert u.reg_read(UC_X86_REG_EFLAGS)==0x246
        setup(30);disable(4,4);reg('rbx',caster)
        run('craymel_stun_duration',record+32,end=0x8e66d,aligned=True)
        assert get(record+32,'H')==204
        disable(4,7);reg('rbx',caster)
        run('craymel_stun_duration',record+32,end=0x8e66d,aligned=True)
        assert get(record+32,'H')==240
        # Early milestones reach their real events, including heal consumption,
        # first ward cooldown, and the actual paid-TP accumulator.
        setup(5);run('craymel_heal_target',caster,target,400,1)
        assert hp(target)==1400 and hp(actors+0x248)==1060
        setup(15);run('craymel_cast_completed',caster,70);run('craymel_cast_completed',caster,54)
        run('craymel_heal_target',caster,target,400,0);assert hp(target)==1420
        run('craymel_cast_completed',caster,54)
        run('craymel_heal_target',caster,target,400,0);assert hp(target)==1820
        setup(15);put(caster+0x52,'B',10);put(caster+0x8c,'H',100)
        assert run('craymel_interruption_ward',caster,0)==1
        cs=slot(caster);assert get(cs+96,'I')==300 and get(cs+100,'I')==1500
        put(base+0x12cea40,'I',300);assert run('craymel_interruption_ward',caster,0)==0
        put(base+0x12cea40,'I',1500);assert run('craymel_interruption_ward',caster,0)==1
        for level,amount in ((4,0),(5,5),(14,5),(15,6),(24,6),(25,8),(30,8)):
            setup(level);run('craymel_mana_spent',caster,49,100)
            assert get(target+0x34,'H')==100
            run('craymel_mana_spent',caster,51,100)
            assert get(target+0x34,'H')==100+2*amount
            assert get(caster+0x34,'H')==100
        for spirit,levels in enumerate(LEVELS):
            for node,threshold in enumerate(levels):
                for level in (0,threshold-1,threshold,30,31,255):
                    for on in (0,1):
                        setup(level,on)
                        assert run('craymel_faculty_enabled',caster,spirit,node)==int(on and threshold<=level<=30)
                        disable(spirit,node)
                        assert run('craymel_faculty_enabled',caster,spirit,node)==0
        for on in (0,1):
            for level,pct in ((4,0),(5,5),(9,5),(10,10),(20,15),(30,20)):
                for cost in (0,1,9,30,99):
                    setup(level,on)
                    assert run('craymel_discount_cost',caster,cost)==(cost*(100-pct*on)+99)//100
        setup();assert run('craymel_offensive_power',record,100,0)==115
        put(caster+0x2c,'I',999);assert run('craymel_offensive_power',record,100,0)==130
        put(record+12,'I',0x10000);assert run('craymel_offensive_power',record,100,0)==195
        assert run('craymel_offensive_power',record,100,2)==130
        put(flag,'B',0);assert run('craymel_offensive_power',record,100,0)==100
        # Execute the entire native debit function, including accessory order.
        for on in (0,1):
            for consume in (0,1):
                setup(on=on);put(base+0x12cea70,'Q',base+0x562a50)
                native=get(base+0x562a50+71*24,'B')
                charged=(native*80+99)//100 if on else native
                assert run(0x8fe50,caster,71,consume)==1
                assert get(caster+0x34,'H')==100-(charged if consume else 0)
        # A blocked hit never reaches the native damage/ailment calculation.
        setup();roll=0;put(sp+0x28,'Q',record+32)
        before=bytes(u.mem_read(caster,0x248))
        run('craymel_damage_admission',target,caster,record,record)
        assert get(record+32,'I')==0x40000000 and bytes(u.mem_read(caster,0x248))==before
        roll=99
        setup();put(caster+0x52,'B',10);put(caster+0x8c,'H',100)
        assert run('craymel_interruption_ward',caster,0)==1
        cs=slot(caster);assert get(cs+96,'I')==300 and get(cs+100,'I')==600
        disable(3,6);put(base+0x12cea40,'I',300)
        assert run('craymel_interruption_ward',caster,0)==0
        put(base+0x12cea40,'I',600);assert run('craymel_interruption_ward',caster,0)==1
        setup();run('craymel_cast_completed',caster,70);cs=slot(caster)
        assert get(cs+47,'B')==1
        run('craymel_cast_completed',caster,54);assert get(cs+88,'I')==15 and get(cs+47,'B')==0
        put(target+0x2c,'I',1950);run('craymel_heal_target',caster,target,600,1)
        ts=slot(target)
        assert hp(target)==2000 and get(ts+8,'I')==300
        assert hp(actors+0x248)==1345,'50% heal sharing'
        assert get(ts+16,'I')==172 and get(ts+20,'I')==5
        put(base+0x12cea40,'I',600)
        assert run('craymel_incoming_damage',target,500,0)==500,'expired shield'
        # Regeneration advances only with battle time, exactly five payments.
        setup();run('craymel_heal_target',caster,target,400,0);ts=slot(target)
        assert hp(target)==1400
        for frame in (59,60,119,120,180,240,300):
            put(base+0x12cea40,'I',frame);run('craymel_regeneration_tick')
            assert hp(target)==1400+20*min(frame//60,5)
        assert get(ts+20,'I')==0
        # Disabling a faculty mid-effect stops future healing.
        setup();run('craymel_heal_target',caster,target,400,0);disable(6,4)
        put(base+0x12cea40,'I',60);run('craymel_regeneration_tick');assert hp(target)==1400
        # Protection is charged once, checks pre-heal HP, and expires at 5s.
        setup();put(target+0x2c,'I',400);run('craymel_heal_target',caster,target,200,0)
        assert run('craymel_incoming_damage',target,101,0)==51
        put(base+0x12cea40,'I',300);assert run('craymel_incoming_damage',target,101,0)==101
        # One ailment per caster cooldown; rare flags remain untouched.
        setup();put(target+0x30,'I',0x80000001)
        run('craymel_heal_target',caster,target,1,0);assert get(target+0x30,'I')==0x80000000
        put(target+0x30,'I',0x80000400);run('craymel_heal_target',caster,target,1,0)
        assert get(target+0x30,'I')==0x80000400
        # Real native heal entry uses caster context; unrelated heals unchanged.
        setup();put(record+8,'H',54);put(base+m['spell_mastery']['context_rva'],'Q',record)
        run(0x8d5e0,target,30);assert hp(target)==1600
        assert hp(actors+0x248)==1300
        setup(on=0);run(0x8d5e0,target,30);assert hp(target)==1600 and hp(actors+0x248)==1000
        # Perfect dodge rejects both damage admission and native hit reaction.
        for level,chance in ((14,0),(15,5),(29,5),(30,10)):
            for roll_value in (0,4,5,9,10,99):
                setup(level);roll=roll_value
                assert run('craymel_evade_hit',caster)==int(roll_value<chance)
        setup();before=bytes(u.mem_read(target,0x248));run(0x8e320,0,0x40000000,record,caster)
        assert bytes(u.mem_read(target,0x248))==before
        # Fatal protection spends one charge, while healing during stasis is allowed.
        setup();disable(8,1);put(caster+0x2c,'I',100)
        assert run('craymel_incoming_damage',caster,1000,0)==99
        assert run('craymel_evade_hit',caster)==1
        put(base+0x12cea40,'I',120);assert run('craymel_incoming_damage',caster,1000,0)==1000
        # Stasis checks the action entry itself, and releases exactly at expiry.
        setup();cs=slot(caster);put(cs+48,'I',120)
        run(0xd51f0,caster)
        put(base+0x12cea40,'I',120);run(0xd51f0,caster,end=0xd51f5)
        # Clock insertion preserves all live volatile SIMD values.
        setup();run('craymel_heal_target',caster,target,400,0)
        put(base+0x12cea40,'I',59)
        vectors={UC_X86_REG_XMM0+i:0x123456789abcdef0123456789abcdef0+i for i in range(6)}
        for register,value in vectors.items():u.reg_write(register,value)
        run('craymel_battle_tick',end=0xd3297,aligned=True)
        assert hp(target)==1420 and get(base+0x12cea40,'I')==60
        assert vectors=={register:u.reg_read(register) for register in vectors}
        # Snapshot item gains before sharing: an all-party item cannot create
        # a feedback loop between both mages, and the global switch stops it.
        for on in (0,1):
            setup(on=on);item_deltas=((0,0),(0,0),(400,40),(400,40))
            assert run('craymel_item_completed',record)==1
            assert hp(target)==1000+200*on and get(target+0x34,'H')==100+20*on
            assert hp(caster)==1400+100*on and get(caster+0x34,'H')==140+10*on
        item_deltas=None
        # Native TP debit -> bounded sharing, never admission-only.
        setup();run('craymel_mana_spent',caster,49,100);assert get(target+0x34,'H')==100
        run('craymel_mana_spent',caster,1,51);assert get(target+0x34,'H')==108
        # Enemy and physical character origins never gain mage faculties.
        setup();assert run('craymel_discount_cost',target,20)==20
        put(caster+0x51,'B',1);assert run('craymel_discount_cost',caster,20)==20
    finally:u.hook_del(h)
    return count
