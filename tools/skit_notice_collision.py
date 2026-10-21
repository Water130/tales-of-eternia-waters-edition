"""Read-only overlap check of the native UI queue before appending the notice.

Command 0x0c holds sprite/glyph size; 8/9 draw it. Command 5 carries PSP-style
vertices: window 0x80011e, flat rectangle 0x800100, rotated sprite 0x800183.
Unknown geometry is skipped without dereferencing. It must not reserve every UI
corner (world-map buffers can use other vertex formats). Known buffers remain
bounds-checked before accessing their vertices.
"""


def emit_collision(emit, mem, state):
    formats={}
    for tex in range(4):
        for color in (0,4,5,6,7):
            for vertex in (2,3):
                offset=0;alignment=1
                if tex:
                    width=(1,2,4)[tex-1];alignment=max(alignment,width);offset+=2*width
                if color:
                    width=4 if color==7 else 2
                    alignment=max(alignment,width);offset=(offset+width-1)//width*width+width
                width=2 if vertex==2 else 4
                alignment=max(alignment,width);offset=(offset+width-1)//width*width
                stride=(offset+3*width+alignment-1)//alignment*alignment
                formats[0x800000|tex|(color<<2)|(vertex<<7)]=(stride,offset,vertex==3)
    dispatch=''
    branches=''
    for fmt,(stride,offset,isfloat) in formats.items():
        dispatch+=f'cmp eax, {fmt}; je format_{fmt}\n'
        branches+=f'format_{fmt}:\n mov ebx, {stride}; mov esi, {offset}; mov edi, {int(isfloat)}; jmp vertices\n'
    return emit('skit_notice_occupied', f'''
        push rbx
        push rsi
        push rdi
        push r12
        push r13
        push r14
        push r15
        sub rsp, 0x20
        movaps xmmword ptr [rsp], xmm6
        movaps xmmword ptr [rsp+0x10], xmm7
        mov r12d, dword ptr {mem(state+12)}
        sub r12d, 4
        lea r13d, [r12+78]
        # The overworld minimap is submitted before the objective-HUD queue
        # boundary. Reserve its lower-right footprint independently of that
        # boundary so terrain exclusion cannot also exclude the map.
        cmp word ptr {mem(0x119ea28)}, 2
        jne map_clear
        # The rotating compass also precedes the objective-HUD boundary.
        # Protect its whole top-left footprint, including cardinal labels,
        # even when camera/terrain commands are deliberately ignored.
        cmp r12d, 100
        jge compass_clear
        cmp r13d, 0
        jle compass_clear
        mov eax, dword ptr {mem(state+16)}
        sub eax, 4
        cmp eax, 64
        jge compass_clear
        add eax, 33
        test eax, eax
        jg busy
    compass_clear:
        cmp r13d, 380
        jle map_clear
        cmp dword ptr {mem(state+16)}, 151
        jge busy
    map_clear:
        mov rax, qword ptr {mem(0x644a10)}
        test rax, rax
        je busy
        movsxd r9, dword ptr [rax+0x4e0]
        test r9, r9
        js busy
        cmp r9, qword ptr [rax+0x4d8]
        ja busy
        cmp r9, 65536
        ja busy
        mov r8, qword ptr [rax+0x4d0]
        test r8, r8
        je busy
        xor edx, edx
        cmp word ptr {mem(0x119ea28)}, 2
        jne queue_start
        cmp rax, qword ptr {mem(state+32)}
        jne queue_start
        mov edx, dword ptr {mem(state+28)}
        cmp rdx, r9
        ja busy
    queue_start:
        imul r9, r9, 80
        add r9, r8
        imul rdx, rdx, 80
        add r8, rdx
        mov r14, qword ptr {mem(0x644a58)}
        test r14, r14
        je busy
        mov eax, dword ptr [r14+0x2000008]
        cmp eax, 0x2000000
        ja busy
        add r14, 8
        lea r15, [r14+rax]
        xorps xmm4, xmm4
        xorps xmm5, xmm5
    command:
        cmp r8, r9
        jae free
        mov eax, dword ptr [r8]
        cmp eax, 12
        je size
        cmp eax, 8
        je sprite
        cmp eax, 9
        je sprite
        cmp eax, 5
        jne next
        mov eax, dword ptr [r8+12]
        test eax, 0x800000
        je next
        cmp qword ptr [r8+24], 0
        jne next
        {dispatch}
        jmp next
        {branches}
    vertices:
        mov ecx, dword ptr [r8+16]
        test ecx, ecx
        je next
        cmp ecx, 4096
        ja busy
        mov r10, qword ptr [r8+32]
        cmp r10, r14
        jb busy
        mov eax, ecx
        imul rax, rbx
        add rax, r10
        cmp rax, r15
        ja busy
        add r10, rsi
        mov eax, 0x7f7fffff
        movd xmm0, eax
        movaps xmm1, xmm0
        mov eax, 0xff7fffff
        movd xmm2, eax
        movaps xmm3, xmm2
    vertex:
        test edi, edi
        jne float_vertex
        movsx eax, word ptr [r10]
        cvtsi2ss xmm6, eax
        movsx eax, word ptr [r10+2]
        cvtsi2ss xmm7, eax
        jmp bounds
    float_vertex:
        movss xmm6, dword ptr [r10]
        movss xmm7, dword ptr [r10+4]
    bounds:
        minss xmm0, xmm6
        minss xmm1, xmm7
        maxss xmm2, xmm6
        maxss xmm3, xmm7
        add r10, rbx
        dec ecx
        jne vertex
        jmp overlap
    size:
        movss xmm4, dword ptr [r8+16]
        movss xmm5, dword ptr [r8+20]
        jmp next
    sprite:
        movss xmm0, dword ptr [r8+8]
        movss xmm1, dword ptr [r8+12]
        movaps xmm2, xmm0
        movaps xmm3, xmm1
        addss xmm2, xmm4
        addss xmm3, xmm5
    overlap:
        # Ignore a full-screen background. Menus/dialogue are gated separately;
        # their individual border/text commands still reserve their corners.
        cvttss2si eax, xmm0
        cvttss2si ecx, xmm1
        cvttss2si edx, xmm2
        cvttss2si esi, xmm3
        cmp eax, 0
        jg intersect
        cmp ecx, 0
        jg intersect
        cmp edx, 480
        jl intersect
        cmp esi, 272
        jge next
    intersect:
        cmp eax, edx
        jge next
        cmp ecx, esi
        jge next
        cmp eax, r13d
        jge next
        cmp edx, r12d
        jle next
        mov ebx, dword ptr {mem(state+16)}
        add ebx, 29
        cmp ecx, ebx
        jge next
        sub ebx, 33
        cmp esi, ebx
        jg busy
    next:
        add r8, 80
        jmp command
    free:
        xor eax, eax
        jmp done
    busy:
        mov eax, 1
    done:
        movaps xmm6, xmmword ptr [rsp]
        movaps xmm7, xmmword ptr [rsp+0x10]
        add rsp, 0x20
        pop r15
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
