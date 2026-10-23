"""Centered native text runs: numbers green, words white, shared fitting."""
import re
import struct


def encode_runs(text, payload, state, string):
    parts=[]
    for part in re.split(r'([+−-]?\d+(?:[.,]\d+)?\s*%?)',text):
        if part:
            parts.append((string(part),0xff70f0a0 if re.search(r'\d',part) else 0xffffffff))
    assert 0 < len(parts) <= 8, text
    payload.extend(b'\0'*((-len(payload))%4))
    ptr=state+len(payload)
    payload.extend(struct.pack('<I',len(parts)))
    for part in parts:payload.extend(struct.pack('<2I',*part))
    return ptr


def emit_rich_text(emit,mem,name='mastery_rich_text',left=False,muted=False):
    # RCX runs, EDX center, R8D y, R9D width. All segments share one
    # compression factor, so the native font cannot overlap neighboring runs.
    return emit(name,f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        sub rsp, 0x80
        mov rbx, rcx
        mov ebp, edx
        mov esi, r8d
        mov edi, r9d
        xor r12d, r12d
        mov dword ptr [rsp+0x58], 0
    measure:
        cmp r12d, dword ptr [rbx]
        jae measured
        mov ecx, dword ptr [rbx+r12*8+4]
        lea rax, {mem(0)}
        add rcx, rax
        mov eax, 0x40e00000
        cmp qword ptr {mem(0x644a18)}, 0
        je font_ready
        movzx edx, byte ptr {mem(0x11c9ce8)}
        dec edx
        cmp edx, -1
        je font_ready
        cmp edx, 5
        jbe adjusted
        cmp edx, 9
        jb font_ready
    adjusted:
        mov eax, 0x40f00000
    font_ready:
        movd xmm1, eax
        xor r8d, r8d
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        mov dword ptr [rsp+0x28], -1
        call 0xb240
        movss dword ptr [rsp+0x60+r12*4], xmm0
        addss xmm0, dword ptr [rsp+0x58]
        movss dword ptr [rsp+0x58], xmm0
        inc r12d
        jmp measure
    measured:
        mov eax, 0x3f800000
        movd xmm1, eax
        cvtsi2ss xmm2, edi
        comiss xmm0, xmm2
        jbe scale_ready
        movaps xmm1, xmm2
        divss xmm1, xmm0
    scale_ready:
        movss dword ptr [rsp+0x5c], xmm1
        mulss xmm0, xmm1
        mulss xmm0, dword ptr {mem(0x524860)}
        cvtsi2ss xmm1, ebp
        {'' if left else 'subss xmm1, xmm0'}
        movss dword ptr [rsp+0x58], xmm1
        xor r12d, r12d
    draw:
        cmp r12d, dword ptr [rbx]
        jae done
        mov ecx, dword ptr [rbx+r12*8+4]
        lea rax, {mem(0)}
        add rcx, rax
        movss xmm1, dword ptr [rsp+0x58]
        cvtsi2ss xmm2, esi
        xorps xmm3, xmm3
        mov dword ptr [rsp+0x20], 0x40e00000
        mov eax, dword ptr [rbx+r12*8+8]
        {'mov eax, 0xff999999' if muted else ''}
        mov dword ptr [rsp+0x28], eax
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        movss xmm0, dword ptr [rsp+0x60+r12*4]
        mulss xmm0, dword ptr [rsp+0x5c]
        movss dword ptr [rsp+0x40], xmm0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
        movss xmm0, dword ptr [rsp+0x60+r12*4]
        mulss xmm0, dword ptr [rsp+0x5c]
        addss xmm0, dword ptr [rsp+0x58]
        movss dword ptr [rsp+0x58], xmm0
        inc r12d
        jmp draw
    done:
        add rsp, 0x80
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
