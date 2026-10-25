"""Execute settings x64, stub only renderer/OS APIs, test actual hook dispatch."""
import struct
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

def check_settings(u,base,m,actors,enemies,stats,sp,reset,put,get,reg,regs):
    sp-=0x1000  # Native title epilogue references its 0x200-byte stack frame.
    info=m['mod_settings'];sym=m['symbols'];data=base+m['data_rva']
    feature_count=len(info['features'])
    category=base+info['category_state_rva'];first=info['category_first']
    from mod_settings_patch import FEATURES, CATEGORIES, DEFAULTS, GROUPS, HIDDEN
    def grouped(values):
        out=bytearray(values)
        for master,members in GROUPS.items():
            for member in members:out[member]=out[master]
        return bytes(out)
    menus=[list(range(first,first+len(CATEGORIES)))+[feature_count]]+[ids for _,_,ids in CATEGORIES]
    def focus(logical):
        put(category,'B',0 if logical>=feature_count+2 or logical==feature_count else next(i for i,items in enumerate(menus[1:],1) if logical in items))
        put(selected,'B',logical)
    label_map={i:fr for i,(_,fr,_) in enumerate(FEATURES)}
    label_map[feature_count+1]='Commandes clavier (PC)'
    label_map.update({first+i:fr for i,(fr,_,_) in enumerate(CATEGORIES)})
    row_step=info['row_step'];visible=info['visible_rows'];scroll=base+info['scroll_top_rva']
    flags=base+info['flags_rva'];page=base+info['page_rva'];selected=base+info['selection_rva']
    initialized=base+info['initialized_rva'];error=base+info['error_rva']
    def read_flags():return bytes(get(base+r,'B') for r in info['flag_rvas'])
    def write_flags(values):
        for r,v in zip(info['flag_rvas'],values):put(base+r,'B',v)
    def read_snapshot():return bytes(get(base+r,'B') for r in info['snapshot_rvas'])
    def write_snapshot(values):
        for r,v in zip(info['snapshot_rvas'],values):put(base+r,'B',v)
    sentinel=m['data_rva']-16;api=0x60000000
    u.mem_map(api,0x1000)
    names={'GetEnvironmentVariableW':api+0x20,'GetPrivateProfileIntW':api+0x30,'WritePrivateProfileStringW':api+0x40}
    put(base+0x2a9058,'Q',api);put(base+0x2a9060,'Q',api+0x10)
    values={};reads=[];writes=[];texts=[];rects=[];fail_write=False;fail_key=None;missing=None;environment='C:\\Users\\Élodie\\AppData\\Local'
    count=0;real_rect=False;real_font=False;mouse_calls=[];allocation=0x40000000
    submitted=[];native_draws=[];brands=[];cursors=[];hint_buttons=[];input_device=0
    u.mem_map(allocation,0x2401000)
    vertex_pool=allocation+0x300000
    def cstring(p,wide=False):
        out=bytearray();stride=2 if wide else 1
        for i in range(2048):
            chunk=bytes(u.mem_read(p+i*stride,stride))
            if chunk==b'\0'*stride:return out.decode('utf-16-le' if wide else 'utf-8')
            out.extend(chunk)
        raise AssertionError('Unterminated string')
    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('ABI',hex(u.reg_read(UC_X86_REG_RIP)),hex(rsp))
        u.reg_write(UC_X86_REG_RAX,value)
        # Real Windows calls may clobber all volatile registers.
        for name in ('rcx','rdx','r8','r9','r10','r11'):reg(name,0xdead0000)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    def callback(emu,a,size,_):
        rcx=u.reg_read(regs['rcx']);rdx=u.reg_read(regs['rdx']);r8=u.reg_read(regs['r8']);r9=u.reg_read(regs['r9'])
        rsp=u.reg_read(UC_X86_REG_RSP)
        if a==api:assert cstring(rcx)=='kernel32.dll';ret(123)
        elif a==api+0x10:
            name=cstring(rdx);ret(0 if name==missing else names[name])
        elif a==api+0x20:
            assert cstring(rcx,True)=='LOCALAPPDATA'
            if len(environment)<r8:u.mem_write(rdx,(environment+'\0').encode('utf-16-le'))
            ret(len(environment))
        elif a==api+0x30:
            key=cstring(rdx,True);assert cstring(rcx,True)=='Features'
            assert cstring(r9,True)==environment+'\\TalesOfEternia-WatersEdition.ini'
            reads.append(key);ret(values.get(key,r8)&0xffffffff)
        elif a==api+0x40:
            key=cstring(rdx,True);value=cstring(r8,True)
            assert cstring(rcx,True)=='Features' and value in ('0','1')
            assert cstring(r9,True)==environment+'\\TalesOfEternia-WatersEdition.ini'
            writes.append((key,value))
            failed=fail_write or key==fail_key
            if not failed:values[key]=int(value)
            ret(0 if failed else 1)
        elif a==api+0x50:ret(input_device) # Platform's current input family only.
        elif a==base+0x12cb0:
            hint_buttons.append((rcx,get(rsp+0x28,'f'),get(rsp+0x38,'f'),get(rsp+0x40,'f')))
            ret() # Texture resource draw boundary; native glyph choice ran.
        elif a==base+0xb240 and not real_font:
            s=cstring(rcx);f=struct.unpack('<f',u.reg_read(UC_X86_REG_XMM1).to_bytes(16,'little')[:4])[0]
            width=len(s)*f/2
            ret();u.reg_write(UC_X86_REG_XMM0,struct.unpack('<I',struct.pack('<f',width))[0])
        elif a==base+0xb480:
            xy=[struct.unpack('<f',u.reg_read(r).to_bytes(16,'little')[:4])[0] for r in (UC_X86_REG_XMM1,UC_X86_REG_XMM2)]
            texts.append(dict(text=cstring(rcx),x=xy[0],y=xy[1],color=get(rsp+0x30,'I'),size=get(rsp+0x28,'f')))
            if not real_font:ret()
        elif a==base+0x6a320:ret(123) # Native UI atlas lookup, not window drawing.
        elif a==base+0x52f10:
            # Font-provider boundary only. Execute b240/b480/acb0/a9b0 fully.
            u.mem_write(r9,b'\0'*0x70)
            put(r9,'fffff',6.0,12.0,0.0,0.0,7.0)
            ret()
        elif a==base+0x1a5d0:
            mouse_calls.append(True);ret(0x10000000)
        elif a==base+sym['title_logo_draw']:brands.append(True);ret(1)
        elif a==base+0x250b50:
            cursors.append((rcx,rdx,r8,r9))
            if not real_rect:ret()
        elif a==base+0x60bf0:submitted.append(rdx);ret()
        elif a==base+0x62010:native_draws.append((rdx,r8,r9,get(rsp+0x28,'Q'),get(rsp+0x30,'Q')));ret()
        elif a==base+sym['settings_backdrop'] and not real_rect:
            rects.append(True);ret()
    h=u.hook_add(UC_HOOK_CODE,callback)
    def setup():
        reset();put(base+0x8c9180,'III',0,0,0);write_flags(bytes(DEFAULTS));u.mem_write(initialized,b'\0'*16)
        put(base+0x644a18,'Q',0);put(base+0x11c9ce8,'H',0x103)
        put(base+0x10e1d3c,'H',0);put(base+0x11cc540,'Q',0)
        put(base+0x644a10,'Q',0)
        put(base+0x644a58,'Q',0);put(base+0x644a20,'Q',0);put(base+0x11c9e18,'Q',0)
        put(base+0x6449f8,'Q',0);put(base+0x86191f,'B',0)
        submitted.clear();native_draws.clear();brands.clear()
        cursors.clear();hint_buttons.clear()
        reads.clear();writes.clear();texts.clear();rects.clear()
    def run(name,stops=(),mid=False):
        nonlocal count
        count+=1;entry=sp-8 if mid else sp
        u.reg_write(UC_X86_REG_RSP,entry);put(entry,'Q',base+sentinel)
        reached=[];targets={base+s for s in stops} if stops else {base+sentinel}
        def stop(_,a,size,user):
            if a in targets:reached.append(a-base);u.emu_stop()
        hh=u.hook_add(UC_HOOK_CODE,stop)
        # Earlier suites execute some native blocks without this stop hook.
        # Invalidate those cached translations so their newly observed internal
        # instruction boundaries are dispatched to the callback as well.
        for target in targets:u.ctl_remove_cache(target-16,target+16)
        try:u.emu_start(base+sym.get(name,name) if isinstance(name,int) else base+sym[name],base+m['data_rva'],count=1000000 if real_font else 100000)
        except Exception as exc:
            raise AssertionError((name,hex(u.reg_read(UC_X86_REG_RIP)-base),str(exc))) from exc
        finally:u.hook_del(hh)
        assert reached,(name,'no continuation',hex(u.reg_read(UC_X86_REG_RIP)-base))
        assert u.reg_read(UC_X86_REG_RSP)==entry+(0 if mid else 8),(name,'stack')
        return reached[0]
    try:
        # Existing/missing settings, Unicode path, bounds, idempotent loading.
        setup();run('settings_initialize');assert read_flags()==bytes(DEFAULTS) and len(reads)==feature_count
        assert get(initialized,'B')==1 and get(error,'B')==0
        run('settings_initialize');assert len(reads)==feature_count
        values={k:0 for i,k in enumerate(info['features']) if i!=33};setup();run('settings_initialize')
        assert read_flags()==b'\0'*feature_count, 'missing Craymel EXP member must follow its saved master'
        values={k:0 for k in info['features'][:34]};setup();run('settings_initialize')
        assert read_flags()==b'\0'*34+bytes(DEFAULTS[34:]), 'new independent options retain their default during migration'
        values={k:i%2 for i,k in enumerate(info['features'][:10])};setup();run('settings_initialize')
        assert read_flags()==bytes(i%2 for i in range(10))+bytes(DEFAULTS[10:]), 'both new control options migrate without resetting old preferences'
        values={k:i%2 for i,k in enumerate(info['features'])};setup();run('settings_initialize')
        assert read_flags()==grouped(i%2 for i in range(feature_count))
        # Conflicting old INI keys cannot leave a partially enabled group. Only
        # the saved master controls the group; unrelated controls stay intact.
        for master,members in GROUPS.items():
            for enabled in (0,1):
                values={k:DEFAULTS[i] for i,k in enumerate(info['features'])}
                for member in members:values[info['features'][member]]=1-enabled
                values[info['features'][master]]=enabled
                setup();run('settings_initialize')
                expected=bytearray(DEFAULTS)
                for member in members:expected[member]=enabled
                assert read_flags()==bytes(expected)
        for missing in names:
            setup();run('settings_initialize');assert get(initialized,'B')==2 and get(error,'B')==1
            assert read_flags()==bytes(DEFAULTS)
        missing=None;saved_env=environment
        for environment in ('','x'*960,'x'*1024):
            setup();run('settings_initialize');assert get(initialized,'B')==2 and not reads
        environment=saved_env
        # The final flag is beyond the first snapshot qword: make it nonzero,
        # so omitting its copy on opening cannot pass by matching zeroed memory.
        values[info['features'][-1]]=1
        # Native menu count is 4 or 5; preserve all native actions/submenus.
        for extra in (0,2):
            total=5+extra//2
            for cursor in range(total):
                for button,delta in ((0x10,-1),(0x40,1),(0,0)):
                    setup();put(base+0x11cc540,'Q',extra);put(base+0xbb1c64,'H',cursor)
                    reg('r13',button);reg('rsi',0)
                    end=run('settings_title_navigation',(0x1b9417,0x1b98d7,0x1b92bf),True)
                    assert end==0x1b9417 and get(base+0xbb1c64,'H')==(cursor+delta)%total
                setup();put(base+0x11cc540,'Q',extra);put(base+0xbb1c64,'H',cursor)
                reg('r13',0);reg('rsi',0x2000)
                end=run('settings_title_navigation',(0x1b9417,0x1b98d7),True)
                assert (end==0x1b98d7)==(cursor==total-1)
                assert get(page,'B')==int(cursor==total-1)
                if cursor==total-1:
                    assert read_snapshot() == read_flags(), 'opening snapshot includes every option'
        for submenu in (10,20,30,40):
            setup();put(base+0x10e1d3c,'H',submenu)
            assert run('settings_title_navigation',(0x1b92bf,),True)==0x1b92bf
        # One press changes exactly its group. Hidden children cannot be
        # selected, and every persisted member matches its master.
        setup();run('settings_initialize');put(page,'B',1)
        for i,key in enumerate(info['features']):
            if i in HIDDEN:continue
            for button in (0x2000,0x20,0x80):
                before=read_flags();focus(i);start=len(writes)
                reg('rsi',button);reg('r13',0)
                run('settings_panel_input',(0x1b98d7,),True)
                after=bytearray(before);after[i]^=1
                after=grouped(after)
                assert read_flags()==after
                assert writes[start:]==[(info['features'][j],str(after[j])) for j in GROUPS.get(i,(i,))]
                assert get(selected,'B')==i,'saving members moved the visible selection'
                assert all(values[info['features'][j]]==after[j] for j in GROUPS.get(i,(i,)))
        # A failure in an intermediate member must not disappear when the
        # remaining writes succeed. Reload restores the group from its master.
        for master,members in GROUPS.items():
            focus(master);fail_key=info['features'][members[1]]
            reg('rsi',0x2000);reg('r13',0)
            run('settings_panel_input',(0x1b98d7,),True)
            assert get(error,'B')==1
            before=read_flags();fail_key=None
            put(initialized,'B',0);run('settings_initialize')
            assert read_flags()==before and get(error,'B')==0
        fail_write=True;reg('rsi',0x2000);reg('r13',0)
        run('settings_panel_input',(0x1b98d7,),True);assert get(error,'B')==1
        fail_write=False
        for cat,order in enumerate(menus):
            put(category,'B',cat)
            for cursor in order:
                for button,delta in ((0x10,-1),(0x40,1)):
                    before=read_flags();put(selected,'B',cursor);reg('rsi',0);reg('r13',button)
                    run('settings_panel_input',(0x1b98d7,),True)
                    assert get(selected,'B')==order[(order.index(cursor)+delta)%len(order)]
                    assert read_flags()==before
        # Right-stick scroll consumes mirrored navigation; the left stick
        # and physical D-pad still select settings. Back works while held.
        for row in (12,17):
            setup();put(initialized,'B',1);put(page,'B',1);focus(row)
            before=read_flags();offset=base+m['progression_ui']['help_state_rva']+2
            put(base+0x8c9180,'III',0x02000040,0,0x02000040)
            reg('rsi',0);reg('r13',0x40)
            run('settings_panel_input',(0x1b98d7,),True)
            assert get(selected,'B')==row and get(offset,'H')==1,(row,get(selected,'B'),get(offset,'H'))
            assert read_flags()==before and not writes
            put(base+0x8c9188,'I',0);run('settings_panel_input',(0x1b98d7,),True)
            assert get(selected,'B')==row and get(offset,'H')==1,(row,get(selected,'B'),get(offset,'H'))
            put(base+0x8c9180,'III',0x40,0,0x40)
            reg('rsi',0);reg('r13',0x40);run('settings_panel_input',(0x1b98d7,),True)
            assert get(selected,'B')!=row and read_flags()==before
            run('settings_description_input');assert get(offset,'H')==0
            focus(row);put(base+0x8c9180,'III',0x02000040,0,0x02000040)
            reg('rsi',0x4000);run('settings_panel_input',(0x1b98d7,),True)
            assert get(category,'B')==0 and read_flags()==before
        setup();run('settings_initialize');put(page,'B',1)
        # Opening and leaving a category preserves settings and the initial snapshot.
        for cat in range(1,len(menus)):
            focus(first+cat-1);before=read_flags();saved=read_snapshot();n=len(writes)
            reg('rsi',0x2000);reg('r13',0);run('settings_panel_input',(0x1b98d7,),True)
            assert get(category,'B')==cat and get(selected,'B')==menus[cat][0]
            reg('rsi',0x4000);run('settings_panel_input',(0x1b98d7,),True)
            assert get(page,'B')==1 and get(category,'B')==0 and get(selected,'B')==first+cat-1
            assert read_flags()==before and read_snapshot()==saved and len(writes)==n
        # Header reset restores the values captured on opening; defaults turn
        # all features on. Both persist each key without touching saves.
        snapshot=base+info['snapshot_rva'];choice=base+info['reset_choice_rva']
        write_snapshot(grouped(i%2 for i in range(feature_count)))
        for default in (0,1):
            focus(feature_count);put(choice,'B',default);reg('rsi',0x2000);reg('r13',0)
            run('settings_panel_input',(0x1b98d7,),True)
            assert read_flags()==(bytes(DEFAULTS) if default else read_snapshot())
            assert get(selected,'B')==feature_count and get(error,'B')==0
            assert [key for key,_ in writes[-feature_count:]]==info['features']
            assert bytes(values[key] for key in info['features'])==read_flags()
            saved=read_flags();put(initialized,'B',0);run('settings_initialize')
            assert read_flags()==saved,'reset changed after reloading the INI'
        for button in (0x4000,8):
            put(page,'B',1);reg('rsi',button);reg('r13',0)
            run('settings_panel_input',(0x1b98d7,),True);assert get(page,'B')==0
        for opened in (0,1):
            setup();mouse_calls.clear();put(page,'B',opened)
            run('settings_title_mouse_poll',(0x1b8f9a,),True)
            assert len(mouse_calls)==1-opened
            assert u.reg_read(regs['rax'])==(0 if opened else 0x10000000)
        # All non-French text languages, independently of voice language.
        for lang in range(16):
            for voice in (0,1):
                setup();put(initialized,'B',1);put(base+0x11c9ce8,'BB',lang,voice)
                put(base+0xbb1c64,'H',4);run('settings_draw')
                assert len(texts)==1
                assert texts[0]['text']==('Options de mods' if lang==3 else 'Mod settings')
                assert texts[0]['color']==0xff51ff4b and texts[0]['y']==224
                texts.clear();put(page,'B',1);focus(first);run('settings_draw')
                strings=[t['text'] for t in texts]
                for fr,en,_ in CATEGORIES:assert (fr if lang==3 else en) in strings
                assert len(texts)>6+2*len(CATEGORIES) and rects
                assert all(25<t['x']<455 and 26<=t['y']<=236 for t in texts)
                labels=[t for t in texts if t['y'] in range(55,55+row_step*visible,row_step) and t['x']==34]
                assert len(labels)==len(CATEGORIES) and all(t['size']==8.5 and t['color']==0xff49bfff for t in labels)
                assert cursors[-1]==(1,55,43,2)
        # Mid-function wrapper must restore live volatile registers/XMM values.
        setup();put(initialized,'B',1);put(base+0x10e1d3c,'H',20)
        before={r:u.reg_read(v) for r,v in regs.items() if r!='rcx'}
        xmms={r:0xdeadbeef1234567890+i for i,r in enumerate(range(UC_X86_REG_XMM0,UC_X86_REG_XMM5+1))}
        for r,v in xmms.items():u.reg_write(r,v)
        run('settings_title_render',(0x1ba980,),True)
        assert before=={r:u.reg_read(regs[r]) for r in before}
        assert all(u.reg_read(r)==v for r,v in xmms.items())
        # Early hook must not draw the page or skip native R12 preservation.
        put(page,'B',1);texts.clear();rects.clear()
        run(0x1ba979,(0x1ba980,),True)
        assert not texts and not rects
        before={r:u.reg_read(v) for r,v in regs.items() if r!='rcx'}
        put(sp-8+0x170,'Q',0x12345678)
        run(0x1bbc0d,(0x1bbc15,),True)
        assert u.reg_read(regs['rcx'])==0x12345678
        assert before=={r:u.reg_read(regs[r]) for r in before}
        assert all(u.reg_read(r)==v for r,v in xmms.items())
        # Actual deferred title rendering with NO battle context. The old
        # 0.10.1 battle helper crashes at 11f68d in this scenario.
        setup();real_rect=True;put(initialized,'B',1);put(page,'B',1)
        context=allocation+0x1000;commands=allocation+0x10000;state=allocation+0x8000
        u.mem_write(context,b'\0'*0x8000)
        put(base+0x644a10,'Q',context);put(context+0x4d0,'Q',commands);put(context+0x4d8,'Q',0x6666)
        put(base+0x644a58,'Q',vertex_pool);put(vertex_pool+0x2000008,'I',0)
        put(base+0x11c9e18,'Q',allocation+0x9000)
        put(base+0x11cc57c,'I',0xffcca060)
        put(base+0x12cea68,'Q',0) # The title screen has no battle context.
        scratch=bytes(u.mem_read(base+0x11ce620,0xa0))
        run('settings_title_overlay',(0x1bbc15,),True)
        assert bytes(u.mem_read(base+0x11ce620,0xa0))==scratch
        assert get(base+0x12cea68,'Q')==0
        quads=[p for p in submitted if get(p,'I')==5]
        windows=[p for p in quads if get(p+12,'I')==0x80011e];assert len(windows)==21,len(windows)
        for window,x,w,y in ((windows[:3],26,76,31),(windows[3:12],377,77,32),(windows[12:],25,429,50)):
            vertices=[get(p+32,'Q')+i*16 for p in window for i in range(4)]
            assert min(get(v+8,'h') for v in vertices)==x
            assert max(get(v+8,'h') for v in vertices)==x+w,(x,w,[get(v+8,'h') for v in vertices])
            assert min(get(v+10,'h') for v in vertices)==y
            assert all(get(v+12,'h')==0 for v in vertices)
        assert get(get(windows[3]+32,'Q')+4,'I')==0xffcca060
        # Execute the real final title command sequence, version text, pointer
        # cleanup and epilogue hook. The panel's dimmer/windows must be queued
        # AFTER every title command, not at the old early menu-entry hook.
        put(base+0x644a70,'Q',allocation+0xc000)
        put(allocation+0xc008,'I',0)
        put(allocation+0xc018,'Q',allocation+0x100000)
        put(allocation+0x100000+0x2dcf0,'Q',allocation+0xc200)
        put(allocation+0xc208,'Q',allocation+0xc100)
        u.mem_write(allocation+0xc100,b'Ver. 2.0.0\0')
        put(base+0x861919,'B',0)
        submitted.clear();texts.clear();put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0)
        run(0x1bb999,(0x1bbc15,),True)
        assert texts[0]['text'].startswith('Ver. 2.0.0')
        assert texts[1]['text']=='Options de mods'
        title_end=next(i for i,p in enumerate(submitted) if get(p,'I')==0x3c)
        panel_start=next(i for i,p in enumerate(submitted) if get(p,'I')==5)
        assert title_end<panel_start
        # Every category/feature/keyboard row and highlight uses its local index.
        for cat,ids in enumerate(menus):
            for index,logical in enumerate(ids):
                if logical==feature_count:continue
                focus(logical);submitted.clear();put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0)
                run('settings_backdrop')
                p=[p for p in submitted if get(p,'I')==5][-1];v=get(p+32,'Q')
                assert get(p+12,'I')==0x80019c
                visual=index-get(scroll,'B');assert 0<=visual<visible
                assert tuple(get(v+i,'f') for i in (4,8,12,20,40))==(31,54+row_step*visual,0,240,64.5+row_step*visual)
                assert 64.5+row_step*visual<225
                texts.clear();submitted.clear();cursors.clear()
                put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0)
                run('settings_draw')
                top=get(scroll,'B')
                assert [t['text'] for t in texts if t['x']==34]==[label_map[i] for i in ids[top:top+visible] if i!=feature_count]
                assert cursors[-1][2]==43+row_step*visual
                assert all(55<=t['y']<=208 for t in texts if t['x']==34)
                if cat:
                    assert 'Réinit.' not in [t['text'] for t in texts]
                if logical<feature_count:
                    assert cursors[-1][1]==(55 if read_flags()[logical] else 95)
        assert get(scroll,'B')==0
        # Execute native UTF-8 measurement and glyph emission too. The older
        # tests stubbed b480 and therefore could not detect hidden/missing text.
        real_font=True
        put(base+0x644a18,'Q',allocation+0x9000);put(base+0x644a20,'Q',allocation+0x9000)
        put(allocation+0x9008,'f',12.0)
        for language in (3,1):
            put(base+0x11c9ce8,'B',language);focus(0)
            submitted.clear();texts.clear();put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0)
            run('settings_draw')
            assert len(texts)>3*len(menus[1])
            glyphs=[p for p in submitted if get(p,'I')==9]
            assert len(glyphs)>200,len(glyphs)
            sizes=[p for p in submitted if get(p,'I')==12]
            assert len(sizes)==len(glyphs)
            assert all(get(p+8,'f')>0 and get(p+12,'f')>0 for p in sizes)
            assert all(get(p+16,'f')==0 for p in glyphs)
            assert all(20<=get(p+8,'f')<455 and 20<=get(p+12,'f')<248 for p in glyphs)
            for y in range(55,55+row_step*len(menus[1]),row_step):
                assert any(y<=get(p+12,'f')<y+10 for p in glyphs),(y,sorted(set(get(p+12,'f') for p in glyphs)),get(context+0x4e0,'I'))
            assert any(get(p,'I')==0x1b and get(p+8,'I')==4 for p in submitted)
        for language in (3,1):
            put(base+0x11c9ce8,'B',language)
            for row in range(feature_count+2+len(CATEGORIES)):
                put(selected,'B',row);texts.clear();submitted.clear()
                put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0)
                run('settings_description_draw')
                expected=m['progression_ui']['help_entries'][row][int(language!=3)]
                body=expected[2:];visible_help=m['progression_ui']['help_visible_lines']
                rendered=[cstring(base+expected[0])]+[cstring(base+r) for r in body[:visible_help]]
                assert [t['text'] for t in texts[:len(rendered)]]==rendered
                assert all(t['x']==258 and 63<=t['y']<=216 for t in texts)
                if len(body)>visible_help:
                    assert 'défiler' in texts[-1]['text'] if language==3 else 'scroll' in texts[-1]['text']
                    offset=base+m['progression_ui']['help_state_rva']+2
                    before_flags=read_flags()
                    for _ in range(len(body)+5):
                        put(base+0x8c9188,'I',0x02000000);run('settings_description_input')
                    assert get(offset,'H')==len(body)-visible_help and read_flags()==before_flags
                    texts.clear();submitted.clear();put(context+0x4e0,'I',0);put(vertex_pool+0x2000008,'I',0);run('settings_description_draw')
                    assert [t['text'] for t in texts[1:1+visible_help]]==[cstring(base+r) for r in body[-visible_help:]]
                    put(base+0x8c9188,'I',0x01000000);run('settings_description_input')
                    assert get(offset,'H')==len(body)-visible_help-1
                    put(base+0x8c9188,'I',0)

                assert get(context+0x4e0,'I')<5000,(row,language,get(context+0x4e0,'I'),len(texts),sum(len(t['text']) for t in texts))
        real_font=False
        # Run the REAL hint/layout/selection chain, switching the platform
        # input family between frames (gamepads 0/1/2, keyboard 4/5).
        put(base+0x6449f8,'Q',allocation+0xa000)
        put(allocation+0xa010,'I',1)
        put(base+0x85ff28,'Q',api+0x50)
        put(base+0x644a60,'Q',allocation+0xb000)
        families=[]
        for input_device in (0,1,2,4,5):
            for language in (3,1):
                put(base+0x11c9ce8,'B',language);focus(0)
                texts.clear();hint_buttons.clear();put(context+0x4e0,'I',0)
                run('settings_hints')
                assert [t['text'] for t in texts]==(['Retour','Sélect.','Modifier'] if language==3 else ['Back','Select','Modify'])
                assert len(hint_buttons)==3 and all(t['y']==252 and 200<t['x']<455 for t in texts)
                assert texts[0]['x']>texts[1]['x']>texts[2]['x']
                families.append(tuple(b[0] for b in hint_buttons))
        assert len(set(families))>=3,families
        put(selected,'B',feature_count);texts.clear();run('settings_hints')
        assert texts[-1]['text']=='Confirm'
        # Missing/exhausted renderer must be harmless and submit nothing.
        for missing in ('context','buffer','capacity','arena','arena_capacity','atlas'):
            setup()
            put(base+0x644a58,'Q',0 if missing=='arena' else vertex_pool)
            put(vertex_pool+0x2000008,'I',0x1fffff0 if missing=='arena_capacity' else 0)
            put(base+0x11c9e18,'Q',0 if missing=='atlas' else allocation+0x9000)
            if missing!='context':
                put(base+0x644a10,'Q',context);put(context+0x4e0,'I',0)
                put(context+0x4d0,'Q',0 if missing=='buffer' else commands)
                put(context+0x4d8,'Q',8 if missing=='capacity' else 128)
            run('settings_backdrop');assert not submitted
        real_rect=False
        # The new common hook runs before Start as well as on the menu, but
        # NEVER before the original title reveal, while loading or in a panel.
        for phase in (0,29,30,160,229,230,400,0x4650,1000000):
            for visible in (False,True):
                for opened in (0,1):
                    setup();put(page,'B',opened);reg('rbx',phase)
                    for p in (0x10e1e70,0x10e1e78):put(base+p,'Q',actors if visible else 0)
                    before={r:u.reg_read(v) for r,v in regs.items()}
                    for r,v in xmms.items():u.reg_write(r,v)
                    run(0x1bae9d,(0x1baea3,),True)
                    assert bool(brands)==(230<=phase<1000000 and visible and not opened)
                    assert before=={r:u.reg_read(regs[r]) for r in before}
                    assert all(u.reg_read(r)==v for r,v in xmms.items())
                    assert bool(u.reg_read(UC_X86_REG_EFLAGS)&1)==(phase<230)
        # Exercise actual native entry sites with features disabled.
        setup();write_flags(b'\0'*feature_count)
        put(data+0x20,'B',1);put(base+0x12cea98,'hhhh',12,32,512,0)
        run(0x10d515,(0x10d51c,),True)
        assert get(data+0x20,'B')==0 and get(base+0x12cea98,'h')==12
        put(data,'Q',actors);reg('rdi',enemies);reg('rsi',50)
        u.reg_write(UC_X86_REG_EFLAGS,0x242)
        run(0x8f099,(0x8f0a1,),True)
        assert get(enemies+0x2c,'i')==950 and get(actors+0x34,'h')==10
        reg('rax',stats);reg('rdx',5);put(stats+0x1c,'h',100)
        run(0x118b36,(0x118b3d,),True);assert u.reg_read(regs['rdx'])==500
        for enabled,y in ((0,232),(1,236)):
            put(flags+4,'B',enabled);run(0x80af8,(0x80afd,),True)
            assert u.reg_read(regs['rax'])==y
        # Confirm no cross-feature switches are written by rendering or fallback.
        assert read_flags()==bytes(int(i==4) for i in range(feature_count))
    finally:
        u.hook_del(h);u.mem_unmap(api,0x1000);u.mem_unmap(allocation,0x2401000)
        write_flags(b'\1'*feature_count)
    return count
