"""Draw the game's cage_pic atlas through its native resource/render pipeline.

Catalog: root[7] -> 423490 -> 4bd230, item 4 = asset 07010021,
ten palettes at 4c26b0. Private texture-state objects use native UV conversion.
The game owns loading/caching/unloading; no file copies, new handles or threads.
"""

def emit_spirit_icons(emit, mem, data_rva):
    getter=emit('ui_spirit_texture_resource', f'''
        sub rsp, 0x48
        mov r9d, 4
        mov eax, dword ptr [rcx+0x14]
        mov dword ptr [rsp+0x20], eax
        mov dword ptr [rsp+0x28], 0
        mov byte ptr [rsp+0x30], 0
        mov rcx, qword ptr {mem(0x644a28)}
        test rcx, rcx
        je unavailable
        mov edx, 7
        xor r8d, r8d
        call 0xfb40
        # Resolve the native lazy texture object even for palette zero. The
        # catalogue returns an opaque resource ID, not the GPU texture handle.
        mov qword ptr [rsp+0x38], rax
        test rax, rax
        je unavailable
        mov rcx, qword ptr {mem(0x644a30)}
        test rcx, rcx
        je unavailable
        mov rdx, rax
        call 0x5c170
        mov rax, qword ptr [rsp+0x38]
        add rsp, 0x48
        ret
    unavailable:
        xor eax, eax
        add rsp, 0x48
        ret
    ''')
    # Called from the same prologue as 12cb0. EDI remains the spirit index.
    bind=emit('ui_bind_spirit_atlas', f'''
        sub rsp, 0x28
        lea r10, {mem(data_rva+0x1900)}
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
        imul eax, edi, 24
        lea r9, {mem(data_rva+0x1800)}
        add r9, rax
        mov qword ptr [r9], r10
        mov dword ptr [r9+8], 7
        mov dword ptr [r9+12], 0
        mov dword ptr [r9+16], 4
        mov dword ptr [r9+20], edi
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        mov rdx, qword ptr [rcx+0x4d0]
        test rdx, rdx
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        cmp rax, qword ptr [rcx+0x4d8]
        jae done
        inc dword ptr [rcx+0x4e0]
        imul rax, rax, 80
        add rdx, rax
        mov dword ptr [rdx], 0x22
        mov qword ptr [rdx+8], r9
        # Type-2 UV conversion divides by these dimensions at state+1d4/1d8.
        # Its fifth argument is state+8, not state. 1/1 sampled outside atlas.
        mov dword ptr [rdx+16], 240
        mov dword ptr [rdx+20], 120
        mov dword ptr [rdx+24], 4
        call 0x60bf0
    done:
        add rsp, 0x28
        ret
    ''')
    draw=emit('ui_draw_spirit_atlas', f'''
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
        jmp 0x12ce9
    ''')
    return emit('ui_spirit_icon', f'''
        sub rsp, 0x58
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        cmp qword ptr [rcx+0x4d0], 0
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        add rax, 9
        cmp rax, qword ptr [rcx+0x4d8]
        jae done
        cmp edi, 10
        jae done
        # Unlike PSX battle sprites, this atlas path inherits renderer RGBA.
        # Always submit opaque white, as the native menu atlas callers do.
        mov ecx, 0xffffffff
        call 0x6c550
        # Five frames per spirit, two groups of five spirits, 24x24 cells.
        mov eax, edi
        xor edx, edx
        mov ecx, 5
        div ecx
        imul eax, eax, 120
        imul edx, edx, 24
        # The atlas contains front through back over a half turn. Reflect
        # intermediate poses for the other half: eight continuous directions.
        # Battle ticks freeze with the battle rather than using a new timer.
        mov r8d, dword ptr {mem(0x12cea40)}
        shr r8d, 3
        and r8d, 7
        mov r10d, r8d
        mov r9d, 8
        sub r9d, r8d
        cmp r8d, 4
        cmova r8d, r9d
        imul r8d, r8d, 24
        add eax, r8d
        lea r9d, [rax+24]
        cmp r10d, 4
        jbe uv_ready
        xchg eax, r9d
    uv_ready:
        cvtsi2ss xmm0, eax
        movss dword ptr [rsp+0x30], xmm0
        cvtsi2ss xmm0, r9d
        movss dword ptr [rsp+0x40], xmm0
        cvtsi2ss xmm0, edx
        movss dword ptr [rsp+0x38], xmm0
        add edx, 24
        cvtsi2ss xmm0, edx
        movss dword ptr [rsp+0x48], xmm0
        mov dword ptr [rsp+0x20], 0x41000000
        mov dword ptr [rsp+0x28], 0x41000000
        lea eax, [rsi+83]
        cvtsi2ss xmm1, eax
        lea eax, [rbp+17]
        cvtsi2ss xmm2, eax
        mov eax, 509
        cvtsi2ss xmm3, eax
        call {draw:#x}
    done:
        add rsp, 0x58
        ret
    ''')
