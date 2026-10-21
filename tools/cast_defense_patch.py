"""Guard cancellation and deliberate mage jumping, Steam build 25190541.

Run after the controller and shortcut readers, before the common cast tick.
Use native mapped per-actor inputs; never change the shared input buffer.
"""


def emit_cast_defense(emit, mem, jump, data):
    save = 'pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    restore = 'pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    entry = emit('cast_defense_controls', f'''
        {save}
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        cmp byte ptr [rcx+0x51], 0
        jne done
        cmp word ptr [rcx+0x3c], 1
        jne done
        cmp byte ptr [rcx+0x57], 1
        jb done
        cmp byte ptr [rcx+0x57], 2
        ja done
        cmp dword ptr [rcx+0x2c], 0
        jle done
        cmp word ptr [rcx+0x44], 0
        jne done
        cmp byte ptr [rcx+0x74], 0
        jne done
        test dword ptr [rcx+0x30], 0x4000
        jne done
        cmp word ptr [rcx+0x12], 0
        jne done
        mov rax, qword ptr [rcx+0xf0]
        test rax, rax
        je done
        test word ptr [rax], 0x200
        jne done
        cmp byte ptr {mem(data+0x1a0a)}, 0
        je jump_option
        cmp byte ptr [rcx+0x52], 10
        jne jump_option
        cmp word ptr [rcx+0x8c], 0
        jle done
        test byte ptr [rax+4], 0x80
        je done
        test byte ptr [rax], 0x80
        je done
        cmp qword ptr [rcx+0xe8], 0
        je done
        cmp qword ptr {mem(0x12cea60)}, 0
        je done
        sub rsp, 0x20
        call 0x712e0
        add rsp, 0x20
        mov byte ptr [rcx+0x52], 0
        mov byte ptr [rcx+0x75], 0
        mov word ptr [rcx+0x90], 6
        jmp done
    jump_option:
        movzx edx, byte ptr [rcx+0x4f]
        cmp edx, 3
        ja done
        cmp edx, 1
        jbe fighter_jump
        cmp byte ptr {mem(data+0x1a0b)}, 0
        je done
        jmp deliberate_jump
    fighter_jump:
        cmp byte ptr {mem(data+0x1a0d)}, 0
        je done
    deliberate_jump:
        cmp byte ptr [rcx+0x52], 3
        ja done
        test byte ptr [rax], 0x80
        je block_bare_jump
        test byte ptr [rax+0x10], 1
        je block_bare_jump
        cmp byte ptr [rax+0xd], 2
        jb block_bare_jump
        mov word ptr [rcx+0x90], 3
        cmp byte ptr [rcx+0x52], 2
        jne done
        mov byte ptr [rcx+0x52], 0
        jmp done
    block_bare_jump:
        cmp word ptr [rcx+0x90], 3
        jne done
        mov word ptr [rcx+0x90], 0
        cmp byte ptr [rcx+0x52], 2
        jb walking_direction
        jne running_direction
        jmp done
    walking_direction:
        test byte ptr [rax+0x10], 2
        je walking_right
        mov word ptr [rcx+0x90], 1
        jmp done
    walking_right:
        test byte ptr [rax+0x10], 8
        je done
        mov word ptr [rcx+0x90], 2
        jmp done
    running_direction:
        cmp byte ptr [rcx+0x53], 0xff
        jne running_left
        test byte ptr [rax+0x10], 8
        jne brake
        jmp done
    running_left:
        cmp byte ptr [rcx+0x53], 1
        jne done
        test byte ptr [rax+0x10], 2
        je done
    brake:
        mov word ptr [rcx+0x90], 5
    done:
        {restore}
        movzx r13d, word ptr [rcx+0x90]
        jmp 0xd5214
    ''')
    jump(0xd520c, 8, entry, 'Mapped Guard cancels pending casts; separately optional mage and fighter Guard plus Up jumps')
    return dict(hook=0xd520c, continuation=0xd5214, native_cleanup=0x712e0,
                cancel_option='GuardSpellCancel', cancel_flag_index=10,
                jump_option='MageGuardJump', jump_flag_index=11,
                fighter_jump_option='FighterGuardJump', fighter_jump_flag_index=13,
                input='Per-actor native mapped Guard press/hold and Up direction',
                scope='Living grounded party characters under manual/semi-auto control in active combat',
                cancel='Fresh Guard press during a pending cast; native cleanup then native guard transition',
                jump='Keele/Meredy and Reid/Farah: independent switches, Guard held + Up for the native two-tick threshold',
                cancel_takes_priority=True, input_buffer_unchanged=True,
                diagonal_walk_and_dash_brake_preserved=True,
                released_effects_unchanged=True, ai_unchanged=True)
