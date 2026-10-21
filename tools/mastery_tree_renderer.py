"""Two-stage native mastery menu: centered selection, then a rooted tree."""
def emit_tree_draw(emit,mem,ui,data,lookup,value,status,icon,frame,text,number,hints,
                   loc,tabletext,label,names,string,browser):
    block=emit('mastery_menu_lines',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0x28
        mov ebx, dword ptr [rcx]
        lea rsi, [rcx+4]
        mov edi, r8d
        mov ebp, eax
        test ebx, ebx
        je done
    line:
        mov ecx, dword ptr [rsi]
        lea rax, {mem(0)}
        add rcx, rax
        mov edx, 40
        mov r8d, edi
        mov r9d, 395
        mov eax, ebp
        call {text:#x}
        add rsi, 4
        add edi, 8
        dec ebx
        jne line
    done:
        add rsp, 0x28
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    tinted_line=emit('mastery_menu_tinted_link',f'''
        sub rsp, 0x58
        cvtsi2ss xmm0, ecx
        cvtsi2ss xmm1, edx
        cvtsi2ss xmm3, r8d
        cvtsi2ss xmm2, r9d
        movss dword ptr [rsp+0x20], xmm2
        xorps xmm2, xmm2
        mov dword ptr [rsp+0x30], 0xbf800000
        mov dword ptr [rsp+0x40], 0x40000000
        mov dword ptr [rsp+0x48], r10d
        call 0x24490
        add rsp, 0x58
        ret
    ''')
    line=emit('mastery_menu_link',f'mov r10d, 255; jmp {tinted_line:#x}')
    from mastery_rich_text import emit_rich_text
    rich=emit_rich_text(emit,mem)
    from mastery_level_bar import emit_level_bar
    level_bar=emit_level_bar(emit,mem,value,text,line,tinted_line,string)
    # Same seven-point font and locale adjustment as b480. Measure before
    # centering, and account for the native maximum-width compression.
    center=emit('mastery_menu_centered_text',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0x68
        mov rbx, rcx
        mov ebp, edx
        mov esi, r8d
        mov edi, r9d
        mov dword ptr [rsp+0x58], eax
        mov eax, 0x40e00000
        movd xmm1, eax
        cmp qword ptr {mem(0x644a18)}, 0
        je measure
        movzx eax, byte ptr {mem(0x11c9ce8)}
        lea edx, [rax-1]
        cmp edx, 5
        jbe adjusted
        cmp eax, 10
        jb measure
    adjusted:
        addss xmm1, dword ptr {mem(0x524860)}
    measure:
        xor r8d, r8d
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        mov dword ptr [rsp+0x28], -1
        call 0xb240
        cvtsi2ss xmm2, edi
        minss xmm0, xmm2
        mulss xmm0, dword ptr {mem(0x524860)}
        cvttss2si eax, xmm0
        mov edx, ebp
        sub edx, eax
        mov rcx, rbx
        mov r8d, esi
        mov r9d, edi
        mov eax, dword ptr [rsp+0x58]
        call {text:#x}
        add rsp, 0x68
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    title_lines=emit('mastery_menu_node_title',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        sub rsp, 0x30
        mov ebx, dword ptr [rcx]
        lea rsi, [rcx+4]
        mov ebp, edx
        mov edi, r8d
        mov r12d, r9d
        mov dword ptr [rsp+0x28], eax
        cmp ebx, 1
        jne line
        add edi, 4
    line:
        mov ecx, dword ptr [rsi]
        lea rax, {mem(0)}
        add rcx, rax
        mov edx, ebp
        mov r8d, edi
        mov r9d, r12d
        mov eax, dword ptr [rsp+0x28]
        call {center:#x}
        add rsi, 4
        add edi, 8
        dec ebx
        jne line
        add rsp, 0x30
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    selector=emit('mastery_menu_selection_draw',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        sub rsp, 0x30
        mov ecx, 29
        mov edx, 58
        mov r8d, 62
        mov r9d, 114
        call {frame:#x}
        movzx edi, byte ptr {mem(ui+5)}
        mov eax, 5
        cmp edi, eax
        cmova edi, eax
        imul ebp, edi, -10
        add ebp, 116
        movzx r12d, byte ptr {mem(ui+1)}
        sub r12d, 2
        xor eax, eax
        cmp r12d, eax
        cmovl r12d, eax
        movzx eax, byte ptr {mem(ui+5)}
        sub eax, edi
        cmp r12d, eax
        cmovg r12d, eax
        xor r13d, r13d
    item:
        cmp r13d, edi
        jae counter
        mov eax, r12d
        xor edx, edx
        call {lookup:#x}
        mov rbx, rcx
        call {value:#x}
        mov r14d, edx
        cmp r12b, byte ptr {mem(ui+1)}
        jne item_name
        mov ecx, 31
        mov edx, ebp
        mov r8d, 58
        mov r9d, 18
        call {frame:#x}
    item_name:
        {loc('unknown')}
        test r14d, r14d
        je name_ready
        {tabletext('rbx',12)}
    name_ready:
        mov edx, 60
        lea r8d, [rbp+5]
        mov r9d, 52
        mov eax, 0xffcccccc
        cmp r12b, byte ptr {mem(ui+1)}
        jne name_color
        mov eax, 0xff70f0a0
    name_color:
        call {center:#x}
        cmp r12b, byte ptr {mem(ui+1)}
        jne next
        cmp byte ptr {mem(ui+6)}, 0
        jne next
        mov ecx, 1
        mov edx, -59
        lea r8d, [rbp-11]
        mov r9d, 2
        mov dword ptr [rsp+0x20], 255
        call 0x250b50
    next:
        add ebp, 20
        inc r12d
        inc r13d
        jmp item
    counter:
        movzx eax, byte ptr {mem(ui+1)}
        inc eax
        call {number:#x}
        mov edx, 48
        mov r8d, 161
        mov r9d, 25
        mov eax, 0xffbbbbbb
        call {center:#x}
        lea rcx, {mem(string('/'))}
        mov edx, 60
        mov r8d, 161
        mov r9d, 8
        mov eax, 0xffbbbbbb
        call {center:#x}
        movzx eax, byte ptr {mem(ui+5)}
        call {number:#x}
        mov edx, 72
        mov r8d, 161
        mov r9d, 25
        mov eax, 0xffbbbbbb
        call {center:#x}
        add rsp, 0x30
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    return emit('mastery_menu_draw',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        push r15
        sub rsp, 0x38
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        cmp qword ptr [rcx+0x4d0], 0
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        add rax, 6000
        cmp rax, qword ptr [rcx+0x4d8]
        jae done
        mov rax, qword ptr {mem(0x644a58)}
        test rax, rax
        je done
        cmp dword ptr [rax+0x2000008], 0x1fe0000
        ja done
        cmp qword ptr {mem(0x11c9e18)}, 0
        je done
        call 0x21c460
        call 0x24f290
        mov ecx, 25
        mov edx, 28
        mov r8d, 430
        mov r9d, 216
        call {frame:#x}
        {loc('title')}
        cmp byte ptr {mem(ui+3)}, 0
        je page_title
        {loc('spellpage')}
    page_title:
        mov edx, 40
        mov r8d, 36
        mov r9d, 170
        mov eax, 0xffffad61
        call {text:#x}
        movzx eax, byte ptr {mem(ui+4)}
        lea rbx, {mem(names)}
        lea rbx, [rbx+rax*8]
        {tabletext('rbx',0)}
        mov edx, 240
        mov r8d, 36
        mov r9d, 95
        mov eax, 0xffffffff
        call {center:#x}
        {loc('faculties')}
        cmp byte ptr {mem(ui+3)}, 0
        je category
        {loc('spells')}
    category:
        mov edx, 350
        mov r8d, 36
        mov r9d, 85
        mov eax, 0xffffad61
        call {text:#x}
        cmp byte ptr {mem(ui+5)}, 0
        jne populated
        {label('empty',40,100)}
        jmp footer
    populated:
        cmp byte ptr {mem(ui+3)}, 0
        je faculty_page
        call {browser['draw']:#x}
        jmp footer
    faculty_page:
        call {selector:#x}
    tree:
        movzx eax, byte ptr {mem(ui+1)}
        xor edx, edx
        call {lookup:#x}
        mov rbx, rcx
        call {value:#x}
        mov r14d, edx
        mov r15d, eax
        test r14d, r14d
        je links
        {loc('current')}
        cmp dword ptr [rbx], 2
        jne counter_label
        {loc('casts')}
    counter_label:
        mov edx, 326
        mov r8d, 51
        mov r9d, 68
        mov eax, 0xffbbbbbb
        call {text:#x}
        mov eax, r15d
        call {number:#x}
        mov edx, 398
        mov r8d, 51
        mov r9d, 35
        mov eax, 0xffffffff
        call {text:#x}
        cmp dword ptr [rbx], 3
        je links
        mov rcx, rbx
        call {level_bar:#x}
    links:
        mov esi, dword ptr [rbx+28]
        lea rax, {mem(0)}
        add rsi, rax
        mov edi, dword ptr [rsi]
        add rsi, 8
    link:
        test edi, edi
        je root
        movzx eax, byte ptr {mem(ui+1)}
        mov edx, dword ptr [rsi+16]
        call {lookup:#x}
        mov r12, rdx
        call {status:#x}
        mov r10d, 65
        cmp eax, 2
        jb line_color
        cmp dword ptr [r12+40], 0
        je line_color
        mov r10d, 255
    line_color:
        mov ecx, dword ptr [rsi]
        mov edx, dword ptr [rsi+4]
        mov r8d, dword ptr [rsi+8]
        mov r9d, dword ptr [rsi+12]
        call {tinted_line:#x}
        add rsi, 20
        dec edi
        jmp link
    root:
        mov eax, dword ptr [rbx+28]
        lea rcx, {mem(0)}
        mov r12d, dword ptr [rcx+rax+4]
        mov ecx, r12d
        mov edx, 102
        mov r8d, 58
        mov r9d, 28
        cmp dword ptr [rbx], 0
        jne root_frame
        mov edx, 91
        mov r9d, 50
    root_frame:
        call {frame:#x}
        mov rcx, rbx
        call {value:#x}
        mov r14d, edx
        mov ebp, 112
        cmp dword ptr [rbx], 0
        jne root_name
        mov ebp, 122
        mov ecx, dword ptr [rbx+4]
        lea edx, [r12+20]
        mov r8d, 97
        mov r9d, 0xffffffff
        test r14d, r14d
        jne root_icon
        mov r9d, 0xff000000
    root_icon:
        call {icon:#x}
    root_name:
        {loc('unknown')}
        test r14d, r14d
        je root_text
        {tabletext('rbx',12)}
    root_text:
        lea edx, [r12+29]
        mov r8d, ebp
        mov r9d, 50
        mov eax, 0xffffad61
        call {center:#x}
    nodes:
        xor edi, edi
    node:
        cmp edi, dword ptr [rbx+24]
        jae details
        movzx eax, byte ptr {mem(ui+1)}
        mov edx, edi
        call {lookup:#x}
        mov rsi, rdx
        call {status:#x}
        mov r14d, eax
        mov r15d, dword ptr [rsi+48]
        mov ebp, dword ptr [rsi+52]
        mov ecx, r15d
        mov edx, ebp
        mov r8d, 50
        mov r9d, 28
        call {frame:#x}
        test r14d, r14d
        je unknown_title
        {tabletext('rsi',80)}
        mov r12d, dword ptr [rcx]
        lea edx, [r15+25]
        lea r8d, [rbp+1]
        mov r9d, 44
        mov eax, 0xffffad61
    node_text:
        call {title_lines:#x}
        jmp boost
    unknown_title:
        mov r12d, 1
        {loc('unknown')}
        lea edx, [r15+25]
        lea r8d, [rbp+5]
        mov r9d, 44
        mov eax, 0xff999999
        call {center:#x}
    boost:
        {loc('unknown')}
        test r14d, r14d
        je unknown_boost
        {tabletext('rsi',88)}
        lea edx, [r15+25]
        lea r8d, [rbp+15]
        cmp r12d, 1
        je boost_position
        add r8d, 4
    boost_position:
        mov r9d, 44
        call {rich:#x}
        jmp node_cursor
    unknown_boost:
        lea edx, [r15+25]
        lea r8d, [rbp+15]
        mov r9d, 44
        mov eax, 0xffffffff
        call {center:#x}
    node_cursor:
        cmp byte ptr {mem(ui+6)}, 0
        je no_cursor
        cmp dil, byte ptr {mem(ui+2)}
        jne no_cursor
        mov ecx, 1
        lea edx, [r15-92]
        lea r8d, [rbp-12]
        mov r9d, 2
        mov dword ptr [rsp+0x20], 255
        call 0x250b50
    no_cursor:
        inc edi
        jmp node
    details:
        movzx eax, byte ptr {mem(ui+1)}
        movzx edx, byte ptr {mem(ui+2)}
        call {lookup:#x}
        mov rbx, rcx
        mov rsi, rdx
        call {status:#x}
        mov edi, eax
        {loc('unknown')}
        test edi, edi
        je detail_title
        {tabletext('rsi',8)}
    detail_title:
        mov edx, 40
        mov r8d, 174
        mov r9d, 395
        mov eax, 0xffffad61
        call {text:#x}
        test edi, edi
        jne known_details
        {label('recruit',40,185)}
        cmp dword ptr [rsi+40], 0
        je footer
        {label('level',40,218,78)}
        mov eax, dword ptr [rsi+40]
        call {number:#x}
        mov edx, 123
        mov r8d, 218
        mov r9d, 25
        mov eax, 0xffbbbbbb
        call {text:#x}
        jmp footer
    known_details:
        {tabletext('rsi',72)}
        mov r8d, 185
        mov eax, 0xffffffff
        call {block:#x}
        {tabletext('rsi',32)}
        mov r8d, 218
        mov eax, 0xffbbbbbb
        call {block:#x}
        {loc('locked')}
        cmp edi, 1
        je status_text
        {loc('pending')}
        cmp edi, 2
        je status_text
        {loc('off')}
        cmp edi, 3
        je status_text
        {loc('on')}
    status_text:
        cmp dword ptr [rbx], 1
        jne spell_status
        cmp dword ptr [rbx+4], 5
        jne status_ready
        cmp edi, 3
        jb status_ready
        {loc('energyon')}
        cmp edi, 4
        je energy_option
        {loc('energyoff')}
    energy_option:
        cmp byte ptr {mem(data+0x1a41)}, 0
        jne status_ready
        {loc('energyglobaloff')}
        jmp status_ready
    spell_status:
        cmp dword ptr [rbx], 2
        jne status_ready
        cmp dword ptr [rsi+40], 0
        jne spell_option
        {loc('excluded')}
        jmp status_ready
    spell_option:
        cmp byte ptr {mem(data+0x1a0c)}, 0
        jne status_ready
        {loc('globaloff')}
    status_ready:
        mov edx, 40
        mov r8d, 234
        mov r9d, 395
        mov eax, 0xffbbbbbb
        call {text:#x}
    footer:
        call {hints:#x}
    done:
        add rsp, 0x38
        pop r15
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
