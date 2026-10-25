"""Execute both prototype lifecycles, real mesh physics and interruption cleanup."""
def check_prototypes(u,base,m,actors,pool,setup,run,fragment,put,get,reg,regs,calls,mocks):
    fx=base+0x12cfca0;info=m['standalone_teamups'];state=base+info['state_rva']
    meshes=pool+0x19c8
    def arena():
        u.mem_write(pool,bytes(0x10000))
        put(base+0x12cecf0,'Q',pool);put(base+0x12cec20,'Q',pool+0xf000)
        put(base+0x8c9728,'i',512)
    def graphics():
        # GPU submission/projection/managed loader are mocked. Mesh selection,
        # UV routing, native movement and lifetime arithmetic run unmodified.
        mocks.update({0x1a07d0,0x11e6f0,0x121b50,m['symbols']['spell_label_texture_initialize']})
        put(base+0x8c9720,'i',160);put(base+0x8c9724,'i',120)
    row=next(r for r in info['custom_artes'] if r['id']==138)
    for facing in (-1,1):
        a=setup(1,138);arena();put(a+0x53,'b',facing);put(a+0x10,'h',1000)
        put(fx,'Q',a);put(fx+0x36,'B',124);put(a+0x77,'B',1)
        mocks.update({0x7fe70,0x116580});graphics()
        for tick in range(43):
            put(fx+0x38,'H',tick);run(0xcaf30,fx)
            if get(a+0x230,'Q'):run(0x708e0,a)
            put(a+0x23c,'B',1) # Deliberately never advance Palm Strike's frame.
            run(0x85810)
        assert not get(fx,'Q') and not get(a+0x230,'Q') and get(a+0x52,'B')==6
        hits=[c for c in calls if c[0]=='projectile'];assert len(hits)==3,hits
        assert all(c[1:]==(a,base+row['projectile_impact']) for c in hits)
        draws=[c for c in calls if c[0]=='managed_quad'];assert draws and all(c[1:]==(14,1024,4096) for c in draws),draws
        for i,born in enumerate((12,18,24)):
            p=meshes+i*74;age=43-born
            assert get(p,'h')==1000-192*facing-96*facing*age,(i,facing,age,get(p,'h'))
            assert get(p+0xc,'H')==48-age
            assert get(p+0x12,'H')==((age//2)%2)*192+(384 if facing<0 else 0)
            assert get(p+0x14,'H')==3840 and get(p+0x42,'H')==0x6000
            assert get(p+9,'B')==1 and get(p+0xe,'H')==0x20
            assert bytes(u.mem_read(p+0x22,3))==bytes((128,128,128))
        for _ in range(48):run(0x85810)
        assert not any(get(meshes+i*74+8,'B') for i in range(3))
    # Pool exhaustion cannot leave a damaging invisible fourth projectile.
    for occupied in (59,60):
        a=setup(1,138);arena()
        for i in range(occupied):put(base+0x12cee48+i*48+32,'B',5)
        old=bytes(u.mem_read(base+0x12cee48,occupied*48))
        run(info['farah_projectile'],a,base+row['projectile_impact'],3)
        assert bytes(u.mem_read(base+0x12cee48,occupied*48))==old
        assert bool(get(meshes+8,'B'))==(occupied==59)
    for aid,ptr,power,flag,element in ((138,base+row['impact'],80,0x10,0),(139,state+0x51a8,320,0x80,8)):
        assert get(ptr,'B')==flag and get(ptr+1,'B')==element and get(ptr+2,'B')==2
        # Native percentage calculation, including zero damage, not fixed MA HP.
        for amount in (0,100,333,1000):
            a=setup(1 if aid==138 else 3,aid)
            put(base+0x12cea68,'Q',actors+0xc100)
            reg('rbp',a);reg('r12',ptr);reg('rsi',amount)
            fragment(0x8ecbc,0x8ed32)
            assert u.reg_read(regs['rsi'])==amount*power//100
    finality=info['falling_finality']
    for facing,condition in __import__('itertools').product((-1,1),('complete','hit','ko','death','serial','reused','paused','loading')):
        a=setup(3,139);arena();put(base+0x12ceb80,'b',facing);put(fx,'Q',a);put(fx+8,'Q',actors+0x4000)
        put(fx+0x3e,'H',77);put(fx+0x36,'B',60);put(fx+0x40,'H',60)
        # Native effect positions are planar X/Z followed by the Y pair.
        # A nonzero Z must never be mistaken for the target's altitude.
        put(fx+0x22,'hh',1000,777);put(fx+0x2a,'h',-320)
        put(a+0x77,'B',1);put(a+0x23a,'B',7)
        put(a+0x8e,'H',60)
        original=bytes(u.mem_read(base+0x58ab00,0xc00))
        run(0xbd7a0,fx);assert get(fx+0x10,'Q')==base+finality['script']
        mocks.add(0x8f770);graphics()
        for tick in range(49):
            put(fx+0x38,'H',tick)
            if tick==10:
                if condition=='hit':put(a+0x52,'B',7)
                if condition=='ko':put(a+0x2c,'I',0)
                if condition=='death':put(a+0x52,'B',2)
                if condition=='serial':put(a+0x6e,'B',8)
                if condition=='reused':put(meshes+0x42,'H',0x5fe1)
                if condition=='paused':put(base+0x12ceb74,'B',1)
                if condition=='loading':put(fx+0x3a,'H',2)
            if tick==11 and condition in ('paused','loading'):
                assert get(fx,'Q')==a
                put(base+0x12ceb74,'B',0);put(fx+0x3a,'H',1)
            if condition=='reused' and tick==10:put(a+0x52,'B',7)
            run(0x114f50,fx);run(0xbd8b0,fx)
            if tick==8:
                # Re-entered callback at the same tick must not duplicate it.
                run(0xbd8b0,fx)
                assert get(meshes+8,'B')==3 and not get(meshes+74+8,'B')
                assert get(meshes+0x48,'H')==77,'blade must bind the loaded resource'
                assert get(meshes+0x2a,'h')==-128 and get(meshes+0x1c,'h')==-512
                assert get(meshes,'h')==2024 and get(meshes+2,'h')==-2368
            if not get(fx,'Q'):
                assert tick==(48 if condition in ('complete','paused','loading') else 10)
                if condition=='reused':assert get(meshes+8,'B')==3,'do not kill a particle reused by another slot'
                else:assert get(meshes+8,'B')==0,'live blade may not outlast the resource owner'
                break
            run(0x85810)
            if tick==23 and condition=='complete':
                assert get(meshes,'h')==1000 and get(meshes+2,'h')==-320
        else:raise AssertionError('Finality did not release')
        assert bytes(u.mem_read(base+0x58ab00,0xc00))==original,'mutated enemy MA data'
        impacts=[c for c in calls if c[0]=='impact']
        assert len(impacts)==int(condition in ('complete','paused','loading')),impacts
        assert get(a+0x77,'B')==0 and get(a+0x23d,'B')==255,(condition,get(a+0x77,'B'),get(a+0x23d,'B'))
        assert any(c[0]=='native_quad' for c in calls),'native dark sword not submitted'
    # Exhaust all four real mesh banks: neither arte may create invisible hits.
    extra=base+m['particle_capacity']['state_rva']
    for aid,owner in ((138,1),(139,3)):
        a=setup(owner,aid);arena()
        for bank in (pool,extra,extra+0x5600,extra+0xac00):
            for i in range(100):put(bank+0x19c8+i*74+8,'B',1)
        if aid==138:
            run(info['farah_projectile'],a,base+row['projectile_impact'],3)
            assert not get(base+0x12cee48+32,'B')
        else:
            put(fx,'Q',a);put(fx+0x36,'B',60);put(a+0x8e,'H',60)
            put(a+0x77,'B',1);put(a+0x23a,'B',7);run(0xbd7a0,fx)
            mocks.add(0x8f770)
            for tick in (0,8,24,48):
                put(fx+0x38,'H',tick);run(0xbd8b0,fx)
            assert not get(fx,'Q') and not get(a+0x77,'B')
            assert not any(c[0]=='impact' for c in calls)
        u.mem_write(extra,bytes(m['particle_capacity']['size']))
    # Real mesh stepping must keep the animated water lance inside its atlas
    # row, in either facing, and move visual and collision-owned mesh together.
    for owner in (2,3):
        for aid in (144,145):
            for facing in (-1,1):
                a=setup(owner,aid);arena();graphics()
                put(base+0x12ceb80,'b',facing)
                put(fx,'Q',a);put(fx+0x30,'b',facing)
                put(fx+0x20,'h',1000);put(fx+0x28,'h',640)
                row=next(r for r in info['spirit_magic'] if r['id']==aid)
                mocks.add(0x116580)
                run(info['spirit_magic_runtime']['projectile'],fx,aid,base+row['impact'])
                assert get(meshes+8,'B')==1
                for age in range(1,48):
                    run(0x85810)
                    assert get(meshes,'h')==1000-320*facing-160*facing*age
                    assert get(meshes+2,'h')==128
                    assert get(meshes+0xc,'H')==48-age
                    expected_u=((age//2)%4)*112 if aid==144 else (704 if facing<0 else 448)
                    expected_v=4032 if aid==144 and facing<0 else 3968
                    assert get(meshes+0x12,'H')==expected_u,(aid,facing,age,get(meshes+0x12,'H'))
                    assert get(meshes+0x14,'H')==expected_v
                run(0x85810);assert get(meshes+8,'B')==0
    # Exact owned Hyades texels survive the atlas packing (including alpha).
    from hyades_orb_asset import frames
    from PIL import Image
    from pathlib import Path
    sprites,source=frames()
    assert source=='9340b7357f534eadd5ca06f3b924b472cd6e6e94f9010f59508ede00194f9f4b'
    atlas=Image.open(Path(__file__).resolve().parents[1]/'build/combat-test/spell-native-labels.png')
    for i,sprite in enumerate(sprites):assert atlas.crop((i*192,3840,i*192+192,3968)).tobytes()==sprite.tobytes()
    from spirit_projectile_assets import frames as spirit_frames, RECTS
    sprites,_=spirit_frames()
    assert len(sprites)==len(RECTS)==10
    for sprite,(x,y,w,h) in zip(sprites,RECTS):
        assert atlas.crop((x,y,x+w,y+h)).tobytes()==sprite.tobytes()
