"""Native smoke follows actual meteor positions and retains its dark palette."""

def check_fear_alignment(u,base,m,actors,pool,setup,run,put,get,mocks):
    info=m['standalone_teamups'];cfg=info['fear_alignment']
    root=base+0x12cfca0;meshes=pool+0x19c8
    for owner in (2,3):
        a=setup(owner,137)
        u.mem_write(pool,bytes(0x10000));put(base+0x12cecf0,'Q',pool)
        put(base+0x12cec20,'Q',pool+0xf000)
        mocks.add(0x283090)
        fx=root+3*0x120
        put(fx,'Q',a);put(fx+0x36,'B',19);put(fx+0x3e,'H',77)
        put(base+info['identity']['tags']+3*16,'Q',a)
        put(base+info['identity']['tags']+3*16+8,'I',137)
        run(0x9d590,fx);put(fx+0x38,'H',0);run(0x9d630,fx)
        q=base+cfg['queue']+3*128
        assert not any(u.mem_read(q,128))
        assert not get(meshes+8,'B'),'smoke appeared before the first meteor'
        # Real frame captures the native meteor, then emits its original smoke.
        put(fx+0x38,'H',36);run(0x9d630,fx)
        assert get(meshes+8,'B')==7 and get(meshes+74+8,'B')==3
        assert get(q,'Q')==meshes and get(q+8,'H')==36 and get(q+10,'H')==1
        assert bytes(u.mem_read(meshes,6))==bytes(u.mem_read(meshes+74,6))
        assert get(meshes+74+0xe,'H')==0x5c,'smoke lost its subtractive blend'
        assert get(meshes+74+0x10,'H')==0x7d00,'smoke inherited the meteor palette'
        assert get(meshes+74+0xc,'H')==12
        # Follow a moving meteor, rather than a guessed ground coordinate.
        put(meshes,'h',get(meshes,'h')-512);put(meshes+2,'h',get(meshes+2,'h')+512)
        put(fx+0x38,'H',40);run(0x9d630,fx)
        assert get(meshes+148+8,'B')==3
        assert bytes(u.mem_read(meshes,6))==bytes(u.mem_read(meshes+148,6))
        assert bytes(u.mem_read(meshes+0x2a,4))==bytes(u.mem_read(meshes+148+0x2a,4))
        assert not get(meshes+222+8,'B')
        put(fx+0x38,'H',41);run(0x9d630,fx)
        assert not get(meshes+222+8,'B'),'unbounded smoke allocation'
        put(fx+0x38,'H',56);run(0x9d630,fx)
        assert not get(q+10,'H') and not get(meshes+222+8,'B')
        # Other effect slots and recycled slots remain independent.
        untouched=bytes(u.mem_read(base+cfg['queue'],128))
        put(fx+0x38,'H',0);run(0x9d630,fx)
        assert not any(u.mem_read(q,128))
        assert bytes(u.mem_read(base+cfg['queue'],128))==untouched
        put(fx+0x38,'H',144);run(0x9d630,fx)
        assert not get(meshes+222+8,'B'),'late meteor would outlive its resource'
        assert not any(u.mem_read(q,128))
