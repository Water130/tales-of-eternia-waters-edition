"""Unseen camp-skit notice, Steam build 25190541.

Mirror the native camp selector at 16ab39..16abdd, without calling the player
13acc0 (which marks a skit as seen). Native predicates remain authoritative.
Runs at the END of the native exploration HUD, never global frame submission.
Terrain and font query scratch are restored; no save data or input is changed.
"""


def emit_skit_notice(emit, mem, jump, data, symbols):
    state = data + 0x3800
    payload = bytearray(0x40)
    strings = {}
    for name, text in [('title_fr', 'Saynète'), ('title_en', 'Skit'),
                       ('detail_fr', 'Disponible'),
                       ('detail_en', 'Available')]:
        strings[name] = state + len(payload)
        payload.extend((text + '\0').encode('utf-8'))
    assert len(payload) < 0x800  # INI path ends before 3800; logo starts at 4000.

    def save(rva, size, offset):
        return '\n'.join(f'movdqu xmm0, xmmword ptr {mem(rva+i)}; '
                         f'movdqu xmmword ptr [rsp+{offset+i}], xmm0'
                         for i in range(0, size, 16))

    def restore(rva, size, offset):
        return '\n'.join(f'movdqu xmm0, xmmword ptr [rsp+{offset+i}]; '
                         f'movdqu xmmword ptr {mem(rva+i)}, xmm0'
                         for i in range(0, size, 16))

    # Return the ready exploration mode; world terrain queries additionally
    # require the world context. Never query during fades or field events.
    # 866f80 is the active skit; 8c9f98 is the event interpreter wait state.
    ready = emit('skit_exploration_context', f'''
        xor eax, eax
        # Native menu-background capture is requested before switching the
        # exploration renderer. Do not bake the notice into that background.
        cmp byte ptr {mem(0x119ea49)}, 0
        jne done
        test byte ptr {mem(0x11cc542)}, 0x40
        je done
        cmp word ptr {mem(0x866f80)}, 0
        jne done
        cmp word ptr {mem(0x8c9f98)}, 0
        jne done
        cmp word ptr {mem(0x8ca0c0)}, -1
        jne done
        # 8cab70 selects the scene animation table, not input ownership.
        # Native field control predicate 1a1be0 reads the NEXT byte.
        test byte ptr {mem(0x8cab71)}, 0x0c
        jne done
        # Keep hidden throughout all six native dialogue-window lifetimes,
        # including the wait-for-confirm phase and text/page transitions.
        lea rdx, {mem(0x11a7b46)}
        mov ecx, 6
    dialogue:
        cmp word ptr [rdx], 0
        jne done
        add rdx, 0x68
        dec ecx
        jne dialogue
        test byte ptr {mem(0x11cc540)}, 0x10
        jne done
        # Native fade duration/current opacity (same guards as field HUD).
        cmp word ptr {mem(0x62ae30)}, 0
        jne done
        cmp word ptr {mem(0x62ae34)}, 0
        jne done
        movzx ecx, word ptr {mem(0x119ea28)}
        cmp ecx, 6
        je field
        cmp ecx, 2
        jne done
        movzx ecx, byte ptr {mem(0x11cb354)}
        test ecx, ecx
        je region_ok
        cmp ecx, 3
        jne done
    region_ok:
        mov rdx, qword ptr {mem(0x8befc0)}
        test rdx, rdx
        je done
        cmp byte ptr [rdx+4], cl
        jne done
        mov r8, qword ptr [rdx+0x13a0]
        test r8, r8
        je done
        lea r9, {mem(0x15ea90)}
        cmp qword ptr [r8+0xc0], r9
        jne done
        cmp qword ptr [rdx+0x598], 0
        je done
        cmp qword ptr [rdx+0x580], 0
        je done
        cmp qword ptr [rdx+0x5a8], 0
        je done
        cmp word ptr [rdx+8], 0
        jne done
        mov eax, 2
        ret
    field:
        test byte ptr {mem(0x8c2a28)}, 0x0f
        jne done
        mov eax, 6
    done:
        ret
    ''')

    available = emit('skit_notice_context', f'''
        xor eax, eax
        cmp byte ptr {mem(data+0x1a07)}, 0
        je disabled
        jmp {ready:#x}
    disabled:
        ret
    ''')

    probe = emit('skit_notice_probe', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        sub rsp, 0x120
        {save(0x644b40, 0x100, 0x20)}
        xor ebx, ebx
        movsx ebp, word ptr {mem(0x8cdb08)}
        lea rsi, {mem(0x599980)}
        lea r12, {mem(0x11cb0e8)}
    candidate:
        mov eax, ebx
        shr eax, 5
        mov ecx, ebx
        and ecx, 31
        mov eax, dword ptr [r12+rax*4]
        bt eax, ecx
        jc next
        movsx eax, word ptr [rsi+4]
        cmp ebp, eax
        jl next
        movsx eax, word ptr [rsi+6]
        cmp ebp, eax
        jge next
        movzx ecx, word ptr [rsi+2]
        call 0x13ba70
        test eax, eax
        je next
        movzx ecx, byte ptr [rsi+1]
        call 0x13af50
        test eax, eax
        je next
        lea edi, [rbx+1]
        mov ecx, edi
        call 0x13b170
        test eax, eax
        jne found
    next:
        inc ebx
        add rsi, 8
        cmp ebx, 264
        jl candidate
        xor edi, edi
    found:
        {restore(0x644b40, 0x100, 0x20)}
        mov eax, edi
        add rsp, 0x120
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')

    field = symbols['settings_text']
    from skit_notice_collision import emit_collision
    occupied = emit_collision(emit, mem, state)
    def candidates(points):
        return '\n'.join(f'''
            mov dword ptr {mem(state+12)}, {x}
            mov dword ptr {mem(state+16)}, {y}
            call {occupied:#x}
            test eax, eax
            je found
        ''' for x, y in points)
    placement = emit('skit_notice_placement', f'''
        sub rsp, 0x28
        cmp word ptr {mem(0x119ea28)}, 2
        jne field_placement
        {candidates([(5,242),(205,242),(253,242),(5,204),(5,5),(405,5),(205,5)])}
        jmp exhausted
    field_placement:
        {candidates([(405,242),(5,242),(205,242),(253,242),(405,5),(5,5),(5,204),(405,204)])}
    exhausted:
        xor eax, eax
        jmp done
    found:
        mov eax, 1
    done:
        add rsp, 0x28
        ret
    ''')

    # Capture the most recent values of only the GPU states changed by the
    # native window/font routines. Replay them afterwards, without resetting
    # the render target, projection, viewport, scene, or command arena.
    gpu_states = (0x0c, 0x14, 0x1b, 0x1d, 0x21, 0x22, 0x23, 0x2e, 0x39)
    capture_states = '\n'.join(f'''
        cmp eax, {kind}
        jne state_next_{i}
        mov qword ptr [rsp+{0xf0+8*i}], r8
    state_next_{i}:
    ''' for i, kind in enumerate(gpu_states))
    # Keep original ordering: texture/font commands can affect shared GPU
    # state. Replaying them in opcode order could select the wrong texture.
    replay_match = '\n'.join(f'''
        cmp rdx, qword ptr [rsp+{0xf0+8*i}]
        je replay_command
    ''' for i in range(len(gpu_states)))

    def label(name, y, color):
        return f'''
            lea rcx, {mem(strings[name+'_en'])}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne {name}_language
            lea rcx, {mem(strings[name+'_fr'])}
        {name}_language:
            mov edx, dword ptr {mem(state+12)}
            add edx, 6
            mov r8d, dword ptr {mem(state+16)}
            add r8d, {y}
            mov r9d, -7
            mov eax, {color:#x}
            call {field:#x}
        '''

    draw = emit('skit_notice_draw', f'''
        sub rsp, 0x218
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        cmp qword ptr [rcx+0x4d0], 0
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        add rax, 180
        cmp rax, qword ptr [rcx+0x4d8]
        jae done
        mov rax, qword ptr {mem(0x644a58)}
        test rax, rax
        je done
        cmp dword ptr [rax+0x2000008], 0x1fff000
        ja done
        cmp qword ptr {mem(0x11c9e18)}, 0
        je done
        call {placement:#x}
        test eax, eax
        je done
        {save(0x11ce620, 0xa0, 0x50)}
        {save(0x862350, 0x70, 0x150)}
        {chr(10).join(f'mov qword ptr [rsp+{0xf0+8*i}], 0' for i in range(len(gpu_states)))}
        mov rcx, qword ptr {mem(0x644a10)}
        mov eax, dword ptr [rcx+8]
        mov dword ptr [rsp+0x138], eax
        mov r8, qword ptr [rcx+0x4d0]
        movsxd r9, dword ptr [rcx+0x4e0]
        imul r9, r9, 80
        add r9, r8
        mov qword ptr [rsp+0x140], r8
        mov qword ptr [rsp+0x148], r9
    capture:
        cmp r8, r9
        jae captured
        mov eax, dword ptr [r8]
        {capture_states}
        add r8, 80
        jmp capture
    captured:
        mov ecx, dword ptr {mem(state+12)}
        sub ecx, 80
        mov edx, dword ptr {mem(state+16)}
        sub edx, 16
        xor r8d, r8d
        mov r9d, 70
        mov dword ptr [rsp+0x20], 25
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 240
        call 0x25aaa0
        {label('title', 2, 0xffffd090)}
        {label('detail', 12, 0xffffffff)}
    replay:
        mov rdx, qword ptr [rsp+0x140]
        cmp rdx, qword ptr [rsp+0x148]
        jae replayed
        {replay_match}
        jmp replay_next
    replay_command:
        mov rcx, qword ptr {mem(0x644a10)}
        call 0x60bf0
    replay_next:
        add qword ptr [rsp+0x140], 80
        jmp replay
    replayed:
        test dword ptr [rsp+0x138], 0x10
        jne restore_texture
        mov ecx, 4
        call 0x6f4b0
    restore_texture:
        test dword ptr [rsp+0x138], 0x200
        jne restored
        mov ecx, 9
        call 0x6f4b0
    restored:
        {restore(0x862350, 0x70, 0x150)}
        {restore(0x11ce620, 0xa0, 0x50)}
    done:
        add rsp, 0x218
        ret
    ''')

    frame = emit('skit_notice_frame', f'''
        sub rsp, 0x28
        call {available:#x}
        test eax, eax
        je hidden
        cmp dword ptr {mem(state+24)}, 0
        je controls_ready
        dec dword ptr {mem(state+24)}
        jmp done
    controls_ready:
        cmp eax, dword ptr {mem(state+8)}
        je same_context
        mov dword ptr {mem(state+8)}, eax
        mov qword ptr {mem(state)}, 0
    same_context:
        cmp dword ptr {mem(state)}, 0
        je refresh
        mov eax, dword ptr {mem(state+4)}
        test eax, eax
        je wait
        dec eax
        lea rdx, {mem(0x11cb0e8)}
        bt dword ptr [rdx], eax
        jc refresh
    wait:
        dec dword ptr {mem(state)}
        jmp render
    refresh:
        call {probe:#x}
        mov dword ptr {mem(state+4)}, eax
        mov dword ptr {mem(state)}, 29
    render:
        cmp dword ptr {mem(state+4)}, 0
        je done
        call {draw:#x}
        jmp done
    hidden:
        mov qword ptr {mem(state)}, 0
        # Half a second of uninterrupted control prevents flicker between
        # dialogue pages or chained scene events.
        mov dword ptr {mem(state+24)}, 30
    done:
        add rsp, 0x28
        ret
    ''')

    # World terrain can emit screen-space polygons, particularly during camera
    # rotation. Only commands appended by its HUD can reserve notice positions.
    begin = emit('skit_notice_world_hud_begin', f'''
        push rax
        mov rax, qword ptr {mem(0x644a10)}
        mov qword ptr {mem(state+32)}, rax
        test rax, rax
        je no_queue
        mov eax, dword ptr [rax+0x4e0]
    no_queue:
        mov dword ptr {mem(state+28)}, eax
        pop rax
        push rbx
        sub rsp, 0x20
        jmp 0x157e66
    ''')
    jump(0x157e60, 6, begin, 'Record world HUD queue boundary before minimap and prompts')
    # Both sites run after normal exploration HUD rendering. Never intercept
    # 6f070: it also submits resource loads and partially built scene frames.
    entry = emit('skit_notice_world_hud', f'''
        sub rsp, 0x30
        mov qword ptr [rsp+0x20], rax
        call {frame:#x}
        mov rax, qword ptr [rsp+0x20]
        add rsp, 0x30
        add rsp, 0x20
        pop rbx
        ret
    ''')
    jump(0x157f1f, 6, entry, 'Skit notice after native world-map HUD')
    entry = emit('skit_notice_field_hud', f'''
        call 0x25c490
        sub rsp, 0x30
        mov qword ptr [rsp+0x20], rax
        call {frame:#x}
        mov rax, qword ptr [rsp+0x20]
        add rsp, 0x30
        jmp 0x198a59
    ''')
    jump(0x198a54, 5, entry, 'Skit notice after native town/dungeon HUD')
    return dict(state_rva=state, strings=strings, refresh_frames=30,
                camp_table_rva=0x599980, camp_count=264, viewed_rva=0x11cb0e8,
                native_predicates=[0x13af50, 0x13ba70, 0x13b170],
                scope='Inferia/Celestia world map and field exploration; native location/story/party predicates; Camp Skits option',
                presentation='Bottom-left world map, bottom-right field; other corners, bottom center and raised side positions if occupied; hidden during transitions or unsafe rendering',
                gpu_restore_commands=list(gpu_states),
                runtime_validated=False), bytes(payload)
