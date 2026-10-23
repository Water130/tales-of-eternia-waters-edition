"""Compact read-only Spectacles information while the native R1 selector is open."""
from combat_ui_layout import SCAN_LABELS, SCAN_DRAWN


def emit_target_panel(emit,mem,data,eligible):
    # Name lookup and resistance rules match 91CA0..923C6; unlike the item
    # routine this renderer never writes the Compendium or consumes its timer.
    label=emit('scan_panel_label',f'''
        lea rax, {mem(data+SCAN_LABELS)}
        lea rax, [rax+rcx*8]
        mov ecx, dword ptr [rax+4]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne ready
        mov ecx, dword ptr [rax]
    ready:
        lea rax, {mem(data)}
        add rcx, rax
        ret
    ''')
    # Integer coordinates are already in final screen space. Native font and
    # clipping/maximum width handle translated names; size is deliberately small.
    text=emit('scan_panel_text',f'''
        sub rsp, 0x58
        mov dword ptr [rsp+0x28], eax
        cvtsi2ss xmm1, edx
        cvtsi2ss xmm2, r8d
        cvtsi2ss xmm0, r9d
        movss dword ptr [rsp+0x40], xmm0
        mov eax, 0x43ff8000
        movd xmm3, eax
        mov dword ptr [rsp+0x20], 0x40c00000
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
        add rsp, 0x58
        ret
    ''')
    number=emit('scan_panel_number',f'''
        # EAX nonnegative value, RDI destination -> RDI advanced.
        sub rsp, 0x18
        xor r8d, r8d
        mov r9d, 10
    digit:
        xor edx, edx
        div r9d
        add dl, 48
        mov byte ptr [rsp+r8], dl
        inc r8d
        test eax, eax
        jne digit
    copy:
        dec r8d
        mov al, byte ptr [rsp+r8]
        mov byte ptr [rdi], al
        inc rdi
        test r8d, r8d
        jne copy
        add rsp, 0x18
        ret
    ''')
    resistance=emit('scan_panel_resistance',f'''
        # RCX actor, EDX element 0..9 -> 0 none, 1 resistant, 2 weak.
        mov r8, qword ptr [rcx+0xe8]
        movsx eax, byte ptr [r8+rdx+0x31]
        test eax, eax
        je done
        js weak
        movsx r8d, byte ptr [rcx+0x78]
        mov edx, eax
        sub edx, r8d
        cmp eax, 95
        jg classify
        cmp edx, -25
        jle classify
        cmp edx, 30
        jl none
    classify:
        test edx, edx
        js none
        mov eax, 1
        ret
    weak:
        mov eax, 2
        ret
    none:
        xor eax, eax
    done: ret
    ''')
    return emit('ui_scanned_target_panel',f'''
        push rbx; push rbp; push rsi; push rdi
        push r12; push r13; push r14; push r15
        sub rsp, 0x48
        mov rbx, rcx
        mov rsi, rdx
        # The native renderer decrements its timer after drawing. Keep the
        # frame latch too, so the final closing frame cannot show both panels.
        cmp byte ptr {mem(0x12d0f00)}, 0
        jne done
        cmp byte ptr {mem(data+SCAN_DRAWN)}, 0
        jne done
        movzx eax, byte ptr {mem(0x12ceb8d)}
        test eax, eax
        je done
        dec eax
        cmp al, byte ptr {mem(0x12cece8)}
        jae done
        cmp eax, 5
        jae done
        mov rdx, qword ptr {mem(0x12cecd8)}
        test rdx, rdx
        je done
        imul eax, eax, 0x248
        add rdx, rax
        cmp word ptr [rdx+0x3c], 1
        jne done
        movzx eax, byte ptr [rdx+0x63]
        cmp al, byte ptr {mem(0x12cece9)}
        jae done
        imul eax, eax, 0x248
        add rax, qword ptr {mem(0x12cece0)}
        cmp rax, rbx
        jne done
        call {eligible:#x}
        test r11d, r11d
        je done
        cmp qword ptr {mem(0x644a10)}, 0
        je done
        # Native Spectacles dimensions (96 x 56), with a 24-unit gutter beyond
        # the target frame to leave the R1 directional prompt unobstructed.
        mov ebp, dword ptr [rsi+0x108]
        add ebp, 24
        mov eax, 380
        cmp ebp, eax
        cmovg ebp, eax
        mov eax, 4
        cmp ebp, eax
        cmovl ebp, eax
        mov r12d, dword ptr [rsi+0x10c]
        sub r12d, 54
        mov eax, 12
        cmp r12d, eax
        cmovl r12d, eax
        mov eax, 160
        cmp r12d, eax
        cmovg r12d, eax
        lea ecx, [rbp-80]
        lea edx, [r12-16]
        mov r8d, 508
        mov r9d, 96
        mov dword ptr [rsp+0x20], 56
        mov rax, qword ptr {mem(0x12cea68)}
        test rax, rax
        je done
        add rax, 0x40
        mov qword ptr [rsp+0x28], rax
        call 0x11ac40
        call 0x24f290
        xor ecx, ecx
        call {label:#x}
        mov rdi, rcx
        mov rax, qword ptr {mem(0x644a70)}
        test rax, rax
        je name
        movsxd rdx, dword ptr [rax+8]
        cmp edx, 12
        ja name
        mov rax, qword ptr [rax+0x18]
        test rax, rax
        je name
        movzx ecx, byte ptr [rbx+0x4f]
        lea r8, {mem(0x12d0f33)}
        movzx ecx, byte ptr [r8+rcx]
        mov rax, qword ptr [rax+rcx*8+0x214d0]
        test rax, rax
        je name
        mov rcx, qword ptr [rax+rdx*8+8]
        test rcx, rcx
        cmovz rcx, qword ptr [rax+8]
        test rcx, rcx
        cmovnz rdi, rcx
    name:
        mov rcx, rdi
        lea edx, [rbp+4]; lea r8d, [r12-6]; mov r9d, 88
        mov eax, 0xffffffff; call {text:#x}
        mov ecx, 1; call {label:#x}
        lea edx, [rbp+8]; lea r8d, [r12+6]; mov r9d, 20
        mov eax, 0xffffffff; call {text:#x}
        lea rdi, {mem(data+0x1680)}
        mov eax, dword ptr [rbx+0x2c]; call {number:#x}
        mov byte ptr [rdi], 0
        lea rcx, {mem(data+0x1680)}
        lea edx, [rbp+28]; lea r8d, [r12+6]; mov r9d, 60
        mov eax, 0xffffffff; call {text:#x}
        lea rdi, {mem(data+0x1680)}
        mov byte ptr [rdi], 47; inc rdi
        mov rax, qword ptr [rbx+0xe8]
        mov eax, dword ptr [rax+0x18]; call {number:#x}
        mov byte ptr [rdi], 0
        lea rcx, {mem(data+0x1680)}
        lea edx, [rbp+44]; lea r8d, [r12+14]; mov r9d, 48
        mov eax, 0xffffffff; call {text:#x}
        mov r13d, 1
    row:
        lea ecx, [r13+1]; call {label:#x}
        lea edx, [rbp+8]
        imul r8d, r13d, 15; lea r8d, [r8+r12+13]
        mov r9d, 20; mov eax, 0xffffffff; call {text:#x}
        xor r14d, r14d
        xor r15d, r15d
    element:
        mov rcx, rbx; mov edx, r14d; call {resistance:#x}
        cmp eax, r13d; jne next
        # Same native colored discs and localized element captions as the
        # item panel (2518A0). Native Spectacles shows at most five per row.
        cmp r15d, 5; jae next
        imul ecx, r15d, 14; lea ecx, [rcx+rbp-54]
        imul edx, r13d, 15; lea edx, [rdx+r12-6]
        mov r8d, 511; lea r9d, [r14+1]
        mov dword ptr [rsp+0x20], 255
        call 0x2518a0
        inc r15d
    next:
        inc r14d; cmp r14d, 10; jb element
        test r15d, r15d; jne next_row
        mov ecx, 4; call {label:#x}
        lea edx, [rbp+40]; imul r8d, r13d, 15; lea r8d, [r8+r12+13]
        mov r9d, 20; mov eax, 0xffbbbbbb; call {text:#x}
    next_row:
        inc r13d; cmp r13d, 2; jbe row
    done:
        add rsp, 0x48
        pop r15; pop r14; pop r13; pop r12
        pop rdi; pop rsi; pop rbp; pop rbx
        ret
    ''')
