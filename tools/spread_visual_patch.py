"""Close Spread's upper rim without modifying any vanilla column vertex or UV."""


def emit_spread_visual(emit, mem, jump, data_rva):
    save = '\n'.join(f'movdqu xmm0, xmmword ptr {mem(0x11ce620+i)}\n'
                     f'movdqu xmmword ptr [rsp+{0x30+i:#x}], xmm0'
                     for i in range(0, 0xa0, 16))
    restore = '\n'.join(f'movdqu xmm0, xmmword ptr [rsp+{0x30+i:#x}]\n'
                        f'movdqu xmmword ptr {mem(0x11ce620+i)}, xmm0'
                        for i in range(0, 0xa0, 16))
    cap = emit('spread_column_cap', f'''
        push rbx
        push rsi
        push rdi
        push r12
        sub rsp, 0xf8
        cmp edx, 1
        jne done
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        cmp byte ptr {mem(data_rva+0x20)}, 1
        jne done
        # Native builders assume allocation succeeds. Reserve the entire cap.
        mov rax, qword ptr {mem(0x644a58)}
        test rax, rax
        je done
        cmp dword ptr [rax+0x2000008], 0x1fffb00
        ja done
        mov rax, qword ptr {mem(0x644a10)}
        test rax, rax
        je done
        cmp qword ptr [rax+0x4d0], 0
        je done
        movsxd rdx, dword ptr [rax+0x4e0]
        add rdx, 160
        cmp rdx, qword ptr [rax+0x4d8]
        ja done
        mov rsi, rcx
        {save}
        mov rax, qword ptr {mem(0x8c9730)}
        mov qword ptr [rsp+0xd0], rax
        movdqu xmm0, xmmword ptr {mem(0x8c9720)}
        movdqu xmmword ptr [rsp+0xe0], xmm0
        # Native rim Y=-192: only the closure rises 12 world units above it.
        mov dword ptr {mem(0x8c9730)}, 0xff340000
        mov word ptr {mem(0x8c9734)}, 0
        call 0x1a07d0
        movzx r12d, word ptr {mem(0x8c9724)}
        shl r12d, 16
        mov r12w, word ptr {mem(0x8c9720)}
        mov dword ptr {mem(0x11ce670)}, 0x00ffffff
        mov dword ptr {mem(0x11ce674)}, 0x00ffffff
        mov dword ptr {mem(0x11ce678)}, 0x00ffffff
        mov dword ptr {mem(0x11ce67c)}, 0x00ffffff
        # Reuse the water material and continue the original top-row phase.
        sub word ptr {mem(0x11ce68c)}, 32
        and word ptr {mem(0x11ce68c)}, 127
        xor edi, edi
    segment:
        mov eax, dword ptr [rsi+rdi*4]
        mov dword ptr {mem(0x11ce640)}, eax
        lea ebx, [rdi+1]
        and ebx, 15
        mov eax, dword ptr [rsi+rbx*4]
        mov dword ptr {mem(0x11ce644)}, eax
        mov dword ptr {mem(0x11ce648)}, r12d
        mov dword ptr {mem(0x11ce64c)}, r12d
        call 0x11ed60
        add word ptr {mem(0x11ce68a)}, 32
        and word ptr {mem(0x11ce68a)}, 127
        inc edi
        cmp edi, 16
        jb segment
        mov rax, qword ptr [rsp+0xd0]
        mov qword ptr {mem(0x8c9730)}, rax
        movdqu xmm0, xmmword ptr [rsp+0xe0]
        movdqu xmmword ptr {mem(0x8c9720)}, xmm0
        {restore}
    done:
        add rsp, 0xf8
        pop r12
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    hook = emit('spread_cap_after_native_mesh', f'''
        sub rsp, 0x20
        lea rcx, [rsp+0x60]
        mov edx, dword ptr [rsp+0x48]
        call {cap:#x}
        add rsp, 0x20
        xor ecx, ecx
        mov dword ptr {mem(0x11ce664)}, 0x00400040
        jmp 0xc0cb2
    ''')
    jump(0xc0ca6, 12, hook, 'Close Spread upper rim while preserving the complete vanilla column')
