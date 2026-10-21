"""Explore-only skit playback through the original reader, never the renderer.

Raw L2 is 0x40000, Select is 1 (5d4e7/5d566). Native control defaults
40d80 assign the two rings to action IDs 12/14 (L1/R1), leaving L2 free.
If any exploration binding uses action ID 13, require L2+Select instead.
"""


def emit_skit_shortcut(emit, mem, jump, data, symbols, keyboard_bridge):
    previous, claimed, actions = data+0x1a60, data+0x1a64, data+0x1a68
    flag = data+0x1a40
    # Native bindings at +54..80 are exploration actions 13..24. Action
    # bytes in the input structure have held/pressed/repeated/changed banks.
    bindings = emit('skit_shortcut_bindings', f'''
        xor eax, eax
        mov rdx, qword ptr {mem(0x644a60)}
        test rdx, rdx
        je missing
        mov ecx, 13
    next:
        cmp dword ptr [rdx+rcx*4+0x20], 13
        jne other
        bts eax, ecx
    other:
        inc ecx
        cmp ecx, 25
        jb next
        ret
    missing:
        mov eax, -1
        ret
    ''')
    update = emit('skit_shortcut_input', f'''
        lea rax, {mem(0x8c9180)}
        cmp rcx, rax
        jne fast_return
        push rbx
        sub rsp, 0x30
        mov rbx, rcx
        mov eax, dword ptr [rbx]
        and eax, 0x40001
        mov edx, dword ptr {mem(previous)}
        mov dword ptr {mem(previous)}, eax
        not edx
        and edx, eax
        mov dword ptr [rsp+0x20], edx
        cmp byte ptr {mem(flag)}, 0
        je release
        mov ecx, dword ptr {mem(claimed)}
        test ecx, ecx
        je new_press
        test eax, ecx
        jne consume
    release:
        mov dword ptr {mem(claimed)}, 0
        mov dword ptr {mem(actions)}, 0
        jmp done
    new_press:
        # No deferred playback when holding the button through a transition.
        test eax, 0x40000
        je done
        cmp dword ptr [rsp+0x20], 0
        je done
        call {symbols['skit_exploration_context']:#x}
        test eax, eax
        je done
        # Native overlay/menu input modes, in addition to the scene guards.
        cmp word ptr {mem(0x8c8a80)}, 0
        jne done
        cmp word ptr {mem(0x8c8a90)}, 0
        jne done
        cmp eax, 2
        jne resources
        cmp dword ptr {mem(0x8befb0)}, 0
        jne done
    resources:
        cmp qword ptr {mem(0x644a60)}, 0
        je done
        cmp qword ptr {mem(0x11c9e18)}, 0
        je done
        cmp word ptr {mem(0x866f84)}, 0
        jne done
        call {bindings:#x}
        mov dword ptr {mem(actions)}, eax
        test eax, eax
        je single
        mov eax, dword ptr [rbx]
        and eax, 0x40001
        cmp eax, 0x40001
        jne done
        jmp accepted
    single:
        test dword ptr [rsp+0x20], 0x40000
        je done
        mov eax, dword ptr [rbx]
        and eax, 0x40001
    accepted:
        mov dword ptr {mem(claimed)}, eax
        call {symbols['skit_notice_probe']:#x}
        test eax, eax
        je consume
        mov ecx, eax
        # Original player owns resource loading, viewed flags and audio.
        # No camp command, healing, teleport, event pointer or save edits.
        call 0x13acc0
    consume:
        mov eax, dword ptr {mem(claimed)}
        not eax
        and dword ptr [rbx], eax
        and dword ptr [rbx+4], eax
        and dword ptr [rbx+8], eax
        and dword ptr [rbx+12], eax
        # Also suppress any remapped ring/camera action attached to L2.
        mov eax, dword ptr {mem(actions)}
        xor ecx, ecx
    action:
        bt eax, ecx
        jnc skip
        mov byte ptr [rbx+rcx+0xa4], 0
        mov byte ptr [rbx+rcx+0xc4], 0
        mov byte ptr [rbx+rcx+0xe4], 0
        mov byte ptr [rbx+rcx+0x104], 0
    skip:
        inc ecx
        cmp ecx, 32
        jb action
    done:
        add rsp, 0x30
        pop rbx
    fast_return:
        ret
    ''')
    if not keyboard_bridge:
        bridge = emit('skit_shortcut_poll', f'''
            push rax
            sub rsp, 0x28
            mov rcx, rbx
            call {update:#x}
            add rsp, 0x28
            pop rax
            mov rbx, qword ptr [rsp+0x30]
            jmp 0x19df42
        ''')
        jump(0x19df3d, 5, bridge, 'Handle explore-only skit shortcut after native input')
    return dict(flag_rva=flag, previous_rva=previous, claimed_rva=claimed,
                actions_rva=actions, native_player_rva=0x13acc0,
                input_rva=update, poll_hook_rva=0x19df3d,
                control='L2/LT; L2+Select if rebound to an exploration action',
                native_ring_defaults={'Sorcerer': 'R1/RB', 'Freeze': 'L1/LB'},
                runtime_validated=False)
