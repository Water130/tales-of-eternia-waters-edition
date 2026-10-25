"""Compact party HUD with readable owned-spirit progress below portrait feet."""


def emit_hud_layout(emit, mem, jump, edit, data_rva, rect, save_ui, restore_ui):
    # Native formation restored by building from original; HUD portraits only.
    edit(0x80af8, b'\xb8\xec\x00\x00\x00', 'Portrait feet at Y=236 in lowered HUD')
    edit(0x80b1b, b'\x66\x41\x83\xe8\x1c', 'Portraits right four units within unchanged 48-unit slots')
    for metric, site, y in [(0,0xd1c23,208),(1,0xd1cd4,223)]:
        fn = emit(f'ui_hud_number_{metric}', f'''
            lea edx, [rdi{'+3' if metric == 0 else '-1'}]
            mov r8d, {y}
            # Original atlas, glyph dimensions and native kerning (12-4=8).
            # Native renderer anchors the final digit; four digits span 36.
            mov r9d, 4
            call 0x1114a0
            jmp {site+5:#x}
        ''')
        jump(site,5,fn,('Align HP glyph ink with gauge (+4 units)' if metric==0 else 'Preserve TP digit anchor'))

    from spirit_icon_patch import emit_spirit_icons
    icon = emit_spirit_icons(emit, mem, data_rva)
    draw = emit('ui_all_spirit_max', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        sub rsp, 0xf8
        {save_ui()}
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        cmp byte ptr [rbx+0x51], 0
        jne done
        movzx eax, byte ptr [rbx+0x4f]
        sub eax, 2
        cmp eax, 1
        ja done
        movzx r12d, byte ptr [rbx+0x4e]
        cmp r12d, 4
        jae done
        mov r14, qword ptr {mem(0x12cea60)}
        test r14, r14
        je done
        # Footer groups expand rightwards; the second mage follows the first
        # group if it is wide. All ten owned records fit without tiny rows.
        mov esi, -35
        xor ebp, ebp
        mov r11, qword ptr {mem(0x12cecd8)}
        test r11, r11
        je own_anchor
    previous_slot:
        cmp ebp, r12d
        jae own_anchor
        movzx edx, byte ptr [r11+0x4f]
        sub edx, 2
        cmp edx, 1
        ja next_slot
        add edx, 3
        xor ecx, ecx
        xor eax, eax
    count_previous:
        cmp byte ptr [r14+rcx*8+0xbb8], dl
        jne next_count
        cmp byte ptr [r14+rcx*8+0xbb9], 0
        je next_count
        inc eax
    next_count:
        inc ecx
        cmp ecx, 10
        jb count_previous
        test eax, eax
        je next_slot
        imul edx, ebp, 48
        sub edx, 35
        cmp esi, edx
        cmovl esi, edx
        imul eax, eax, 14
        lea esi, [rsi+rax+2]
    next_slot:
        inc ebp
        add r11, 0x248
        jmp previous_slot
    own_anchor:
        # Keele's 16-unit direction pad needs its own space when Meredy's
        # miniature group extends into his column.
        cmp byte ptr [rbx+0x4f], 2
        jne pad_space_done
        cmp esi, -35
        je pad_space_done
        add esi, 18
    pad_space_done:
        imul eax, r12d, 48
        sub eax, 35
        cmp esi, eax
        cmovl esi, eax
        mov ebp, 237
        xor edi, edi
    spirit:
        movzx eax, byte ptr [rbx+0x4f]
        inc eax
        cmp byte ptr [r14+rdi*8+0xbb8], al
        jne next_spirit
        cmp byte ptr [r14+rdi*8+0xbb9], 0
        je next_spirit
        mov rax, qword ptr {mem(0x644a58)}
        test rax, rax
        je done
        cmp dword ptr [rax+0x2000008], 0x1ffff00
        ja done
        call {icon:#x}
        movzx eax, word ptr [r14+rdi*8+0xbba]
        shr eax, 12
        mov edx, 10
        cmp eax, edx
        cmova eax, edx
        lea rdx, {mem(data_rva+0x700)}
        mov r13d, dword ptr [rdx+rdi*4]
        or r13d, 0xff000000
        lea rcx, {mem(data_rva+0x1980)}
        lea rcx, [rcx+rax*8]
        mov r12, rcx
        # Match the native font metrics, with no maximum-width clamp.
        mov eax, 5
        cvtsi2ss xmm1, eax
        # b480 increases glyph size by 0.5 for these native language IDs.
        # Measure the effective size, while passing nominal 5 to the drawer.
        cmp qword ptr {mem(0x644a18)}, 0
        je measure_ready
        movzx eax, word ptr {mem(0x11c9ce8)}
        lea edx, [rax-1]
        cmp dl, 5
        jbe adjusted_font
        cmp al, 10
        jb measure_ready
    adjusted_font:
        addss xmm1, dword ptr {mem(0x524860)}
    measure_ready:
        xor r8d, r8d
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        mov dword ptr [rsp+0x28], -1
        call 0xb240
        mov eax, 2
        cvtsi2ss xmm1, eax
        divss xmm0, xmm1
        lea eax, [rsi+87]
        cvtsi2ss xmm1, eax
        subss xmm1, xmm0
        mov rcx, r12
        mov eax, 264
        cvtsi2ss xmm2, eax
        mov eax, 510
        cvtsi2ss xmm3, eax
        mov dword ptr [rsp+0x20], 0x40a00000
        mov dword ptr [rsp+0x28], r13d
        mov byte ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x40], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
        add esi, 14
    next_spirit:
        inc edi
        cmp edi, 10
        jb spirit
    done:
        {restore_ui()}
        add rsp, 0xf8
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        jmp 0xd1e5b
    ''')
    jump(0xd1d46,7,draw,'Owned Craymel miniatures and 0/10 through MAX below portraits')
