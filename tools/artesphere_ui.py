"""Seven rows in the native arte editor; isolated expanded shortcut scratch.
Native assignment states, learned-arte list, descriptions and controller hints
remain in use. Expanded pairs never occupy another player's save-data slots.
"""
import struct


def emit_ui(emit,mem,jump,edit,state,profile,extra,strings,loc,symbols,
            initialize,enter,leave,name_table,L2,R2):
    page=state+1
    scratch=state+0xc00
    # EAX = selected character, or -1 for an invalid/empty native party slot.
    character=emit('artesphere_menu_character',f'''
        movzx ecx, byte ptr {mem(0x111a674)}
        cmp word ptr {mem(0x1119f98)}, 7
        jb party
        movsx ecx, word ptr {mem(0x1119f9e)}
    party:
        mov eax, -1
        cmp ecx, 5
        ja done
        lea rdx, {mem(0x11cad10)}
        movzx eax, word ptr [rdx+rcx*2]
        dec eax
        cmp eax, 6
        jbe done
        mov eax, -1
    done:
        ret
    ''')
    # Native pair addressing becomes (row-4)*2 + partySlot*8.
    for at,off,delta in [(0x229b72,5,0),(0x229c37,5,1),(0x229cc3,5,1),
                         (0x22a3bd,4,0),(0x22a3c5,4,1),(0x22a57b,5,1),
                         (0x22ae04,4,0),(0x22ae0c,4,1),(0x22bd9c,5,1),
                         (0x226ca6,5,0),(0x226caf,4,1),(0x227881,5,1),
                         (0x228141,5,1)]:
        edit(at+off,struct.pack('<I',scratch-8+delta),'Expanded native shortcut address',False)
    for at,tail in [(0x229b6e,0x8a),(0x229c33,0x88),(0x229cbf,0x88),
                    (0x22a3ad,0x88),(0x22a577,0x8a),(0x22adfb,0x88),(0x22bd98,0x88),
                    (0x226ca2,0xb0),(0x22787d,0x88),(0x22813d,0x88)]:
        edit(at+3,bytes([tail]),'Eight-byte native editor pair stride',False)
    edit(0x229c6c,b'\x06','Navigate seventh native assignment row',False)
    # Four directional rows at y=75,89,103,117; three ally rows at 132,152,172.
    edit(0x22538e,b'\x0e','Directional highlight spacing',False)
    edit(0x2255a2,b'\x0e','Directional button spacing',False)
    edit(0x225677,b'\x0e','Directional row spacing',False)
    edit(0x22567a,struct.pack('<I',131),'End four directional rows',False)
    # Both the active hand and the dimmed assignment hand use legacy integer
    # coordinates (+16 at 250b50). Keep their native offset from the row text.
    for at in (0x2263a2,0x2263d2):
        edit(at,b'\x0e','Compact directional hand cursor spacing',False)
    for at in (0x2263b4,0x2263db):
        edit(at,b'\x14','Compact ally hand cursor spacing',False)
    for at in (0x2263bd,0x2263df):
        edit(at,b'\x29','Align ally hand cursor with native shortcut row',False)
    floats={0x524a48:20.,0x524c64:132.,0x524c74:135.25,0x524c84:139.5,0x524c90:142.5}
    for at,size,off,old in [(0x2253ce,8,4,0x524a48),(0x2253d6,8,4,0x524c64),
        (0x225409,9,5,0x524c74),(0x2256cf,9,5,0x524c84),(0x2256d8,9,5,0x524c90),
        (0x225800,8,4,0x524a48),(0x22580b,8,4,0x524c64),(0x22596c,8,4,0x524c64),
        (0x225a4a,8,4,0x524a48)]:
        target=state+0xc60+list(floats).index(old)*4
        edit(at+off,struct.pack('<i',target-at-size),'Compact native assignment layout',False)
    edit(0x225a6a,b'\x03','Render three native shortcut rows',False)
    pair_pointer=emit('artesphere_row_pointer',f"""
        lea r13, [rax*8+{scratch+1}]
        jmp 0x2256cf
    """)
    jump(0x2256c7,8,pair_pointer,'Three native ally commands in private editor storage')
    # Third row has no vanilla mouse descriptor: never overwrite right-list row 1.
    hitbox=emit('artesphere_row_hitbox',f"""
        cmp r15d, 2
        jne original
        lea r14, {mem(state+0xcc4)}
    original:
        movzx eax, byte ptr [r13]
        jmp 0x225705
    """)
    jump(0x225700,5,hitbox,'Keep third assignment hit box outside native list descriptors')
    # Temporarily append one bounded descriptor during the native mouse poll.
    # The native left-row callback already accepts index 6. Restore both the
    # count and unused descriptor immediately; no other menu owns this entry.
    save_desc=';'.join(f'mov rax, qword ptr [rbx+{i}]; mov qword ptr {mem(state+0xe00+i)}, rax'
                       for i in range(0,56,8))
    restore_desc=';'.join(f'mov rax, qword ptr {mem(state+0xe00+i)}; mov qword ptr [rbx+{i}], rax'
                          for i in range(0,56,8))
    geometry=';'.join(f'mov rax, qword ptr {mem(state+0xcc0+i)}; mov qword ptr [rbx+{i}], rax'
                      for i in range(0,32,8))
    mouse=emit('artesphere_native_mouse',f'''
        cmp word ptr {mem(0x1119f96)}, 0
        jne original
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne original
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne original
        cmp word ptr {mem(0x1119f98)}, 2
        ja original
        movzx eax, byte ptr {mem(0x111a674)}
        cmp eax, 4
        jae original
        lea r10, {mem(0x11cad38)}
        cmp byte ptr [r10+rax], 0
        je original
        cmp dword ptr {mem(0x86241c)}, 128
        jae original
        push rbx
        push rsi
        push rdi
        sub rsp, 0x40
        mov qword ptr [rsp+0x20], rcx
        mov qword ptr [rsp+0x28], rdx
        mov qword ptr [rsp+0x30], r8
        mov esi, dword ptr {mem(0x86241c)}
        imul eax, esi, 56
        lea rbx, {mem(0x860560)}
        add rbx, rax
        {save_desc}
        {geometry}
        mov dword ptr [rbx+0x20], 6
        mov dword ptr [rbx+0x24], 0
        lea rax, {mem(0x222960)}
        mov qword ptr [rbx+0x28], rax
        mov qword ptr [rbx+0x30], 1
        inc dword ptr {mem(0x86241c)}
        mov rcx, qword ptr [rsp+0x20]
        mov rdx, qword ptr [rsp+0x28]
        mov r8, qword ptr [rsp+0x30]
        call 0x1a5d0
        mov edi, eax
        {restore_desc}
        mov dword ptr {mem(0x86241c)}, esi
        mov eax, edi
        add rsp, 0x40
        pop rdi
        pop rsi
        pop rbx
        ret
    original:
        jmp 0x1a5d0
    ''')
    edit(0x228b14,b'\xe8'+struct.pack('<i',mouse-0x228b19),
         'Native mouse selection for seventh assignment row',False)
    text=symbols['settings_text']
    glyph=emit('artesphere_row_trigger',f"""
        cmp r15d, 2
        jne original
        sub rsp, 0x40
        # Native atlas cell 15: PS4 R2 and Xbox RT. Explicit families keep
        # both glyphs visible together, independently of the current device.
        mov ecx, 15
        xor edx, edx
        xor r8d, r8d
        mov eax, 0x41f80000
        movd xmm3, eax
        mov dword ptr [rsp+0x20], 0x432e0000
        mov dword ptr [rsp+0x28], 0
        mov dword ptr [rsp+0x30], 0x41400000
        mov dword ptr [rsp+0x38], 255
        call 0x13410
        mov ecx, 15
        mov edx, 3
        xor r8d, r8d
        mov eax, 0x423c0000
        movd xmm3, eax
        mov dword ptr [rsp+0x20], 0x432e0000
        mov dword ptr [rsp+0x28], 0
        mov dword ptr [rsp+0x30], 0x41400000
        mov dword ptr [rsp+0x38], 255
        call 0x13410
        {loc('trigger')}
        mov edx, 44
        mov r8d, 176
        mov r9d, -6
        mov eax, 0xffffffff
        call {text:#x}
        add rsp, 0x40
        jmp 0x2258ee
    original:
        cmp dword ptr [rbx+0x10], esi
        jbe original_skip
        jmp 0x225839
    original_skip:
        jmp 0x225846
    """)
    jump(0x225834,5,glyph,'Native R2 and RT button icons on seventh assignment row')
    # Build and commit only at editor-call boundaries, under the selected A/B scope.
    prepare=emit('artesphere_prepare_rows',f"""
        xor ecx, ecx
        lea r8, {mem(0x11cad3c)}
        lea r9, {mem(scratch)}
        lea r10, {mem(0x11cad10)}
        lea r11, {mem(extra)}
    next:
        mov eax, dword ptr [r8+rcx*4]
        mov dword ptr [r9+rcx*8], eax
        mov dword ptr [r9+rcx*8+4], 0
        movzx eax, word ptr [r10+rcx*2]
        dec eax
        cmp eax, 6
        ja skip
        movzx edx, byte ptr {mem(page)}
        lea eax, [rdx+rax*2]
        movzx eax, word ptr [r11+rax*2]
        mov word ptr [r9+rcx*8+4], ax
    skip:
        inc ecx
        cmp ecx, 4
        jb next
        ret
    """)
    commit=emit('artesphere_commit_rows',f"""
        xor ecx, ecx
        lea r8, {mem(0x11cad3c)}
        lea r9, {mem(scratch)}
        lea r10, {mem(0x11cad10)}
        lea r11, {mem(extra)}
    next:
        mov eax, dword ptr [r9+rcx*8]
        mov dword ptr [r8+rcx*4], eax
        movzx eax, word ptr [r10+rcx*2]
        dec eax
        cmp eax, 6
        ja skip
        movzx edx, byte ptr {mem(page)}
        lea eax, [rdx+rax*2]
        movzx edx, word ptr [r9+rcx*8+4]
        mov word ptr [r11+rax*2], dx
    skip:
        inc ecx
        cmp ecx, 4
        jb next
        ret
    """)
    native_input=emit('artesphere_native_input',
                      'mov qword ptr [rsp+0x18], rbx; jmp 0x228ad5')
    update=emit('artesphere_menu_input',f"""
        push rbx
        sub rsp, 0x20
        call {initialize:#x}
        cmp word ptr {mem(0x1119f96)}, 0
        jne native
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne native
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne native
        cmp word ptr {mem(0x1119f98)}, 2
        ja native
        test dword ptr {mem(0x8c9184)}, {L2}
        je shortcut
        xor byte ptr {mem(page)}, 1
        xor eax, eax
        jmp done
    shortcut:
        # R2 moves focus to row seven, then native Confirm opens its learned list.
        test dword ptr {mem(0x8c9184)}, {R2}
        je native
        movzx eax, byte ptr {mem(0x111a674)}
        cmp eax, 4
        jae native
        lea rcx, {mem(0x11cad38)}
        cmp byte ptr [rcx+rax], 0
        je native
        mov word ptr {mem(0x1119f98)}, 2
        mov word ptr {mem(0x1119f9a)}, 6
    native:
        call {enter:#x}
        call {prepare:#x}
        call {native_input:#x}
        mov ebx, eax
        call {commit:#x}
        call {leave:#x}
        mov eax, ebx
    done:
        add rsp, 0x20
        pop rbx
        ret
    """)
    jump(0x228ad0,5,update,'Seven-row native assignment and scoped A/B editing')
    # ECX arte ID -> RAX translated native arte name; fallback is localized None.
    name=emit('artesphere_arte_name',f'''
        {loc('empty','rax')}
        test ecx, ecx
        je done
        cmp ecx, 255
        ja done
        imul ecx, ecx, 24
        lea rdx, {mem(0x562a54)}
        movsxd rcx, dword ptr [rdx+rcx]
        test ecx, ecx
        js done
        mov rdx, qword ptr {mem(0x644a70)}
        test rdx, rdx
        je done
        movsxd r8, dword ptr [rdx+8]
        mov rdx, qword ptr [rdx+0x18]
        test rdx, rdx
        je done
        mov rdx, qword ptr [rdx+rcx*8]
        test rdx, rdx
        je done
        cmp qword ptr [rdx+r8*8+8], 0
        je fallback
        lea rdx, [rdx+r8*8]
    fallback:
        cmp qword ptr [rdx+8], 0
        je done
        mov rax, qword ptr [rdx+8]
    done:
        ret
    ''')
    draw=emit('artesphere_draw',f"""
        sub rsp, 0x28
        {loc('a')}
        cmp byte ptr {mem(page)}, 0
        je title
        {loc('b')}
    title:
        mov edx, 240
        mov r8d, 9
        mov r9d, 7
        mov eax, 0xffffcf8d
        call {text:#x}
        {loc('help')}
        mov edx, 240
        mov r8d, 20
        mov r9d, 6
        mov eax, 0xffdddddd
        call {text:#x}
        cmp byte ptr {mem(state+7)}, 0
        je done
        {loc('fail')}
        mov edx, 240
        mov r8d, 239
        mov r9d, 6
        mov eax, 0xff8080ff
        call {text:#x}
    done:
        add rsp, 0x28
        ret
    """)
    native_draw=emit('artesphere_native_draw',
                     'mov r11, rsp; mov qword ptr [r11+8], rbx; jmp 0x224927')
    render=emit('artesphere_menu_render',f"""
        sub rsp, 0x28
        call {enter:#x}
        call {prepare:#x}
        call {native_draw:#x}
        call {leave:#x}
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne done
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne done
        call {draw:#x}
    done:
        add rsp, 0x28
        ret
    """)
    jump(0x224920,7,render,'Native seven-row arte editor and compact header help')
    return dict(native_input=0x228ad0,native_renderer=0x224920,
                row_scratch_rva=scratch,seventh_slot='Seventh native assignment row, including native caster and learned-arte selection',
                page_behavior='tap L2 in editor; hold L2 in battle')
