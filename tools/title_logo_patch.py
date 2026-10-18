"""Embedded PNG wordmark, loaded and owned by the native texture manager.

Resource registration mirrors 3a544..3a627 (the game's own PNG path).
The private UI texture state uses the existing type-2 pixel UV conversion.
No title texture replacement, managed assembly patch, file I/O or extra thread.
"""
import hashlib
import math
import struct
from pathlib import Path

PNG = Path(__file__).resolve().parents[1]/'assets/branding/waters-edition-blue.png'

def emit_title_logo(emit, mem, data):
    png=PNG.read_bytes()
    assert png[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack('>II',png[16:24])
    assert (width,height)==(2149,732)
    cache=data+0x1c00;obj=data+0x1c40;vt=data+0x1c80
    # Crop transparent outer padding by UVs; keep the source PNG unchanged.
    bounds=(36,153,2113,596)
    initialize=emit('title_logo_initialize',f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x30
        mov rbx, qword ptr {mem(0x644a30)}
        test rbx, rbx
        je unavailable
        cmp qword ptr {mem(0x8602e8)}, 0
        je unavailable
        cmp qword ptr [rbx+0x60], 0
        je unavailable
        cmp qword ptr {mem(cache)}, rbx
        je cached
        mov qword ptr {mem(cache)}, rbx
        mov qword ptr {mem(cache+8)}, 0
        mov qword ptr {mem(cache+16)}, 0
        lea rsi, [rbx+8]
        mov rcx, rsi
        mov rax, qword ptr [rsi]
        call qword ptr [rax]
        mov ecx, 0x30
        mov edx, 1
        mov r8d, 8
        call 0x261290
        test rax, rax
        je unlock
        mov rdi, rax
        mov qword ptr [rdi+0x10], 0
        mov dword ptr [rdi+0x18], -1
        mov dword ptr [rdi+8], 1
        lea rax, {mem(0x51a430)}
        mov qword ptr [rdi], rax
        lea rax, {mem(data+0x4000)}
        mov qword ptr [rdi+0x20], rax
        mov dword ptr [rdi+0x28], {len(png)}
        mov rcx, qword ptr [rbx+0x60]
        mov rdx, rdi
        call 0x5b410
        test rax, rax
        je release
        mov qword ptr {mem(cache+8)}, rax
        mov qword ptr {mem(cache+16)}, rdi
        mov rcx, qword ptr [rbx+0x68]
        mov qword ptr [rcx+rax*8-8], rdi
        mov qword ptr [rsp+0x20], rdi
        lea rcx, [rbx+0x90]
        lea rdx, [rsp+0x20]
        call 0x5b620
        jmp unlock
    release:
        mov rcx, rdi
        mov edx, 1
        call 0x5b7d0
    unlock:
        mov rcx, rsi
        mov rax, qword ptr [rsi]
        call qword ptr [rax+0x10]
    cached:
        mov rax, qword ptr {mem(cache+16)}
        test rax, rax
        je unavailable
        cmp dword ptr [rax+0x18], -1
        je unavailable
        mov rax, qword ptr {mem(cache+8)}
        jmp done
    unavailable:
        xor eax, eax
    done:
        add rsp, 0x30
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    getter=emit('title_logo_resource',f'mov rax, qword ptr {mem(cache+8)}; ret')
    bind=emit('title_logo_bind',f'''
        sub rsp, 0x28
        lea r10, {mem(vt)}
        lea rax, {mem(0x690e0)}
        mov qword ptr [r10], rax
        lea rax, {mem(0x69120)}
        mov qword ptr [r10+8], rax
        lea rax, {mem(getter)}
        mov qword ptr [r10+16], rax
        lea rax, {mem(0x9d50)}
        mov qword ptr [r10+24], rax
        lea rax, {mem(0x3c030)}
        mov qword ptr [r10+32], rax
        mov qword ptr [r10+40], rax
        lea r9, {mem(obj)}
        mov qword ptr [r9], r10
        mov rcx, qword ptr {mem(0x644a10)}
        mov rdx, qword ptr [rcx+0x4d0]
        movsxd rax, dword ptr [rcx+0x4e0]
        inc dword ptr [rcx+0x4e0]
        imul rax, rax, 80
        add rdx, rax
        mov dword ptr [rdx], 0x22
        mov qword ptr [rdx+8], r9
        mov dword ptr [rdx+16], {width}
        mov dword ptr [rdx+20], {height}
        mov dword ptr [rdx+24], 4
        call 0x60bf0
        add rsp, 0x28
        ret
    ''')
    quad=emit('title_logo_quad',f'''
        sub rsp, 0x78
        movaps xmmword ptr [rsp+0x60], xmm6
        movaps xmmword ptr [rsp+0x50], xmm7
        movaps xmmword ptr [rsp+0x40], xmm8
        movaps xmm8, xmm3
        movaps xmmword ptr [rsp+0x30], xmm9
        movaps xmm9, xmm2
        movaps xmmword ptr [rsp+0x20], xmm10
        movaps xmm10, xmm1
        call {bind:#x}
        call 0x12c10
        cmp byte ptr {mem(cache+0x30)}, 0
        je native_quad
        # Additive halo: native blend (ADD, SRC_ALPHA, FIX white), as used
        # by the game's own additive effects at 11e303. Black outlines add 0.
        sub rsp, 0x30
        xor ecx, ecx
        mov edx, 2
        mov r8d, 10
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0xffffff
        call 0x6fd70
        add rsp, 0x30
    native_quad:
        jmp 0x12cee
    ''')
    fb=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
    display_height=124*(bounds[3]-bounds[1])/(bounds[2]-bounds[0])
    # Soft cyan light behind the unchanged blue lettering. Every copy uses
    # identical scale/UVs; the final opaque face restores standard alpha blend.
    halo=[]
    for radius,alpha in ((2.2,18),(1.1,36)):
        for i in range(8):
            a=i*math.pi/4
            halo.append((293+radius*math.cos(a),160+radius*math.sin(a),(alpha<<24)|0xffd080,1))
    layers=halo+[(293,160,0xffffffff,0)]
    layer_asm=[]
    for x,y,color,is_glow in layers:
        layer_asm.append(f'''
            mov byte ptr {mem(cache+0x30)}, {is_glow}
            mov ecx, {color}
            call 0x6c550
            mov eax, {fb(x)}
            movd xmm1, eax
            mov eax, {fb(y)}
            movd xmm2, eax
            mov eax, 509
            cvtsi2ss xmm3, eax
            call {quad:#x}
        ''')
    draw=emit('title_logo_draw',f'''
        sub rsp, 0x58
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je unavailable
        cmp qword ptr [rcx+0x4d0], 0
        je unavailable
        movsxd rax, dword ptr [rcx+0x4e0]
        add rax, 180
        cmp rax, qword ptr [rcx+0x4d8]
        jae unavailable
        call {initialize:#x}
        test rax, rax
        je unavailable
        {chr(10).join(f'mov dword ptr [rsp+{offset}], {fb(value)}' for offset,value in zip((0x20,0x28,0x30,0x38,0x40,0x48),(124,display_height,*bounds)))}
        {chr(10).join(layer_asm)}
        mov eax, 1
        jmp done
    unavailable:
        xor eax, eax
    done:
        add rsp, 0x58
        ret
    ''')
    return draw,png,dict(png_sha256=hashlib.sha256(png).hexdigest(),png_bytes=len(png),
        png_rva=data+0x4000,cache_rva=cache,size=[width,height],uv_bounds=list(bounds),
        screen_rect=[293,160,124,display_height],glow='16 low-opacity additive cyan offsets; unchanged opaque face last',
        ownership='Native PNG resource manager; one cached texture per manager lifetime')
