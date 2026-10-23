"""Execute the native mastery UI, font/window emission and save integration.

OS, font metrics and GPU submission are boundaries. No live visual claim.
"""
import struct
import re
import sys
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def check_mastery_menu(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['mastery_menu'];sym=m['symbols'];ui=base+info['state_rva']
    choices=base+info['choices']['live_rva'];data=base+m['data_rva']
    usage=base+m['artesphere']['usage']['live_rva']
    rows=info['rows'];table=base+info['table_rva'];master=base+0x11ca420
    arena=0x68000000;api=0x6b000000
    u.mem_map(arena,0x2401000);u.mem_map(api,0x1000)
    vertices=arena+0x300000
    context=arena+0x1000;commands=arena+0x10000;stop=data-16
    texts=[];submitted=[];native=[];buttons=[];cursors=[];silhouettes=[];gauges=[];frames=[];links=[];meters=[];alphas=[];node_colors=[]
    records={};save_ok=True;io_ok=True;device=0;calls=0;max_commands=0;hint_keys=[]
    nonvolatile=('rbx','rbp','rsi','rdi','r12','r13','r14','r15')
    def get_from(raw,offset,fmt):return struct.unpack_from('<'+fmt,raw,offset)[0]
    def string(p,wide=False):
        raw=bytearray();step=2 if wide else 1
        for i in range(2048):
            b=bytes(u.mem_read(p+i*step,step))
            if b==b'\0'*step:return raw.decode('utf-16-le' if wide else 'utf8')
            raw.extend(b)
        raise AssertionError('unterminated string')
    def f(register):
        return struct.unpack('<f',(u.reg_read(register)&0xffffffff).to_bytes(4,'little'))[0]
    def ret(value=0):
        rsp=u.reg_read(UC_X86_REG_RSP)
        assert rsp%16==8,('alignment',hex(u.reg_read(UC_X86_REG_RIP)-base),hex(rsp))
        reg('rax',value)
        for r in ('rcx','rdx','r8','r9','r10','r11'):reg(r,0xdead0000)
        for r in (UC_X86_REG_XMM0,UC_X86_REG_XMM1,UC_X86_REG_XMM2,
                  UC_X86_REG_XMM3,UC_X86_REG_XMM4,UC_X86_REG_XMM5):u.reg_write(r,0)
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    observed={api,api+0x10,api+0x20,api+0x30,api+0x40}|{base+a for a in (
        0x594d0,0x2a41e0,sym['mastery_status_native_input'],sym['mastery_status_native_draw'],
        0x251390,0xb480,0x52f10,0x6a320,0x60bf0,0x62010,0x12cb0,0x140c0,sym['mastery_menu_spirit_icon'],
        sym['mastery_menu_frame'],sym['mastery_node_frame'],sym['mastery_menu_tinted_link'],sym['mastery_spell_meter_rect'],0x250b50)}
    def boundary(_,address,length,user):
        if address not in observed:return
        a=address-base;rcx,rdx,r8,r9=[u.reg_read(regs[r]) for r in ('rcx','rdx','r8','r9')]
        rsp=u.reg_read(UC_X86_REG_RSP)
        if address==api:assert string(rcx)=='kernel32.dll';ret(1)
        elif address==api+0x10:
            ret(api+(0x20 if string(rdx)=='GetPrivateProfileStructW' else 0x30))
        elif address in (api+0x20,api+0x30):
            key=(string(rcx,True),string(rdx,True))
            assert (key[0],r9) in (('MasteryChoices-v1',232),('SpellCatchUp-v1',1800),('ArteUsage-v1',1800),('Artesphere-v1',104),('Artesphere-v2',104))
            if address==api+0x30:
                if io_ok:records[key]=bytes(u.mem_read(r8,r9))
                ret(int(io_ok))
            else:
                if io_ok and key in records:u.mem_write(r8,records[key])
                ret(int(io_ok and key in records))
        elif address==api+0x40:ret(device)
        elif a==0x594d0:ret(int(save_ok))
        elif a==0x2a41e0:u.mem_write(rcx,bytes(u.mem_read(rdx,r8)));ret(rcx)
        elif a in (sym['mastery_status_native_input'],sym['mastery_status_native_draw']):
            native.append(a)
            if a==sym['mastery_status_native_draw']:put(ui+8,'i',214)
            ret(77)
        elif a==0x251390:
            gauges.append((rcx,rdx,r9,get(rsp+0x38,'H'),get(rsp+0x40,'B'),get(rsp+0x28,'H'),get(rsp+0x30,'H')))
        elif a==0xb480:
            texts.append((string(rcx),f(UC_X86_REG_XMM1),f(UC_X86_REG_XMM2),get(rsp+0x30,'I')))
            # Do not stub font layout: it caught black/empty menus previously.
        elif a==0x52f10:
            u.mem_write(r9,b'\0'*0x70);put(r9,'fffff',6.,12.,0.,0.,7.);ret()
        elif a==0x6a320:ret(123)
        elif a==0x60bf0:submitted.append(bytes(u.mem_read(rdx,80)));ret()
        elif a==0x62010:ret()
        elif a==0x140c0:hint_keys.append(r9)
        elif a==0x12cb0:
            buttons.append((rcx,f(UC_X86_REG_XMM1),f(UC_X86_REG_XMM2)))
            ret() # Actual 21cbb0 -> 140c0 -> 13d70 chose the device glyph.
        elif a==sym['mastery_menu_spirit_icon']:
            silhouettes.append((rcx,r9)) # Continue actual atlas binding and quad emission.
        elif a in (sym['mastery_menu_frame'],sym['mastery_node_frame']):
            frames.append((rcx,rdx,r8,r9))
            if a==sym['mastery_node_frame']:node_colors.append((rcx,rdx,u.reg_read(regs['r10'])))
        elif a==sym['mastery_menu_tinted_link']:
            links.append((rcx,rdx));alphas.append(u.reg_read(regs['r10']))
        elif a==sym['mastery_spell_meter_rect']:meters.append((rcx,rdx,r8,r9,u.reg_read(regs['r10'])))
        elif a==0x250b50:
            cursors.append((rcx,rdx,r8,r9)) # Continue native cursor placement.
    hook=u.hook_add(UC_HOOK_CODE,boundary)
    def setup(char=2):
        reset();u.mem_write(ui,b'\0'*0x200);u.mem_write(choices,b'\0'*224)
        u.mem_write(usage,b'\0'*1792);u.mem_write(master,b'\0'*0x1070)
        u.mem_write(context,b'\0'*0x8000)
        put(base+0x111a658,'HH',0,0);put(base+0x111a668,'BB',1,255)
        put(base+0x111a672,'BBB',4,0,0);put(base+0x11cad10,'4H',char+1,2,3,4)
        u.mem_write(base+0x11cad38,b'\1'*7)
        put(base+0x11c9da0,'Q',0);put(base+0x8c9180,'III',0,0,0)
        put(base+0x11c9ce8,'B',3);put(data+0x1a0c,'B',1);put(data+0x1a10,'B',1)
        put(base+0x644a10,'Q',context);put(context+0x4d0,'Q',commands)
        put(context+0x4d8,'Q',0x6666);put(base+0x644a58,'Q',vertices);put(vertices+0x2000008,'I',0)
        for addr in (0x644a18,0x644a20,0x11c9e18):put(base+addr,'Q',arena+0x9000)
        put(arena+0x9008,'f',12.);put(base+0x11cc57c,'I',0xffcca060)
        put(base+0x6449f8,'Q',arena+0xa000);put(arena+0xa010,'I',1)
        put(base+0x644a60,'Q',arena+0xb000);put(base+0x85ff28,'Q',api+0x40)
        put(base+0x2a9058,'Q',api);put(base+0x2a9060,'Q',api+0x10)
        u.mem_write(data+0x3000,('C:\\Local\\TalesOfEternia-WatersEdition.ini\0').encode('utf-16-le'))
        texts.clear();submitted.clear();native.clear();buttons.clear();silhouettes.clear();cursors.clear()
    def run(entry,ends=None,aligned=False):
        nonlocal calls
        calls+=1;rsp=sp-8 if aligned else sp
        u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        u.reg_write(UC_X86_REG_EFLAGS,0x202)
        targets={base+n for n in ends} if ends else {stop};reached=[]
        saved={r:u.reg_read(regs[r]) for r in nonvolatile}
        def halt(_,address,length,user):
            if address in targets:reached.append(address);u.emu_stop()
        h=u.hook_add(UC_HOOK_CODE,halt)
        try:
            # Earlier suites can cache native blocks before this callback exists.
            # Flush once when installing the observer, not once per key press.
            u.emu_start(base+(sym[entry] if isinstance(entry,str) else entry),stop+1,count=2000000)
            assert reached,(entry,'no continuation',hex(u.reg_read(UC_X86_REG_RIP)-base))
            if not ends:
                assert u.reg_read(UC_X86_REG_RSP)==rsp+8,('stack',entry)
                assert saved=={r:u.reg_read(regs[r]) for r in nonvolatile},('ABI',entry)
        except Exception as ex:
            raise AssertionError((entry,hex(u.reg_read(UC_X86_REG_RIP)-base),
                {r:hex(u.reg_read(regs[r])) for r in regs},len(texts),get(context+0x4e0,'I'),
                get(vertices+0x2000008,'I'))) from ex
        finally:u.hook_del(h)
    def press(button):
        put(base+0x8c9184,'II',button,0);run(0x241960);put(base+0x8c9184,'I',0)
    def current_rows():
        return [get(ui+0x20+i*2,'H') for i in range(get(ui+5,'B'))]
    def select(kind,key):
        found=next(i for i,r in enumerate(rows) if r['kind']==kind and r['key']==key and r['mask']&(1<<get(ui+4,'B')))
        if get(ui+6,'B'):press(0x4000)
        put(ui+1,'BB',current_rows().index(found),0)
        before=bytes(u.mem_read(choices,224))
        if kind!=2:
            press(0x2000)
            assert get(ui+6,'B')==1 and bytes(u.mem_read(choices,224))==before,'opening a tree toggled a faculty'
        return table+found*32
    def draw():
        nonlocal max_commands
        texts.clear();submitted.clear();buttons.clear();silhouettes.clear();cursors.clear();frames.clear();links.clear();meters.clear();alphas.clear();gauges.clear();node_colors.clear()
        put(context+0x4e0,'I',0);put(vertices+0x2000008,'I',0)
        run(0x23fa00)
        assert all(0<=x<480 and 0<=y<270 for _,x,y,_ in texts),texts
        glyphs=[p for p in submitted if struct.unpack_from('<I',p)[0]==9]
        assert glyphs,('no native glyph commands',texts)
        assert all(0<=struct.unpack_from('<f',p,8)[0]<480 and 0<=struct.unpack_from('<f',p,12)[0]<270 for p in glyphs)
        assert all(c[3]==2 for c in cursors)
        max_commands=max(max_commands,get(context+0x4e0,'I'))
        assert get(context+0x4e0,'I')<6000,'exceeded reserved complete-page budget'
        atlas_quads=[p for p in submitted if struct.unpack_from('<I',p)[0]==8]
        for p in atlas_quads:
            x,y,z=struct.unpack_from('<3f',p,8)
            if get(ui+3,'B'):assert y==61 and x in (38,120,202,284,366) and z==0,(x,y,z)
            else:
                r=rows[current_rows()[get(ui+1,'B')]]
                assert x==r['root'][0]+20 and y==113 and z==0,(x,y,z)
        if get(ui,'B') and get(ui+5,'B'):
            if get(ui+3,'B'):
                assert len(silhouettes)==5
                assert (34,171,407,69) in frames
                assert len([t for t in texts if t[0] in ('Page 1 / 2','Page 2 / 2')])==1
                assert any(t[0] in ('Activer / désactiver','Toggle') for t in texts)
            else:
                r=rows[current_rows()[get(ui+1,'B')]]
                rx,ry,rw,rh=r['root'];origin=(rx+rw,ry+rh//2)
                assert (29,58,62,114) in frames,'persistent sidebar missing'
                assert len(cursors)==1
                assert (min(n['y'] for n in r['nodes'])+max(n['y']+28 for n in r['nodes']))/2==132
                assert len(frames)==10+len(r['nodes'])
                assert (rx,107 if r['kind']==0 else ry,rw,50 if r['kind']==0 else rh) in frames
                root_texts=[t for t in texts if t[2]==(138 if r['kind']==0 else 128) and rx<=t[1]<rx+rw]
                assert len(root_texts)==1
                from mastery_tree_layout import connections
                expected=connections(r)
                assert len(links)>=len(expected)
                # Additional paths belong to the animated elemental root.
                cores=alphas[:len(expected)]
                unlocked=False
                for color in cores:
                    if color!=0xff28160c:unlocked=True
                    else:assert not unlocked,'locked branches obscure an unlocked junction'
                actual=[]
                for ptr,count in links[:len(expected)]:
                    xy=[struct.unpack('<ff',u.mem_read(ptr+i*8,8)) for i in range(count)]
                    mid=[((xy[i][0]+xy[i+1][0])/2,(xy[i][1]+xy[i+1][1])/2) for i in range(0,count,2)]
                    path=next((p for p in expected if abs(p['points'][-1][0]-mid[-1][0])<0.001 and
                               abs(p['points'][-1][1]-mid[-1][1])<0.001),None)
                    assert path and len(mid)==len(path['points'])
                    assert all(abs(a-c)<0.001 and abs(b-d)<0.001 for (a,b),(c,d) in zip(mid,path['points']))
                    n=r['nodes'][path['node']]
                    start=origin if n['parent']<0 else (r['nodes'][n['parent']]['x']+42,n['y']+14)
                    assert mid[0]==start and mid[-1]==(n['x'],n['y']+14),'disconnected ribbon'
                    actual.append(path['node'])
                assert sorted(actual)==list(range(len(r['nodes'])))
                ribbons=[p for p in submitted if get_from(p,0,'I')==5 and get_from(p,12,'I')==0x80019c]
                # Other native widgets also use type 5; identify our flat RGBs.
                flat=[]
                for p in ribbons:
                    count=get_from(p,8,'I');ptr=get_from(p,32,'Q')
                    color=get(ptr,'I')
                    if color in ({0xff080604}|set(alphas)):
                        assert count==4,'native UI accepts four-vertex segments'
                        assert all(get(ptr+i*16,'I')==color for i in range(count)),'longitudinal fading'
                        flat.append(color)
                assert len(flat)==sum((count//2-1)*2 for _,count in links)
                for n in r['nodes']:
                    assert n['y']+28<190
                    assert (n['x'],n['y'],42,28) in frames
                    bubble=[t for t in texts if n['x']<=t[1]<n['x']+42 and n['y']<=t[2]<n['y']+28]
                    lang=0 if get(base+0x11c9ce8,'B')==3 else 1
                    if bubble[0][0]=='???':
                        assert [t[0] for t in bubble]==['???','???']
                        assert all(t[3]==0xff999999 for t in bubble)
                        assert (n['x'],n['y'],0xff706050) in node_colors
                    else:
                        count=len(n['title_lines'][lang])
                        assert [t[0] for t in bubble[:count]]==n['title_lines'][lang],bubble
                        locked=bubble[0][3]==0xff999999
                        node_color=next(c for x,y,c in node_colors if (x,y)==(n['x'],n['y']))
                        assert node_color==0xff706050 if locked else node_color in (0xffcca060,0xffefd080)
                        assert all(t[3]==(0xff999999 if locked else 0xffffad61) for t in bubble[:count])
                        assert ''.join(t[0] for t in bubble[count:])==n['label'][lang],bubble
                        for t in bubble[count:]:assert t[3]==(0xff999999 if locked else 0xff70f0a0 if re.search(r'\d',t[0]) else 0xffffffff),t
                        assert bubble[-1][2]==n['y']+(15 if count==1 else 19)
    try:
        if '--browser-stress-only' in sys.argv:
            u.ctl_remove_cache(base,base+0x300000)
            for language in (3,1):
                setup(2);put(base+0x11c9ce8,'B',language)
                u.mem_write(base+0x11cb0b8,b'\xff'*16)
                for key in range(10):put(base+0x11cafd8+key*8,'BB',3,30)
                press(0x8000);press(0x1000)
                for index in range(get(ui+5,'B')):
                    put(ui+1,'B',index)
                    draw()
                    assert not any(t[0]=='???' for t in texts)
            return dict(cases=calls,all_spell_names_all_viewports=True,max_render_commands=max_commands)
        # Corroborate the status fields against actual native RIP operands.
        # The previous test copied six-byte-offset mistakes from the patch.
        def rip(site,size):return site+size+get(base+site+size-4,'i')
        assert rip(0x23fa19,8)==0x111a669
        assert rip(0x23fa6a,7)==0x111a674
        assert rip(0x241fb9,7)==0x111a672
        assert rip(0x2419de,7)==0x111a658
        assert rip(0x241a93,7)==0x111a65a
        assert rip(0x2419eb,7)==0x111a668
        u.ctl_remove_cache(base,base+0x300000)
        # Execute the actual native tail, including font measurement and all
        # patched hint callsites. The prepend helper consumes its returned edge.
        edges={}
        for language in (3,1):
            for device in (0,1,2,4,5):
                for title_state in (0,1,2):
                    for party_size in (1,4):
                        setup();put(base+0x11c9ce8,'B',language)
                        put(base+0x111a65c,'H',int(title_state==1))
                        put(base+0x111a672,'B',party_size)
                        manager=arena+0xc000;catalog=arena+0x100000
                        put(base+0x644a70,'Q',manager);put(manager+8,'I',0);put(manager+0x18,'Q',catalog)
                        words=(['Retour','Changer de titre','Sélect. personnage','Changer de titre','Sélect. personnage']
                               if language==3 else ['Back','Change title','Select character','Change title','Select character'])
                        for i,(offset,word) in enumerate(zip((0x1ff48,0x20270,0x1ff58,0x1ff60,0x1ff78),words)):
                            record=arena+0xd000+i*0x20;address=arena+0xe000+i*0x100
                            put(catalog+offset,'Q',record);put(record+8,'Q',address)
                            u.mem_write(address,(word+'\0').encode('utf8'))
                        reg('rbx',arena+0xe000);reg('rbp',0xff000000);reg('rsi',255)
                        u.reg_write(UC_X86_REG_XMM7,get(base+0x23fb41+0x2e4e7b,'I'))
                        run(0x241648 if title_state==2 else 0x241720,[0x241865],True)
                        edge=get(ui+8,'i');assert 0<edge<374
                        assert edge==u.reg_read(regs['rax'])
                        original_left=min([x for _,x,y,_ in texts]+[x for _,x,y in buttons])
                        original_count=len(texts);command_start=len(submitted);run('mastery_status_entry_hint')
                        assert len(texts)==original_count+1
                        title,x,y,_=texts[-1]
                        assert title==('Maîtrise' if language==3 else 'Mastery')
                        glyphs=[p for p in submitted[command_start:] if struct.unpack_from('<I',p)[0]==9]
                        assert glyphs and max(struct.unpack_from('<f',p,8)[0] for p in glyphs)+7<=original_left,(title_state,device,language,texts,buttons)
                        assert all(0<=x<480 for _,x,_,_ in texts)
                        edges[(language,device,title_state,party_size)]=x
                assert edges[(language,device,1,4)]<edges[(language,device,0,4)]
        put(base+0x644a70,'Q',0)
        # The same context-dependent key reaches both input and native hints.
        for language in (3,1):
            for device in (0,1,2,4,5):
                for source,mode,key in ((0,0,0x8000),(0,2,0x8000),
                                        (1,0,0x1000),(1,1,0x8000),(1,2,0x8000)):
                    setup();put(base+0x11c9ce8,'B',language)
                    put(base+0x11cad38,'B',mode)
                    put(ui+0xc,'B',source);put(ui+8,'i',210);hint_keys.clear()
                    run('mastery_status_entry_hint')
                    assert hint_keys==[key],(source,device,hint_keys)
                    assert len(buttons)==1,(source,device,buttons)
                    assert [t[0] for t in texts]==['Maîtrise' if language==3 else 'Mastery']
                    assert 0<=buttons[0][1]<texts[0][1]<480,(source,device,buttons,texts)
        for char in range(7):
            setup(char);press(0);assert native==[sym['mastery_status_native_input']]
            press(0x8000);assert get(ui,'B')==1 and get(ui+4,'B')==char
            expected=[i for i,r in enumerate(rows) if r['mask']&(1<<char) and r['kind']!=2]
            assert current_rows()==expected
            assert get(ui+6,'B')==0
            if expected:
                draw();assert any(t[2]==190 for t in texts),'live tree missing beside sidebar'
                assert any(t[0] in ("Voir l'arbre",'View tree') for t in texts)
                before=bytes(u.mem_read(choices,224));press(0x2000)
                assert get(ui+6,'B')==1 and bytes(u.mem_read(choices,224))==before
            for _ in range(20):press(0x20)
            if expected:
                n=get(ui+2,'B');assert rows[expected[0]]['nodes'][n]['neighbors'][1]==n
                press(0x4000);assert get(ui,'B')==1 and get(ui+6,'B')==0
            for _ in range(len(expected)+2):press(0x40)
            assert get(ui+1,'B')==max(0,len(expected)-1)
            if expected:
                draw()
                press(0x2000);draw()
                assert get(ui+6,'B')==1
                assert len(silhouettes)==(1 if rows[expected[-1]]['kind']==0 else 0)
                press(0x4000);assert get(ui+1,'B')==len(expected)-1 and get(ui+6,'B')==0
            press(0x4000);assert get(ui,'B')==0
            assert len(native)==1,'cancel leaks into native Status'
        # Auto uses Triangle; Semi-auto/Manual use Square. Select and the
        # native Auto toggle / Clear key remain available to Techniques.
        for char in range(7):
            for mode,key in ((0,0x1000),(1,0x8000),(2,0x8000)):
                other=key^0x9000
                for held,pressed,opens in ((0,other,False),(key,0,False),(0,1,False),
                                           (0,0x2000,False),(0,key,True),(key,key,True)):
                    setup(char)
                    # Put the character in a different party slot to catch
                    # accidental indexing by character ID instead of slot.
                    slot=(char+2)%4
                    put(base+0x111a674,'B',slot);put(base+0x11cad10+slot*2,'H',char+1)
                    put(base+0x11cad38+slot,'B',mode)
                    put(base+0x1119f96,'HH',0,0)
                    put(base+0x1119fa4,'BB',1,255)
                    put(base+0x8c9180,'II',held,pressed)
                    run('mastery_tech_input')
                    assert get(ui,'B')==int(opens) and u.reg_read(regs['rax'])==int(not opens),(char,mode,held,pressed)
                    assert not native,'Techniques dispatched the Status input handler'
                    if opens:
                        assert get(ui+4,'B')==char and get(ui+0xc,'B')==1
                        assert bytes(u.mem_read(choices,224))==b'\0'*224
                        put(base+0x8c9184,'I',0);run('mastery_tech_input')
                        assert get(ui,'B')==1,'held entry key closed the panel'
                        put(base+0x8c9184,'I',0x4000);run('mastery_tech_input')
                        assert get(ui,'B')==0 and u.reg_read(regs['rax'])==0,'Back leaked to native Techniques'
        for char in (0,1):
            for pressed,opens in ((0x1000,True),(0x8000,False),(0x2000,False)):
                setup(char);put(base+0x1119f96,'HH',0,4);put(base+0x1119fa4,'BB',1,255)
                put(base+0x8c9184,'I',pressed);run('mastery_tech_input')
                assert get(ui,'B')==int(opens) and u.reg_read(regs['rax'])==int(not opens)
        for field,fmt,val in ((0x1119f96,'H',1),(0x1119fa4,'B',0),
                              (0x1119fa5,'B',0),(0x1119f98,'H',3)):
            setup(2);put(base+0x1119f96,'HH',0,0);put(base+0x1119fa4,'BB',1,255)
            put(base+field,fmt,val);put(base+0x8c9180,'II',0x8000,0x8000)
            run('mastery_tech_input');assert get(ui,'B')==0 and u.reg_read(regs['rax'])==1
        # List confirmation must never activate the first unlocked faculty.
        # Holding Confirm is not a second press; Back preserves the selected
        # row, while a category change deliberately returns to list selection.
        setup(1);put(data+0x1a41,'B',1)
        put(base+0x11cb038,'B',30);put(base+0x11cb040,'B',30)
        press(0x8000);press(0x40);press(0x40);press(0x40)
        before=bytes(u.mem_read(choices,224));press(0x2000)
        assert get(ui+1,'B')==3 and get(ui+6,'B')==1
        assert bytes(u.mem_read(choices,224))==before
        put(base+0x8c9184,'II',0,0x2000);run(0x241960)
        assert bytes(u.mem_read(choices,224))==before
        put(base+0x8c9188,'I',0);press(0x2000)
        assert get(choices+48,'B')==1
        press(0x4000);assert get(ui+1,'B')==3 and get(ui+6,'B')==0
        setup(2);press(0x8000);press(0x2000);press(0x1000)
        assert get(ui+3,'B')==1 and get(ui+6,'B')==0
        press(0x2000);assert get(ui+6,'B')==0,'empty spell list opened a tree'
        # Opening is restricted to the fully entered status page, not title
        # selection, transitions, hidden popups or an invalid character slot.
        for field,fmt,value in ((0x111a658,'H',1),(0x111a65a,'H',1),
                                (0x111a668,'B',2),(0x111a669,'B',127),
                                (0x111a674,'B',4),(0x11cad10,'H',0),(0x11cad10,'H',8)):
            setup();put(base+field,fmt,value);press(0x8000)
            assert get(ui,'B')==0 and native
        setup();put(base+0x11c9da0,'Q',actors);put(actors+8,'B',1);press(0x8000)
        assert get(ui,'B')==0
        # Entry uses the native selected party slot, including a changed order.
        setup();put(base+0x111a674,'B',2);put(base+0x11cad10,'4H',4,3,1,2)
        press(0x8000);assert get(ui+4,'B')==0
        press(0x4000)
        # Third bar and compact native gauges, read-only at both boundary levels.
        for language in (3,1):
            for punch,kick in ((0,0),(1,30),(14,10),(30,30),(255,255),(30,0)):
                setup(1);put(base+0x11c9ce8,'B',language)
                put(data+0x1a0e,'B',1);put(base+0x11cb038,'B',punch);put(base+0x11cb040,'B',kick)
                before=bytes(u.mem_read(master,0x1070));reg('r12',255);gauges.clear()
                run(0x240621,[0x240979],True)
                assert len(gauges)==6
                assert [g[3] for g in gauges[1::2]]==[min(30,punch)*2,min(30,kick)*2,min(30,punch,kick)*2]
                assert [g[1] for g in gauges]==[189,189,201,201,213,213]
                assert all(g[0]==22 and g[4]==255 for g in gauges)
                assert any(t[0]==('Niveau Énergie' if language==3 else 'Energy Lv.') for t in texts)
                assert [t[0] for t in texts if t[1]==175]==[f'{min(30,punch)}/30',f'{min(30,kick)}/30',f'{min(30,punch,kick)}/30']
                assert bytes(u.mem_read(master,0x1070))==before
                put(data+0x1a0e,'B',0);texts.clear();gauges.clear()
                run(0x240621,[0x240628],True);assert not texts and not gauges
        # Known native metadata families, mixed arcanes, heals and invalid IDs.
        for arte,want in ((1,3),(2,4),(13,5),(22,10),(25,6),(26,7),(39,9),(40,9),(41,9),(42,6),(0,0xffffffff),(43,0xffffffff),(255,0xffffffff)):
            setup();reg('rcx',arte);run('arte_category_index');assert u.reg_read(regs['rax'])==want
        for language in (3,1):
            setup();put(base+0x11c9ce8,'B',language);put(data+0x1a0f,'B',1)
            reg('rbp',1);reg('r13',255);run(0x2272aa,[0x2272b1],True)
            assert [t[0] for t in texts]==['Tranchant' if language==3 else 'Slash']
            assert texts[0][1:3]==(302,200)
            texts.clear();put(data+0x1a0f,'B',0);run(0x2272aa,[0x2272b1],True);assert not texts
        put(data+0x1a0e,'B',1);put(data+0x1a0f,'B',1)
        # All unknown Craymels remain selectable, but no names, descriptions
        # or level requirements enter the renderer in either language.
        for lang in (3,1):
            for key in range(10):
                setup();put(base+0x11c9ce8,'B',lang);press(0x8000);row=select(0,key)
                put(ui+2,'B',get(row+24,'I')-1);draw()
                assert silhouettes and all(tint==0xff000000 for _,tint in silhouettes)
                assert [t[0] for t in texts if t[2]==190]==['???']
                assert any('Craymel' in t[0] and t[2]==201 for t in texts)
                assert not any(t[2] in (209,217,225,236) for t in texts)
                assert not any(r['name'][int(lang!=3)] in [t[0] for t in texts] for r in rows if r['kind']==0)
                put(base+0x11cafd8+key*8,'BB',3,30);draw()
                assert (key,0xffffffff) in silhouettes
                assert [t[0] for t in texts if t[2]==190]!=['???']
                assert any(t[0] in ('Faculté activée','Faculty enabled','Prérequis non atteints','Requirements not met') for t in texts if t[2]==236)
                before=bytes(u.mem_read(choices,224))
                ni=get(ui+2,'B');reg('rcx',row);reg('rdx',base+get(row+20,'I')+ni*info['node_size'])
                run('mastery_menu_node_status');unlocked=u.reg_read(regs['rax'])==4
                press(0x2000)
                from craymel_milestones import faculty_id
                expected=bytearray(before);bit=2*256+faculty_id(key,ni)
                if unlocked:expected[bit//8]^=1<<(bit%8)
                assert bytes(u.mem_read(choices,224))==bytes(expected),'wrong per-faculty preference'
        # Illumination tracks requirements, including preview faculties. Bright
        # paths draw last at shared roots; the damage caption is one centered group.
        setup(3);put(data+0x1a43,'B',1);press(0x8000);select(0,0)
        for level,lit in ((4,0),(5,1),(9,1),(10,2),(15,3),(20,5),(25,6),(30,8)):
            put(base+0x11cafd8,'BB',3,level);draw()
            assert sum(c!=0xff28160c for c in alphas[:8])==lit,(level,alphas)
            caption=[t for t in texts if t[2]==163]
            joined=''.join(t[0] for t in caption)
            from summon_growth import MAX_BONUS
            assert joined==f'Invocation : dégâts +{(level-1)*MAX_BONUS[0]//29} %',joined
            assert all(94<=t[1]<=160 for t in caption)
            assert not any('conditionnel' in n['description'][0] for r in rows if r['name'][1]=='Efreet' for n in r['nodes'])
        # Six real Energy faculties have independent persisted bits. Reading
        # a locked node cannot toggle it; a global off switch retains choices.
        for level in (9,10,15,20,25,30):
            setup(1);put(data+0x1a41,'B',1)
            put(base+0x11cb038,'B',level);put(base+0x11cb040,'B',30)
            press(0x8000);row=select(1,5)
            assert get(row+24,'I')==6
            for ni,threshold in enumerate((10,20,30,15,25,30)):
                put(ui+2,'B',ni)
                reg('rcx',row);reg('rdx',base+get(row+20,'I')+ni*info['node_size'])
                run('mastery_menu_node_status');assert u.reg_read(regs['rax'])==(4 if level>=threshold else 1)
                before=get(choices+48,'B');press(0x2000)
                assert get(choices+48,'B')==before^((1<<ni) if level>=threshold else 0)
                if level>=threshold:
                    draw();assert any(t[0]=='Faculté désactivée' for t in texts)
                    press(0x2000);draw();assert any(t[0]=='Faculté activée' for t in texts)
            assert bytes(u.mem_read(choices,224))==b'\0'*224
        put(data+0x1a41,'B',0);press(0x2000);draw()
        assert get(choices+48,'B')==32
        assert any('Progression de Farah désactivée'==t[0] for t in texts)
        put(data+0x1a41,'B',1)
        # Extra normal attacks live in the combined branches; both levels count.
        for char in (0,1):
            for level in (14,15,29,30):
                setup(char)
                group=data+(0x1a4f if char==0 else 0x1a41)
                other=data+(0x1a41 if char==0 else 0x1a4f)
                put(group,'B',1);put(other,'B',0)
                put(base+0x11cb028+char*16,'B',level)
                put(base+0x11cb030+char*16,'B',30)
                press(0x8000);row=select(1,4 if char==0 else 6)
                nodes=rows[current_rows()[get(ui+1,'B')]]['nodes']
                real=[(i,n) for i,n in enumerate(nodes) if n['implemented']]
                assert len(real)==2
                for rank,(ni,n) in enumerate(real):
                    put(ui+2,'B',ni)
                    reg('rcx',row);reg('rdx',base+get(row+20,'I')+ni*info['node_size'])
                    run('mastery_menu_node_status')
                    assert u.reg_read(regs['rax'])==(4 if level>=n['required'] else 1)
                    before=bytes(u.mem_read(choices,224));press(0x2000)
                    bit=char*256+134+rank
                    after=bytearray(before)
                    if level>=n['required']:after[bit//8]^=1<<(bit%8)
                    assert bytes(u.mem_read(choices,224))==bytes(after)
                    if level>=n['required']:
                        draw();assert any(t[0]=='Faculté désactivée' for t in texts)
                        press(0x2000)
                assert bytes(u.mem_read(choices,224))==b'\0'*224
                put(group,'B',0);draw()
                if level==30:assert any('progression' in t[0].lower() and 'désactivée' in t[0] for t in texts)
        put(data+0x1a4f,'B',1);put(data+0x1a41,'B',1)
        # Exact integer EXP ranks and progress toward the next rank, including
        # non-divisible 999-use projectile/area thresholds.
        from spell_growth import Track, PROJECTILE_CAPS
        for cap,limit in ((25,500),(15,500),(3,999),(6,999),(50,999)):
            track=Track(cap,limit)
            for uses in range(1001):
                reg('rcx',uses);reg('rdx',cap);reg('r8',limit)
                run('mastery_track_progress')
                assert tuple(u.reg_read(regs[r]) for r in ('rax','rdx','r8','r9'))==track.progress(uses)
        for aid in (71,73,75):
            cap=PROJECTILE_CAPS.get(aid,50)
            previous=0
            for uses in range(1001):
                reg('rcx',uses);reg('rdx',aid);run('mastery_spell_total_level')
                normalized=min(25,uses//20)*400 + min(15,uses*15//500)*2000
                normalized+=min(cap,uses*cap//999)*10000//cap
                assert u.reg_read(regs['r8'])==normalized
                level=u.reg_read(regs['rax'])
                assert level==1+normalized*29//50000 and level>=previous
                assert (level==30)==(uses>=999)
                previous=level
        # Dedicated spell progress covers each caster, supported bonuses,
        # informational heals and exact next thresholds (not just major nodes).
        for char in (2,3):
            for language in (3,1):
                setup(char);put(base+0x11c9ce8,'B',language)
                u.mem_write(master+char*0xd0+0x7a,bytes([54,59,60,63,71])+b'\0'*27)
                press(0x8000);press(0x1000)
                assert [rows[i]['key'] for i in current_rows()]==[r['key'] for r in rows if r['kind']==2]
                for aid in (54,59,60,63,71):
                    row=select(2,aid)
                    for casts in (0,24,25,99,100,124,125,249,250,499,500,624,625,9999):
                        put(usage+(char*128+aid)*2,'H',casts)
                        reg('rcx',row);run('mastery_spell_progress')
                        if aid==71:
                            bonus=min(25,casts//20);nxt=(bonus+1)*20 if bonus<25 else 0
                            remaining=max(0,nxt-casts);progress=100 if not nxt else casts%20*5
                        elif aid==63:
                            bonus=sum(casts>=n for n in (100,250,500))
                            nxt=(100,250,500,0)[bonus];last=(0,100,250,500)[bonus]
                            remaining=max(0,nxt-casts);progress=100 if not nxt else (casts-last)*100//(nxt-last)
                        else:bonus=nxt=remaining=progress=0
                        assert [u.reg_read(regs[r]) for r in ('rax','rdx','r8','r9')]==[bonus,nxt,progress,remaining]
                    draw()
                    assert any(t[0]==('Progression des sorts' if language==3 else 'Spell progression') for t in texts)
                    if aid<63:
                        assert any('effets natifs' in t[0].lower() or 'native effects' in t[0].lower() for t in texts)
                        before=bytes(u.mem_read(choices,224));press(0x2000)
                        assert before==bytes(u.mem_read(choices,224))
                    else:
                        assert any(t[0]=='MAX' for t in texts)
                        if aid==63:
                            assert any(g[0]==((76-80)&0xffffffff) and g[1]==187 and g[2]==160 for g in gauges),'missing native filled buff EXP gauge'
                        else:
                            labels=('Puissance','Incantation','Récupération','Critique','Zone') if language==3 else ('Power','Casting','Recovery','Critical','Area')
                            assert all(any(t[0]==label+' : ' if language==3 else t[0]==label+': ' for t in texts) for label in labels)
                            assert sum(t[0]=='MAX' for t in texts)==6
                            assert any(t[0]==('Niv. 30' if language==3 else 'Lv. 30') for t in texts)
                            # One gray native backing and one yellow native
                            # fill per gauge, never two stacked gradients.
                            assert len(gauges)==12,gauges
                            assert [(g[2],g[5],g[6]) for g in gauges]==[(128,128,128),(160,160,104)]*6
                            assert [g[3] for g in gauges]==[84,84]+[65,65]*5
                            assert sum(t[0]=='-15%' for t in texts)==2
                            assert not any('\u2212' in t[0] for t in texts)
                        put(usage+(char*128+aid)*2,'H',26);draw()
                        if aid==63:
                            assert any(t[0]==('EXP avant le prochain gain' if language==3 else 'EXP to next gain') for t in texts)
                            assert any(t[0]=='74' and t[2]==213 for t in texts)
                        else:
                            assert any(t[0]=='+1%' for t in texts)
                            assert not any(t[0]=='MAX' for t in texts)
                            assert len(gauges)==12
                            assert [g[1] for g in gauges[::2]]==[161,177,192,207,177,192]
        for char in (2,3):
            setup(char)
            u.mem_write(master+char*0xd0+0x7a,bytes([71])+bytes(31))
            press(0x8000);press(0x1000);row=select(2,71)
            put(usage+(char*128+71)*2,'H',20)
            put(base+m['artesphere']['usage']['catchup']['live_rva']+(char*128+71)*2,'H',40)
            reg('rcx',row);run('mastery_menu_value')
            assert u.reg_read(regs['rax'])==60
            draw()
            assert any(t[0]=='60' and t[2]==174 for t in texts), 'credited uses must follow catch-up EXP'
            assert any(t[0]=='+3%' for t in texts)
            put(usage+((char^1)*128+71)*2,'H',500);draw()
            assert any(t[0]=='Rattrapage EXP x3' for t in texts)
        # Learned spells only; locked milestones still expose their details.
        for char in (2,3):
            setup(char);u.mem_write(master+char*0xd0+0x7a,bytes([63,64,65,66,71,73])+b'\0'*26)
            press(0x8000);press(0x1000)
            assert len(current_rows())>30
            row=select(2,71);draw()
            assert any(t[0]=='+0%' for t in texts)
            before=bytes(u.mem_read(choices,224));press(0x2000)
            assert bytes(u.mem_read(choices,224))==before
            put(usage+(char*128+71)*2,'H',625);draw()
            assert any('activée' in t[0] for t in texts)
            press(0x2000)
            assert get(choices+char*32+71//8,'B')==128
            assert sum(bytes(u.mem_read(choices,224)))==128
            assert get(usage+(char*128+71)*2,'H')==625
            draw();assert any('désactivée' in t[0] for t in texts)
            put(data+0x1a0c,'B',0);press(0x2000);draw()
            assert not any(bytes(u.mem_read(choices,224)))
            assert any(t[0]=='Progression magique désactivée' for t in texts)
        # Fixed five-column pages and all starter spells, including before
        # acquisition. Availability and cast counts belong to each mage.
        browser=info['spell_browser'];order=[0,1,2,6,8,3,4,5,7,9]
        assert browser['page_order']==order
        starters={70:2,72:2,75:2,79:3,82:3,86:3}
        for char in (2,3):
            setup(char)
            owned=[aid for aid,owner in starters.items() if owner==char]
            u.mem_write(master+char*0xd0+0x7a,bytes(owned)+b'\0'*29)
            press(0x8000);press(0x1000)
            assert len(current_rows())==42
            for aid,owner in starters.items():
                row=select(2,aid)
                put(usage+(2*128+aid)*2,'H',24)
                put(usage+(3*128+aid)*2,'H',625)
                reg('rcx',aid);run('mastery_spell_availability')
                assert u.reg_read(regs['rax'])==(2 if char==owner else 1)
                reg('rcx',row);run('mastery_menu_value')
                assert u.reg_read(regs['rax'])==(24 if char==2 else 625)
                assert u.reg_read(regs['rdx'])==1
                draw()
                name=next(r['name'][0] for r in rows if r['kind']==2 and r['key']==aid)
                assert any(t[0]==name and t[3]==(0xffffffff if char==owner else 0xff999999) for t in texts if 84<=t[2]<=152)
                assert all(tint==0xff000000 for key,tint in silhouettes)
                assert any(t[0]==str(24 if char==2 else 625) and t[2]==174 for t in texts)
                assert any(t[0]==('Page 1 / 2' if aid in (70,72,75) else 'Page 2 / 2') for t in texts)
            # Moving from Maxwell to Gnome switches the entire fixed page.
            put(ui+1,'B',browser['groups'][4][0]);press(0x20);draw()
            assert [key for key,tint in silhouettes]==order[5:]
            press(0x80);draw();assert [key for key,tint in silhouettes]==order[:5]
            # Full longest column is navigable; no row falls below the pane.
            put(ui+1,'B',0)
            for _ in range(15):press(0x40)
            assert get(ui+1,'B')==browser['groups'][0][1]-1
            draw();assert (36,150,75,16) in frames
        setup(2);press(0x8000);press(0x1000);row=select(2,71)
        reg('rcx',71);run('mastery_spell_availability');assert u.reg_read(regs['rax'])==0
        draw();assert any('découvrir' in t[0] for t in texts)
        assert not any('Principal' in t[0] or 'Partenaire' in t[0] for t in texts)
        assert any('???' in t[0] and 'niveau' in t[0] for t in texts)
        put(base+0x11cb0b8+71//8,'B',1<<(71%8))
        put(usage+(2*128+71)*2,'H',99)
        for assigned,want in ((False,1),(True,2),(False,1)):
            put(master+2*0xd0+0x7a,'B',71 if assigned else 0)
            reg('rcx',71);run('mastery_spell_availability');assert u.reg_read(regs['rax'])==want
            draw();assert any(t[0]=='99' and t[2]==174 for t in texts)
        # Craymel headers show current-level EXP, resetting after a level-up.
        # Draw the actual bar, not only a progress helper, to catch stale UI.
        setup(2);press(0x8000);row=select(0,0)
        for level,experience,want in ((1,0,0),(1,243,5000),(10,22396,0),(10,25978,4999),(30,712938,10000)):
            put(base+0x11cafd8,'BB',3,level);put(base+0x11cafd8+4,'I',experience)
            before=bytes(u.mem_read(master,0x1070))
            reg('rcx',0);run('craymel_exp_progress_tree');assert u.reg_read(regs['rax'])==want
            texts.clear();gauges.clear();reg('rcx',row);run('mastery_level_bar')
            assert all(t[2]==55 and t[1]==316 for t in texts), 'EXP belongs beside the bar'
            assert len(texts)==1 and (texts[0][0]=='MAX' if level==30 else '/' in texts[0][0])
            width=198*want//10000
            assert [g[3] for g in gauges]==[198]+([width] if width else [])
            assert [(g[2],g[5],g[6]) for g in gauges]==[(128,128,128)]+([(192,192,48)] if width else [])
            if level==30:assert any(t[0]=='MAX' for t in texts)
            assert bytes(u.mem_read(master,0x1070))==before
        row=select(0,3);put(base+0x11cafd8+3*8,'BB',3,30)
        node=base+get(row+20,'I')+6*info['node_size']
        reg('rcx',row);reg('rdx',node);run('mastery_menu_node_status');assert u.reg_read(regs['rax'])==1
        put(base+0x11cafd8+4*8,'BB',4,30)
        reg('rcx',row);reg('rdx',node);run('mastery_menu_node_status');assert u.reg_read(regs['rax'])==4
        # Live input family is resolved by the original hint/glyph dispatch.
        setup();press(0x8000);families=[]
        for device in (0,1,2,4,5):
            draw();families.append(tuple(b[0] for b in buttons))
        assert len(set(families))>=3,families
        # Fully named acquired rows are more expensive than unknown silhouettes.
        for lang in (3,1):
            put(base+0x11c9ce8,'B',lang)
            for key in range(10):put(base+0x11cafd8+key*8,'BB',3,30)
            for key in range(10):
                select(0,key)
                for ni in range(len(rows[current_rows()[get(ui+1,'B')]]['nodes'])):
                    put(ui+2,'B',ni);draw()
                    assert all(28<=y<241 for _,x,y,_ in texts if y<250)
                    assert len([t for t in texts if t[2] in (201,209,217,225)])<=4
                    node=rows[current_rows()[get(ui+1,'B')]]['nodes'][ni]
                    for direction,button in enumerate((0x80,0x20,0x10,0x40)):
                        put(ui+2,'B',ni);press(button)
                        assert get(ui+2,'B')==node['neighbors'][direction]

        put(base+0x11c9ce8,'B',3)
        # Native closed status still draws, plus a mapped Square entry hint.
        press(0x4000);press(0x4000);draw();assert native[-1]==sym['mastery_status_native_draw']
        assert any(t[0]=='Maîtrise' for t in texts)
        setup();press(0x8000)
        for kind in ('context','commands','capacity','vertices','vertex_capacity','texture'):
            texts.clear();submitted.clear()
            if kind=='context':put(base+0x644a10,'Q',0)
            elif kind=='commands':put(context+0x4d0,'Q',0)
            elif kind=='capacity':put(context+0x4e0,'I',0x6666-5000)
            elif kind=='vertices':put(base+0x644a58,'Q',0)
            elif kind=='vertex_capacity':put(vertices+0x2000008,'I',0x1fffff0)
            else:put(base+0x11c9e18,'Q',0)
            run('mastery_menu_draw');assert not submitted and not texts,kind
            setup();press(0x8000)
        # All native levels, and the combined lower level, are read correctly.
        for char,expected in ((0,{0:17,1:11,4:11}),(1,{2:24,3:16,5:16,6:16})):
            setup(char);press(0x8000)
            for offset,level in ((0,17),(8,11),(16,24),(24,16)):put(base+0x11cb028+offset,'B',level)
            for key,level in expected.items():
                reg('rcx',select(1,key));run('mastery_menu_value');assert u.reg_read(regs['rax'])==level
        # Full existing save hooks include the new choices. All 21 slots
        # freeze a distinct snapshot before the worker and retain native bytes.
        setup();raw=actors+0x4000;dest=actors+0x6000
        u.mem_write(raw,bytes(i%251 for i in range(0x12d4)))
        snapshots={}
        for slot in range(21):
            pattern=bytes((slot*7+i)%256 for i in range(224));snapshots[slot]=pattern
            u.mem_write(choices,pattern);put(usage+(2*128+71)*2,'H',slot+30)
            run('artesphere_save_snapshot',[0x24db28],True)
            u.mem_write(choices,b'\xee'*224)
            reg('rsi',0x12d4);reg('r12',slot);reg('rbp',actors)
            run('artesphere_queue_profile',[0x3f3a8],True)
        for slot in reversed(range(21)):
            reg('r12',slot);reg('r15',raw);put(sp+0x58,'Q',0x12d4)
            run('artesphere_save_commit')
            assert records[('MasteryChoices-v1',f'Slot{slot:02}')][8:]==snapshots[slot]
        for slot in range(21):
            u.mem_write(choices,b'\xcc'*224);put(ui,'B',1)
            reg('rcx',dest);reg('rdx',raw);reg('r8',0x12d4)
            reg('r14',0x12d4);reg('r15',dest);reg('rbx',raw);reg('r12',slot)
            run('artesphere_read_stage',[0x40172],True)
            assert bytes(u.mem_read(choices,224))==b'\xcc'*224,'preview modified preferences'
            saved=bytes(u.mem_read(dest,0x12d4));reg('rcx',dest)
            run('artesphere_import_profile',[0x24db46])
            assert bytes(u.mem_read(choices,224))==snapshots[slot]
            assert bytes(u.mem_read(dest,0x12d4))==saved
            assert get(usage+(2*128+71)*2,'H')==slot+30 and get(ui,'B')==0
        for mode in ('missing','mismatch','io_fail','wrong_buffer'):
            if mode=='missing':del records[('MasteryChoices-v1','Slot00')]
            else:records[('MasteryChoices-v1','Slot00')]=records[('MasteryChoices-v1','Slot01')]
            if mode=='mismatch':put(raw+1,'B',255)
            io_ok=mode!='io_fail'
            reg('rcx',dest);reg('rdx',raw);reg('r8',0x12d4)
            reg('r14',0x12d4);reg('r15',dest);reg('rbx',raw);reg('r12',0)
            run('artesphere_read_stage',[0x40172],True)
            reg('rcx',dest+(16 if mode=='wrong_buffer' else 0))
            run('artesphere_import_profile',[0x24db46])
            assert not any(bytes(u.mem_read(choices,224)))
            put(raw+1,'B',1)
        io_ok=True;save_ok=False;before=dict(records)
        reg('r12',0);reg('r15',raw);put(sp+0x58,'Q',0x12d4);run('artesphere_save_commit')
        assert records==before
        save_ok=True;io_ok=False;reg('r12',0);reg('r15',raw);put(sp+0x58,'Q',0x12d4)
        run('artesphere_save_commit');assert records==before
        u.mem_write(choices,b'\xff'*224);put(ui,'I',0x01010101)
        run('mastery_preferences_new_game')
        assert not any(bytes(u.mem_read(choices,224))) and get(ui,'I')==0
        return dict(cases=calls,spoiler_safe=True,native_font_and_windows=True,
                    all_21_save_slots=True,per_character_spell_switches=True,
                    preview_faculties_not_implemented=True,two_stage_confirmation=True,
                    centered_rooted_trees=True,max_render_commands=max_commands,visual_validation=False)
    finally:
        u.hook_del(hook);u.mem_write(choices,b'\0'*224);u.mem_write(ui,b'\0'*0x200)
