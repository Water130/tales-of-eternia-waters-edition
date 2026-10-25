"""Exercise actual admission, scripts, callbacks and projectile allocation."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from farah_regulus_artes import ARTES, NAME_SITES, DESCRIPTIONS

def check_farah_artes(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['standalone_teamups'];data=base+m['data_rva'];master=base+0x11ca420
    a=actors+0x248;fx=base+0x12cfca0;particle=actors+0x7000
    prefs=base+m['mastery_menu']['choices']['live_rva'];stop=data-16
    symbols=m['symbols'];calls=[];mocks=set();cases=0;draws=[]
    def trace(_,addr,size,user):
        rva=addr-base
        if rva not in mocks:return
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8,('ABI',hex(rva),hex(rsp))
        value=0
        if rva==0x114980:
            calls.append(('launch',u.reg_read(regs['rdx'])))
        elif rva==0x131c0:
            draws.append(tuple(get(rsp+o,'I') for o in (0x48,0x50,0x58,0x60)))
        elif rva==0x114dd0:
            calls.append(('native_announcement',))
        elif rva==0x2506e0:
            calls.append(('announcement',u.reg_read(regs['rcx'])))
        elif rva==0x7fe70:
            actor=u.reg_read(regs['rcx']);motion=u.reg_read(regs['rdx'])
            calls.append(('motion',motion))
            put(actor+0x23a,'B',motion);put(actor+0x23c,'B',0);put(actor+0x238,'H',0)
        elif rva==0x8b7e0:
            ptr=u.reg_read(regs['rcx']);assert ptr==base+0x5932fa
            u.mem_write(particle,bytes(u.mem_read(ptr,74)));value=particle
            calls.append(('particle',))
        elif rva==0x115ee0:
            calls.append(('release',));put(fx,'Q',0)
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,trace)
    def run(rva,*args):
        nonlocal cases
        for key,v in zip(('rcx','rdx','r8','r9'),args):reg(key,v)
        u.reg_write(UC_X86_REG_RSP,sp);put(sp,'Q',stop)
        keep={k:u.reg_read(regs[k]) for k in ('rbx','rsi','rdi','rbp','r12','r13','r14','r15')}
        try:u.emu_start(base+rva,stop,count=100000)
        except Exception as ex:raise AssertionError(('at',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rva))) from ex
        assert u.reg_read(UC_X86_REG_RIP)==stop,(hex(rva),'did not finish')
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        assert keep=={k:u.reg_read(regs[k]) for k in keep},('nonvolatile',hex(rva))
        cases+=1;return u.reg_read(regs['rax'])
    def fragment(start,end):
        nonlocal cases
        # These sites are in an existing function body with aligned RSP.
        u.reg_write(UC_X86_REG_RSP,sp-8)
        u.ctl_remove_cache(base+end-16,base+end+16)
        try:u.emu_start(base+start,base+end,count=100000)
        except Exception as ex:raise AssertionError(('fragment at',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(start))) from ex
        assert u.reg_read(UC_X86_REG_RIP)==base+end,('continuation',hex(start))
        assert u.reg_read(UC_X86_REG_RSP)==sp-8,('fragment stack',hex(start))
        cases+=1
    def string(ptr):
        return bytes(u.mem_read(ptr,512)).split(b'\0')[0].decode('utf8')
    def setup(aid,level=30):
        reset();calls.clear();mocks.clear()
        u.mem_write(master,bytes(0x1000));u.mem_write(prefs,bytes(224))
        u.mem_write(base+m['craymel_faculties']['fighter_expansion']['state_rva'],bytes(0x800))
        put(data+0x1a41,'B',1);put(data+0x1a42,'B',0);put(data+0x1a63,'B',0)
        put(base+0x12cea60,'Q',master);put(base+0x6449e0,'Q',actors+0xc200)
        put(base+0x12cea70,'Q',base+info['metadata']);put(base+0x12cea78,'Q',base+info['launch'])
        put(master+0xc18,'B',level);put(master+0xc20,'B',level)
        put(a+0x6d,'B',aid);put(a+0x6e,'B',7);put(a+0x8e,'H',124)
        put(a+0x34,'H',200);put(a+0x64,'B',0);put(a+0x65,'B',0);put(a+0x52,'B',0)
        put(a+0xf0,'Q',actors+0x9000);put(a,'Q',actors+0x4000)
        put(a+0x53,'b',1);put(a+0x10,'h',1000)
        put(a+0xe8,'Q',actors+0x8000);put(actors+0x802f,'B',1)
        run(info['initialize'])
    try:
        for aid,physical,message,tp,tree,level,pref,names in ARTES:
            row=next(r for r in info['farah_artes'] if r['id']==aid)
            for lv in (0,level-1,level,30,31):
                for char in (0,1,2):
                    setup(aid,lv)
                    before=bytes(u.mem_read(master,0x1000))
                    assert run(info['unlocked'],char,aid,master)==0
                    assert bytes(u.mem_read(master,0x1000))==before
            for condition in ('ok','off','preference','locked','wrong_owner','low_tp','full_pool','airborne'):
                setup(aid,level-1 if condition=='locked' else level)
                if condition=='off':put(data+0x1a41,'B',0)
                if condition=='preference':put(prefs+32+pref//8,'B',1<<(pref%8))
                if condition=='wrong_owner':put(a+0x4f,'B',0)
                if condition=='low_tp':put(a+0x34,'H',tp-1)
                if condition=='full_pool':
                    for i in range(16):put(fx+i*0x120,'Q',a)
                if condition=='airborne':put(a+0x12,'h',-100)
                old=get(a+0x34,'H');before=bytes(u.mem_read(master,0x1000))
                mocks.update({0x712e0,0x8d520,0x114980,0x114dd0,0x1b5ca0,0x2506e0})
                run(0x112d10,a,aid);mocks.clear()
                assert not calls,(aid,condition,calls)
                assert get(a+0x34,'H')==old,(aid,condition,'TP')
                assert bytes(u.mem_read(master,0x1000))==before
            # Suspended prototypes stay absent from compact lists and bindings,
            # even when their former mastery requirements are met.
            setup(aid,level)
            u.mem_write(master+0xd0+0x7a,bytes((25,114,0,39,122))+bytes(27))
            native_list=bytes(u.mem_read(master+0xd0+0x7a,32))
            run(m['fringe']['refresh'],master)
            rows=bytes(u.mem_read(base+m['fringe']['state_rva']+0xd0,128))
            assert aid not in rows and rows.rstrip(b'\0').count(0)==0
            assert rows[:2]==bytes((25,39)) and not any(i in rows for i in range(114,126))
            assert bytes(u.mem_read(master+0xd0+0x7a,32))==native_list
            assert run(symbols['artesphere_learned'],1,aid)==0
            put(prefs+32+pref//8,'B',1<<(pref%8))
            assert run(symbols['artesphere_learned'],1,aid)==0
            setup(aid)
            usage=base+info['usage_rva'];u.mem_write(usage,bytes(1792))
            put(usage+8,'H',0xa55a)
            run(symbols['arte_usage_increment'],1,aid)
            assert get(usage+(128+aid-122)*2,'H')==1
            assert get(usage+8,'H')==0xa55a,'counter touched Auto choices'
            # All native list, detail and shortcut names, in both languages.
            from build_combat_patch import CS, BACKUP, pefile
            original=pefile.PE(str(BACKUP))
            for lang in (1,3):
                setup(aid);put(base+0x11c9ce8,'B',lang)
                for site,(index,scale,dest,end) in NAME_SITES.items():
                    reg(index,aid*scale);fragment(site,end)
                    assert string(u.reg_read(regs[dest]))==names[lang==1],(aid,lang,hex(site))
                    # Existing entries still read the native-equivalent metadata.
                    ins=next(CS.disasm(original.get_data(site,15),site))
                    memop=next(o for o in ins.operands if o.type==3).mem
                    reg(ins.reg_name(memop.base),base)
                    reg(ins.reg_name(memop.index),physical*(24//memop.scale))
                    fragment(site,site+ins.size)
                    destreg=ins.reg_name(ins.operands[0].reg)
                    destreg={'ecx':'rcx','eax':'rax'}.get(destreg,destreg)
                    assert u.reg_read(regs[destreg])==get(base+info['metadata']+physical*24+4,'I')
                reg('rdi',base+info['launch']+aid*8);reg('rdx',0)
                calls.clear();mocks.update({0x114dd0,0x2506e0});fragment(0x112c53,0x112c58);mocks.clear()
                assert calls==[('announcement',base+row['names'][lang==1])]
                assert string(get(base+0x12cea88,'Q'))==names[lang==1]
                assert get(base+0x12ceb90,'B')==60 and get(base+0x12ceb91,'B')==0
                reg('rdi',base+info['launch']+25*8);calls.clear()
                mocks.update({0x114dd0,0x2506e0});fragment(0x112c53,0x112c58);mocks.clear()
                assert calls==[('native_announcement',)]
                reg('rbp',aid);reg('rdi',base);reg('rsi',0);reg('r9',0xffffffffffffffff);reg('r10',0)
                mocks.update({0xd500,0xd620});fragment(0x227421,0x227822);mocks.clear()
                assert string(get(base+0x11cce00,'Q'))==DESCRIPTIONS[aid][lang==1]
            setup(aid)
            icons=[]
            for icon_id in (physical,aid):
                draws.clear();put(sp+0x28,'B',255);mocks.update({0x6c550,0x131c0})
                run(0x42570,icon_id,248,60);mocks.clear();icons.append(list(draws))
            assert icons[0]==icons[1] and icons[1] and any(icons[1][0]),(aid,'icon',icons)
            for current_tp in (tp-1,tp,133):
                put(master+0xd0+0x3e,'H',current_tp)
                for disabled in (0,1):
                    put(base+info['auto_disabled_rva'],'H',disabled<<(aid-126))
                    put(sp-8+0x80,'Q',0xd0)
                    reg('rdi',aid);reg('r14',255);reg('r12',255);reg('r13',60);reg('r15',40)
                    mocks.update({0x6c550,0x131c0});fragment(0x225eac,0x225fca);mocks.clear()
                    expected=0xff808080 if disabled else (0xff6060e0 if current_tp<tp else 0xfffffdfa)
                    assert u.reg_read(regs['rbx'])==expected,(aid,'color',current_tp,disabled)
            # Run real native interpreter and 116090 with only renderer,
            # motion-frame data and release mocked. All motion IDs are Farah's.
            setup(aid);put(fx,'Q',a);put(fx+0x36,'B',124)
            mocks.update({0x7fe70,0x8b7e0,0x115ee0})
            for tick in range(180):
                put(fx+0x38,'H',tick)
                run(0xcaf30,fx)
                script=get(a+0x230,'Q')
                if not get(fx,'Q'):break
                assert base+row['script']<=script<base+row['script']+len(bytes.fromhex(row['script_hex']))
                run(0x708e0,a)
                if get(a+0x230,'Q'):
                    put(a+0x23c,'B',get(a+0x23c,'B')+1)
            else:raise AssertionError((aid,'script failed to terminate'))
            motions=[x[1] for x in calls if x[0]=='motion']
            assert motions=={130:[25],131:[29,25],132:[22,23],133:[25,26,29,25]}[aid],(aid,motions)
            assert sum(x[0]=='particle' for x in calls)>=1,(aid,calls)
            assert not get(a+0x230,'Q')
            if aid in (130,132):
                assert get(base+0x12cee48+8,'Q')==a
                assert get(base+0x12cee48+0x18,'Q')==base+row['projectile_impact']
                assert get(base+row['projectile_impact']+9,'B')==(3 if aid==132 else 0)
                assert get(particle+0xc,'H')==48
                # Preserve the native sphere until its final eight ticks,
                # then fade each channel instead of cutting the image off.
                assert get(particle+0x25,'B')==40
                assert bytes(u.mem_read(particle+0x26,3))==bytes((224,224,224))
                if aid==132:assert bytes(u.mem_read(particle+0x22,3))==bytes((128,72,24))
            else:
                assert get(particle+0xc,'H')==12
                assert bytes(u.mem_read(particle+0x22,3))==bytes((128,128,128))
            # The old native enemy texture was not loaded in player battles.
            # Every adaptation now binds the independent managed sprite atlas.
            assert get(particle+0x42,'H')==0x6000
            assert get(particle+0x44,'HH')==1024 and get(particle+0x46,'H')==4096
            assert get(particle+0x14,'H')==3840 and get(particle+0x48,'H')==0
            # Interrupted, KO, ended, replaced and timed-out effects release.
            for condition in ('hit','ko','ended','serial','timeout'):
                setup(aid);put(fx,'Q',a);put(fx+0x36,'B',124)
                mocks.update({0x7fe70,0x8b7e0,0x115ee0})
                run(0xcaf30,fx);put(fx+0x38,'H',1)
                if condition=='hit':put(a+0x52,'B',7)
                if condition=='ko':put(a+0x2c,'I',0)
                if condition=='ended':put(a+0x230,'Q',0)
                if condition=='serial':put(a+0x6e,'B',8)
                if condition=='timeout':put(fx+0x38,'H',360)
                run(0xcaf30,fx);assert not get(fx,'Q'),(aid,condition)
            # No accidental out-of-range family writes to the 256-byte ledger.
            setup(aid);run(symbols['fighter_expansion_commit'],a,aid)
            record=base+m['craymel_faculties']['fighter_expansion']['state_rva']+256
            assert get(record+76,'I')==1<<(aid-116)
            # Execute native stat selection and percentage-power calculation.
            # Increasing Punch increases damage; Kick does not substitute for it.
            for ptr in (base+row['impact'],base+row['projectile_impact']+8):
                assert get(ptr,'B')==0x10 and get(ptr+2,'B')==2
                for punch,kick,defense in ((100,900,20),(400,900,20),(400,100,80)):
                    setup(aid);victim=actors+0x4000;target_stats=actors+0x8200
                    put(a+0xb8,'B',1);put(actors+0x801e,'h',punch);put(actors+0x8020,'h',kick)
                    put(victim+0xe8,'Q',target_stats);put(target_stats+0x22,'h',defense)
                    reg('rbp',a);reg('r12',ptr);reg('rdx',victim)
                    fragment(0x8e96b,0x8e9bd)
                    assert u.reg_read(regs['r15'])==punch and u.reg_read(regs['rbx'])==punch-defense//2
                for amount in (0,100,333,1000):
                    setup(aid);config=actors+0xc100;put(base+0x12cea68,'Q',config)
                    reg('rbp',a);reg('r12',ptr);reg('rsi',amount)
                    fragment(0x8ecbc,0x8ed32)
                    assert u.reg_read(regs['rsi'])==amount*get(ptr+10,'H')//100
        for full in (False,True):
            for facing in (-1,1):
                setup(130);put(a+0x53,'b',facing);mocks.add(0x8b7e0)
                if full:
                    for i in range(60):put(base+0x12cee48+i*48+32,'B',5)
                before=len(calls)
                run(info['farah_projectile'],a,base+info['farah_artes'][0]['projectile_impact'],0)
                assert len(calls)-before==int(not full)
                if not full:assert get(particle+0x2a,'h')==-192*facing
        # Motion 25 may hold frame 1 indefinitely. Real particle allocation
        # and real native release must still leave a projectile and free Farah.
        pool_area=0x67000000;u.mem_map(pool_area,0x10000)
        setup(130);put(fx,'Q',a);put(fx+0x36,'B',124)
        put(base+0x12cecf0,'Q',pool_area);put(base+0x12cec20,'Q',pool_area+0xf000)
        put(a+0x77,'B',1);mocks.add(0x7fe70)
        for tick in range(31):
            put(fx+0x38,'H',tick);run(0xcaf30,fx)
            if get(a+0x230,'Q'):run(0x708e0,a)
            put(a+0x23c,'B',1)
        assert get(fx,'Q')==0 and get(a+0x230,'Q')==0
        assert get(a+0x77,'B')==0 and get(a+0x52,'B')==6
        assert get(a+0x18,'H')==0
        live=pool_area+0x19c8
        assert get(live+8,'B') and get(live+0xc,'H')==48
        assert get(live+0x25,'B')==40
        assert bytes(u.mem_read(live+0x26,3))==bytes((224,224,224))
        assert get(base+0x12cee48,'Q')==live
        # Cosmetic bursts do not consume a damage slot, even at capacity.
        for aid in (131,133):
            setup(aid);u.mem_write(pool_area,bytes(0x10000))
            put(base+0x12cecf0,'Q',pool_area);put(base+0x12cec20,'Q',pool_area+0xf000)
            for i in range(60):put(base+0x12cee48+i*48+32,'B',5)
            before=bytes(u.mem_read(base+0x12cee48,60*48))
            run(info['farah_projectile'],a,0,2)
            assert get(live+8,'B') and get(live+0xc,'H')==12
            assert bytes(u.mem_read(base+0x12cee48,60*48))==before
        u.mem_unmap(pool_area,0x10000)
    finally:u.hook_del(h)
    return cases
