"""Execute standalone entry unlock, UI/list, launch and counter paths offline."""
from itertools import product
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_teamups(u,base,m,actors,stats,sp,reset,put,get,reg,regs):
    info=m['standalone_teamups'];data=base+m['data_rva'];master=base+0x11ca420
    usage=base+info['usage_rva'];meta=base+info['metadata'];launch=base+info['launch']
    sentinel=data-16;cases=0;calls=[];stubs=set();draws=[];descriptions=[]
    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('ABI',hex(u.reg_read(UC_X86_REG_RIP)),hex(rsp))
        reg('rax',value);u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def trace(emu,address,size,user):
        rva=address-base
        if rva in stubs:
            if rva==0x131c0:
                stack=u.reg_read(UC_X86_REG_RSP)
                draws.append(tuple(get(stack+off,'I') for off in (0x48,0x50,0x58,0x60)))
            if rva==0xd500:
                ptr=u.reg_read(regs['rcx'])
                descriptions.append(bytes(u.mem_read(ptr,256)).split(b'\0')[0].decode('utf8') if ptr else None)
            if rva==0x114980:
                calls.append((u.reg_read(regs['rcx']),u.reg_read(regs['rdx'])))
                put(u.reg_read(regs['rcx'])+0x58,'B',8)
            ret()
    h=u.hook_add(UC_HOOK_CODE,trace)
    def execute(start,end=None,aligned=False):
        nonlocal cases
        target=sentinel if end is None else base+end
        rsp=sp-8 if aligned else sp;u.reg_write(UC_X86_REG_RSP,rsp)
        if end is None:put(rsp,'Q',sentinel)
        u.ctl_remove_cache(target-16,target+16)
        u.emu_start(base+start,target,count=200000)
        assert u.reg_read(UC_X86_REG_RIP)==target,('continuation',hex(start),hex(u.reg_read(UC_X86_REG_RIP)))
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(8 if end is None else 0),('stack',hex(start))
        cases+=1
    def setup(on=1):
        reset();calls.clear();put(data+0x1a63,'B',on);put(data+0x1a42,'B',0)
        u.mem_write(master,b'\0'*0x1000);u.mem_write(usage,b'\0'*(7*128*2))
        u.mem_write(usage+0xd000,b'\0'*(7*128*2))
        put(base+0x12cea60,'Q',master);put(base+0x12cea70,'Q',meta);put(base+0x12cea78,'Q',launch)
        put(base+0x6449e0,'Q',actors+0xc200)
        for i in range(4):
            a=actors+i*0x248;put(a,'Q',actors+0x4000);put(a+0x34,'H',500)
            put(a+0x64,'B',0);put(a+0x65,'B',0);put(a+0x52,'B',0)
        execute(info['initialize'])
    def unlock(r,physical=50,k=50,me=0):
        put(master+0xc28+r['physical']*2,'H',physical)
        put(usage+(2*128+r['spell'])*2,'H',k)
        put(usage+(3*128+r['spell'])*2,'H',me)
    try:
        setup()
        assert bytes(u.mem_read(meta,126*24))==bytes(u.mem_read(base+0x562a50,126*24))
        assert bytes(u.mem_read(launch,114*8))==bytes(u.mem_read(base+0x551780,114*8))
        for r in (r for r in info['recipes'] if r['id']<130):
            assert get(meta+r['id']*24,'B')==r['tp']
            assert get(meta+r['id']*24+4,'I')==r['name_message']
            assert get(launch+r['id']*8,'B')==r['effect']
            assert get(launch+r['id']*8+1,'B')==0
            for on,p,k,me,owner in product((0,1),(49,50,9999),(0,25,49,50),(0,25,49,50),(0,1,2,3)):
                setup(on);unlock(r,p,k,me);before=bytes(u.mem_read(master,0x1000))
                reg('rcx',owner);reg('rdx',r['id']);reg('r8',master);execute(info['unlocked'])
                expected=on and owner==r['character'] and p>=50 and max(k,me)>=50
                assert u.reg_read(regs['rax'])==int(expected),(r,on,p,k,me,owner)
                assert bytes(u.mem_read(master,0x1000))==before
            for on in (0,1):
                setup(on);unlock(r);before=bytes(u.mem_read(master,0x1000))
                reg('rcx',master);execute(m['fringe']['refresh'])
                rows=base+m['fringe']['state_rva']+r['character']*0xd0
                assert (r['id'] in u.mem_read(rows,128))==bool(on)
                reg('rcx',r['character']);reg('rdx',r['id']);reg('r8',master)
                execute(m['fringe']['available']);assert u.reg_read(regs['rax'])==on
                # The same command gate serves palette B/C; native page A is
                # independently checked by the whole arte-start routine below.
                reg('rcx',r['character']);reg('rdx',r['id'])
                execute(m['symbols']['artesphere_learned']);assert u.reg_read(regs['rax'])==on
                assert bytes(u.mem_read(master,0x1000))==before
            # Actual native physical launch and TP debit, stubbing only engine
            # allocation/audio/presentation. Neither mage may change at all.
            for denied in ('off','locked','wrong_owner','full_pool'):
                setup(denied!='off');unlock(r,49 if denied=='locked' else 50)
                a=actors+r['character']*0x248
                if denied=='wrong_owner':put(a+0x4f,'B',2)
                if denied=='full_pool':
                    for i in range(16):put(base+0x12cfca0+i*0x120,'Q',actors+2*0x248)
                reg('rax',0x12345678);reg('rcx',a);reg('rdx',r['id'])
                execute(0x73790)
                assert u.reg_read(regs['rax'])==0,('AI rejected entry must return false',r['id'],denied)
            for condition in ('ok','off','locked','wrong_owner','low_tp','busy','full_pool','airborne'):
                setup(condition!='off');unlock(r,49 if condition=='locked' else 50)
                a=actors+r['character']*0x248
                if condition=='wrong_owner':put(a+0x4f,'B',2)
                if condition=='low_tp':put(a+0x34,'H',r['tp']-1)
                if condition=='busy':put(base+0x12d0eaa,'H',2)
                if condition=='full_pool':
                    for i in range(16):put(base+0x12cfca0+i*0x120,'Q',actors+2*0x248)
                if condition=='airborne':put(a+0x12,'h',-100)
                before=bytes(u.mem_read(actors+2*0x248,2*0x248));tp=get(a+0x34,'H')
                stubs={0x712e0,0x8d520,0x114980,0x114dd0,0x1b5ca0}
                reg('rcx',a);reg('rdx',r['id']);execute(0x112d10);stubs=set()
                allowed=condition=='ok' or (condition=='busy' and r['effect']>=100)
                assert bool(calls)==allowed,(r['id'],condition,calls,get(a+0x65,'B'))
                assert get(a+0x34,'H')==tp-(r['tp'] if allowed else 0),(r['id'],condition,'TP')
                if allowed:
                    assert calls==[(a,r['effect'])]
                    assert get(a+0x6d,'B')==r['id']
                    assert get(a+0x58,'B')==(0x40 if r['effect']<100 else 8)
                assert bytes(u.mem_read(actors+2*0x248,2*0x248))==before,'mage mutated'
            setup();unlock(r)
            # Execute the native icon renderer through its texture quad call.
            # Virtual entries must match the corresponding native physical icon.
            icons=[]
            for aid in (r['physical'],r['id']):
                draws.clear();reg('rcx',aid);reg('rdx',248);reg('r8',60)
                put(sp+0x28,'B',255);stubs={0x6c550,0x131c0}
                execute(0x42570);stubs=set();icons.append(list(draws))
            assert icons[0]==icons[1] and icons[1] and any(icons[1][0]),('icon',r['id'],icons)
            # Actual editor list color path, including native TP calculation.
            for tp in (r['tp']-1,r['tp'],133):
                put(master+r['character']*0xd0+0x3e,'H',tp)
                put(sp-8+0x68,'H',r['character']);put(sp-8+0x78,'I',0xffffffff)
                reg('rbx',r['id']);reg('r13',r['character']*0xd0)
                reg('r15',0xff000000);reg('r12',255)
                stubs={0x6c550,0x131c0}
                execute(0x2250a0,0x22517b,aligned=True);stubs=set()
                expected=0xff6060e0 if tp<r['tp'] else 0xffffffff
                assert u.reg_read(regs['rdi'])==expected,('list color',r['id'],tp,hex(u.reg_read(regs['rdi'])),u.reg_read(regs['rax']),hex(u.reg_read(regs['r13'])),get(master+r['character']*0xd0+0x3e,'H'))
                # Alternate native list layout also has Auto Yes/No coloring.
                for disabled in (0,1):
                    put(base+info['auto_disabled_rva'],'H',disabled<<(r['id']-126))
                    put(sp-8+0x80,'Q',r['character']*0xd0)
                    reg('rdi',r['id']);reg('r14',255);reg('r12',255);reg('r13',60);reg('r15',40)
                    stubs={0x6c550,0x131c0}
                    execute(0x225eac,0x225fca,aligned=True);stubs=set()
                    expected=0xff808080 if disabled else (0xff6060e0 if tp<r['tp'] else 0xfffffdfa)
                    assert u.reg_read(regs['rbx'])==expected,('grid color',r['id'],tp,disabled,hex(u.reg_read(regs['rbx'])))
                put(base+info['auto_disabled_rva'],'H',0)
            # Native description pointer -> layout -> cache -> cached repeat.
            for lang in (3,1,3):
                put(base+0x11c9ce8,'B',lang)
                for repeated in (False,True):
                    descriptions.clear();reg('rbp',r['id']);reg('rdi',base)
                    reg('rsi',0);reg('r9',0xffffffffffffffff);reg('r10',0)
                    stubs={0xd500,0xd620}
                    execute(0x227421,0x227822,aligned=True);stubs=set()
                    cached=get(base+0x11cce00,'Q')
                    value=bytes(u.mem_read(cached,256)).split(b'\0')[0].decode('utf8')
                    assert value and (descriptions==[] if repeated else descriptions==[value]),('description cache',r['id'],lang,descriptions,value)
                    assert 'Standalone' not in value and 'autonome' not in value
                    if r['id']==129:assert ('5 %' if lang==3 else '5%') in value
            reg('rcx',r['id']);execute(m['symbols']['arte_category_index'])
            assert u.reg_read(regs['rax']) in (3,4,5,6,7,8)
            # New count is kept in unused sidecar slots 0..3 per character.
            reg('rcx',r['character']);reg('rdx',r['id']);execute(m['symbols']['arte_usage_increment'])
            assert get(usage+(r['character']*128+r['id']-126)*2,'H')==1
            assert get(master+0xc28+r['physical']*2,'H')==50
            reg('rcx',r['id']);execute(0x38040)
            before=bytes(u.mem_read(master,0x1000))
            for disabled in (0,1,0):
                if disabled or get(base+info['auto_disabled_rva'],'H'):
                    reg('r8',r['id']);execute(0x22b67b,0x22b6c9,aligned=True)
                assert bool(get(base+info['auto_disabled_rva'],'H')&(1<<(r['id']-126)))==bool(disabled)
                reg('rdi',r['id']);reg('rcx',r['id']&31)
                execute(0x225ede,0x225ee6,aligned=True)
                assert bool(u.reg_read(regs['rax'])&(1<<(r['id']&31)))==not_disabled(disabled)
                reg('rbx',r['id']);execute(0x73ed4,0x73edd,aligned=True)
                reg('rbx',r['id']);execute(0x73f09,0x73f6c if disabled else 0x73f21,aligned=True)
                assert bytes(u.mem_read(master,0x1000))==before
        # No reserved slots: native holes and stale virtual IDs are removed
        # from the transient list, then only qualifying recipes are appended.
        # Execute the real count hook and both native list-reader layouts.
        from build_combat_patch import CS, BACKUP, pefile
        original=pefile.PE(str(BACKUP))
        for ch in (0,1):
            own=[r for r in info['recipes'] if r['character']==ch and r['id']<130]
            for bits in range(4):
                for enabled in (0,1):
                    setup(enabled);put(data+0x1a42,'B',1)
                    native=[1,2,3,4] if ch==0 else [25,26,27,28]
                    source=[native[0],0,native[1],0,native[2],native[3],own[0]['id'],own[1]['id']]
                    u.mem_write(master+0x7a+ch*0xd0,bytes(source))
                    for j,r in enumerate(own):
                        if bits&(1<<j):unlock(r)
                    before=bytes(u.mem_read(master,0x1000))
                    reg('rcx',master);execute(m['fringe']['refresh'])
                    expected=native+[r['id'] for j,r in enumerate(own) if enabled and bits&(1<<j)]
                    rows=base+m['fringe']['state_rva']+ch*0xd0
                    assert bytes(u.mem_read(rows,128))==bytes(expected)+bytes(128-len(expected))
                    reg('rcx',master);execute(m['fringe']['menu_refresh'])
                    reg('rcx',0);reg('r11',actors);reg('r9',ch*0xd0)
                    execute(0x223290,0x22359f,aligned=True)
                    assert get(actors+8,'H')==len(expected) and u.reg_read(regs['r9'])==4
                    for site in (0x225032,0x225e2a):
                        ins=next(CS.disasm(original.get_data(site,15),site))
                        op=next(o for o in ins.operands if o.type==3)
                        for idx,aid in enumerate(expected):
                            reg(ins.reg_name(op.mem.base),base)
                            reg(ins.reg_name(op.mem.index),ch*0xd0+idx)
                            execute(site,site+ins.size,aligned=True)
                            dest=ins.reg_name(ins.operands[0].reg)
                            assert u.reg_read(regs[{'ebx':'rbx','edi':'rdi'}[dest]])==aid
                    assert before==bytes(u.mem_read(master,0x1000))
        # Four unlocked entries fit without any native learned-list/save write.
        setup()
        for r in (r for r in info['recipes'] if r['id']<130):unlock(r)
        before=bytes(u.mem_read(master,0x1000))
        reg('rcx',master);execute(m['fringe']['refresh'])
        for ch,expected in ((0,[126,128]),(1,[127,129])):
            rows=base+m['fringe']['state_rva']+ch*0xd0
            assert [v for v in u.mem_read(rows,128) if v]==expected
        assert bytes(u.mem_read(master,0x1000))==before
        # Run the actual native heal, HP clamp and numeric event creation. The
        # cooperative 50% heal is unchanged; only Farah's virtual arte uses 5%.
        for char,side,aid,percent in ((1,0,129,5),(1,0,30,50),(0,0,129,50),(1,1,129,50)):
            for maximum,current in ((3042,1000),(3042,3000),(9999,1),(100,100)):
                setup();a=actors+0x248
                put(a+0x4f,'B',char);put(a+0x51,'B',side);put(a+0x6d,'B',aid)
                put(stats+0x18,'I',maximum);put(a+0x2c,'I',current)
                put(base+0x865a08,'I',0)
                reg('rcx',a)
                execute(0xca19e,0xca1a8,aligned=True)
                assert get(a+0x2c,'I')==min(maximum,current+maximum*percent//100),('heal',char,side,aid,maximum,current,get(a+0x2c,'I'))
                assert get(base+0x12d0f42+4,'H')==maximum*percent//100
    finally:
        u.hook_del(h);put(data+0x1a63,'B',1)
    return cases


def not_disabled(value):
    return not bool(value)
