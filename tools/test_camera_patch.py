"""Camera integration checks, including the game's real projection routine."""
def check_camera(uc, BASE, DATA, ACTORS, ENEMIES, STATS, IMPACT, SP,
                 reset, put, get, reg, run, REGS, constants):
    UC_HOOK_CODE,UC_X86_REG_RSP,UC_X86_REG_EFLAGS=constants
    count=0
    # Synthetic wide supported arena isolates framing maths from stage limits.
    fixture=DATA+0x800+127*16
    fixture_original=bytes(uc.mem_read(fixture,16))
    put(fixture,'8h',-10000,10000,-320,256,49,256,512,0)
    def execute():
        nonlocal count
        saved={r:uc.reg_read(v) for r,v in REGS.items() if r!='rcx'}
        flags=uc.reg_read(UC_X86_REG_EFLAGS)
        run('adaptive_battle_camera',[0x10d51c])
        assert saved=={r:uc.reg_read(REGS[r]) for r in saved}, 'camera register corruption'
        assert uc.reg_read(UC_X86_REG_EFLAGS)==flags, 'camera flags changed'
        assert uc.reg_read(REGS['rcx'])==get(BASE+0x12cea98,'Q'), 'native read not replayed'
        assert bytes(uc.mem_read(BASE+0x12cea98,6))==bytes(uc.mem_read(BASE+0x12ceab8,6))
        count+=1
        return -get(BASE+0x12cea98,'h'),get(BASE+0x12cea9c,'h')
    def actor_setup(player,target):
        reset();put(ACTORS+0x57,'B',2);put(ACTORS,'Q',ENEMIES)
        put(BASE+0x12cea90,'hhh',64,0,0)
        put(BASE+0x12d0eb2,'H',127)
        put(ACTORS+0x10,'h',player);put(ENEMIES+0x10,'h',target)
        put(BASE+0x12ceb78,'h',512)
        put(BASE+0x12cea98,'hhhh',-100,32,512,0)
    def native_project(x,center,z,far=0,pitch=False):
        # Actual original x64 perspective path, not a duplicate of the hook.
        uc.mem_write(BASE+0x8c92d0,b'\0'*32)
        for off in (0,8,16):put(BASE+0x8c92d0+off,'h',4096)
        if pitch:put(BASE+0x8c92d0,'9h',4096,0,0,0,4076,-401,0,401,4076)
        put(BASE+0x8c92e4,'iii',-center,32,z)
        put(BASE+0x8c96f0,'i',512);put(BASE+0x8c9718,'i',160);put(BASE+0x8c92c4,'i',120)
        put(IMPACT,'hhh',x,0,far)
        reg('rcx',IMPACT);reg('rdx',IMPACT+0x10);reg('r9',IMPACT+0x20)
        put(SP,'Q',BASE+0x19f9e6)
        uc.emu_start(BASE+0x19f890,BASE+0x19f9e6,count=500)
        assert uc.reg_read(UC_X86_REG_RSP)==SP
        return get(IMPACT+0x10,'h')
    # Ordinary arena extremes, both directions, old 80-unit failure and close pairs.
    positions=[-2560,-1536,-1,0,448,1600,3200,5600,7676,8192]
    for p in positions:
        for t in positions:
            actor_setup(p,t);c,z=execute()
            assert c==((p>>4)+(t>>4))//2
            assert 512<=z<32768
            for pos in (p>>4,t>>4):
                for edge in (pos-64,pos+64):
                    assert 32<=native_project(edge,c,z)<=288,(p,t,c,z,edge)
    # Live-observed ordinary spell pitch must never disable ground coverage.
    for pitch in [56,64,68,80,96]:
        actor_setup(-2560,8192);put(BASE+0x12cea90,'h',pitch)
        execute()
        assert get(BASE+0x12cea90,'h')==64 and get(DATA+0x20,'B')==1
    for effect_id in list(range(1,26))+[61,62,66]:
        for pitch in [0,64,96,384,512]:
            actor_setup(-2560,8192)
            effect=BASE+0x12cfca0
            put(effect,'Q',ACTORS);put(effect+0x33,'B',1);put(effect+0x36,'B',effect_id)
            put(BASE+0x12cea90,'h',pitch);put(BASE+0x12ceab0,'h',384)
            execute()
            assert get(BASE+0x12cea90,'h')==get(BASE+0x12ceab0,'h')==64
            assert get(DATA+0x20,'B')==1
    # Selection menu temporarily follows enemy+5; manual actor is still slot 0.
    actor_setup(0,7680);put(BASE+0x12ceb8e,'B',6)
    assert execute()[0]==240
    # Index is authoritative over the previous target pointer while cycling.
    actor_setup(0,1600);put(ACTORS+0x63,'B',1)
    put(ENEMIES+0x248+0x3c,'H',1);put(ENEMIES+0x248+0x2c,'i',1000)
    put(ENEMIES+0x248+0x10,'h',7680)
    assert execute()[0]==240
    # Controlled character changed to slot 2; tracked slot 0 is now AI.
    actor_setup(0,6400);put(ACTORS+0x57,'B',0)
    put(ACTORS+2*0x248+0x57,'B',2);put(ACTORS+2*0x248+0x10,'h',3200)
    assert execute()[0]==300
    # A selected controlled actor on another slot takes precedence.
    actor_setup(0,6400);put(BASE+0x12ceb8d,'B',3)
    put(ACTORS+2*0x248+0x57,'B',1);put(ACTORS+2*0x248+0x10,'h',3200)
    assert execute()[0]==300
    # No arbitrary target pointer dereference, invalid/dead index falls back safely.
    for ptr,selected,enemy_state,enemy_hp,expected in [
        (0xdeadbeef,255,1,1000,100),(ENEMIES+1,255,1,1000,100),
        (ENEMIES,255,1,1000,200),(ENEMIES,0,2,1000,100),
        (ENEMIES,0,1,0,100)]:
        actor_setup(1600,4800);put(ACTORS,'Q',ptr);put(ACTORS+0x63,'B',selected)
        put(ENEMIES+0x3c,'H',enemy_state);put(ENEMIES+0x2c,'i',enemy_hp)
        assert execute()[0]==expected
    # Target changes use bounded, damped motion, including zoom OUT. A newly
    # selected distant target may enter the frame during the transition.
    actor_setup(-2560,-1536);previous=execute()
    for target in [8192,-1536,8192]:
        put(ENEMIES+0x10,'h',target)
        path=[]
        for i in range(90):
            put(BASE+0x12cea98,'hhh',900,-200,128)
            put(BASE+0x12ceab8,'hhh',900,-200,128)
            c,z=execute();path.append((c,z))
            assert abs(c-previous[0])<=17,(i,c,previous)
            assert abs(z-previous[1])<=65,(i,z,previous)
            assert get(BASE+0x12cea9a,'h')==32
            previous=(c,z)
        desired=(-160+(target>>4))//2
        assert abs(path[-1][0]-desired)<=1
        for pos in (-160,target>>4):
            for edge in (pos-64,pos+64):assert 31<=native_project(edge,c,z)<=289
        for axis in [0,1]:
            vals=[x[axis] for x in path]
            assert vals==sorted(vals) or vals==sorted(vals,reverse=True), ('camera oscillation',axis)
    # Tiny alternating movements must not create abrupt one-axis zoom kicks.
    actor_setup(0,1600);previous=execute()
    for t in [1599,1600,1601,1600]*20:
        put(ENEMIES+0x10,'h',t);current=execute()
        assert abs(current[0]-previous[0])<=1 and abs(current[1]-previous[1])<=2
        previous=current
    # Default zoom preference is respected; invalid values cannot overflow.
    for default,expected in [(512,512),(768,768),(-1,512),(32767,512)]:
        actor_setup(0,0);put(BASE+0x12ceb78,'h',default);assert execute()[1]==expected
    # Battle exit/new battle: preserve native cinematic state and reset smoothing.
    actor_setup(0,8192);execute();put(BASE+0x12d0ef7,'B',5)
    put(BASE+0x12cea98,'hhhh',17,48,512,0);put(BASE+0x12ceab8,'hhhh',17,48,512,0)
    execute();assert get(BASE+0x12cea98,'h')==17 and get(DATA+0x20,'B')==0
    put(BASE+0x12d0ef7,'B',6);put(ACTORS+0x10,'h',0);put(ENEMIES+0x10,'h',0)
    assert execute()==(0,512)
    # Malformed tables, dead controller: native camera is preserved, state disabled.
    for addr,fmt,value in [(BASE+0x12cecd8,'Q',0),(BASE+0x12cece8,'B',0),
                           (BASE+0x12cece8,'B',255),(ACTORS+0x3c,'H',2)]:
        actor_setup(0,8192);put(addr,fmt,value)
        put(BASE+0x12ceab8,'hhhh',-100,32,512,0)
        assert execute()==(100,512) and get(DATA+0x20,'B')==0
    # Audited arena borders, actual perspective and pitch, both left/right.
    import json
    from pathlib import Path
    rows=json.loads((Path(__file__).resolve().parents[1]/'audit/build-25190541/camera_floor_geometry.json').read_text())['stages']
    for row in rows:
        if not row['compatible']:continue
        left,right=row['drawn_bounds'][0];far=row['bounds'][2][1]
        for p,t in [(-160,-96),(352,512),(-160,512),(512,-160),(0,0)]:
            p=max(left+128,min(right-128,p));t=max(left+128,min(right-128,t))
            actor_setup(p*16,t*16);put(BASE+0x12d0eb2,'H',row['stage'])
            put(BASE+0x12ceb78,'h',2048)
            c,z=execute()
            assert native_project(left,c,z,far,True)<0,(row['stage'],c,z,'left visible')
            assert native_project(right,c,z,far,True)>320,(row['stage'],c,z,'right visible')
            if row['function']=='0xda330':
                anchor=native_project(-384,c,z,576,True)
                assert anchor<0 and anchor+512>320,(row['stage'],c,z,'far forest gap',anchor)
            assert 0<native_project(p,c,z)<320 and 0<native_project(t,c,z)<320,(row['stage'],p,t,c,z)
    # A rapid outward zoom may not uncover a side while the center catches up.
    for p,t in [(-160,-96),(352,512)]:
        actor_setup(p*16,t*16);put(BASE+0x12d0eb2,'H',7)
        previous=execute();put(BASE+0x12ceb78,'h',2048)
        for frame in range(140):
            c,z=execute()
            assert abs(c-previous[0])<=17 and abs(z-previous[1])<=65,(frame,c,z,previous)
            assert native_project(-384,c,z,256,True)<0
            assert native_project(640,c,z,256,True)>320
            anchor=native_project(-384,c,z,576,True)
            assert anchor<0 and anchor+512>320,(frame,c,z,'far forest transition gap',anchor)
            previous=(c,z)
        # The deeper left backdrop shifts the widest valid view rightwards.
        assert abs(c-178)<=1
    # Every summon and every pool slot retain native camera XYZ and native goal.
    for effect_id in range(26,36):
        for slot in [0,7,15]:
            actor_setup(0,4800);execute()
            effect=BASE+0x12cfca0+slot*0x120
            put(effect,'Q',ACTORS);put(effect+0x33,'B',1);put(effect+0x36,'B',effect_id)
            put(BASE+0x12cea98,'hhh',-200,48,600)
            put(BASE+0x12ceab8,'hhh',-300,12,900)
            run('adaptive_battle_camera',[0x10d51c]);count+=1
            assert get(BASE+0x12cea98,'h')==-200 and get(BASE+0x12cea9a,'h')==48
            assert get(BASE+0x12ceab8,'h')==-300 and get(BASE+0x12ceabc,'h')==900
            assert get(DATA+0x20,'B')==2
            put(effect+0x33,'B',0)
            c,z=execute();assert abs(c-200)<=4 and abs(z-600)<=16
            assert 44<=get(BASE+0x12cea9a,'h')<=48
    # All unsupported layouts, including out-of-range IDs, retain native
    # rotation, position and native target even when an ordinary spell runs.
    for stage in [r['stage'] for r in rows if not r['compatible']]+[128,65535]:
        actor_setup(0,8192);put(BASE+0x12d0eb2,'H',stage)
        put(BASE+0x12cea90,'hhh',80,0,0)
        put(BASE+0x12cea98,'hhh',-200,48,600)
        put(BASE+0x12ceab8,'hhh',-300,12,900)
        effect=BASE+0x12cfca0
        put(effect,'Q',ACTORS);put(effect+0x33,'B',1);put(effect+0x36,'B',66)
        before=bytes(uc.mem_read(BASE+0x12cea90,0x30))
        run('adaptive_battle_camera',[0x10d51c]);count+=1
        assert bytes(uc.mem_read(BASE+0x12cea90,0x30))==before,stage
    uc.mem_write(fixture,fixture_original)
    return count
