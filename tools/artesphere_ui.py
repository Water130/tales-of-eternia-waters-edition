"""Original six-row arte editor, scoped to A/B/C without geometry patches."""


def emit_ui(emit,mem,jump,state,loc,symbols,initialize,enter,leave,L2,R2,data):
    page=state+1
    native_input=emit('artesphere_native_input',
                      'mov qword ptr [rsp+0x18], rbx; jmp 0x228ad5')
    update=emit('artesphere_menu_input',f"""
        push rbx
        sub rsp, 0x20
        call {initialize:#x}
        mov eax, dword ptr {mem(data+0x1a80)}
        test eax, eax
        je mastery_done
        lea rdx, {mem(0)}
        add rax, rdx
        call rax
        test eax, eax
        je done
    mastery_done:
        cmp byte ptr {mem(data+0x1a47)}, 0
        je native
        cmp word ptr {mem(0x1119f96)}, 0
        jne native
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne native
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne native
        cmp word ptr {mem(0x1119f98)}, 2
        ja native
        mov al, 2
        test dword ptr {mem(0x8c9184)}, {R2}
        jne select_page
        mov al, 1
        test dword ptr {mem(0x8c9184)}, {L2}
        je native
    select_page:
        cmp byte ptr {mem(page)}, al
        jne changed
        xor eax, eax
    changed:
        mov byte ptr {mem(page)}, al
        xor eax, eax
        jmp done
    native:
        call {enter:#x}
        call {native_input:#x}
        mov ebx, eax
        call {leave:#x}
        mov eax, ebx
    done:
        add rsp, 0x20
        pop rbx
        ret
    """)
    jump(0x228ad0,5,update,'Native six-row assignments with scoped A/B/C editing')
    text=symbols['settings_text']
    draw=emit('artesphere_draw',f"""
        sub rsp, 0x28
        cmp byte ptr {mem(data+0x1a47)}, 0
        je done
        {loc('a')}
        mov eax, 0xffffad61
        cmp byte ptr {mem(page)}, 0
        je title
        {loc('b')}
        mov eax, 0xff6666ff
        cmp byte ptr {mem(page)}, 1
        je title
        {loc('c')}
        mov eax, 0xff40dfff
    title:
        mov edx, 240
        mov r8d, 9
        mov r9d, 7
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
        mov eax, dword ptr {mem(data+0x1a84)}
        test eax, eax
        je native
        lea rdx, {mem(0)}
        add rax, rdx
        call rax
        test eax, eax
        jne done
    native:
        call {enter:#x}
        call {native_draw:#x}
        call {leave:#x}
        mov eax, dword ptr {mem(data+0x1a88)}
        test eax, eax
        je after_hint
        lea rdx, {mem(0)}
        add rax, rdx
        call rax
    after_hint:
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne done
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne done
        call {draw:#x}
    done:
        add rsp, 0x28
        ret
    """)
    jump(0x224920,7,render,'Original six-row arte editor and three-color page header')
    return dict(native_input=0x228ad0,native_renderer=0x224920,
                native_layout=True,rows=6,
                page_colors={'A':'blue','B':'red','C':'yellow'},
                page_behavior='tap L2 for B/A or R2 for C/A in editor; hold L2 for B or R2 for C in battle')
