"""Native textured quads with per-vertex colors, scoped to damage digits only.

The vertex format is the native 12e30 textured primitive (UV/XYZ floats),
with its supported RGBA8888 field added, as in mastery_tree_links.
The normal 1227b0 texture binding and its two HD outline/face passes remain.
"""


def emit_gradient(emit, mem, jump, data):
    context = data + 0x13c0
    # Same private call ABI as 14360: integer xy/z, UV xy in r9/stack20,
    # texture width/height stack38/40, on-screen width/height stack48/50.
    vertices = []
    for index, (right, bottom) in enumerate(((False, False), (True, False),
                                             (False, True), (True, True))):
        off = index * 24
        vertices.append(f'''
            cvtsi2ss xmm0, r9d
            {'cvtsi2ss xmm4, dword ptr [rsp+0x40]; addss xmm0, xmm4' if right else ''}
            movss dword ptr [r11+{off}], xmm0
            cvtsi2ss xmm0, dword ptr [rsp+0x28]
            {'cvtsi2ss xmm4, dword ptr [rsp+0x48]; addss xmm0, xmm4' if bottom else ''}
            movss dword ptr [r11+{off+4}], xmm0
            mov eax, dword ptr {mem(context+4+int(bottom)*4)}
            mov dword ptr [r11+{off+8}], eax
            cvtsi2ss xmm0, ecx
            {'cvtsi2ss xmm4, dword ptr [rsp+0x50]; addss xmm0, xmm4' if right else ''}
            movss dword ptr [r11+{off+12}], xmm0
            cvtsi2ss xmm0, edx
            {'cvtsi2ss xmm4, dword ptr [rsp+0x58]; addss xmm0, xmm4' if bottom else ''}
            movss dword ptr [r11+{off+16}], xmm0
            cvtsi2ss xmm0, r8d
            movss dword ptr [r11+{off+20}], xmm0
        ''')
    draw = emit('damage_gradient_quad', f'''
        cmp byte ptr {mem(context)}, 0; je native
        mov r10, qword ptr {mem(0x644a58)}
        test r10, r10; je native
        mov eax, dword ptr [r10+0x2000008]
        lea r11, [r10+rax+8]
        add eax, 96; cmp eax, 0x2000000; ja native
        mov dword ptr [r10+0x2000008], eax
        {''.join(vertices)}
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx; je done
        mov rdx, qword ptr [rcx+0x4d0]
        test rdx, rdx; je done
        movsxd rax, dword ptr [rcx+0x4e0]
        cmp rax, qword ptr [rcx+0x4d8]; jae done
        inc dword ptr [rcx+0x4e0]
        imul rax, rax, 80; add rdx, rax
        mov dword ptr [rdx], 5
        mov dword ptr [rdx+8], 4
        mov dword ptr [rdx+12], 0x80019f
        mov dword ptr [rdx+16], 4
        mov qword ptr [rdx+24], 0
        mov qword ptr [rdx+32], r11
        jmp 0x60bf0
    native: jmp 0x14360
    done: ret
    ''')
    for site in (0x122a90, 0x122bd9, 0x122d09):
        hook = emit(f'damage_gradient_pass_{site:x}', f'call {draw:#x}; jmp {site+5:#x}')
        jump(site, 5, hook, 'Two-tone native digit quad; all non-damage sprite calls remain native')
    return context
