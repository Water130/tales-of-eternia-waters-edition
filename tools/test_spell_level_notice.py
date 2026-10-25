"""Victory notices: true crossings, separate casters, locale and native ABI."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from spell_growth import OFFENSIVE, POWER, CAST, AREA, PROJECTILE_CAPS, Track


def check_spell_notices(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['spell_level_notices'];sym=m['symbols'];data=base+m['data_rva']
    usage=base+m['artesphere']['usage']['live_rva']
    snapshot=base+info['state_rva'];queue=base+info['queue_rva'];counts=base+info['counts_rva']
    stop=data-16;cases=0;texts=[];effects=[];native_nodes=[];real_effect=False
    active=base+info['active_rva']
    def setup():
        reset();u.mem_write(usage,bytes(1792));put(data+0x1a0c,'B',1)
        put(base+0x644a30,'Q',0)
        put(base+0x644a10,'Q',actors+0xc000);put(base+0x644a18,'Q',actors+0xd000)
        put(base+0x644a70,'Q',0);put(base+0x12cea68,'Q',actors+0xe000)
        put(base+0x573c3e,'B',0);put(base+0x11c9ce8,'B',3)
        for char in (2,3):
            put(actors+char*0x248+0x7a,'h',80+100*(char-2))
            put(actors+char*0x248+0x82,'h',60)
        put(base+0x12ced08,'Q',actors+0xa000);put(base+0x12ced10,'Q',actors+0xb800)
        put(base+0x12ceb74,'B',0)
        for char in (2,3):put(actors+char*0x248+0x10,'h',1000*char)
        texts.clear();effects.clear();native_nodes.clear()
    def text_hook(_,address,size,user):
        if address==base+0x117640:
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
            effects.append((u.reg_read(regs['rcx']),u.reg_read(regs['rdx'])))
            if real_effect:return
            # The native effect protects the victory screen for 96 frames.
            put(base+0x12cea54,'H',96)
            u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
            return
        if real_effect and address in [base+r for r in (0xc7210,0x8b7e0,0x8b6a0,0x8b540,0x283090,0x1b5ca0)]:
            rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
            if address in [base+r for r in (0x8b7e0,0x8b6a0,0x8b540)]:
                ptr=actors+0xe000+len(native_nodes)*0x100
                native_nodes.append(ptr);u.mem_write(ptr,bytes(0x100));reg('rax',ptr)
            elif address==base+0x283090:reg('rax',13)
            u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
            return
        if address!=base+0xb480:return
        rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
        ptr=u.reg_read(regs['rcx']);raw=bytearray()
        for i in range(120):
            b=bytes(u.mem_read(ptr+i,1))
            if b==b'\0':break
            raw.extend(b)
        else:raise AssertionError('unterminated notice')
        texts.append(raw.decode('utf-8'))
        dest=get(rsp,'Q')
        for r in ('rax','rcx','rdx','r8','r9','r10','r11'):reg(r,0xdead)
        for i in range(6):u.reg_write(UC_X86_REG_XMM0+i,0xdead)
        u.reg_write(UC_X86_REG_RIP,dest);u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,text_hook)
    def run(name,end=None):
        nonlocal cases
        cases+=1;rsp=sp-8 if end else sp
        u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        dest=base+end if end else stop
        u.emu_start(base+sym[name],dest,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==dest,(name,hex(u.reg_read(UC_X86_REG_RIP)))
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if end else 8)
    def begin():
        u.reg_write(UC_X86_REG_XMM0,0)
        run('craymel_battle_reset',0x11c6f6)
    def uses(char,aid,n):put(usage+(char*128+aid)*2,'H',n)
    def dispatch(char,frame=88):
        reg('rcx',actors+char*0x248);reg('rdx',frame);run('spell_notice_dispatch')
    def level(aid,n):
        shape=Track(PROJECTILE_CAPS.get(aid,50),500)
        score=POWER.value(n)*400+CAST.value(n)*2000+shape.value(n)*10000//shape.cap
        if aid==76:score=(score+AREA.value(n)*200)*5//6
        return 1+score*29//50000
    def ranks(aid,n):
        return POWER.value(n)+CAST.value(n)+Track(PROJECTILE_CAPS.get(aid,50),500).value(n)+(AREA.value(n) if aid==76 else 0)
    try:
        for aid in OFFENSIVE:
            shape=Track(PROJECTILE_CAPS.get(aid,50),500)
            thresholds={t.threshold(i) for t in ((POWER,CAST,shape,AREA) if aid==76 else (POWER,CAST,shape)) for i in range(1,t.cap+1)}
            samples={0,19,20,26,27,33,34,499,500,998,999,1000,9999}
            samples.update(v+d for v in thresholds for d in (-1,0))
            for n in sorted(samples):
                setup();uses(2,aid,n);begin();uses(2,aid,n+1)
                run('spell_notice_prepare')
                expected=int(ranks(aid,n+1)>ranks(aid,n))
                assert get(counts,'B')==expected and get(counts+1,'B')==0,(aid,n)
                if expected:assert get(queue,'B')==aid|(128 if level(aid,n+1)==level(aid,n) else 0)
                before=bytes(u.mem_read(queue,0x110));run('spell_notice_prepare')
                assert bytes(u.mem_read(queue,0x110))==before,'duplicate victory settlement'
        for language in (3,1):
            # Regression: a passive can grow while the total stays at level 1.
            # Meredy's Lightning crosses power/area ranks at 20 uses.
            setup();uses(3,86,19);begin();uses(3,86,27)
            put(base+0x11c9ce8,'B',language);run('spell_notice_prepare')
            assert level(86,19)==level(86,27)==1
            assert get(counts,'B')==0 and get(counts+1,'B')==1
            assert get(queue+128,'B')==86|128
            dispatch(3)
            reg('rcx',88);run('spell_notice_draw')
            assert not texts # the name is now part of the native mesh
            assert effects==[(actors+3*0x248,1)]
            setup();uses(2,71,33);uses(2,73,33);uses(3,71,99);begin()
            uses(2,71,500);uses(2,73,500);uses(3,71,500)
            put(base+0x11c9ce8,'B',language)
            reg('rcx',87);run('spell_notice_draw');assert not texts
            reg('rcx',88);run('spell_notice_draw');assert not texts,'No award on escape/result alone'
            put(sp-8+0x60,'I',2);run('spell_notice_award_hook',0x119e30)
            for frame,expected_ids in ((88,[71,71]),(89,[71,71]),(143,[71,71]),(144,[]),(152,[73]),(208,[]),(216,[])):
                dispatch(2,frame);dispatch(3,frame)
                texts.clear();reg('rcx',frame);run('spell_notice_draw')
                assert not texts,(frame,texts)
            assert effects==[(actors+2*0x248,1),(actors+3*0x248,1),(actors+2*0x248,1)]
            # The actual native JMP callsite restores every volatile/SSE input.
            texts.clear();put(sp-8+0x58,'I',152);put(sp-8+0x5c,'I',123)
            saved={r:u.reg_read(v) for r,v in regs.items()}
            xmm=[u.reg_read(UC_X86_REG_XMM0+i) for i in range(6)]
            run('spell_notice_victory_hook',0x119e81)
            saved['r13']=123
            assert saved=={r:u.reg_read(v) for r,v in regs.items()}
            assert xmm==[u.reg_read(UC_X86_REG_XMM0+i) for i in range(6)]
            assert not texts
        # Native gains have priority; ordinary updates never replay a gain.
        setup();begin();uses(2,71,500);run('spell_notice_prepare')
        put(actors+2*0x248+0xa0,'H',64);dispatch(2)
        assert not effects and get(active,'B')==0
        put(actors+2*0x248+0xa0,'H',0);dispatch(2,89);assert not effects
        dispatch(2,152);dispatch(2,152);dispatch(2,216)
        assert len(effects)==1 and get(actors+2*0x248+0xa0,'H')==0
        # Run the real native effect constructor and compare every generated
        # node against an ordinary level-up, not against a recreated animation.
        real_effect=True
        setup();reg('rcx',actors+2*0x248);reg('rdx',1)
        rsp=sp;put(rsp,'Q',stop);u.reg_write(UC_X86_REG_RSP,rsp)
        u.emu_start(base+0x117640,stop,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==stop
        expected=[bytes(u.mem_read(p,0x100)) for p in native_nodes]
        assert len(expected)==11
        setup();begin();uses(2,71,500);run('spell_notice_prepare');dispatch(2)
        actual=[bytes(u.mem_read(p,0x100)) for p in native_nodes]
        # UP!, particles, sound and all animation fields remain exactly native.
        for i,(a,e) in enumerate(zip(actual,expected)):
            if i not in (2,3):assert a==e,(i,'native effect changed')
            else:
                for offset in range(0x100):
                    if offset not in list(range(0x12,0x1a))+list(range(0x3a,0x3c))+list(range(0x42,0x48)):
                        assert a[offset]==e[offset],(i,offset)
                assert int.from_bytes(a[0x42:0x44],'little')==0x6000
                assert a[0x44:0x48]==bytes.fromhex('00040010')
                entry=base+info['native_labels']['table_rva']+71*32+(i-2)*8
                assert a[0x12:0x1a]==bytes(u.mem_read(entry,8))
        assert get(base+info['native_labels']['context_rva'],'I')==0
        assert get(actors+2*0x248+0xa0,'H')==0
        real_effect=False
        # Both JMP continuations preserve native registers and incoming flags.
        setup();begin();uses(2,71,500);run('spell_notice_prepare')
        put(sp-8+0x58,'I',88);reg('r13',actors+2*0x248)
        saved={r:u.reg_read(v) for r,v in regs.items()}
        xmm=[u.reg_read(UC_X86_REG_XMM0+i) for i in range(6)]
        run('spell_notice_schedule_hook',0x119e37)
        assert saved=={r:u.reg_read(v) for r,v in regs.items()}
        assert xmm==[u.reg_read(UC_X86_REG_XMM0+i) for i in range(6)]
        assert len(effects)==1
        reg('r13',0);run('spell_notice_schedule_hook',0x119e5e)
        setup();uses(2,71,10)
        extra=base+m['artesphere']['usage']['catchup']['live_rva']+(2*128+71)*2
        put(extra,'H',23);begin();uses(2,71,11);put(extra,'H',25)
        run('spell_notice_prepare')
        assert get(counts,'B')==1 and get(queue,'B')==71
        assert get(snapshot+71*2,'H')==33
        # Off, counter rollback, escape/new battle, no inherited victory notice.
        setup();uses(2,71,500);begin();uses(2,71,0);run('spell_notice_prepare')
        assert bytes(u.mem_read(counts,2))==b'\0\0'
        setup();begin();uses(2,71,500);put(data+0x1a0c,'B',0)
        reg('rcx',88);run('spell_notice_draw');assert not texts
        put(data+0x1a0c,'B',1);begin();reg('rcx',88);run('spell_notice_draw');assert not texts
        assert bytes(u.mem_read(snapshot,512))==bytes(u.mem_read(usage+512,512))
        from test_native_notice_mesh import check_native_labels
        cases+=check_native_labels(u,base,m,actors,sp,reset,put,get,reg,regs)
        return cases
    finally:u.hook_del(h)
