"""Tint newly allocated Keele/Meredy casting particles, never shared templates.

RGB consumers: 0x88c9d (+0x10), 0x858fa (+0x22), 0x86e4a (+0x0a).
Native fourth byte, lifetimes, particle geometry and update routines are kept.
"""
COLORS = {
    'water': (64, 155, 255), 'wind': (74, 230, 130),
    'fire': (255, 90, 40), 'earth': (200, 145, 65),
    'ice': (140, 240, 255), 'lightning': (255, 230, 65),
    'light': (255, 245, 190), 'dark': (170, 80, 235),
    'elemental': (235, 120, 220), 'time': (80, 230, 210),
}

# Per-instance RGB, secondary gradient, and signed RGB evolution. The fourth
# bytes are native delay/phase counters (NOT alpha) and must remain untouched.
PROFILES = {
    0xcc73e: [(0x10,48),(0x14,24),(0x18,-6)],  # Keele hand rings, darker
    0xcc860: [(0x22,112),(0x26,-12)],          # Meredy rising motes
    0xcc8da: [(0x10,64),(0x14,32),(0x18,-12)],# Meredy ground gradient
    0xcc900: [(0x22,160),(0x26,-8)],          # Meredy rising texture
    0xcc92a: [(0x0a,128),(0x0e,80),(0x12,-8)],# Meredy energy, both colors
}

def profile_data():
    import struct
    return b''.join(b''.join(struct.pack('<BhB',o,v,0) for o,v in p).ljust(32,b'\0')
                    for p in PROFILES.values())


def emit_casting_colors(emit, mem, jump, edit, data_rva):
    color_rva = data_rva+0x700
    # Private ABI: RAX allocation, RDI owning casting effect, EDX RGB offset.
    # All registers/flags restored. Only the three RGB bytes may change.
    tint = emit('tint_cast_particle', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        test rax, rax
        je done
        cmp rax, qword ptr {mem(0x12cec20)}
        je done
        mov r8, qword ptr [rdi]
        test r8, r8
        je done
        cmp byte ptr [r8+0x51], 0
        jne done
        movzx ecx, byte ptr [r8+0x4f]
        sub ecx, 2
        cmp ecx, 1
        ja done
        movzx ecx, byte ptr [r8+0x6c]
        shr ecx, 2
        dec ecx
        cmp ecx, 9
        ja done
        lea r8, {mem(color_rva)}
        lea r8, [r8+rcx*4]
        lea r9, [rax+rdx]
        movzx r10d, byte ptr [r9]
        movzx ecx, byte ptr [r9+1]
        cmp r10d, ecx
        cmovb r10d, ecx
        movzx ecx, byte ptr [r9+2]
        cmp r10d, ecx
        cmovb r10d, ecx
        mov r11d, 3
    channel:
        movzx eax, byte ptr [r8]
        imul eax, r10d
        xor edx, edx
        mov ecx, 255
        div ecx
        mov byte ptr [r9], al
        inc r8
        inc r9
        dec r11d
        jne channel
    done:
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        ret
    ''')
    profile = emit('tint_cast_profile', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        push rbx
        push rsi
        push rbp
        test rax, rax
        je done
        cmp rax, qword ptr {mem(0x12cec20)}
        je done
        mov r8, qword ptr [rdi]
        test r8, r8
        je done
        cmp byte ptr [r8+0x51], 0
        jne done
        movzx ecx, byte ptr [r8+0x4f]
        sub ecx, 2
        cmp ecx, 1
        ja done
        movzx ecx, byte ptr [r8+0x6c]
        shr ecx, 2
        dec ecx
        cmp ecx, 9
        ja done
        cmp edx, 5
        jae done
        mov rbx, rax
        # Native ABR=2 subtracts the tinted glyph from the background, making
        # it black on dark scenery. Only these two private cast particles use
        # that mode. Switch to additive, retaining the texture page/CLUT bits.
        cmp edx, 0
        je ring_blend
        cmp edx, 4
        jne blend_ready
        and word ptr [rbx+0x5a], 0xff9f
        or word ptr [rbx+0x5a], 0x20
        jmp blend_ready
    ring_blend:
        and word ptr [rbx+0x38], 0xff9f
        or word ptr [rbx+0x38], 0x20
    blend_ready:
        shl edx, 5
        lea rsi, {mem(data_rva+0x1700)}
        add rsi, rdx
        lea rbp, {mem(color_rva)}
        lea rbp, [rbp+rcx*4]
    record:
        movzx r9d, byte ptr [rsi]
        test r9d, r9d
        je done
        add r9, rbx
        movsx r10d, word ptr [rsi+1]
        mov r11d, r10d
        neg r11d
        cmovs r11d, r10d
        xor r8d, r8d
    channel:
        movzx eax, byte ptr [rbp+r8]
        imul eax, r11d
        xor edx, edx
        mov ecx, 255
        div ecx
        test r10d, r10d
        jge positive
        neg eax
    positive:
        mov byte ptr [r9+r8], al
        inc r8d
        cmp r8d, 3
        jb channel
        add rsi, 4
        jmp record
    done:
        pop rbp
        pop rsi
        pop rbx
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        ret
    ''')
    sites = [(0xcc6f4, 0x8b540, 0x10), (0xcc73e, 0x8b540, 0x10),
             (0xcc78e, 0x8b7e0, 0x22), (0xcc7c3, 0x8b7e0, 0x22),
             (0xcc7f6, 0x8b7e0, 0x22), (0xcc860, 0x8b7e0, 0x22),
             (0xcc8da, 0x8b540, 0x10), (0xcc900, 0x8b7e0, 0x22),
             (0xcc92a, 0x8b6a0, 0x0a)]
    for site, constructor, offset in sites:
        target, argument = (profile,list(PROFILES).index(site)) if site in PROFILES else (tint,offset)
        start = emit(f'cast_color_{site:x}', f'''
            call {constructor:#x}
            push rdx
            mov edx, {argument}
            call {target:#x}
            pop rdx
            jmp {site+5:#x}
        ''')
        jump(site, 5, start, f'Tint private casting particle at {site:x}')
    edit(0xcc8b6,b'\x90'*3,'Keep Meredy motes in their elemental hue instead of adding red alone')
    return b''.join(bytes(rgb)+b'\0' for rgb in COLORS.values())
