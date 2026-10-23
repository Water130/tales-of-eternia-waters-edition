"""Keep the legacy TIM descriptors separate for concurrently active spell IDs.

6a4e0 keys descriptors by virtual VRAM address, so later TIM uploads overwrite
earlier rectangles/part indices even though draw commands carry a resource ID.
Snapshot the completed load, including links between parts of the SAME asset.
The native vtable still resolves/caches the game's textures. No GPU assets,
save data, spell geometry, damage or animation timings are changed.

CLUT objects have a separate lifetime: 6acf0 reused them by (x,y) alone.
Retain their native allocation/map ownership, but include spell resource ID in
reuse and draw matching. A shallow snapshot would leave dangling map pointers.
"""
PARTS = 64
STRIDE = 0x80  # original pointer, VRAM key, native 0x68-byte descriptor, padding
BANK = 0x10 + PARTS * STRIDE
COUNT = 78


def emit_spell_textures(emit, mem, jump, data):
    def owned(yes, no):
        # EAX is a resource ID, not an effect ID.
        return f'''
            lea ecx, [eax-123]
            cmp ecx, 76
            jbe {yes}
            jmp {no}
        '''
    palette_reuse = emit('spell_palette_reuse', f'''
        mov eax, dword ptr [rbp-0x39]
        cmp eax, dword ptr [rbx+8]
        je coordinates
        {owned('foreign', 'existing')}
    existing:
        mov eax, dword ptr [rbx+8]
        {owned('foreign', 'coordinates')}
    coordinates:
        cmp dword ptr [rbx+0x10], r12d
        jne foreign
        jmp 0x6ad4e
    foreign:
        jmp 0x6ad54
    ''')
    jump(0x6ad48, 6, palette_reuse,
         'Spell palettes: retain native CLUT objects belonging to other resources')
    palette_select = emit('spell_palette_select', f'''
        mov eax, dword ptr [rdi+0x14]
        {owned('resource', 'unowned')}
    unowned:
        # Enemy/character assets also share VRAM coordinates. Never let an
        # unowned draw borrow a retained party-spell palette; the loader
        # isolates that pair in both directions, so selection must too.
        mov eax, dword ptr [rdx+8]
        {owned('foreign', 'coordinates')}
    resource:
        cmp eax, dword ptr [rdx+8]
        jne foreign
    coordinates:
        mov ecx, dword ptr [rdx+0x10]
        cmp r12d, ecx
        jmp 0x5f4ab
    foreign:
        jmp 0x5f4c5
    ''')
    jump(0x5f4a5, 6, palette_select,
         'Spell palettes: resolve queued draws by resource and CLUT coordinates')
    capture = emit('spell_texture_capture', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        push r15
        sub rsp, 0x28
        mov eax, ecx
        cmp eax, {COUNT}
        jae done
        test eax, eax
        je done
    allowed:
        imul ebp, eax, {BANK}
        lea rbx, {mem(data)}
        add rbx, rbp
        lea r12d, [eax+122]
        mov dword ptr [rbx], 0
        mov rax, qword ptr {mem(0x11c9e18)}
        test rax, rax
        je done
        mov r13, qword ptr [rax+0x48]
        test r13, r13
        je done
        mov r14, qword ptr [r13]
        mov r15d, 4096
        lea rdi, [rbx+0x10]
    node:
        cmp r14, r13
        je link_start
        dec r15d
        je invalid
        mov rsi, qword ptr [r14+0x28]
        test rsi, rsi
        je next_node
        cmp dword ptr [rsi+8], 4
        jne next_node
        cmp dword ptr [rsi+0xc], r12d
        jne next_node
        cmp dword ptr [rbx], {PARTS}
        jae invalid
        mov qword ptr [rdi], rsi
        mov rax, qword ptr [r14+0x20]
        mov qword ptr [rdi+8], rax
        # Copy the native descriptor; resolve its links in a second pass.
        mov ecx, 13
        add rdi, 0x10
        rep movsq
        add rdi, 8
        inc dword ptr [rbx]
    next_node:
        # Bounded in-order traversal of the native std::map.
        mov rax, qword ptr [r14+0x10]
        cmp byte ptr [rax+0x19], 0
        jne parent
        mov r14, rax
    leftmost:
        dec r15d
        je invalid
        mov rax, qword ptr [r14]
        cmp byte ptr [rax+0x19], 0
        jne node
        mov r14, rax
        jmp leftmost
    parent:
        mov rax, qword ptr [r14+8]
    ascend:
        dec r15d
        je invalid
        cmp byte ptr [rax+0x19], 0
        jne parent_done
        cmp r14, qword ptr [rax+0x10]
        jne parent_done
        mov r14, rax
        mov rax, qword ptr [rax+8]
        jmp ascend
    parent_done:
        mov r14, rax
        jmp node
    link_start:
        mov r14d, dword ptr [rbx]
        lea rdi, [rbx+0x10]
    link_entry:
        test r14d, r14d
        je done
        mov r15d, 0x40
    link:
        mov rdx, qword ptr [rdi+r15+0x10]
        xor eax, eax
        test rdx, rdx
        je set_link
        mov ecx, dword ptr [rbx]
        lea rsi, [rbx+0x10]
    find_link:
        cmp qword ptr [rsi], rdx
        je found_link
        add rsi, {STRIDE}
        dec ecx
        jne find_link
        jmp set_link
    found_link:
        lea rax, [rsi+0x10]
    set_link:
        mov qword ptr [rdi+r15+0x10], rax
        # Recompute active-link selection at the native draw boundary.
        mov byte ptr [rdi+r15+0x18], 0
        add r15d, 0x10
        cmp r15d, 0x50
        jbe link
        add rdi, {STRIDE}
        dec r14d
        jmp link_entry
    invalid:
        mov dword ptr [rbx], 0
    done:
        add rsp, 0x28
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
    loaded = emit('spell_texture_loaded', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x20
        # R12 is the resource ID passed to every upload in this load.
        # The shared pending-effect tag may already name a different request.
        lea ecx, [r12d-122]
        call {capture:#x}
        add rsp, 0x20
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        mov rsi, qword ptr {mem(0x8659d8)}
        jmp 0x11574e
    ''')
    jump(0x115747, 7, loaded, 'Spell textures: snapshot completed native TIM load')
    cached = emit('spell_texture_cached_load', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x20
        # R13 is reset by the native type-5/model branch (75e74).
        # R12 retains the actual texture resource throughout the entire load.
        lea ecx, [r12d-122]
        call {capture:#x}
        add rsp, 0x20
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        mov r15, qword ptr [rsp+0x40]
        jmp 0x75f1c
    ''')
    jump(0x75f17, 5, cached, 'Spell textures: refresh descriptors after cached TIM load')
    continuation = emit('spell_texture_continuation_load', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x20
        # A running effect can upload its next resource directly in 1158a0,
        # bypassing both the initial and cached-load entry points.
        lea ecx, [r13d-122]
        call {capture:#x}
        add rsp, 0x20
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        movzx edx, byte ptr {mem(0x12d0efb)}
        jmp 0x115cdb
    ''')
    jump(0x115cd4, 7, continuation, 'Spell textures: capture continuation resource loads')
    lookup = emit('spell_texture_lookup', f'''
        push rax
        push rdx
        push r8
        mov eax, dword ptr {mem(0x59431c)}
        sub eax, 122
        cmp eax, {COUNT}
        jae fallback
        test eax, eax
        je fallback
        imul eax, eax, {BANK}
        lea rdx, {mem(data)}
        add rdx, rax
        mov r8d, dword ptr [rdx]
        test r8d, r8d
        je fallback
        cmp r8d, {PARTS}
        ja fallback
        add rdx, 0x10
    search:
        cmp qword ptr [rdx+8], rdi
        je found
        add rdx, {STRIDE}
        dec r8d
        jne search
        jmp fallback
    found:
        lea rsi, [rdx+0x10]
    fallback:
        pop r8
        pop rdx
        pop rax
        mov rcx, qword ptr {mem(0x644a10)}
        jmp 0x11d03e
    ''')
    jump(0x11d037, 7, lookup, 'Spell textures: bind the owning spell descriptor')
    return dict(state_rva=data, size=BANK*COUNT, bank_size=BANK,
                parts=PARTS, stride=STRIDE,
                palette_isolation='Native CLUT lifetime; resource-aware reuse and queued-draw selection',
                resource_ids=list(range(123,200)),
                note='Per-resource native TIM metadata for every large effect, including boss-only assets; runtime rendering requires visual validation.')
