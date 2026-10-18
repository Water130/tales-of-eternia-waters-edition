"""Extend only projected outside ground tiles; preserve camera, backdrop and gameplay.

Native grid points are captured without changing projection outputs. The temporary
grid is adjusted only at the first ground draw, after backdrop anchors were used.
Only audited flat rectangular grids with one recognised ground draw are eligible.
"""
import json, struct
from pathlib import Path

def emit_floor(emit, mem, edit, data_rva):
    report=json.loads((Path(__file__).resolve().parent.parent/'audit/build-25190541/camera_floor_geometry.json').read_text())
    stages=report['stages']
    if len(stages)>128:raise ValueError('Stage table exceeds reserved storage')
    state=data_rva+0x40
    mappings=data_rva+0x300
    table=data_rva+0x800
    save='pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    restore='pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    capture=emit('capture_ground_border',f'''
        sub rsp, 0x28
        call 0x1a07d0
        lea rsp, [rsp+0x28]
        {save}
        lea r11, {mem(state)}
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne disabled
        cmp byte ptr {mem(data_rva+0x20)}, 1
        jne disabled
        cmp word ptr {mem(0x12cea90)}, 64
        jne disabled
        cmp dword ptr {mem(0x12cea92)}, 0
        jne disabled
        movsx eax, word ptr {mem(0x12cea9c)}
        cmp eax, 512
        jl disabled
        cmp eax, 4096
        jg disabled
        movzx eax, word ptr {mem(0x12d0eb2)}
        cmp eax, {len(stages)}
        jae disabled
        mov r8d, eax
        shl eax, 4
        lea r10, {mem(table)}
        add r10, rax
        cmp word ptr [r10+8], 0
        je disabled
        movsx ecx, word ptr {mem(0x8c9730)}
        movsx edx, word ptr {mem(0x8c9734)}
        cmp cx, word ptr [r10]
        jne existing_grid
        cmp dx, word ptr [r10+6]
        jne existing_grid
        mov dword ptr [r11], 0
        mov word ptr [r11+4], r8w
        mov byte ptr [r11+6], 0
        mov qword ptr [r11+8], rbx
        movzx eax, word ptr [r10+8]
        lea rax, [rbx+rax*4]
        mov qword ptr [r11+16], rax
    existing_grid:
        cmp word ptr [r11+4], r8w
        jne disabled
        cmp byte ptr [r11+6], 0
        jne disabled
        cmp rbx, qword ptr [r11+8]
        jb disabled
        cmp rbx, qword ptr [r11+16]
        jae disabled
        lea rax, [rsp+64]
        cmp rbx, rax
        jbe disabled
        add rax, 0x800
        cmp rbx, rax
        jae disabled
        cmp dword ptr {mem(0x8c9728)}, 0
        jle finished
        mov eax, dword ptr {mem(0x8c9720)}
        mov r8d, dword ptr {mem(0x8c9724)}
        mov r9d, eax
        and r9d, 0xffff
        shl r8d, 16
        or r9d, r8d
        cmp cx, word ptr [r10]
        jne right_border
        cmp eax, -16
        jle right_border
        mov eax, -16
    right_border:
        cmp cx, word ptr [r10+2]
        jne front_border
        cmp eax, 336
        jge front_border
        mov eax, 336
    front_border:
        cmp dx, word ptr [r10+4]
        jne pack_point
        cmp dword ptr {mem(0x8c9724)}, 256
        jge pack_point
        mov r8d, 0x01000000
    pack_point:
        and eax, 0xffff
        or eax, r8d
        cmp eax, r9d
        je finished
        mov ecx, dword ptr [r11]
        cmp ecx, 64
        jae disabled
        shl ecx, 4
        lea r10, {mem(mappings)}
        add r10, rcx
        mov dword ptr [r10], r9d
        mov dword ptr [r10+4], eax
        mov qword ptr [r10+8], rbx
        inc dword ptr [r11]
        jmp finished
    disabled:
        mov dword ptr [r11], 0
        mov word ptr [r11+4], 0xffff
    finished:
        {restore}
        ret
    ''')
    draw=emit('extend_ground_border',f'''
        {save}
        lea r11, {mem(state)}
        cmp byte ptr [r11+6], 0
        jne draw_native
        movzx eax, word ptr {mem(0x12d0eb2)}
        cmp ax, word ptr [r11+4]
        jne draw_native
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne draw_native
        mov r8d, dword ptr [r11]
        test r8d, r8d
        je draw_native
        cmp r8d, 64
        ja draw_native
        lea rax, [rsp+64]
        mov rdx, qword ptr [r11+8]
        cmp rdx, rax
        jbe draw_native
        add rax, 0x800
        cmp qword ptr [r11+16], rax
        ja draw_native
        lea r10, {mem(mappings)}
        mov r9d, r8d
    validate:
        mov rdx, qword ptr [r10+8]
        cmp rdx, qword ptr [r11+8]
        jb draw_native
        cmp rdx, qword ptr [r11+16]
        jae draw_native
        mov eax, dword ptr [r10]
        cmp dword ptr [rdx], eax
        jne draw_native
        add r10, 16
        dec r9d
        jne validate
        mov byte ptr [r11+6], 1
        lea r10, {mem(mappings)}
    apply:
        mov rdx, qword ptr [r10+8]
        mov eax, dword ptr [r10+4]
        mov dword ptr [rdx], eax
        mov eax, dword ptr [r10]
        mov r9d, dword ptr [r10+4]
        cmp dword ptr [rcx+0x20], eax
        jne corner_b
        mov dword ptr [rcx+0x20], r9d
    corner_b:
        cmp dword ptr [rcx+0x24], eax
        jne corner_c
        mov dword ptr [rcx+0x24], r9d
    corner_c:
        cmp dword ptr [rcx+0x28], eax
        jne corner_d
        mov dword ptr [rcx+0x28], r9d
    corner_d:
        cmp dword ptr [rcx+0x2c], eax
        jne next_mapping
        mov dword ptr [rcx+0x2c], r9d
    next_mapping:
        add r10, 16
        dec r8d
        jne apply
    draw_native:
        {restore}
        jmp 0x11e6f0
    ''')
    payload=bytearray(len(stages)*16)
    edited=set()
    for row in stages:
        if not row['compatible']:continue
        xmin,xmax=row['drawn_bounds'][0]
        near=row['drawn_bounds'][2][0]
        far=row['bounds'][2][1]
        struct.pack_into('<hhhhh',payload,row['stage']*16,xmin,xmax,near,far,row['point_count'])
        # Forest variants 6/7/8 share da330. Its far background starts at
        # world (-384,0,576), beyond the ground's Z=256. Four native 128-pixel
        # tiles cover 512 pixels. At native minimum depth 512, projecting the
        # audited 1024-world-unit width is narrower than those tiles, so this
        # Left edge uses the offset forest backdrop; right edge still uses the
        # ground boundary. A 576 minimum depth covers its fixed 512-pixel width.
        camera_far = 576 if row['function']=='0xda330' else far
        struct.pack_into('<hh',payload,row['stage']*16+10,camera_far,576 if row['function']=='0xda330' else 512)
        for address,destination,label in [(row['callsite'],capture,'Capture audited ground grid'),
                                          (row['floor_calls'][0],draw,'Extend audited ground border at draw')]:
            rva=int(address,16)
            if rva in edited:continue
            edit(rva,b'\xe8'+struct.pack('<i',destination-rva-5),f'{label} {rva:x}')
            edited.add(rva)
    return dict(supported_stages=[r['stage'] for r in stages if r['compatible']],
                excluded_stages=[r['stage'] for r in stages if not r['compatible']],
                stage_count=len(stages),pixel_bounds=[-16,336,256],
                limits='Audited flat grids only, normal rotation (64,0,0), camera depth 512..4096; outside tiles may stretch.'),bytes(payload)
