"""Execute optional Fringe list/reader/validation hooks against native recipes."""
import itertools
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS


def check_fringe(uc,base,m,actor,sp,reset,put,get,reg,regs):
    info=m['fringe'];state=base+info['state_rva'];data=base+m['data_rva']
    master=base+0x11ca420;flag=data+0x1a42
    end=base+m['data_rva']-0x10;count=0
    recipes=[]
    for i in range(48):
        row=tuple(uc.mem_read(base+0x564d40+i*5,5))
        if row[0]==255:break
        recipes.append(row)
    native=[[1,2],[24,25],[70,72,75],[79,82,86],[55],[62],[]]

    def setup(owners=(3,)*10,levels=(30,)*10,on=True):
        reset();put(flag,'B',on)
        put(data+0x1a63,'B',0) # isolate the independent team-up option
        uc.mem_write(master,b'\0'*0x1000)
        for ch,arts in enumerate(native):uc.mem_write(master+0x7a+ch*0xd0,bytes(arts))
        for i,(o,l) in enumerate(zip(owners,levels)):put(master+0xbb8+i*8,'BB',o,l)
        put(base+0x12cea60,'Q',master)
        uc.mem_write(state,b'\xA5'*0x1000)

    def execute(site,stops=(),entry=False):
        nonlocal count
        count+=1
        rsp=sp if entry else sp-8
        uc.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',end)
        reached=[]
        def step(u,a,size,_):
            if a==end or a-base in stops:reached.append(a-base);u.emu_stop()
        h=uc.hook_add(UC_HOOK_CODE,step) if stops else None
        try:uc.emu_start(base+site,end if not stops else end+1,count=500000)
        finally:
            if h:uc.hook_del(h)
        if not stops and uc.reg_read(UC_X86_REG_RIP)==end:reached.append(end-base)
        assert reached,('continuation',hex(site),hex(uc.reg_read(UC_X86_REG_RIP)))
        assert uc.reg_read(UC_X86_REG_RSP)==rsp+(8 if reached[0]==end-base else 0),('stack',hex(site))
        return reached[0]

    def expected(owners,levels,on):
        rows=[list(x) for x in native]
        if on:
            for art,p,s,lp,ls in recipes:
                if owners[p] in (3,4) and owners[s] and levels[p]>=lp and levels[s]>=ls:
                    ch=owners[p]-1
                    if art not in rows[ch]:rows[ch].append(art)
        return rows

    # Every split of the ten level-30 spirits; shared cage has >32 spells.
    max_count=0
    for bits in range(1024):
        owners=tuple(3+((bits>>i)&1) for i in range(10));levels=(30,)*10
        setup(owners,levels);before=bytes(uc.mem_read(master,0x1000))
        reg('rcx',master);execute(info['refresh'],entry=True)
        want=expected(owners,levels,True)
        for ch,row in enumerate(want):
            got=list(uc.mem_read(state+ch*0xd0,128))
            assert [x for x in got if x]==row,(bits,ch,got,row)
            assert bytes(uc.mem_read(state+ch*0xd0+128,80))==b'\xA5'*80
            max_count=max(max_count,len(row))
        assert before==bytes(uc.mem_read(master,0x1000)),'save mutated'
    assert max_count>32
    # Thresholds, possession, primary assignment and switch independence.
    for art,p,s,lp,ls in recipes:
        for owner,partner,low,on in itertools.product((3,4),(0,3,4),(0,1,2),(False,True)):
            owners=[0]*10;levels=[0]*10
            owners[p]=owner;owners[s]=partner
            levels[p]=max(0,lp-(low==1));levels[s]=max(0,ls-(low==2))
            setup(owners,levels,on);want=expected(owners,levels,on)
            for ch in (2,3):
                reg('rcx',ch);reg('rdx',art);reg('r8',master)
                execute(info['available'],entry=True)
                assert uc.reg_read(regs['rax'])==int(art in want[ch]),(art,p,s,owner,partner,low,on,ch)
    setup(on=False);reg('rcx',master);execute(info['refresh'],entry=True)
    assert list(uc.mem_read(state+2*0xd0,32))==native[2]+[0]*29
    # OFF and ON data are refreshed, not cached across a load or reassignment.
    setup();reg('rcx',2);reg('rdx',73);reg('r8',master)
    execute(info['available'],entry=True);yes=uc.reg_read(regs['rax'])
    put(flag,'B',0);reg('rcx',2);reg('rdx',73);reg('r8',master)
    execute(info['available'],entry=True);assert yes==1 and uc.reg_read(regs['rax'])==0

    # Menu count uses the last occupied row, including rows after index31.
    setup();reg('rcx',master);execute(info['refresh'],entry=True)
    reg('r9',2*0xd0);reg('rbx',base);reg('rcx',0);reg('r11',actor)
    execute(0x223290,[0x22359f]);assert get(actor+8,'H')==max(i+1 for i,v in enumerate(uc.mem_read(state+2*0xd0,128)) if v)

    # Battle membership retains native TP check, while recognising row>31.
    for on,ch,art in [(1,2,101),(1,3,101),(0,2,70),(0,2,101)]:
        setup(on=on);reg('rcx',master);execute(info['refresh'],entry=True)
        put(actor+0x4f,'B',ch);reg('r11',actor);reg('rbx',art)
        reg('r10',master+0x7a+ch*0xd0)
        got=execute(0x74592,[0x7459a,0x745f3,0x74598])
        if on:assert got==(0x7459a if art in expected((3,)*10,(30,)*10,True)[ch] else 0x745f3)
        else:assert got==0x74598

    # AI bucket overflow guard never writes outside its 32-entry bucket.
    for on,n in itertools.product((0,1),(0,31,32,63)):
        put(flag,'B',on);put(actor,'B',n);reg('rdx',actor);reg('rcx',actor+64)
        got=execute(0x73f59,[0x73f5f,0x73f65])
        assert got==(0x73f65 if on and n>=32 else 0x73f5f)
        if got==0x73f5f:assert uc.reg_read(regs['rcx'])==actor+64+n

    # Native menu indexed reads use all 128 entries only while enabled.
    from build_combat_patch import CS, BACKUP, pefile
    original=pefile.PE(str(BACKUP))
    for site in info['menu_reads']:
        ins=next(CS.disasm(original.get_data(site,15),site))
        op=next(o for o in ins.operands if o.type==3)
        for on in (0,1):
            put(flag,'B',on)
            reg(ins.reg_name(op.mem.base),base)
            if op.mem.index:reg(ins.reg_name(op.mem.index),7)
            pos=7 if op.mem.index else 0
            put(base+0x11ca49a+pos,'B',70);put(state+pos,'B',101)
            execute(site,[site+ins.size])
            if ins.mnemonic=='lea':assert uc.reg_read(regs[ins.reg_name(ins.operands[0].reg)])==base+(info['state_rva'] if on else 0x11ca49a)
            elif ins.mnemonic.startswith('mov'):
                rn=ins.reg_name(ins.operands[0].reg);rn={'eax':'rax','ebx':'rbx','ecx':'rcx','edi':'rdi','ebp':'rbp'}.get(rn,rn.removesuffix('d'))
                assert uc.reg_read(regs[rn])==(101 if on else 70),(hex(site),rn,on)

    # Directional and ally assignment cleanup preserves unlocked extended
    # spells; an absent primary still clears them. Native lists stay unaltered.
    for primary_on in (0,1):
        owners=[3]*10
        if not primary_on:owners=[0]*10
        setup(owners)
        uc.mem_write(master+0x9a+2*0xd0,bytes([70,73,101,255]))
        reg('r15',master)
        execute(0x21e0fa,[0x21e281])
        wanted=expected(owners,(30,)*10,True)[2]
        got=list(uc.mem_read(master+0x9a+2*0xd0,4))
        assert got==[a if a in wanted else 0 for a in (70,73,101,255)],(primary_on,got,wanted)
    put(flag,'B',0)
    return dict(cases=count,recipes=len(recipes),max_list=max_count,all_cage_splits=True,
        native_save_lists_unchanged=True,visual_validation=False)
