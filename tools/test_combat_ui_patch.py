"""Execute gauge hooks plus the actual native quad builder/projection at both bases."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS


def check_combat_ui(uc, base, manifest, actors, enemies, stats, impact, sp,
                    reset, put, get, reg, regs):
    data = base+manifest['data_rva']
    sym = manifest['symbols']
    sentinel = manifest['data_rva']-0x10
    allocation = 0x40000000
    uc.mem_map(allocation, 0x2001000)
    count = 0
    checks = []
    nonvolatile = ['rbx','rbp','rsi','rdi','r12','r13','r14','r15']

    def setup():
        reset()
        put(data+0x1a05, 'B', 1)
        put(data+0x1a4b, 'B', 0)
        put(base+0x11c9ce8, 'B', 3)
        uc.mem_write(data+0x1000, b'\0'*0x208)
        uc.mem_write(data+0x1400, b'\0'*0xd0)
        put(base+0x573c3e, 'B', 0)
        uc.mem_write(base+0x11ce620, b'\0'*0xa0)
        put(base+0x644a58, 'Q', allocation)
        put(allocation+0x2000008, 'I', 0)
        put(base+0x644a10, 'Q', 0)
        put(base+0x644a18, 'Q', 0)
        put(base+0x12d0f00, 'B', 0)
        put(data+0x167f, 'B', 0)
        put(base+0x12cea68, 'Q', actors+0xc100)
        put(stats+0x18, 'i', 1000)
        for i in range(5):put(actors+i*0x248+0x4e, 'B', i)
        uc.mem_write(base+0x8c92d0, b'\0'*32)
        for off in (0,8,16):put(base+0x8c92d0+off, 'h', 4096)
        put(base+0x8c92e4, 'iii', 0,32,512)
        put(base+0x8c96f0, 'i', 512)
        put(base+0x8c9718, 'i', 160)
        put(base+0x8c92c4, 'i', 120)

    def execute(name, stop=None, stubs=(), intercept=None):
        nonlocal count
        count += 1
        # Mid-function JMP hooks inherit an aligned call-site RSP, leaf functions
        # enter with their native return address (8 mod 16).
        entrysp = sp-8 if stop is not None else sp
        uc.reg_write(UC_X86_REG_RSP, entrysp)
        put(entrysp, 'Q', base+sentinel)
        reached=[]
        saved={r:uc.reg_read(regs[r]) for r in nonvolatile}
        targets={stop if stop is not None else sentinel}
        def step(emu,address,size,user):
            rva=address-base
            if rva in targets:
                reached.append(rva);emu.emu_stop()
            elif name=='ui_capture_cast_anchor' and rva==0x801a6:
                # Run the actual sprite projection and native screen conversion;
                # omit only sprite texture submission, then use the real epilogue.
                emu.reg_write(UC_X86_REG_RIP,base+0x8140c)
            elif rva in stubs or rva==0x11e1f0:
                rsp=emu.reg_read(UC_X86_REG_RSP)
                assert rsp%16==8, ('ABI',name,hex(rva),hex(rsp))
                if intercept:intercept(rva,rsp)
                emu.reg_write(UC_X86_REG_RIP,get(rsp,'Q'))
                emu.reg_write(UC_X86_REG_RSP,rsp+8)
        handle=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+(sym[name] if isinstance(name,str) else name),base+sentinel+1,count=100000)
        finally:uc.hook_del(handle)
        assert reached,(name,'no return',hex(uc.reg_read(UC_X86_REG_RIP)))
        assert uc.reg_read(UC_X86_REG_RSP)==entrysp+(0 if stop is not None else 8),name
        assert saved=={r:uc.reg_read(regs[r]) for r in nonvolatile},(name,'ABI nonvolatile')
        return uc.reg_read(regs['rax'])

    def quads():
        length=get(allocation+0x2000008,'I')
        assert length%48==0
        return [[dict(rgb=tuple(uc.mem_read(allocation+8+o+v*12,3)),
                      x=get(allocation+8+o+v*12+4,'h'),
                      y=get(allocation+8+o+v*12+6,'h'),
                      z=get(allocation+8+o+v*12+8,'h')) for v in range(4)]
                for o in range(0,length,48)]

    if 'damage_colors' in manifest['features']:
        for side in [0,1]:
            for element in list(range(11))+[11,15,128,255]:
                setup();reg('rdi',actors);put(actors+0x51,'B',side)
                reg('r12',impact);put(impact+1,'B',element)
                reg('rcx',impact+32);reg('rdx',17)
                execute('tag_damage_color',0x8f07c)
                expected=0x40 if side==0 else 0x10+4*(element if element<=10 else 0)
                assert get(impact+39,'B')==expected
                assert uc.reg_read(regs['rdx'])==1
                assert not (uc.reg_read(UC_X86_REG_EFLAGS)&0x80)
                for lifetime in [56,40,20,1]:
                    reg('rbx',impact+34);reg('rbp',lifetime)
                    put(base+0x11ce670,'I',0x99808080)
                    execute('draw_damage_color',0x11cf45,[0x1114a0])
                    color=bytes(uc.mem_read(base+0x11ce670,4))
                    wanted=bytes((128,76+(56-lifetime)//2,76+(56-lifetime)//2)) if side==0 else bytes(uc.mem_read(data+0x1300+(expected-0x10),3))
                    assert color[:3]==wanted and color[3]==0x99
        for original_type in [0,2,4,255]:
            setup();reg('rbx',impact);put(impact+5,'B',original_type)
            put(base+0x11ce670,'I',0x99885511)
            execute('draw_damage_color',0x11cf45,[0x1114a0])
            assert get(base+0x11ce670,'I')==0x99885511
        for original_type in (1,3):
            for lifetime in (56,40,20,1):
                setup();reg('rbx',impact);reg('rbp',lifetime)
                put(impact+5,'B',original_type)
                execute('draw_damage_color',0x11cf45,[0x1114a0])
                assert bytes(uc.mem_read(base+0x11ce670,3))==bytes((112,128,112))
        checks.append('Damage ring: 11 elements, received-hit priority, native Symphonia mint recovery pair')

        # Exercise native 1114a0 -> 1227b0 -> both HD passes -> actual packed
        # vertex commands. Verify glyph cells, two-tone colors, return scope,
        # and unmodified HP/TP calls outside the damage ring.
        import struct
        pairs=[('205080','102850'),('308050','185030'),('802810','501008'),
               ('705020','483010'),('708080','385868'),('805080','582858'),
               ('808058','585830'),('301850','180828'),('708070','508050')]
        for tag,pair in list(zip(range(0x14,0x34,4),pairs))+[(0x34,('808080','808080')),(1,pairs[-1]),(3,pairs[-1])]:
            setup()
            put(data+0x1a03,'B',1)
            context=actors+0xc800
            put(base+0x644a10,'Q',context)
            put(context+0x4d0,'Q',allocation+0x10000)
            put(context+0x4d8,'Q',4096)
            put(context+0x4e0,'I',0)
            reg('rbx',impact);put(impact+5,'B',tag);reg('rbp',40)
            reg('rcx',135);reg('rdx',100);reg('r8',80);reg('r9',4)
            # Mid-function hook RSP = sp-8; these are the native stack args.
            for off,val in ((0x20,40),(0x28,24 if tag in (1,3) else 0),(0x30,12),(0x38,12)):
                put(sp-8+off,'I',val)
            captured=[]
            def capture_gradient(rva,rsp):
                if rva==0x60bf0:
                    c=bytes(uc.mem_read(uc.reg_read(regs['rdx']),80))
                    if struct.unpack_from('<I',c)[0]==5:
                        assert struct.unpack_from('<3I',c,8)==(4,0x80019f,4)
                        ptr=struct.unpack_from('<Q',c,32)[0]
                        captured.append([struct.unpack('<2fI3f',uc.mem_read(ptr+i*24,24)) for i in range(4)])
            execute('draw_damage_color',0x11cf45,(0x12b90,0x11ded0,0x60bf0),capture_gradient)
            assert len(captured)==6, ('two native HD passes for three digits',tag,len(captured))
            colors=[int.from_bytes(bytes(min(255,c*2) for c in bytes.fromhex(h))+b'\xff','little') for h in pair]
            for q in captured:
                assert [v[2] for v in q]==[colors[0],colors[0],colors[1],colors[1]],q
                assert q[0][1]==800 and q[2][1]==848,q
                assert q[0][0] in (48,144,240) and q[1][0]-q[0][0]==48,q
            assert get(data+0x13c0,'B')==0, 'gradient state leaked beyond number draw'
        checks.append('Actual native damage glyph pipeline: original numeral strip, paired Symphonia RGBA vertices in both HD passes, no gradient state leakage')

    if 'combat_ui' not in manifest['features']:
        uc.mem_unmap(allocation,0x2001000)
        return checks,count

    # Native Compendium scans persist across encounters and loaded saves.
    # Exercise the actual Spectacles flag write, then the new read-only display.
    for scanned in (False, True):
        for enabled in (False, True):
            for slot in (0,1,7):
                setup()
                master=actors+0xa000
                species=203
                put(base+0x12cea60,'Q',master)
                put(base+0x12cece9,'B',8)
                put(base+0x12d0f33+slot,'B',species)
                put(enemies+0x4f,'B',slot)
                put(enemies+0xe8,'Q',stats)
                put(enemies+0x2c,'i',600)
                put(master+0xcf8+species,'B',1)
                if scanned:
                    reg('rax',master);reg('rcx',species)
                    execute(0x923be,0x923c6)
                put(data+0x1a4b,'B',int(enabled))
                before=bytes(uc.mem_read(master,0x1000))
                reg('rcx',enemies)
                value=execute('ui_scanned_enemy_hp')
                assert value==(600*65536//1000 if scanned and enabled else 0)
                assert bytes(uc.mem_read(master,0x1000))==before
                # A subsequent battle has a different actor slot for that species.
                put(enemies+0x4f,'B',2)
                put(base+0x12d0f33+2,'B',species)
                reg('rcx',enemies)
                assert execute('ui_scanned_enemy_hp')==value
                # Loading a different, unscanned save must not inherit scans.
                put(base+0x12cea60,'Q',actors+0xb000)
                put(actors+0xb000+0xcf8+species,'B',1)
                reg('rcx',enemies)
                assert execute('ui_scanned_enemy_hp')==0
    for casts_enabled in (0,1):
        setup();put(data+0x1a4b,'B',1);put(data+0x1a05,'B',casts_enabled)
        master=actors+0xa000
        put(base+0x12cea60,'Q',master);put(base+0x12d0f33,'B',203)
        put(master+0xcf8+203,'B',3)
        put(enemies+0x4f,'B',0);put(enemies+0xe8,'Q',stats)
        put(enemies+0x2c,'i',500);put(enemies+0x8c,'h',0)
        anchor=data+0x1400+5*16
        put(anchor,'Qii',enemies,240,120);put(anchor+0x108,'ii',270,70)
        execute('ui_cast_bars');q=quads()
        assert len(q)==3 and q[-1][1]['x']-q[-1][0]['x']==14, q
        assert q[-1][0]['y']==64, q
        execute('ui_cast_bars');assert len(quads())==3,'stale anchor drawn again'
    checks.append('Spectacles: saved native scan flag, encounter remap, save isolation, independent optional HP gauge')

    # Real atlas initialization previously overwrote the Spectacles label table
    # at 17B0 (Lightning's entry at 1800 became a vtable pointer). Exercise all
    # ten icon objects before R1, including both translated label tables.
    label_pairs=[('???','???'),('PV','HP'),('Rs :','Rs:'),('Fb :','Wk:'),('—','—'),
                 ('Eau','Water'),('Vent','Wind'),('Feu','Fire'),('Terre','Earth'),('Glace','Ice'),
                 ('Foudre','Volt'),('Lumière','Light'),('Ténèbres','Dark'),('Élémental','Element'),('Temps','Time')]
    setup()
    if 'ui_bind_spirit_atlas' in sym:
        for spirit in range(10):
            reg('rdi',spirit)
            execute('ui_bind_spirit_atlas')
    for language, column in ((3,0),(1,1)):
        put(base+0x11c9ce8,'B',language)
        for index, pair in enumerate(label_pairs):
            reg('rcx',index);execute('scan_panel_label')
            pointer=uc.reg_read(regs['rcx'])
            assert data <= pointer < data+0x2000, ('corrupted Spectacles label', language, index, hex(pointer))
            expected=pair[column].encode('utf-8')+b'\0'
            assert bytes(uc.mem_read(pointer,len(expected)))==expected, (language,index)
    checks.append('Spectacles/Craymel storage regression: ten real atlas initializations followed by all 30 FR/EN labels and R1')

    # The smaller target panel reads the same saved species and resistances as
    # Spectacles; it never re-scans, changes HP, or spends an item.
    for language in (3,1):
        for condition in ('shown','no_selector','other_target','unscanned','off','dead','lens_open','lens_closing_frame'):
            setup();master=actors+0xa000;anchor=data+0x1450
            put(data+0x1a4b,'B',int(condition!='off'))
            put(base+0x11c9ce8,'B',language)
            put(base+0x12cea60,'Q',master);put(base+0x12d0f33,'B',203)
            put(master+0xcf8+203,'B',1 if condition=='unscanned' else 3)
            put(enemies+0xe8,'Q',stats);put(enemies+0x2c,'i',543)
            put(enemies+0x78,'b',50);put(stats+0x18,'I',750)
            put(stats+0x31,'10b',100,0,0,0,-50,-30,0,0,0,0)
            put(base+0x12ceb8d,'B',0 if condition=='no_selector' else 1)
            put(actors+0x63,'B',int(condition=='other_target'))
            if condition=='dead':put(actors+0x3c,'H',2)
            if condition=='lens_open':put(base+0x12d0f00,'B',128)
            if condition=='lens_closing_frame':
                execute('ui_native_spectacles_visible',0xd4198,[0x91ca0])
                assert get(data+0x167f,'B')==1
            put(anchor+0x108,'ii',450,50)
            put(base+0x644a10,'Q',allocation+0x1000)
            manager=allocation+0x2000;catalog=allocation+0x30000;record=allocation+0x2100
            put(base+0x644a70,'Q',manager);put(manager+8,'I',0 if language==3 else 1)
            put(manager+0x18,'Q',catalog);put(catalog+0x214d0+203*8,'Q',record)
            for lang,title in enumerate(('Cisailleur','Slicer')):
                ptr=allocation+0x2200+lang*0x40
                put(record+8+lang*8,'Q',ptr);uc.mem_write(ptr,(title+'\0').encode('utf-8'))
            # Execute native 2518A0, including its palette, circular sprite UVs,
            # localized captions and font sizing; intercept only submission.
            for element in range(1,11):
                msg=get(base+0x50fff8+element*4,'i')
                entry=allocation+0x50000+element*0x100
                put(catalog+msg*8,'Q',entry)
                for lang in (0,1):
                    ptr=entry+0x40+lang*0x40
                    put(entry+8+lang*8,'Q',ptr)
                    uc.mem_write(ptr,(label_pairs[element+4][lang]+'\0').encode('utf8'))
            text=[];windows=[];icons=[];captions=[]
            def panel_boundary(rva,rsp):
                if rva==0x11ac40:
                    windows.append(tuple(uc.reg_read(regs[r])&0xffffffff for r in ('rcx','rdx','r8','r9'))+(get(rsp+0x28,'I'),))
                if rva in (0xb480,0xcb90):
                    ptr=uc.reg_read(regs['rcx']);raw=bytearray()
                    for i in range(128):
                        b=bytes(uc.mem_read(ptr+i,1))
                        if b==b'\0':break
                        raw.extend(b)
                    (text if rva==0xb480 else captions).append(raw.decode('utf8'))
                if rva==0x12cb0:
                    from unicorn.x86_const import UC_X86_REG_XMM1,UC_X86_REG_XMM2
                    import struct
                    coords=tuple(struct.unpack('<f',(uc.reg_read(r)&0xffffffff).to_bytes(4,'little'))[0]
                                 for r in (UC_X86_REG_XMM1,UC_X86_REG_XMM2))
                    icons.append((uc.reg_read(regs['rcx']),coords,get(rsp+0x28,'f'),get(rsp+0x30,'f')))
            before=bytes(uc.mem_read(master,0x1000));before_actor=bytes(uc.mem_read(enemies,0x248))
            reg('rcx',enemies);reg('rdx',anchor)
            execute('ui_scanned_target_panel',stubs=[0x11ac40,0x24f290,0xb480,0x12cb0,0xcb90],intercept=panel_boundary)
            if condition=='shown':
                assert windows==[(300,0xfffffffc,508,96,56)],windows
                assert text==(['Cisailleur','PV','543','/750','Rs :','Fb :'] if language==3 else
                              ['Slicer','HP','543','/750','Rs:','Wk:']),text
                assert captions==(['Eau','Glace','Foudre'] if language==3 else ['Water','Ice','Volt']),captions
                assert icons==[(10,(406.,37.),14.,14.),(10,(406.,52.),14.,14.),(10,(420.,52.),14.,14.)],icons
            else:assert not text and not windows,condition
            assert bytes(uc.mem_read(master,0x1000))==before
            assert bytes(uc.mem_read(enemies,0x248))==before_actor
            if condition=='lens_closing_frame':
                execute('ui_cast_bars')
                assert get(data+0x167f,'B')==0, 'closing latch must reset each HUD frame'
                text.clear();windows.clear()
                reg('rcx',enemies);reg('rdx',anchor)
                execute('ui_scanned_target_panel',stubs=[0x11ac40,0x24f290,0xb480,0x12cb0,0xcb90],intercept=panel_boundary)
                assert len(windows)==1 and text, 'R1 panel must resume on the following frame'
    put(base+0x644a70,'Q',0)
    checks.append('R1 Spectacles: native 96x56 bubble, real elemental discs/captions, HP layout, right gutter, viewport clamp, saved scans, no gameplay writes')

    # Execute the real animated-pad layout and intercept only the final glyph
    # submission. Direction/blink/size stay native; placement shares HUD space.
    for wide in (0,1):
        for slot in range(4):
            for tick in (0,59,60,119,120,255):
                for direction in (1,2,4,8):
                    setup()
                    put(actors+0xc100,'H',0x400 if wide else 0)
                    put(base+0x573c3e,'B',wide)
                    put(base+0x12ceb7e,'B',tick)
                    put(base+0x12cea60,'Q',0)
                    reg('rbx',actors+slot*0x248)
                    captures=[]
                    def capture_pad(rva,rsp):
                        captures.append(tuple(uc.reg_read(regs[r])&0xffffffff for r in ('rcx','rdx','r8','r9'))+
                                        tuple(get(rsp+o,'H' if o==0x38 else 'I') for o in (0x28,0x30,0x38,0x40)))
                    reg('rcx',slot*48+27);reg('rdx',237);reg('r8',direction)
                    execute('ui_fast_cast_pad',0xd53aa,[0x140c0],capture_pad)
                    expected_x=slot*48+30
                    expected_y=250
                    assert captures==[(expected_x,expected_y,510,direction<<4,16,0xffffffff,0,int(tick%120>=60))],captures
                    assert slot*48+48-(captures[0][0]+16)==2, 'pad must leave exactly two units before miniature'
    # A wide Meredy group must not collide with Keele's pad in a later slot.
    for previous_count in range(1,10):
        setup();master=actors+0xa000;put(base+0x12cea60,'Q',master)
        put(actors+0x4f,'B',3);put(actors+0x248+0x4f,'B',2)
        for j in range(10):put(master+0xbb8+j*8,'BBH',4 if j<previous_count else 3,15,0xa000)
        reg('rbx',actors+0x248);icons=[]
        def capture_icon(rva,rsp):
            if rva==sym['ui_spirit_icon']:icons.append(uc.reg_read(regs['rsi']) & 0xffffffff)
        execute('ui_all_spirit_max',0xd1e5b,[0xb240,0xb480,sym['ui_spirit_icon']],capture_icon)
        captures=[]
        execute('ui_fast_cast_pad',0xd53aa,[0x140c0],capture_pad)
        assert icons and icons[0]+83-(captures[0][0]+16)==2
        assert captures[0][0]>=48+(previous_count-1)*14+8+2
    checks.append('Fast-cast pad adjacent to miniatures in all slots/modes; two-unit gap including a preceding Meredy group, native animation and direction')

    for maximum in [-1,0,1,100,9999,0x7fffffff]:
        for current in [-10,0,1,50,9999,0x7fffffff]:
            setup();reg('rcx',current & 0xffffffff);reg('rdx',maximum & 0xffffffff)
            result=execute('ui_ratio')
            expected=0 if maximum<=0 or current<=0 else min(current,maximum)*65536//maximum
            assert result==expected,(current,maximum,result,expected)
    for metric in [0,1]:
        setup();reg('rcx',actors);reg('rdx',metric)
        put(actors+(0x2c if metric==0 else 0x34),'i' if metric==0 else 'h',1000 if metric==0 else 100)
        assert execute('ui_hud_fraction')==31
        put(actors+(0x2c if metric==0 else 0x34),'i' if metric==0 else 'h',250 if metric==0 else 25)
        values=[]
        for frame in range(90):
            reg('rcx',actors);reg('rdx',metric);values.append(execute('ui_hud_fraction'))
        assert values[0]<31 and values[0]>7 and values[-1]==7
        assert values==sorted(values,reverse=True)
        put(base+0x12ceb7a,'B',1)
        put(actors+(0x2c if metric==0 else 0x34),'i' if metric==0 else 'h',0)
        reg('rcx',actors);reg('rdx',metric)
        assert execute('ui_hud_fraction')==7
    setup();put(data+0x1204,'I',100);put(base+0x12cea40,'I',1)
    uc.mem_write(data+0x1000,b'\xff'*0x80)
    execute('ui_frame_guard')
    assert bytes(uc.mem_read(data+0x1000,0x80))==b'\0'*0x80
    assert get(data+0x1204,'I')==1
    checks.append('Animated HP/TP: clamped real/max ratios, easing, pause, and new-battle state reset')

    for metric,y in [(0,220),(1,235)]:
        for party_slot in range(4):
            setup();actor=actors+party_slot*0x248
            put(actor+0x2c,'i',500);put(actor+0x34,'h',50)
            reg('rbx',actor)
            scratch=bytes(uc.mem_read(base+0x11ce620,0xa0))
            gameplay=bytes(uc.mem_read(actors,0x1000))
            execute(f'ui_hud_bar_{metric}',0xd1aaa if metric==0 else 0xd1b3d)
            q=quads();assert len(q)==3
            assert q[2][0]['x']==party_slot*48-20+80
            assert q[2][1]['x']-q[2][0]['x']==15
            assert q[1][1]['x']==party_slot*48+11+80, 'gauge right edge moved'
            assert q[2][0]['y']==y+16
            assert all(v['z']==507 for quad in q for v in quad)
            assert q[2][0]['rgb']==((84,219,120) if metric==0 else (80,173,255))
            assert bytes(uc.mem_read(base+0x11ce620,0xa0))==scratch
            assert bytes(uc.mem_read(actors,0x1000))==gameplay
    checks.append('Native quad renderer: all 4 HUD slots, HP/TP positions, 50% width, correct colors and restored render scratch')
    # Run the actual native digit layout, intercept only final glyph submission.
    for slot_index in range(4):
        for metric,y,site,value in [(0,208,0xd1c28,9999),(0,208,0xd1c28,1000),(0,208,0xd1c28,999),(1,223,0xd1cd9,999)]:
            setup();reg('rdi',slot_index*48);reg('rcx',value);reg('r9',4)
            entrysp=sp-8
            for off,val in [(0x20,0),(0x28,200),(0x30,12),(0x38,12)]:put(entrysp+off,'B',val)
            glyphs=[]
            def capture_glyph(rva,rsp):
                glyphs.append((get(base+0x11ce660,'h'),get(base+0x11ce662,'h'),
                               get(base+0x11ce68e,'H')//4,get(base+0x11ce690,'H')//4))
            execute(f'ui_hud_number_{metric}',site,[0x1227b0],capture_glyph)
            assert len(glyphs)==len(str(value)),glyphs
            assert all((gy,w,h)==(y,12,12) for gx,gy,w,h in glyphs),glyphs
            assert max(x+w for x,gy,w,h in glyphs)==slot_index*48+(15 if metric==0 else 11)
            bar_y=220 if metric==0 else 235
            assert y+12==bar_y, 'digits obscure gauge'
            assert min(x for x,gy,w,h in glyphs)>=slot_index*48+(-21 if metric==0 else -25), 'digits extend outside the reserved slot'
            assert all(abs(glyphs[i][0]-glyphs[i-1][0])==8 for i in range(1,len(glyphs))), 'native digit advance'
            if metric:assert min(gy for x,gy,w,h in glyphs)>=223, 'TP digits over HP gauge'
    # Execute the unchanged portrait branch with only its two new immediates.
    for slot_index in range(4):
        for local_x,local_y in [(-8,-24),(0,0),(8,0)]:
            setup();put(actors+0x56,'B',slot_index);reg('rbx',actors)
            reg('rsi',local_y&0xffff);reg('r15',local_x&0xffff)
            uc.emu_start(base+0x80af3,base+0x80b24,count=100)
            assert (uc.reg_read(regs['r8'])&0xffff)==(slot_index*48-28+local_x)&0xffff
            assert get(base+0x11ce662,'h')==236+local_y
    checks.append('Real digit and portrait layout: 4 unchanged 48-unit slots; full-size 9999/999; 9999 inside gauge; native-size glyphs; lowered HUD')

    # All vitality values are visible. Run the native glyph layout separately;
    # here intercept text/icon submission and verify ownership/placement/state.
    from unicorn.x86_const import UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2
    from casting_color_patch import COLORS
    import struct
    def xmm_float(register):
        return struct.unpack('<f',struct.pack('<I',uc.reg_read(register)&0xffffffff))[0]
    def text_metrics(rsp):
        language=get(base+0x11c9ce8,'H')&255
        adjusted=bool(get(base+0x644a18,'Q')) and (1<=language<=6 or language>=10)
        size=5.5 if adjusted else 5
        assert xmm_float(UC_X86_REG_XMM1)==size
        assert get(rsp+0x28,'f')==0, 'measurement must not clamp label width'
        assert get(rsp+0x30,'i')==-1
        text=bytes(uc.mem_read(uc.reg_read(regs['rcx']),8)).split(b'\0')[0].decode()
        width=(11.5 if text=='MAX' else 12.75)*size/5
        uc.reg_write(UC_X86_REG_XMM0,struct.unpack('<I',struct.pack('<f',width))[0])
    def element_color():
        rgb=list(COLORS.values())[uc.reg_read(regs['rdi'])]
        return int.from_bytes(bytes(rgb)+b'\xff','little')
    for character in [2,3]:
        for slot_index in range(4):
            for owned_count in range(11):
                setup();actor=actors+slot_index*0x248;master=actors+0xa000
                put(base+0x12cea60,'Q',master)
                for j in range(4):put(actors+j*0x248+0x4f,'B',0)
                put(actor+0x4f,'B',character)
                for j in range(10):
                    put(master+0xbb8+j*8,'BBH',character+1,15 if j<owned_count else 0,j*0x1000)
                before=bytes(uc.mem_read(master,0x1000));reg('rbx',actor)
                render_before=bytes(uc.mem_read(base+0x11ce620,0xa0));badges=[];icons=[]
                def capture_badge(rva,rsp):
                    if rva==sym['ui_spirit_icon']:
                        icons.append((uc.reg_read(regs['rdi']),uc.reg_read(regs['rsi'])&0xffffffff,uc.reg_read(regs['rbp'])))
                    elif rva==0xb240:
                        text_metrics(rsp)
                    elif rva==0xb480:
                        assert get(rsp+0x30,'I')==element_color()
                        ptr=uc.reg_read(regs['rcx'])
                        text=bytes(uc.mem_read(ptr,8)).split(b'\0')[0].decode()
                        badges.append((text,xmm_float(UC_X86_REG_XMM1),xmm_float(UC_X86_REG_XMM2)))
                execute('ui_all_spirit_max',0xd1e5b,[0xb240,0xb480,sym['ui_spirit_icon']],capture_badge)
                assert len(badges)==len(icons)==owned_count,(character,owned_count,badges)
                for j,(text,x,y) in enumerate(badges):
                    assert (text,x,y)==(f'{j}/10',slot_index*48+52+j*14-12.75/2,264)
                    assert x+14<=480 and y+5<=270
                    assert icons[j]==(j,(slot_index*48-35+j*14)&0xffffffff,237)
                    assert x+12.75/2==slot_index*48+52+j*14, 'icon/text center differs from portrait'
                assert bytes(uc.mem_read(master,0x1000))==before
                assert bytes(uc.mem_read(base+0x11ce620,0xa0))==render_before
    # The renderer changes effective font size for several language IDs.
    for language in [0,1,2,6,7,9,10,255]:
        setup();master=actors+0xa000;put(base+0x12cea60,'Q',master)
        put(base+0x644a18,'Q',1);put(base+0x11c9ce8,'H',language)
        put(actors+0x4f,'B',2);put(master+0xbb8,'BBH',3,15,0xa000)
        reg('rbx',actors);positions=[]
        def localized_text(rva,rsp):
            if rva==0xb240:text_metrics(rsp)
            elif rva==0xb480:
                assert get(rsp+0x28,'f')==5, 'drawer must retain nominal size'
                positions.append(xmm_float(UC_X86_REG_XMM1))
        execute('ui_all_spirit_max',0xd1e5b,[0xb240,0xb480,sym['ui_spirit_icon']],localized_text)
        width=11.5*(1.1 if 1<=language<=6 or language>=10 else 1)
        assert len(positions)==1 and abs(positions[0]+width/2-52)<1e-5
    # Both cage groups stay separate for every split and order of party slots.
    for first_slot in range(3):
        for second_slot in range(first_slot+1,4):
            for split in range(11):
                setup();master=actors+0xa000;put(base+0x12cea60,'Q',master)
                for j in range(4):put(actors+j*0x248+0x4f,'B',0)
                put(actors+first_slot*0x248+0x4f,'B',2)
                put(actors+second_slot*0x248+0x4f,'B',3)
                for j in range(10):put(master+0xbb8+j*8,'BBH',3 if j<split else 4,15,0xa000)
                groups=[]
                for slot_index in [first_slot,second_slot]:
                    badges=[];reg('rbx',actors+slot_index*0x248)
                    def capture_max(rva,rsp):
                        if rva==0xb240:
                            text_metrics(rsp)
                        elif rva==0xb480:
                            assert bytes(uc.mem_read(uc.reg_read(regs['rcx']),4))==b'MAX\0'
                            assert get(rsp+0x30,'I')==element_color(), 'MAX must use spirit element tint'
                            badges.append(xmm_float(UC_X86_REG_XMM1))
                    execute('ui_all_spirit_max',0xd1e5b,[0xb240,0xb480,sym['ui_spirit_icon']],capture_max)
                    groups.append(badges)
                assert len(groups[0])==split and len(groups[1])==10-split
                if all(groups):assert max(groups[0])+14 < min(groups[1])
                assert max(groups[0]+groups[1])+14<=480
    for exclusion in ['wrong_owner','locked','enemy','fighter','invalid_slot','outside_battle','no_master','buffer_full']:
        setup();master=actors+0xa000;actor=actors;put(base+0x12cea60,'Q',master)
        put(actor+0x4f,'B',2);put(master+0xbb8,'BBH',3,15,0xa000)
        if exclusion=='wrong_owner':put(master+0xbb8,'B',4)
        if exclusion=='locked':put(master+0xbb9,'B',0)
        if exclusion=='enemy':put(actor+0x51,'B',1)
        if exclusion=='fighter':put(actor+0x4f,'B',0)
        if exclusion=='invalid_slot':put(actor+0x4e,'B',4)
        if exclusion=='outside_battle':put(base+0x12d0ef7,'B',5)
        if exclusion=='no_master':put(base+0x12cea60,'Q',0)
        if exclusion=='buffer_full':put(allocation+0x2000008,'I',0x2000000)
        reg('rbx',actor);badges=[]
        execute('ui_all_spirit_max',0xd1e5b,[0xb480,sym['ui_spirit_icon']],lambda r,s:badges.append(r))
        assert not badges,exclusion
    checks.append('Owned-spirit footer: 0-10 per mage, all vitality values, MAX, both mage groups in every party order without overlapping, ownership/lock guards, no gameplay writes')
    for missing in [False,True]:
        setup()
        if missing:put(base+0x644a58,'Q',0)
        else:put(allocation+0x2000008,'I',0x2000000)
        scratch=bytes(uc.mem_read(base+0x11ce620,0xa0))
        reg('rcx',0);reg('rdx',0);reg('r8',36);reg('r9',3);reg('rax',0xffffff)
        execute('ui_rectangle')
        assert bytes(uc.mem_read(base+0x11ce620,0xa0))==scratch
    checks.append('Additional HUD geometry safely omitted if the native vertex buffer is missing or exhausted')

    def capture_anchor(actor, world_scaling=1):
        put(actors+0xc100,'H',0x400)
        put(base+0x573c3e,'B',world_scaling)
        reg('rbx',actor);reg('rcx',actor);reg('rdx',0)
        execute('ui_capture_cast_anchor',0x81534)
        x,y=get(actor+0x7a,'h'),get(actor+0x7c,'h')
        screen=(x*3//2,y*3//2-20) if world_scaling else (x+80,y+16)
        put(base+0x573c3e,'B',0)
        # HUD portrait rendering overwrites the actor field later in the frame.
        # That must never displace the independent world anchor.
        put(actor+0x7a,'hh',300,240)
        return screen

    for side,actor,index in [(0,actors,0),(0,actors+2*0x248,2),(1,enemies,5)]:
        setup();reg('rbx',actor);reg('rdx',124)
        execute('ui_capture_cast_duration',0x112fff)
        assert get(actor+0x8c,'H')==124
        assert get(data+0x1100+index*16+8,'I')==124
        put(actor+0x6c,'B',4)
        for remaining,width in [(124,0),(94,5),(64,10),(34,15),(4,20),(2,20),(0,None)]:
            put(allocation+0x2000008,'I',0)
            put(actor+0x8c,'h',remaining)
            sx,sy=capture_anchor(actor)
            scratch=bytes(uc.mem_read(base+0x11ce620,0xa0))
            projection=bytes(uc.mem_read(base+0x8c9720,32))
            gameplay=bytes(uc.mem_read(actors,0x1000))
            execute('ui_cast_bars')
            q=quads()
            if width is None:assert not q
            else:
                assert len(q)==(3 if width else 2),(remaining,len(q))
                if width:
                    assert q[-1][1]['x']-q[-1][0]['x']==width
                    assert q[-1][0]['rgb']==(232,127,230)
                assert q[0][0]['x']==sx-11
                assert q[0][0]['y']==sy+3
                assert q[1][2]['y']-q[1][0]['y']==2
            assert bytes(uc.mem_read(base+0x11ce620,0xa0))==scratch
            assert bytes(uc.mem_read(base+0x8c9720,32))==projection
            assert bytes(uc.mem_read(actors,0x1000))==gameplay
            assert get(data+0x1400+index*16,'Q')==0, 'stale world anchor'
    # Native world scaling differs from HUD: exercise both modes, independently
    # from the later draw flag, with a moving/zooming camera and two nearby casters.
    for world_scaling in [0,1]:
        for draw_flag in [0,1]:
            for depth in [384,512,768]:
                setup();centers=[]
                put(base+0x8c92e4,'iii',-70,25,depth)
                for index,element in [(0,4),(1,12)]:
                    actor=actors+index*0x248
                    put(actor+0x10,'h',index*40*16)
                    put(actor+0x6c,'B',element)
                    reg('rbx',actor);reg('rdx',124)
                    execute('ui_capture_cast_duration',0x112fff)
                    put(actor+0x8c,'h',64)
                    centers.append(capture_anchor(actor,world_scaling))
                put(base+0x573c3e,'B',draw_flag)
                put(base+0x8c92e4,'iii',500,-100,512)  # late matrix differs
                execute('ui_cast_bars');q=quads()
                assert len(q)==6
                for i,(x,y) in enumerate(centers):
                    assert q[i*3][0]['x']==x-11 and q[i*3][0]['y']==y+3
                    assert q[i*3+2][0]['rgb']==(232,127,230)
                assert q[0][1]['x']<q[3][0]['x'], 'adjacent caster bars overlap'
                assert get(base+0x573c3e,'B')==draw_flag
                put(allocation+0x2000008,'I',0)
                execute('ui_cast_bars');assert not quads(), 'missing sprite must not reuse prior frame'
    # Same-slot recast immediately captures a new total; zero max safely omitted.
    setup();reg('rbx',actors);reg('rdx',240);execute('ui_capture_cast_duration',0x112fff)
    reg('rdx',30);execute('ui_capture_cast_duration',0x112fff)
    assert get(data+0x1108,'I')==30
    for death in [0,2]:
        put(allocation+0x2000008,'I',0);put(actors+0x3c,'H',death)
        capture_anchor(actors)
        execute('ui_cast_bars');assert not quads()
    checks.append('Cast bars: actual sprite projection plus world/HUD coordinate conversion, independent portrait/late-matrix changes, fixed pink 20x2 below feet, two close casters, no stale frame, native timing/hold/KO/recast')

    def draw_item():
        put(allocation+0x2000008,'I',0)
        seen=[]
        def text_stub(rva,rsp):
            if rva==0xb480:
                seen.append(bytes(uc.mem_read(uc.reg_read(regs['rcx']),6)))
                assert get(rsp+0x28,'I')==0x40e00000
        scratch=bytes(uc.mem_read(base+0x11ce620,0xa0))
        gameplay=bytes(uc.mem_read(base+0x12cea40,0x26c0))
        execute('ui_item_bar',stubs=[0xb480],intercept=text_stub)
        assert bytes(uc.mem_read(base+0x11ce620,0xa0))==scratch
        assert bytes(uc.mem_read(base+0x12cea40,0x26c0))==gameplay
        return quads(),seen

    for duration in [26,90]:
        setup();reg('rax',duration);execute('ui_capture_item_cooldown',0xd5adb)
        assert get(base+0x12cea5a,'H')==duration and get(data+0x1200,'H')==duration
        for remaining in [duration,duration//2,4,1,0]:
            put(base+0x12cea5a,'H',remaining)
            q,seen=draw_item()
            if remaining==0:
                assert not q and not seen
                assert get(data+0x1202,'H')==0
            else:
                width=64*(duration-remaining)//duration
                assert len(q)==(3 if width else 2) and seen==[b'OBJET\0']
                assert q[1][0]['x']==208 and q[1][1]['x']==272
                assert q[1][0]['y']==58
                if width:assert q[-1][1]['x']-q[-1][0]['x']==width
            assert get(base+0x12cea5a,'H')==remaining
        # An immediately queued second item must not resurrect the last cooldown.
        put(base+0x12cea5a,'H',4);put(actors+0xbe,'H',1)
        assert draw_item()==([],[])
        # Nor should a pending item with an old display flag survive.
        put(data+0x1202,'H',1)
        assert draw_item()==([],[]) and get(data+0x1202,'H')==0
    for counter in [0,4,90]:
        setup();put(base+0x12cea5a,'H',counter)
        assert draw_item()==([],[]), 'no item execution was captured'
    for restriction in ['scenario','effect']:
        setup();reg('rax',90);execute('ui_capture_item_cooldown',0xd5adb)
        if restriction=='scenario':put(base+0x12d0f02,'B',8)
        else:put(base+0x12d0eb2,'H',100)
        assert draw_item()==([],[])
    setup();reg('rax',90);execute('ui_capture_item_cooldown',0xd5adb)
    put(base+0x12cea5a,'H',45);put(base+0x12ceb7a,'B',1)
    first=draw_item()
    assert first==draw_item() and len(first[0])==3
    put(base+0x12d0ef7,'B',0);execute('ui_frame_guard')
    assert get(data+0x1202,'H')==0 and draw_item()==([],[])
    if 'mod_settings' in manifest['features']:
        setup();reg('rax',90);execute('ui_capture_item_cooldown',0xd5adb)
        put(base+0x12cea5a,'H',45)
        for language in range(16):
            put(base+0x11c9ce8,'B',language)
            q,seen=draw_item()
            assert q and seen[0].split(b'\0')[0]==(b'OBJET' if language==3 else b'ITEM')
        put(data+0x1a06,'B',0)
        assert draw_item()==([],[])
        assert get(base+0x12cea5a,'H')==45
        put(data+0x1a06,'B',1)
    checks.append('Shared item bar: top-center geometry; only actual 26/90-tick recharge is visible; hidden ready/before-use/queued/restricted/outside battle; paused timer unchanged')
    # Execute the native victory-number coordinate calculations for all four
    # HUD slots, both text passes and bounce extremes. Reward value is untouched.
    setup()
    for slot in range(4):
        for bounce in (-12,0,12,24):
            for start,stop in ((0x11a40e,0x11a449),(0x11a45f,0x11a48d)):
                reg('rsi',actors);reg('rdi',23);reg('r14',bounce&0xffffffffffffffff)
                put(actors+0x1a,'B',slot)
                execute(start,stop)
                assert uc.reg_read(regs['rcx'])==23
                assert uc.reg_read(regs['r8'])==220+bounce
                assert uc.reg_read(regs['rdx'])==(slot*48-bounce-8)&0xffffffff
    # Run the actual native number/glyph/quad pipeline, intercepting only
    # texture binding and command dispatch. Compare against the unmodified
    # draw calls via the disabled-HUD option: coordinates, UVs, sizes, colors
    # and both native text passes must be identical, with only Z changed.
    import struct
    for wide in (0,1):
        for slot in range(4):
            for bounce in (-12,0,12,24):
                for amount in (23,9999):
                    outputs=[]
                    for enabled in ((0,1) if 'mod_settings' in manifest['features'] else (1,)):
                        setup()
                        put(data+0x1a04,'B',enabled)
                        put(base+0x573c3e,'B',wide)
                        put(actors+0xc100,'H',0x400 if wide else 0)
                        context=actors+0xc800
                        put(base+0x644a10,'Q',context)
                        put(context+0x4d0,'Q',allocation+0x10000)
                        put(context+0x4d8,'Q',4096)
                        put(context+0x4e0,'I',0)
                        # Native recovery setup at 11a15a/11a166.
                        put(base+0x11ce684,'H',510)
                        put(base+0x11ce680,'I',1)
                        put(base+0x11ce670,'I',0xff80ff80)
                        reg('rsi',actors);reg('rdi',amount)
                        reg('r14',bounce&0xffffffffffffffff);reg('r13',0x59)
                        put(actors+0x1a,'B',slot)
                        gameplay=bytes(uc.mem_read(actors,0x1000))
                        commands=[]
                        def capture_victory(rva,rsp):
                            if rva==0x60bf0:
                                commands.append(bytes(uc.mem_read(uc.reg_read(regs['rdx']),80)))
                        execute(0x11a40e,0x11a492,(0x12b90,0x11ded0,0x60bf0),capture_victory)
                        glyphs=[struct.unpack_from('<5f',c,8) for c in commands
                                if struct.unpack_from('<I',c)[0]==8]
                        assert glyphs, 'native victory glyphs were not submitted'
                        assert all(g[2]==(506 if enabled else 510) for g in glyphs),glyphs
                        assert get(base+0x11ce684,'H')==510, 'depth leaked to subsequent UI'
                        assert bytes(uc.mem_read(actors,0x1000))==gameplay
                        normalized=[]
                        for c in commands:
                            c=bytearray(c)
                            if struct.unpack_from('<I',c)[0]==8:
                                struct.pack_into('<f',c,16,510)
                            normalized.append(bytes(c))
                        outputs.append(normalized)
                    assert outputs[0]==outputs[-1], 'victory rendering changed beyond depth'
    if 'mod_settings' in manifest['features']:
        put(data+0x1a04,'B',1)
    checks.append('Victory TP: original amount/X/Y/bounce and both native glyph passes preserved in all slots/widescreen modes; actual glyph depth 506 in front of gauge depth 507; scratch restored; HUD-off keeps native depth')
    uc.mem_unmap(allocation,0x2001000)
    return checks,count
