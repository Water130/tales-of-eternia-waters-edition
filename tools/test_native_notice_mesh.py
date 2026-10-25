"""Native label renderer: resource binding, UVs, layers and state isolation."""
import struct,io,hashlib
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *

def check_native_labels(u,base,m,actors,sp,reset,put,get,reg,regs):
    info=m['spell_level_notices']['native_labels'];sym=m['symbols']
    from PIL import Image
    from damage_color_patch import PAIRS
    png=bytes(u.mem_read(base+info['png_rva'],info['png_bytes']))
    assert hashlib.sha256(png).hexdigest()==info['png_sha256']
    atlas=Image.open(io.BytesIO(png));assert atlas.size==(1024,4096)
    state=base+info['texture_state_rva'];stop=base+m['data_rva']-16
    arena=0x50000000;u.mem_map(arena,0x2001000)
    manager=actors+0xc000;cmds=actors+0xd000;owner=actors+0xb800;asset=actors+0xb900
    calls=[];cases=0
    def hook(_,address,size,user):
        if address!=base+0x60bf0:return
        p=u.reg_read(regs['rdx']);raw=bytes(u.mem_read(p,80));verts=None
        if get(p,'I')==5:verts=bytes(u.mem_read(get(p+32,'Q'),64))
        calls.append((raw,verts));rsp=u.reg_read(UC_X86_REG_RSP);assert rsp%16==8
        u.reg_write(UC_X86_REG_RIP,get(rsp,'Q'));u.reg_write(UC_X86_REG_RSP,rsp+8)
    h=u.hook_add(UC_HOOK_CODE,hook)
    def run(name,end=None):
        nonlocal cases
        cases+=1;rsp=sp-8 if end else sp;u.reg_write(UC_X86_REG_RSP,rsp);put(rsp,'Q',stop)
        dest=base+end if end else stop
        u.emu_start(base+sym[name],dest,count=100000)
        assert u.reg_read(UC_X86_REG_RIP)==dest
        assert u.reg_read(UC_X86_REG_RSP)==rsp+(0 if end else 8)
    try:
        reset();put(base+0x644a10,'Q',manager);put(base+0x644a58,'Q',arena)
        put(base+0x644a30,'Q',owner);put(base+0x8602e8,'Q',1);put(owner+0x60,'Q',1)
        put(state,'QQQ',owner,7,asset);put(asset+0x18,'I',0)
        put(manager+0x4d0,'QQI',cmds,50,0)
        put(base+0x12cea68,'Q',actors+0xe000)
        for lang in (3,1):
            put(base+0x11c9ce8,'B',lang)
            for aid in map(int,info['abbreviations']):
                for shadow in (0,1):
                    put(state+0xc4,'I',aid+1);reg('rcx',actors+0xf000);reg('rdx',shadow)
                    run('spell_label_assign')
                    rect=bytes(u.mem_read(base+info['table_rva']+aid*32+int(lang!=3)*16+shadow*8,8))
                    assert bytes(u.mem_read(actors+0xf012,8))==rect
                    x,y,w,hgt=struct.unpack('<4H',rect)
                    assert w<=320 and x+w<=1024 and y+hgt<=4096
                    palette=info['element_palettes'][str(aid)]
                    element=get(base+0x551780+aid*8+2,'B')&15
                    assert palette['element']==element
                    assert (palette['primary'],palette['secondary'])==tuple(p.hex() for p in PAIRS[element])
                    if aid in (93,94):
                        assert element==9 and palette['primary']==palette['secondary']=='808080'
                    for yy in (10,30,50):
                        t=yy-4
                        rgb=tuple(round((min(255,a*2)*(56-t)+min(255,b*2)*t)/56)
                                  for a,b in zip(*PAIRS[element]))
                        if shadow:rgb=tuple(255-c for c in rgb)
                        pixels=list(atlas.crop((x,y+yy,x+w,y+yy+1)).get_flattened_data())
                        assert (*rgb,255) in pixels,(aid,lang,shadow,yy,rgb)
                    put(base+0x11ce640,'8h',0,0,w//4,0,0,16,w//4,16)
                    u.mem_write(base+0x11ce68a,rect)
                    put(base+0x11ce684,'h',100);put(base+0x11ce620,'I',0x00808080)
                    put(arena+0x2000008,'I',0);put(manager+0x4e0,'I',0);calls.clear()
                    reg('rdx',0x5fff);reg('r8',1024);reg('r9',4096)
                    run('spell_label_mesh_draw')
                    binds=[r for r,v in calls if int.from_bytes(r[:4],'little')==0x22]
                    assert len(binds)==1 and struct.unpack_from('<II',binds[0],16)==(1024,4096)
                    draws=[v for r,v in calls if v is not None];assert len(draws)==1
                    uv=[struct.unpack_from('<2f',draws[0],i*16) for i in range(4)]
                    assert uv==[(x+.5,y+.5),(x+w-.5,y+.5),(x+.5,y+hgt-.5),(x+w-.5,y+hgt-.5)],uv
                    assert get(state+0xc0,'B')==0
        # A missing/not-yet-ready texture never sends the marker to a native index lookup.
        put(asset+0x18,'I',0xffffffff);calls.clear();reg('rdx',0x5fff);run('spell_label_mesh_draw');assert not calls
        # Ordinary constructor nodes are untouched outside spell construction.
        put(state+0xc4,'I',0);before=bytes(u.mem_read(actors+0xf000,0x4a))
        reg('rcx',actors+0xf000);reg('rdx',0);run('spell_label_assign')
        assert bytes(u.mem_read(actors+0xf000,0x4a))==before
        return cases
    finally:
        u.hook_del(h);u.mem_unmap(arena,0x2001000)
        for p in (0x644a10,0x644a58,0x644a30,0x8602e8):put(base+p,'Q',0)
        put(state+0xc4,'I',0)
