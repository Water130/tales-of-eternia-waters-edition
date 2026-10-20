"""Execute injected x64 and native dispatch; stub OS/render boundaries only."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_EFLAGS
from unicorn.x86_const import UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2
import struct

def check_artesphere(u,base,m,actors,sp,reset,put,get,reg,regs):
    sym=m['symbols'];info=m['artesphere'];state=base+info['state_rva']
    profile=base+info['profile_rva'];extra=base+info['extra_rva'];data=base+m['data_rva']
    master=base+0x11ca420;raw=base+0x8c9180;storage=info['storage']
    api=0x61000000;u.mem_map(api,0x1000)
    ui_arena=0x62000000;u.mem_map(ui_arena,0x2001000)
    names={name:api+0x20+i*0x10 for i,name in enumerate((
        'GetPrivateProfileStructW','WritePrivateProfileStructW','GetAsyncKeyState',
        'GetForegroundWindow','GetWindowThreadProcessId','GetCurrentProcessId'))}
    sentinel=base+m['data_rva']-16;count=0;records={};write_fail=False;native_save=True
    held=set();foreground=True;settings={};polls=[];native_edits=False;draws=[];admit=True
    native_inputs=[];executions=[];checks=[];real_input=False;real_mouse=False;row_render=False;key_writes=[];key_save_ok=True;row_text_y=[];trigger_glyphs=[]
    row_commands=[];text_colors=[]
    def string(ptr,wide=False):
        out=bytearray();step=2 if wide else 1
        for i in range(2048):
            b=bytes(u.mem_read(ptr+step*i,step))
            if b==b'\0'*step:return out.decode('utf-16-le' if wide else 'utf-8')
            out.extend(b)
        raise AssertionError('Unterminated string')
    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('alignment',hex(u.reg_read(UC_X86_REG_RIP)),hex(rsp))
        reg('rax',value)
        for r in ('rcx','rdx','r8','r9','r10','r11'):reg(r,0xdead0000)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def stub(emu,address,size,_):
        a=address-base;rcx=u.reg_read(regs['rcx']);rdx=u.reg_read(regs['rdx'])
        r8=u.reg_read(regs['r8']);r9=u.reg_read(regs['r9']);rsp=u.reg_read(UC_X86_REG_RSP)
        if address==api:
            assert string(rcx) in ('kernel32.dll','user32.dll');ret(1)
        elif address==api+0x10:ret(names[string(rdx)])
        elif address in (names['GetPrivateProfileStructW'],names['WritePrivateProfileStructW']):
            assert string(rcx,True)=='Artesphere-v1' and r9==104
            assert string(get(rsp+0x28,'Q'),True).endswith('TalesOfEternia-WatersEdition.ini')
            key=string(rdx,True)
            if address==names['WritePrivateProfileStructW']:
                if not write_fail:records[key]=bytes(u.mem_read(r8,104))
                ret(int(not write_fail))
            else:
                if key in records:u.mem_write(r8,records[key])
                ret(int(key in records))
        elif address==names['GetForegroundWindow']:ret(0x1234)
        elif address==names['GetWindowThreadProcessId']:
            put(rdx,'I',77 if foreground else 88);ret(1)
        elif address==names['GetCurrentProcessId']:ret(77)
        elif address==names['GetAsyncKeyState']:polls.append(rcx);ret(0x8000 if rcx in held else 0)
        elif address==api+0x100:
            assert string(rcx,True)=='ArtesphereControls';ret(settings.get(string(rdx,True),r8)&0xffffffff)
        elif address==api+0x110:
            assert string(rcx,True)=='ArtesphereControls'
            key_writes.append((string(rdx,True),string(r8,True)));ret(int(key_save_ok))
        elif a==0x1a5d0 and not real_mouse:ret()
        elif a in (0x1a0e0,0x46940,0x222790,0x38040):ret()
        elif row_render and a==0xb240:
            u.reg_write(UC_X86_REG_XMM0,0x42200000);ret()
        elif row_render and a==0xb480:
            row_text_y.append(struct.unpack('<f',struct.pack('<I',u.reg_read(UC_X86_REG_XMM2)&0xffffffff))[0]);ret()
        elif row_render and a==0x13410 and u.reg_read(regs['r15'])!=2:ret()
        elif row_render and a==0x12cb0:
            xy=[struct.unpack('<f',(u.reg_read(r)&0xffffffff).to_bytes(4,'little'))[0]
                for r in (UC_X86_REG_XMM1,UC_X86_REG_XMM2)]
            trigger_glyphs.append((rcx,*xy,get(rsp+0x28,'f'),get(rsp+0x38,'f'),get(rsp+0x40,'f')))
            # Execute the real binding, color and quad builders. Stopping here
            # hid the 0x000000ff (alpha zero) regression in the old glyph test.
        elif row_render and a==0x60bf0:
            row_commands.append(bytes(u.mem_read(rdx,80)));ret()
        elif row_render and a in (0x57e80,0x13790,0x13350,0x42570):ret()
        elif a==0x594d0:ret(int(native_save))
        elif a==0x2a41e0:u.mem_write(rcx,bytes(u.mem_read(rdx,r8)));ret(rcx)
        elif a==sym['artesphere_native_input'] and not real_input:
            native_inputs.append(get(master+0x9a,'I'))
            if native_edits:put(master+0x9a,'I',0x4a494847)
            ret(0x72)
        elif a==sym['artesphere_native_draw']:native_inputs.append(get(master+0x9a,'I'));ret()
        elif a in (sym['settings_text'],sym['settings_field']):
            draws.append(string(rcx));text_colors.append((string(rcx),u.reg_read(regs['rax'])&0xffffffff));ret()
        elif a in (0x25aaa0,0x25a090,0x24490,0x21c460,0x21cbb0):ret(100)
        elif a==0x74510:executions.append(('admit',rcx,rdx));ret(int(admit))
        elif a in (0x112d10,0x74730,0x73790):
            executions.append(('execute',rcx,rdx));put(rcx+0x6d,'B',rdx);ret(1)
        elif a==0x1b5ca0:ret()
    hook=u.hook_add(UC_HOOK_CODE,stub)
    def setup():
        reset();u.mem_write(state,b'\0'*0x400);u.mem_write(master,b'\0'*0x1070)
        put(raw,'III',0,0,0)
        put(base+0x2a9058,'Q',api);put(base+0x2a9060,'Q',api+0x10)
        put(data+0x1a10,'BB',1,0);put(data+0x1b08,'Q',api+0x100);put(data+0x1b10,'Q',api+0x110)
        u.mem_write(data+0x3000,('C:\\Local\\TalesOfEternia-WatersEdition.ini\0').encode('utf-16-le'))
        put(base+0x12cea60,'Q',master);put(base+0x12cea78,'Q',base+0x551780)
        for i in range(7):
            u.mem_write(master+i*0xd0+0x7a,bytes(range(43,75)))
            u.mem_write(master+i*0xd0+0x9a,bytes(range(43+i,47+i)))
        for i in range(4):
            put(master+0x8f0+i*2,'H',i+1)
            actor=actors+i*0x248
            put(actor,'Q',actor);put(actor+0xf0,'Q',base+0x12ceba0+i*32)
            put(actor+0x56,'B',i);put(actor+0x52,'B',0);put(actor+0x75,'B',2)
        put(master+0x91c,'BBBB',3,71,4,72)
        put(base+0x111a674,'B',0);put(base+0x1119f96,'HHHH',0,0,0,0)
        put(base+0x111a670,'BBB',0,0,4);put(base+0x1119f88,'6H',32,32,32,32,0,0)
        put(master+0x918,'4B',1,1,1,1);put(base+0x11c9da0,'Q',0)
        put(base+0x1119fa4,'BB',1,255);put(base+0x11c9ce8,'B',1)
        native_inputs.clear();executions.clear();draws.clear();polls.clear()
    def run(name,stops=None,aligned=False):
        nonlocal count
        count+=1;start=sym[name] if isinstance(name,str) else name;rsp=sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp);u.reg_write(UC_X86_REG_EFLAGS,0x202);put(rsp,'Q',sentinel)
        targets={base+x for x in stops} if stops else {sentinel};reached=[]
        def stop(emu,address,size,_):
            if address in targets:reached.append(address);emu.emu_stop()
        h=u.hook_add(UC_HOOK_CODE,stop)
        try:u.emu_start(base+start,sentinel+1,count=500000)
        except Exception as ex:
            raise AssertionError((name,hex(u.reg_read(UC_X86_REG_RIP)-base),{r:hex(u.reg_read(regs[r])) for r in ('rax','rcx','rdx','r8','r9','r10','r13','rbp')})) from ex
        finally:u.hook_del(h)
        assert reached,(name,'no continuation',hex(u.reg_read(UC_X86_REG_RIP)))
        if stops is None:assert u.reg_read(UC_X86_REG_RSP)==rsp+8,(name,'unbalanced stack')
        return reached[0]-base
    try:
        setup();run('artesphere_initialize');native=bytes(u.mem_read(master,0x1070))
        for i in range(7):assert get(profile+i*4,'I')==get(master+i*0xd0+0x9a,'I')
        u.mem_write(profile,bytes([70,71,72,73])*7);put(state+1,'B',1)
        run('artesphere_enter_editor');assert get(master+0x9a,'I')==0x49484746
        run('artesphere_enter_editor');put(master+0x9a,'I',0x4a494847)
        run('artesphere_leave_editor');assert get(master+0x9a,'I')==0x4a494847
        run('artesphere_leave_editor');assert bytes(u.mem_read(master,0x1070))==native
        assert get(profile,'I')==0x4a494847 and get(state+2,'B')==0
        checks.append('Nested native editor scopes restore A and retain B edits')
        for char in range(7):
            for slot in range(4):
                for held_page in (0,0x40000):
                    setup();run('artesphere_initialize');put(profile+char*4+slot,'B',74)
                    put(raw,'I',held_page);put(actors+0x4f,'B',char);put(actors+0xac+slot,'B',43)
                    reg('rbp',actors);reg('rax',0xac+slot);run(0x114292,[0x114298],True)
                    assert u.reg_read(regs['rbx'])==(74 if held_page else 43)
        for arte,controller,expected in [(255,0,0),(74,1,43),(0,0,0)]:
            setup();put(profile,'B',arte);put(actors+0xac,'B',43);put(actors+0x56,'B',controller)
            put(raw,'I',0x40000);reg('rax',0xac);reg('rbp',actors)
            run(0x114292,[0x114298],True);assert u.reg_read(regs['rbx'])==expected
        for entry in (0x1141c5,0x1141dc):
            reg('rbx',52);run(entry,[0x114298],True);assert u.reg_read(regs['rbx'])==52
        checks.append('56 direction/page cases, invalid IDs, other controllers and native combo branches')
        for page in (0,1):
            for edge in (0,0x80000):
                setup();run('artesphere_initialize');put(extra+page*2,'BB',3,71+page)
                put(raw,'II',page*0x40000,edge);reg('rcx',actors);run(0x113370)
                assert bool(executions)==bool(edge)
                if edge:
                    assert executions[-1][1:]==(actors+2*0x248,71+page)
                    assert get(actors+2*0x248+0xa4,'H')==0x100
        for owner_id,arte,allowed in ((7,71,True),(3,250,True),(3,71,False),(0,0,True)):
            setup();put(extra,'BB',owner_id,arte);put(raw+4,'I',0x80000)
            reg('rcx',actors);admit=allowed;run(0x113370)
            assert not [x for x in executions if x[0]=='execute']
        admit=True
        for page in (0,1):
            for slot in (0,1):
                setup();run('artesphere_initialize');put(profile+28+slot*2,'BB',slot+3,73+slot)
                put(raw,'I',page*0x40000);put(base+0x12ceba0,'I',0x400<<slot);reg('rcx',actors)
                run(0x113370);assert executions[-1][2]==(73+slot if page else 71+slot)
        checks.append('Native dispatcher: R2 edge, both pages, ally slots, absent/unlearned casters and admission refusal')
        setup();run('artesphere_initialize');native=bytes(u.mem_read(master,0x1070))
        put(raw+4,'I',0x40000);run(0x228ad0);assert get(state+1,'B')==1 and not native_inputs
        native_edits=True;put(raw+4,'I',0);run(0x228ad0);native_edits=False
        assert get(profile,'I')==0x4a494847 and bytes(u.mem_read(master,0x1070))==native
        put(raw+4,'I',0x80000);run(0x228ad0)
        assert get(base+0x1119f98,'H')==2 and get(base+0x1119f9a,'H')==6
        assert get(state+3,'B')==0, 'old modal must never open'
        native=bytes(u.mem_read(master,0x1070))
        for palette,letter,color in ((0,'A',0xffffad61),(1,'B',0xff6666ff)):
            for language in (3,1,0):
                put(state+1,'B',palette);put(base+0x11c9ce8,'B',language)
                draws.clear();text_colors.clear();run(0x224920)
                expected=f'Artesphere — Page {letter}'
                assert expected in draws and (expected,color) in text_colors
                assert bytes(u.mem_read(master,0x1070))==native
        # Execute the actual native input state machine, including seven-row
        # navigation, character chooser, learned list, commit and clear.
        real_input=True
        for palette in (0,1):
            setup();put(state+1,'B',palette)
            put(base+0x1119f98,'HH',2,5);put(raw+8,'I',0x40)
            run(0x228ad0);assert get(base+0x1119f9a,'H')==6
            put(raw,'III',0,0x2000,0);run(0x228ad0)
            assert get(base+0x1119f98,'H')==7, 'native caster chooser'
            put(raw,'III',0,0x2000,0);run(0x228ad0)
            assert get(base+0x1119f98,'H')==8, 'native learned-arte list'
            put(base+0x1119f9c,'H',2)
            before=bytes(u.mem_read(master+0x91c,16))
            put(raw,'III',0,0x2000,0);run(0x228ad0)
            assert get(base+0x1119f98,'H')==2
            assert get(extra+palette*2,'H')==0x2d01
            assert bytes(u.mem_read(master+0x91c,16))==before, 'seventh row overwrote a vanilla shortcut'
            put(raw,'III',0,0,0x1000);run(0x228ad0)
            assert get(extra+palette*2,'H')==0
        real_input=False
        checks.append('Native seven-row navigation/caster chooser/learned list/assignment/clear; scoped A/B storage; Artesphere header without accent, page A blue and page B red in FR/EN')
        # Real native hit testing and left-row callback, with only OS polling
        # stubbed. The temporary descriptor is restored byte for byte.
        setup();real_mouse=True
        put(base+0x86241c,'I',1)
        u.mem_write(base+0x860560,b'\0'*56)
        unused=bytes(range(56));u.mem_write(base+0x860598,unused)
        put(state+0xcc0,'8f',20,172,180,20,0,0,0,0)
        put(base+0x862460,'IIBBBBf',40,180,1,1,0,0,0)
        put(base+0x573c58,'i',-1)
        for expected in (0x10000000,0x2000):
            reg('rcx',state+0xf00);reg('rdx',state+0xf04);reg('r8',1)
            run('artesphere_native_mouse')
            assert u.reg_read(regs['rax'])==expected
            assert get(base+0x1119f98,'H')==2 and get(base+0x1119f9a,'H')==6
            assert get(base+0x86241c,'I')==1
            assert bytes(u.mem_read(base+0x860598,56))==unused
        put(base+0x86241c,'I',128)
        u.mem_write(base+0x860560,b'\0'*(128*56))
        reg('rcx',state+0xf00);reg('rdx',state+0xf04);reg('r8',1)
        run('artesphere_native_mouse')
        assert get(base+0x86241c,'I')==128
        real_mouse=False
        checks.append('Native mouse hit testing selects/confirms row seven; temporary descriptor restored; bounded capacity')
        for opacity in (255,128,0):
            setup();put(extra,'H',0x2d01);run('artesphere_prepare_rows')
            row_render=True;row_text_y.clear();row_commands.clear();trigger_glyphs.clear()
            context=actors+0x3000
            put(base+0x644a10,'Q',context)
            put(context+0x4d0,'Q',ui_arena+0x1000)
            put(context+0x4d8,'Q',128);put(context+0x4e0,'I',0)
            put(context+0x548,'Q',ui_arena+0x9000)
            put(base+0x86191a,'B',0)
            put(base+0x644a70,'Q',0);put(base+0x6449f8,'Q',actors);put(actors+0x10,'I',0)
            u.mem_write(base+0x8606e8,b'\x42'*56)
            reg('rsi',0);put(sp-8+0x60,'B',opacity);put(sp-8+0x70,'I',0)
            run(0x225684,[0x225a71],True)
            assert row_text_y==[132.,142.5,152.,162.5,172.,182.5],row_text_y
            assert [get(p,'f') for p in (base+0x86067c,base+0x8606b4,state+0xcc4)]==[132.,152.,172.]
            assert bytes(u.mem_read(base+0x8606e8,56))==b'\x42'*56
            assert '/' in draws and u.reg_read(regs['r15'])==3
            assert [(family,x,y,size) for family,x,y,size,_,_ in trigger_glyphs]==[(0,31.,174.,12.),(4,47.,174.,12.)],trigger_glyphs
            assert all(u0==252/512 and v0==168/512 for *_,u0,v0 in trigger_glyphs),trigger_glyphs
            # Inspect the actual deferred render commands, including the RGBA
            # active at each quad, the two controller atlases and their UVs.
            color=None;atlas=None;quads=[]
            for command in row_commands:
                op=struct.unpack_from('<I',command)[0]
                if op==0x14:color=tuple(command[8:12])
                elif op==0x22:
                    assert struct.unpack_from('<Q',command,8)[0]==ui_arena+0x9000
                    atlas=struct.unpack_from('<I',command,24)[0]
                elif op==0xc:
                    assert struct.unpack_from('<4f',command,8)==(84/512,84/512,12.,12.)
                elif op==8:
                    quads.append((atlas,color,struct.unpack_from('<5f',command,8)))
            assert quads==[(atlas,(255,255,255,opacity),(x,174.,0.,252/512,168/512))
                           for atlas,x in ((0,31.),(4,47.))],('invisible/tinted button quad',quads)
            assert get(base+0x86191a,'B')==0,'native glyph mode must be restored'
        put(base+0x644a10,'Q',0)
        row_render=False
        checks.append('Native renderer emits all three shortcut rows at compact coordinates without overwriting the learned-list hitbox')
        checks.append('R2/RT native RGBA, atlas binding and quads: opaque white when open, matching menu fade at half/zero opacity')
        # Execute each native description/icon reader for all party slots.
        # Different sentinel pairs catch both the old 4-byte stride and row-7
        # reads leaking into the next character's vanilla bindings.
        setup()
        for party in range(4):
            for row in range(4,7):
                caster=party+1;arte=43+party*3+row-4
                put(state+0xc00+party*8+(row-4)*2,'BB',caster,arte)
        for party in range(4):
            for row in range(4,7):
                arte=43+party*3+row-4
                put(base+0x1119f9a,'H',row);reg('rdi',base);reg('r14',party)
                run(0x226c9a,[0x226cfb],True)
                assert u.reg_read(regs['rbp'])==arte
                assert u.reg_read(regs['r15'])==party
                put(sp-8+0x70,'I',party);reg('rdi',base)
                run(0x227870,[0x22788a],True)
                assert u.reg_read(regs['rax'])==arte
                reg('rcx',party);reg('r8',row);reg('r12',base)
                run(0x22813d,[0x22814a],True)
                assert u.reg_read(regs['rcx'])==arte
        # Native hand applies +16 after these row-coordinate calculations.
        for row in range(7):
            put(base+0x1119f9a,'H',row)
            expected=14*row+62 if row<4 else 20*row+41
            run(0x226394,[0x226367],True)
            assert u.reg_read(regs['r8'])==expected
            run(0x2263c4,[0x2263e0],True)
            assert u.reg_read(regs['rcx'])&0xffff==expected
        checks.append('Native description/icon readers address all 7 rows per party; active and dim cursor share compact row coordinates')
        for custom in ({},{'PageKey':65,'ShortcutKey':66},{'PageKey':0,'ShortcutKey':999},{'PageKey':65,'ShortcutKey':65}):
            setup();settings=custom;expected=(65,66) if custom.get('ShortcutKey')==66 else (118,119)
            held=set(expected);foreground=True;run('artesphere_keyboard')
            assert get(raw,'I')==0xc0000 and get(raw+4,'I')==0xc0000 and polls==list(expected)
            put(raw,'III',0x100,0,0);run('artesphere_keyboard')
            assert get(raw,'I')==0xc0100 and get(raw+4,'I')==0
            foreground=False;put(raw,'III',0,0,0);run('artesphere_keyboard');assert get(raw,'I')==0
            foreground=True;held=set();run('artesphere_keyboard');assert get(raw,'I')==0
        checks.append('Configurable keyboard defaults/custom/invalid/duplicate keys, focus, held and edges')
        setup();settings={};held=set();foreground=True;run('artesphere_keyboard')
        keyui=info['keyboard']['ui'];cap=base+keyui['capture_rva'];err=base+keyui['error_rva']
        put(data+0x1a11,'B',2)
        # A held confirm key cannot bind itself. Wait for release before capture.
        held={13};put(raw+4,'I',0x2000);run('artesphere_keys_input');assert get(cap,'B')==1
        run('artesphere_keys_input');assert get(cap,'B')==1
        held=set();put(raw+4,'I',0);run('artesphere_keys_input');assert get(cap,'B')==2
        held={65};run('artesphere_keys_input');assert get(base+info['keyboard']['keys_rva'],'I')==65
        assert key_writes[-1]==('PageKey','65') and get(cap,'B')==0
        # Same-key conflict, Escape cancel, failed writes and focus loss.
        for key,fail,focus in [(119,False,True),(27,False,True),(66,True,True),(67,False,False)]:
            put(cap,'B',2);put(err,'B',0);held={key};key_save_ok=not fail;foreground=focus
            run('artesphere_keys_input');assert get(base+info['keyboard']['keys_rva'],'I')==65
            assert get(err,'B')==(1 if key==119 else 2 if fail else 0)
        key_save_ok=True;foreground=True;held=set();put(cap,'B',0)
        for key,label in [(65,'A'),(118,'F7'),(135,'F24'),(32,'Space'),(186,'VK# 186')]:
            reg('rcx',key);run('artesphere_key_name');assert string(u.reg_read(regs['rax']))==label
        put(base+0x644a10,'Q',actors+0x3000)
        put(actors+0x3000+0x4d0,'Q',ui_arena+0x1000)
        put(actors+0x3000+0x4d8,'Q',1024);put(actors+0x3000+0x4e0,'I',0)
        put(base+0x644a58,'Q',ui_arena);put(ui_arena+0x2000008,'I',0)
        put(base+0x11c9e18,'Q',ui_arena+0x9000)
        draws.clear();run('settings_draw')
        assert 'Keyboard controls (PC)' in draws
        held={65};put(raw,'III',0,0,0);run('artesphere_keyboard');assert get(raw,'I')==0
        put(data+0x1a11,'B',1);put(base+m['mod_settings']['selection_rva'],'B',len(m['mod_settings']['features'])+1)
        reg('rsi',0x2000);reg('r13',0)
        run('settings_panel_input',[0x1b98d7],True);assert get(data+0x1a11,'B')==2
        put(raw+4,'I',0x4000);reg('rsi',0x4000)
        run('settings_panel_input',[0x1b98d7],True);assert get(data+0x1a11,'B')==1
        put(base+0x644a10,'Q',0);draws.clear();run('artesphere_keys_draw');assert not draws
        checks.append('In-game binding capture: release gating, persistence, duplicate/cancel/write failure/focus, key names, alias suppression')

        setup();savebuf=actors+0x9000;u.mem_write(savebuf,bytes((i%251 for i in range(0x12d4))))
        for slot in (0,1,20):
            u.mem_write(profile,bytes([slot+1])*96)
            reg('rcx',1);reg('rdx',slot);reg('r8',savebuf);reg('r9',profile)
            run('artesphere_storage_io');assert u.reg_read(regs['rax'])==1
        for slot in (0,1,20):
            u.mem_write(profile,b'\0'*96)
            reg('rcx',0);reg('rdx',slot);reg('r8',savebuf);reg('r9',profile)
            run('artesphere_storage_io');assert bytes(u.mem_read(profile,96))==bytes([slot+1])*96
        before=bytes(u.mem_read(profile,96));put(savebuf,'B',255)
        reg('rcx',0);reg('rdx',0);reg('r8',savebuf);reg('r9',profile)
        run('artesphere_storage_io');assert u.reg_read(regs['rax'])==0 and bytes(u.mem_read(profile,96))==before
        put(savebuf,'B',0);old_record=records['Slot00'];write_fail=True
        reg('rcx',1);reg('rdx',0);reg('r8',savebuf);reg('r9',profile)
        run('artesphere_storage_io');assert u.reg_read(regs['rax'])==0 and records['Slot00']==old_record
        write_fail=False
        run('artesphere_initialize');run('artesphere_save_snapshot',[0x24db28],True)
        snap=bytes(u.mem_read(base+storage['snapshot_rva'],96))
        reg('r12',2);reg('rsi',0x12d4);reg('rbp',actors)
        run('artesphere_queue_profile',[0x3f3a8],True)
        # A later serialization must not alter an already queued profile.
        u.mem_write(base+storage['snapshot_rva'],b'\x77'*96)
        for success in (False,True):
            native_save=success;reg('r12',2);reg('r15',savebuf);put(sp-8+0x50,'Q',0x12d4)
            run('artesphere_save_site',[0x3fce0],True)
            assert u.reg_read(regs['rax'])==int(success) and ('Slot02' in records)==success
        assert records['Slot02'][8:]==snap
        target=actors+0xb000;reg('rcx',target);reg('rdx',savebuf);reg('r8',0x12d4)
        reg('r12',0);reg('r14',0x12d4);reg('r15',target);reg('rbx',savebuf)
        run('artesphere_read_stage',[0x40172],True)
        assert bytes(u.mem_read(profile,96))==snap and get(base+storage['pending_valid_rva'],'B')==1
        reg('rcx',target);run('artesphere_import_profile',[0x24db46])
        assert bytes(u.mem_read(profile,96))==bytes([1])*96 and get(state,'B')==1
        reg('rcx',target);run('artesphere_import_profile',[0x24db46])
        assert bytes(u.mem_read(profile,96))==b'\0'*96 and get(state,'B')==0
        reg('rcx',master);reg('rdx',actors+0xe000);reg('r8',0x100)
        run('artesphere_new_game',[0x258f96],True)
        assert get(state,'I')==0 and bytes(u.mem_read(profile,96))==b'\0'*96
        checks.append('Per-slot records, native snapshot matching, failed writes, successful save boundary, previews, load fallback and new-game reset')
    finally:
        u.hook_del(hook);u.mem_unmap(api,0x1000);u.mem_unmap(ui_arena,0x2001000)
    return count,checks
