"""Native event/dispatcher lifecycle for the new shared mage spell roster."""
import struct
from custom_test_artes import MAGE_ROSTER

def check_extra_magic(u,base,m,actors,pool_area,setup,run,put,get,calls,mocks):
    info=m['standalone_teamups'];fx=base+0x12cfca0;tags=base+info['identity']['tags']
    from build_combat_patch import BACKUP,pefile
    original=pefile.PE(str(BACKUP));ob=original.OPTIONAL_HEADER.ImageBase
    # Initializers and frame callbacks are read from the original dispatch
    # tables, so a wrong inferred callback cannot give a false green result.
    for owner in (2,3):
        for aid,effect in ((140,57),(141,63),(142,67),(143,16),(144,24),(145,24)):
            a=setup(owner,aid)
            u.mem_write(pool_area,bytes(0x10000));put(base+0x12cecf0,'Q',pool_area)
            put(base+0x12cec20,'Q',pool_area+0xf000)
            put(fx,'Q',a);put(fx+8,'Q',actors+0x4000)
            put(fx+0x36,'B',effect);put(fx+0x3e,'H',effect);put(fx+0x30,'b',1)
            put(fx+0x3c,'H',effect)
            put(fx+0x33,'B',1);put(fx+0x3a,'H',1);put(fx+0x40,'H',effect)
            put(fx+0x20,'h',-1024);put(fx+0x22,'h',1024)
            put(a+0x8e,'H',effect);put(a+0x77,'B',1);put(a+0x23a,'B',7)
            put(tags,'Q',a);put(tags+8,'I',aid)
            # Actor selection may change while the asynchronous loader runs.
            put(a+0x6d,'B',70)
            put(base+m['spell_mastery']['current_roots_rva']+owner*8,'Q',fx)
            put(base+0x12d0ea0,'Q',fx)
            for table in (0x4e9420,0x4e9900,0x4e9b70):
                callback=struct.unpack('<Q',original.get_data(table+effect*8,8))[0]-ob
                put(base+table+effect*8,'Q',base+callback)
            mocks.update({0x11cb80,0x1a07d0,0x11e4d0,0x11ed60,0x279670,0x8f770,
                          0x283090,0x116580,0x116260,0x71490,0x71520,0x1b45e0,0x7fe70,0x7ffa0,0x80090,0x81420})
            preserved=bytes(u.mem_read(a,0x248))
            for tick in range(420):
                assert get(fx+0x38,'H')==tick,('native clock',owner,aid,tick)
                if aid in (141,144,145):
                    put(fx+0x32,'B',1);put(base+0x12ceb74,'B',0x30)
                try:run(0x1158a0)
                except Exception as ex:raise AssertionError((owner,aid,tick,bytes(u.mem_read(fx+0x30,0x18)).hex())) from ex
                if tick==0:
                    row=next(r for r in info['extra_magic']+info['spirit_magic'] if r['id']==aid)
                    assert get(fx+0x10,'Q')==base+row['script'],('private init lost',owner,aid)
                    assert get(fx+0x3e,'H')==0
                    if aid==142:
                        assert get(base+info['launch']+aid*8+2,'B')==8
                        assert get(base+row['impact']+9,'B')==8
                        assert get(fx+0x31,'B')==1
                        # Execute the real coordinate-origin helper.
                        run(0x115e30,fx)
                        assert get(base+0x12ceb82,'h')==1024
                    if aid==143:
                        assert get(base+row['impact']+17,'B')==10
                    if aid==141:
                        for offset in (0,22):
                            assert get(base+row['impact']+offset+11,'B')==6
                            assert get(base+row['impact']+offset+18,'H')==200
                if not get(fx,'Q'):break
                assert get(a+0xf0,'Q')==struct.unpack_from('<Q',preserved,0xf0)[0]
                assert get(a+0x4f,'B')==owner and get(a+0x6d,'B')==70
            else:raise AssertionError(('unreleased native spell',owner,aid))
            assert tick>=60,(aid,'premature release',tick)
            assert get(a+0x77,'B')==0 and get(a+0x23d,'B')==255,(owner,aid,'caster locked')
            damage=[c for c in calls if c[0] in ('impact','projectile','area')]
            assert damage,(owner,aid,'no damaging effect')
            if aid in (144,145):
                assert tick==64
                assert sum(c[0]=='projectile' for c in calls)==(5 if aid==144 else 3)
                p=pool_area+0x19c8
                assert get(p+0x14,'H')==3968 and get(p+0x42,'H')==0x6000
                assert get(p+0x2a,'h')==-320
                assert get(p+9,'B')==1 and get(p+0xe,'H')==0x20
                if aid==144:
                    assert get(p+0xa,'H')==0x10
                    assert get(p+0x1c,'H')==2 and get(p+0x1e,'H')==4
            print('native spell lifecycle',hex(base),owner,aid,'end',tick,'damage events',len(damage))
