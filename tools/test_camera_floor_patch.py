"""Execute native stage grids/projection and collect resulting ground polygons.

Only final draw submission and unrelated decoration/sound calls are stubbed.
Camera, grid construction, culling, edge patch and native bottom-fill decisions run.
"""
import json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RSP,UC_X86_REG_RIP

def check_floor(uc,base,data,manifest,actors,sp,reset,put,get,reg,regs):
    report=json.loads((Path(__file__).resolve().parent.parent/'audit/build-25190541/camera_floor_geometry.json').read_text())
    stages=report['stages'];sentinel=manifest['data_rva']-0x10
    capture=manifest['symbols']['capture_ground_border']
    extend=manifest['symbols']['extend_ground_border']
    count=0

    def in_triangle(p,a,b,c):
        cross=lambda u,v,w:(v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])
        signs=[cross(a,b,p),cross(b,c,p),cross(c,a,p)]
        return min(signs)>=0 or max(signs)<=0

    def stage_case(stage,center=203,depth=1276,rotation=64,phase=6,corrupt=False):
        nonlocal count
        count+=1;row=stages[stage];reset()
        put(base+0x12d0eb2,'H',stage)
        put(base+0x12d0ef7,'B',phase)
        put(base+0x12cea90,'hhh',rotation,0,0)
        put(base+0x12cea98,'hhh',-center,32,depth)
        put(data+0x20,'B',1)
        matrix=[4096,0,0,0,4076,-401,0,401,4076] if rotation==64 else [4096,0,0,0,4096,0,0,0,4096]
        put(base+0x8c92d0,'9h',*matrix)
        put(base+0x8c92e4,'iii',-center,32,depth)
        put(base+0x8c96f0,'i',512);put(base+0x8c9718,'i',160);put(base+0x8c92c4,'i',120)
        put(SP:=sp,'Q',base+sentinel)
        # Nonzero colours exercise the real backdrop path before ground drawing.
        put(base+0x12ceaa0,'hhhhhhh',128,128,128,0,128,128,128)
        actor_before=bytes(uc.mem_read(actors,0x5000))
        camera_before=bytes(uc.mem_read(base+0x12cea90,16))
        originals=[];quads=[];rectangles=[];first=False;reached=False;disabled_grid=None;raw_grid=None
        projection_return=int(row['callsite'],16)+5 if row['callsite'] else -1
        def step(emu,address,size,user):
            nonlocal first,reached,disabled_grid,raw_grid
            rva=address-base
            if rva==sentinel:
                reached=True;emu.emu_stop();return
            if rva==projection_return:
                x=get(base+0x8c9720,'i');y=get(base+0x8c9724,'i')
                originals.append(struct.pack('<HH',x&65535,y&65535))
            if rva==extend and not first:
                first=True
                pointer=get(data+0x48,'Q')
                if pointer:
                    # The backdrop has consumed native coordinates; nothing in
                    # the grid changed during capture or backdrop drawing.
                    raw_grid=bytes(emu.mem_read(pointer,row['grid_span']))
                    assert all(raw_grid[offset:offset+4]==old for offset,old in zip(row['grid_offsets'],originals)),(stage,'pre-draw grid differs')
                    if corrupt and get(data+0x40,'I'):
                        destination=get(data+0x308,'Q')
                        put(destination,'I',get(destination,'I')^1)
                        disabled_grid=bytes(emu.mem_read(pointer,row['grid_span']))
            if rva==0x11e6f0:
                corners=struct.unpack('<8h',emu.mem_read(base+0x11ce640,16))
                quads.append(list(zip(corners[::2],corners[1::2])))
                current=emu.reg_read(UC_X86_REG_RSP)
                assert current%16==8
                target=get(current,'Q');emu.reg_write(UC_X86_REG_RSP,current+8)
                emu.reg_write(UC_X86_REG_RIP,target);return
            if bytes(emu.mem_read(address,1))==b'\xe8':
                raw=bytes(emu.mem_read(address,5))
                target=rva+5+struct.unpack_from('<i',raw,1)[0]
                if target in [capture,manifest['symbols'].get('capture_ground_border_rdi'),extend,0x1a07d0]:return
                if target==0x120f70:
                    rectangles.append(struct.unpack('<4h',emu.mem_read(base+0x11ce660,8)))
                # Native backdrop/quad allocation, cookie check and optional
                # decorations do not need the Unity renderer for this test.
                emu.reg_write(UC_X86_REG_RIP,address+5)
        h=uc.hook_add(UC_HOOK_CODE,step)
        try:uc.emu_start(base+int(row['function'],16),base+sentinel+1,count=90000)
        finally:uc.hook_del(h)
        assert reached,(stage,'native stage did not return')
        assert uc.reg_read(UC_X86_REG_RSP)==SP+8,(stage,'stack imbalance')
        assert bytes(uc.mem_read(actors,0x5000))==actor_before,'Actor/gameplay state changed'
        assert bytes(uc.mem_read(base+0x12cea90,16))==camera_before,'Camera changed'
        eligible=row['compatible'] and phase==6 and rotation==64 and 512<=depth<=4096 and not corrupt
        if eligible:
            assert first and get(data+0x44,'H')==stage and len(originals)==row['point_count'],(stage,'grid not captured')
            # At close zoom the native beach already covers every border.
            # No mutation is then needed, but the coverage check still applies.
            assert get(data+0x46,'B')==int(get(data+0x40,'I')!=0),(stage,depth,'border correction did not run')
            pointer=get(data+0x48,'Q')
            after=bytes(uc.mem_read(pointer,row['grid_span']))
            points=[struct.unpack_from('<hh',after,offset) for offset in row['grid_offsets']]
            padding=set(range(0,row['grid_span'],4))-set(row['grid_offsets'])
            assert all(after[p:p+4]==raw_grid[p:p+4] for p in padding),(stage,'grid padding changed')
            cols=row['point_count']//len(row['z_rows'])
            # All interior coordinates remain bit-for-bit native. Only left,
            # right and front borders may have been extended.
            final_drawn_row=max(row['drawn_grid_indices'])//cols
            for i,point in enumerate(points):
                if i%cols not in [0,cols-1] and i//cols != final_drawn_row:
                    offset=row['grid_offsets'][i]
                    assert after[offset:offset+4]==originals[i],(stage,i,'interior changed')
            top=max(points[0][1],points[cols-1][1])+1
            for y in range(top,241,8):
                for x in [0,40,80,120,160,200,240,280,319]:
                    assert any(in_triangle((x,y),q[0],q[1],q[2]) or in_triangle((x,y),q[1],q[3],q[2]) for q in quads),(stage,center,depth,x,y,'ground gap')
            # Native clearing must not paint black over the extended bottom.
            assert not any(w>=320 and y>=top and height>0 for x,y,w,height in rectangles),(stage,'black bottom fill',rectangles)
        else:
            assert get(data+0x46,'B')==0,(stage,'unexpected correction')
            if corrupt:
                pointer=get(data+0x48,'Q')
                assert bytes(uc.mem_read(pointer,row['grid_span']))==disabled_grid,'Partial mutation after failed validation'
        return len(quads)

    for stage in manifest['floor_extension']['supported_stages']:
        stage_case(stage)
    # Newly accepted alternate draw branches, padded rows and deeper back edge.
    for stage in (47,97,101,111,113):
        for center in (-160,512):
            for depth in (668,2048):
                stage_case(stage,center,depth)
    for center in [-160,0,176,352,512]:
        for depth in [668,1024,1536,2048,3072]:
            stage_case(7,center,depth)
            stage_case(10,center,depth)
    stage_case(7,phase=5)
    stage_case(7,rotation=0)
    stage_case(7,depth=4097)
    stage_case(7,corrupt=True)
    return count
