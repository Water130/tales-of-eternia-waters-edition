"""Solid subpixel ribbons submitted as native four-vertex UI quads."""
import struct
from mastery_tree_layout import ribbon


def store_links(links,payload,state):
    records=[]
    for link in links:
        payload.extend(b'\0'*((-len(payload))%4))
        address=state+len(payload)
        # A dark continuous border keeps the connection readable over the panel.
        for width in (3.6,2.2):
            for x,y in ribbon(link['points'],width):payload.extend(struct.pack('<2f',x,y))
        records.append((address,len(link['points'])*2,0,0,link['node']))
    return records


def emit_links(emit,mem):
    command=emit('mastery_link_state_command',f'''
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        mov rdx, qword ptr [rcx+0x4d0]
        test rdx, rdx
        je done
        movsxd r11, dword ptr [rcx+0x4e0]
        cmp r11, qword ptr [rcx+0x4d8]
        jae done
        inc dword ptr [rcx+0x4e0]
        imul r11, r11, 80
        add rdx, r11
        mov dword ptr [rdx], eax
        mov dword ptr [rdx+8], r8d
        mov dword ptr [rdx+12], r9d
        jmp 0x60bf0
    done:
        ret
    ''')
    setup=emit('mastery_link_render_setup',f'''
        sub rsp, 0x28
        mov eax, 0x20
        xor r8d, r8d
        xor r9d, r9d
        call {command:#x}
        mov ecx, 9
        call 0x6f440
        mov eax, 0x1d
        xor r8d, r8d
        mov r9d, 1
        call {command:#x}
        mov ecx, 4
        call 0x6f440
        xor ecx, ecx
        mov edx, 2
        mov r8d, 3
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        call 0x6fd70
        mov ecx, -1
        call 0x6c550
        add rsp, 0x28
        ret
    ''')
    # RCX immutable xy pairs, EDX vertex count, R10D explicit core ABGR.
    # Locked paths use the panel interior, leaving a hollow black outline.
    draw=emit('mastery_menu_tinted_link',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        sub rsp, 0x20
        mov rsi, rcx
        mov ebp, edx
        mov edi, r10d
        xor ebx, ebx
    layer:
        lea r12d, [rbp-2]
    segment:
        mov r10, qword ptr {mem(0x644a58)}
        test r10, r10
        je done
        mov eax, dword ptr [r10+0x2000008]
        lea r11, [r10+rax+8]
        add eax, 64
        cmp eax, 0x2000000
        ja done
        mov dword ptr [r10+0x2000008], eax
        mov r8, r11
        mov edx, 4
        mov eax, 0xff080604
        test ebx, ebx
        cmovne eax, edi
    vertex:
        mov dword ptr [r8], eax
        mov r9, qword ptr [rsi]
        mov qword ptr [r8+4], r9
        mov dword ptr [r8+12], 0
        add rsi, 8
        add r8, 16
        dec edx
        jne vertex
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
        mov dword ptr [rdx], 5
        mov dword ptr [rdx+8], 4
        mov dword ptr [rdx+12], 0x80019c
        mov dword ptr [rdx+16], 4
        mov qword ptr [rdx+24], 0
        mov qword ptr [rdx+32], r11
        call 0x60bf0
        sub r12d, 2
        je layer_done
        sub rsi, 16
        jmp segment
    layer_done:
        inc ebx
        cmp ebx, 2
        jb layer
    done:
        add rsp, 0x20
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    return setup,draw
