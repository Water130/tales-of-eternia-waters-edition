"""Scoped water-only rendering: native waves, separate rain blend and fades.

The original renderer assumes Chat's cinematic state. In an ordinary spell its
opaque branch draws black texels over the battlefield. Keep its mesh/UV motion,
but explicitly bind resource 174: additive rain, denser alpha-blended waves.
"""

def wire(emit, mem, jump, pe, relocate, state):
    active, fade, layer = state+0x5670, state+0x5678, state+0x567c
    render=emit('tidal_water_render',f'''
        push rbx; push rsi; push rdi; sub rsp, 0xb0; mov rbx, rcx
        movzx eax, word ptr [rbx+0x38]
        cmp eax, 192; jae done
        mov edx, 191; sub edx, eax; cmp eax, edx; cmova eax, edx
        cmp eax, 24; jbe ramp; mov eax, 24
    ramp:
        shl eax, 8; xor edx, edx; mov ecx, 24; div ecx
        test eax, eax; je done
        mov dword ptr {mem(fade)}, eax
        mov qword ptr {mem(active)}, rbx
        # b7460 changes draw globals outside its individual quad submissions.
        # Preserve the whole input state so later battlefield draws do not
        # inherit its dark tint, texture selection or blending mode.
        lea rsi, {mem(0x11ce640)}; lea rdi, [rsp+0x20]
        mov ecx, 18; rep movsq
        mov rcx, rbx; call 0xb7460
        lea rsi, [rsp+0x20]; lea rdi, {mem(0x11ce640)}
        mov ecx, 18; rep movsq
        mov qword ptr {mem(active)}, 0
    done: add rsp, 0xb0; pop rdi; pop rsi; pop rbx; ret
    ''')
    quad=emit('tidal_water_quad',f'''
        cmp qword ptr {mem(active)}, 0; je native
        push rbx; sub rsp, 0x40
        movzx eax, word ptr {mem(0x11ce680)}; mov dword ptr [rsp+0x20], eax
        mov eax, dword ptr {mem(0x11ce6b4)}; mov dword ptr [rsp+0x24], eax
        mov eax, dword ptr {mem(0x11ce6b8)}; mov dword ptr [rsp+0x28], eax
        movzx eax, word ptr {mem(0x11ce686)}; mov dword ptr [rsp+0x2c], eax
        mov eax, dword ptr {mem(0x11ce6c0)}; mov dword ptr [rsp+0x30], eax
        movzx ebx, word ptr {mem(0x11ce6b2)}
        mov word ptr {mem(0x11ce680)}, 1
        mov dword ptr {mem(0x11ce6b4)}, 1
        mov dword ptr {mem(0x11ce6b8)}, 0
        mov word ptr {mem(0x11ce6b2)}, 52
        and word ptr {mem(0x11ce686)}, 0xff9f
        cmp dword ptr {mem(layer)}, 1; je water_blend
        or word ptr {mem(0x11ce686)}, 0x20
    water_blend:
        mov dword ptr {mem(0x11ce6c0)}, 0
        call 0x11ed60
        mov word ptr {mem(0x11ce6b2)}, bx
        mov eax, dword ptr [rsp+0x20]; mov word ptr {mem(0x11ce680)}, ax
        mov eax, dword ptr [rsp+0x24]; mov dword ptr {mem(0x11ce6b4)}, eax
        mov eax, dword ptr [rsp+0x28]; mov dword ptr {mem(0x11ce6b8)}, eax
        mov eax, dword ptr [rsp+0x2c]; mov word ptr {mem(0x11ce686)}, ax
        mov eax, dword ptr [rsp+0x30]; mov dword ptr {mem(0x11ce6c0)}, eax
        add rsp, 0x40; pop rbx; ret
    native: jmp 0x11ed60
    ''')
    copy=emit('tidal_rain_rectangle',f'''
        cmp qword ptr {mem(active)}, 0; je native
        sub rsp, 0x48
        mov rax, qword ptr {mem(0x11ce640)}; mov qword ptr [rsp+0x20], rax
        mov rax, qword ptr {mem(0x11ce648)}; mov qword ptr [rsp+0x28], rax
        mov rax, qword ptr {mem(0x11ce670)}; mov qword ptr [rsp+0x30], rax
        mov rax, qword ptr {mem(0x11ce678)}; mov qword ptr [rsp+0x38], rax
        mov eax, dword ptr {mem(0x11ce660)}
        mov dword ptr {mem(0x11ce640)}, eax
        mov dword ptr {mem(0x11ce644)}, eax
        mov dword ptr {mem(0x11ce648)}, eax
        mov dword ptr {mem(0x11ce64c)}, eax
        mov ax, word ptr {mem(0x11ce664)}
        add word ptr {mem(0x11ce644)}, ax; add word ptr {mem(0x11ce64c)}, ax
        mov ax, word ptr {mem(0x11ce666)}
        add word ptr {mem(0x11ce64a)}, ax; add word ptr {mem(0x11ce64e)}, ax
        mov eax, dword ptr {mem(0x11ce670)}
        mov dword ptr {mem(0x11ce674)}, eax
        mov dword ptr {mem(0x11ce678)}, eax
        mov dword ptr {mem(0x11ce67c)}, eax
        call {quad:#x}
        mov rax, qword ptr [rsp+0x20]; mov qword ptr {mem(0x11ce640)}, rax
        mov rax, qword ptr [rsp+0x28]; mov qword ptr {mem(0x11ce648)}, rax
        mov rax, qword ptr [rsp+0x30]; mov qword ptr {mem(0x11ce670)}, rax
        mov rax, qword ptr [rsp+0x38]; mov qword ptr {mem(0x11ce678)}, rax
        add rsp, 0x48; ret
    native: jmp 0x11e4d0
    ''')
    for site in (0xb778a,0xb781f,0xb78af):
        hook=emit(f'tidal_copy_{site:x}',f'mov dword ptr {mem(layer)}, 0; call {copy:#x}; jmp {site+5:#x}')
        jump(site,5,hook,'Water-only rain: translucent upper rectangles with the same fade as lower rain')
    for site in (0xb77c4,0xb7854,0xb78e4,0xb7aba,0xb7b10,0xb7b72):
        hook=emit(f'tidal_quad_{site:x}',f'mov dword ptr {mem(layer)}, {int(site>=0xb7aba)}; call {quad:#x}; jmp {site+5:#x}')
        jump(site,5,hook,'Water-only spell: scoped native wave blending')
    alpha=emit('tidal_water_alpha',f'''
        push rax; push rcx; push rdx; push r8
        cmp qword ptr {mem(active)}, 0; je done
        mov ecx, dword ptr {mem(fade)}
        # Fade RGB as well as alpha: additive GPU paths can ignore alpha.
        # Each corner keeps its own native color and gradient.
        xor edx, edx
    vertex:
        cmp dword ptr {mem(layer)}, 1; jne channels
        mov byte ptr [rbx+rdx+7], 232
    channels:
        xor r8d, r8d
    channel:
        lea rax, [rbx+rdx]; add rax, r8
        movzx eax, byte ptr [rax+4]; imul eax, ecx; shr eax, 8
        push rdx; add rdx, r8; mov byte ptr [rbx+rdx+4], al; pop rdx
        inc r8d; cmp r8d, 4; jb channel
        add edx, 16; cmp edx, 64; jb vertex
    done: pop r8; pop rdx; pop rcx; pop rax
        {relocate(pe.get_data(0x11f0aa,7),0x11f0aa)}
        jmp 0x11f0b1
    ''')
    jump(0x11f0aa,7,alpha,'Water-only spell: fade all submitted vertices in and out')
    return dict(render=render,quad=quad,copy=copy,alpha=alpha,active=active,fade=fade,layer=layer,wave_alpha=232,
                fade_ticks=24,resource=174,runtime_validated=False)
