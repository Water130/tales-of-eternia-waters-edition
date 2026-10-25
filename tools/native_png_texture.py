"""Native-manager-owned embedded textures, following the verified title PNG path."""
import struct

def emit_png_texture(emit,mem,data,png,prefix):
    width,height=struct.unpack('>II',png[16:24])
    cache=data;obj=data+0x40;vt=data+0x80
    initialize=emit(prefix+'_initialize',f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x30
        mov rbx, qword ptr {mem(0x644a30)}
        test rbx, rbx
        je unavailable
        cmp qword ptr {mem(0x8602e8)}, 0
        je unavailable
        cmp qword ptr [rbx+0x60], 0
        je unavailable
        cmp qword ptr {mem(cache)}, rbx
        je cached
        mov qword ptr {mem(cache)}, rbx
        mov qword ptr {mem(cache+8)}, 0
        mov qword ptr {mem(cache+16)}, 0
        lea rsi, [rbx+8]
        mov rcx, rsi
        mov rax, qword ptr [rsi]
        call qword ptr [rax]
        mov ecx, 0x30
        mov edx, 1
        mov r8d, 8
        call 0x261290
        test rax, rax
        je unlock
        mov rdi, rax
        mov qword ptr [rdi+0x10], 0
        mov dword ptr [rdi+0x18], -1
        mov dword ptr [rdi+8], 1
        lea rax, {mem(0x51a430)}
        mov qword ptr [rdi], rax
        lea rax, {mem(data+0x4000)}
        mov qword ptr [rdi+0x20], rax
        mov dword ptr [rdi+0x28], {len(png)}
        mov rcx, qword ptr [rbx+0x60]
        mov rdx, rdi
        call 0x5b410
        test rax, rax
        je release
        mov qword ptr {mem(cache+8)}, rax
        mov qword ptr {mem(cache+16)}, rdi
        mov rcx, qword ptr [rbx+0x68]
        mov qword ptr [rcx+rax*8-8], rdi
        mov qword ptr [rsp+0x20], rdi
        lea rcx, [rbx+0x90]
        lea rdx, [rsp+0x20]
        call 0x5b620
        jmp unlock
    release:
        mov rcx, rdi
        mov edx, 1
        call 0x5b7d0
    unlock:
        mov rcx, rsi
        mov rax, qword ptr [rsi]
        call qword ptr [rax+0x10]
    cached:
        mov rax, qword ptr {mem(cache+16)}
        test rax, rax
        je unavailable
        cmp dword ptr [rax+0x18], -1
        je unavailable
        mov rax, qword ptr {mem(cache+8)}
        jmp done
    unavailable:
        xor eax, eax
    done:
        add rsp, 0x30
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    getter=emit(prefix+'_resource',f'mov rax, qword ptr {mem(cache+8)}; ret')
    bind=emit(prefix+'_bind',f'''
        sub rsp, 0x28
        lea r10, {mem(vt)}
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
        lea r9, {mem(obj)}
        mov qword ptr [r9], r10
        mov rcx, qword ptr {mem(0x644a10)}
        mov rdx, qword ptr [rcx+0x4d0]
        movsxd rax, dword ptr [rcx+0x4e0]
        inc dword ptr [rcx+0x4e0]
        imul rax, rax, 80
        add rdx, rax
        mov dword ptr [rdx], 0x22
        mov qword ptr [rdx+8], r9
        mov dword ptr [rdx+16], {width}
        mov dword ptr [rdx+20], {height}
        mov dword ptr [rdx+24], 4
        call 0x60bf0
        add rsp, 0x28
        ret
    ''')
    return initialize,bind
