"""Battle framing at the final camera-to-render handoff, build 25190541 only.

10d515 copies current XYZ into the render matrix, after effect camera scripts.
11c6e5..11c707 initializes center (160,120) and focal length 512.
19f995..19f9ab projects x = 160 + (world_x + camera_x)*512/depth.
Actor x is fixed 1/16; depth increases zoom out. Reserve 32 of the 160
horizontal pixels plus 64 world units for sprite bodies on either side.
"""

def emit_camera(emit, mem, jump, data_rva, bounded=False):
    # Private state survives native script writes; not used by gameplay logic.
    initialized=data_rva+0x20
    smooth_x=data_rva+0x24
    smooth_z=data_rva+0x28
    # The last projected row is the narrowest part of a flat arena. Bounds
    # come from the audited native grids, not actor positions. An inset of 16
    # world units keeps texture borders out of view as integer projection rounds.
    bound = emit('camera_bound_pair', f'''
        push rdx
        push r8
        push r9
        push r10
        cmp byte ptr {mem(data_rva+0x6c)}, 1
        jne done
        mov r8d, dword ptr {mem(data_rva+0x60)}
        mov r9d, dword ptr {mem(data_rva+0x64)}
        mov r10d, r9d
        sub r10d, r8d
        imul r10d, r10d, 8
        push rax
        mov eax, r10d
        xor edx, edx
        mov r10d, 5
        div r10d
        mov edx, dword ptr {mem(data_rva+0x68)}
        add edx, dword ptr {mem(data_rva+0x90)}
        inc edx
        sar edx, 1
        sub eax, edx
        mov r10d, eax
        pop rax
        cmp eax, r10d
        cmovg eax, r10d
        mov edx, eax
        add edx, dword ptr {mem(data_rva+0x68)}
        imul edx, edx, 5
        add edx, 15
        sar edx, 4
        add r8d, edx
        mov edx, eax
        add edx, dword ptr {mem(data_rva+0x90)}
        imul edx, edx, 5
        add edx, 15
        sar edx, 4
        sub r9d, edx
        cmp ecx, r8d
        cmovl ecx, r8d
        cmp ecx, r9d
        cmovg ecx, r9d
    done:
        pop r10
        pop r9
        pop r8
        pop rdx
        ret
    ''')
    # After easing the center, allow only the zoom that fits this intermediate
    # center. This makes the camera slide inward before exposing more scenery.
    fit_zoom = emit('camera_fit_zoom', f'''
        push rcx
        push rdx
        push r8
        push r9
        cmp byte ptr {mem(data_rva+0x6c)}, 1
        jne done
        mov r8d, ecx
        sub r8d, dword ptr {mem(data_rva+0x60)}
        mov r9d, dword ptr {mem(data_rva+0x64)}
        sub r9d, ecx
        push rax
        mov eax, r8d
        shl eax, 4
        xor edx, edx
        mov ecx, 5
        div ecx
        sub eax, dword ptr {mem(data_rva+0x68)}
        mov r8d, eax
        mov eax, r9d
        shl eax, 4
        xor edx, edx
        div ecx
        sub eax, dword ptr {mem(data_rva+0x90)}
        cmp r8d, eax
        cmovg r8d, eax
        pop rax
        cmp eax, r8d
        jle done
        mov eax, r8d
        mov r8d, eax
        shl r8d, 8
        mov dword ptr {mem(data_rva+0x34)}, r8d
        mov dword ptr {mem(data_rva+0x38)}, 0
    done:
        pop r9
        pop r8
        pop rdx
        pop rcx
        ret
    ''')
    # Q8 critically damped motion: acceleration and speed bounded in both axes.
    # Record: position, velocity. Return rounded position, preserve pair inputs.
    ease = emit('camera_ease_axis', f'''
        push rcx
        push r9
        push r10
        push r11
        mov r9d, ecx
        shl r9d, 8
        cmp byte ptr {mem(initialized)}, 1
        jne initial
        mov eax, dword ptr [rdx]
        mov r10d, r9d
        sub r10d, eax
        mov ecx, r10d
        sar ecx, 4
        mov r11d, dword ptr [rdx+4]
        sar r11d, 1
        sub ecx, r11d
        mov r11d, r8d
        sar r11d, 2
        cmp ecx, r11d
        cmovg ecx, r11d
        neg r11d
        cmp ecx, r11d
        cmovl ecx, r11d
        add ecx, dword ptr [rdx+4]
        cmp ecx, r8d
        cmovg ecx, r8d
        neg r8d
        cmp ecx, r8d
        cmovl ecx, r8d
        add eax, ecx
        test r10d, r10d
        jle falling
        cmp eax, r9d
        jge initial
        jmp settle
    falling:
        cmp eax, r9d
        jle initial
    settle:
        mov r11d, r9d
        sub r11d, eax
        add r11d, 128
        cmp r11d, 256
        ja moving
        lea r11d, [rcx+128]
        cmp r11d, 256
        jbe initial
    moving:
        mov dword ptr [rdx], eax
        mov dword ptr [rdx+4], ecx
        jmp rounded
    initial:
        mov eax, r9d
        mov dword ptr [rdx], eax
        mov dword ptr [rdx+4], 0
    rounded:
        add eax, 128
        sar eax, 8
        pop r11
        pop r10
        pop r9
        pop rcx
        ret
    ''')
    start=emit('adaptive_battle_camera',f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne reset_camera
        lea r10, {mem(0x12cfca0)}
        mov r11d, 16
        xor ecx, ecx
    cinematic_scan:
        cmp qword ptr [r10], 0
        je next_effect
        cmp byte ptr [r10+0x33], 0
        je next_effect
        movzx eax, byte ptr [r10+0x36]
        cmp eax, 61
        je ordinary_spell
        cmp eax, 62
        je ordinary_spell
        cmp eax, 66
        je ordinary_spell
        dec eax
        cmp eax, 24
        ja native_cinematic
    ordinary_spell:
        mov ecx, 1
    next_effect:
        add r10, 0x120
        dec r11d
        jne cinematic_scan
        cmp dword ptr {mem(0x12cea92)}, 0
        jne native_cinematic
        # Ordinary intermediate/advanced spells share a level battle view,
        # regardless of their requested pitch. Other large effects keep their
        # native cinematic camera. With no effect, only small nudges normalize.
        test ecx, ecx
        jne normal_pitch
        movsx eax, word ptr {mem(0x12cea90)}
        sub eax, 56
        cmp eax, 40
        ja native_cinematic
    normal_pitch:
        mov word ptr {mem(0x12cea90)}, 64
        mov word ptr {mem(0x12ceab0)}, 64
        mov byte ptr {mem(data_rva+0x6c)}, 0
        mov dword ptr {mem(data_rva+0x94)}, 512
        movzx eax, word ptr {mem(0x12d0eb2)}
        cmp eax, 128
        jae arena_ready
        {'' if bounded else 'jmp arena_ready'}
        shl eax, 4
        lea r10, {mem(data_rva+0x800)}
        add r10, rax
        cmp word ptr [r10+8], 0
        je arena_ready
        movsx eax, word ptr [r10]
        add eax, 16
        mov dword ptr {mem(data_rva+0x60)}, eax
        movsx eax, word ptr [r10+2]
        sub eax, 16
        mov dword ptr {mem(data_rva+0x64)}, eax
        movsx eax, word ptr [r10+10]
        mov dword ptr {mem(data_rva+0x68)}, eax
        movsx eax, word ptr [r10+6]
        mov dword ptr {mem(data_rva+0x90)}, eax
        movsx eax, word ptr [r10+12]
        mov dword ptr {mem(data_rva+0x94)}, eax
        mov byte ptr {mem(data_rva+0x6c)}, 1
    arena_ready:
        cmp byte ptr {mem(initialized)}, 2
        jne find_actor
        # Cinematic frames saved their final XYZ in our private easing state.
        mov byte ptr {mem(initialized)}, 1
    find_actor:
        mov r8, qword ptr {mem(0x12cecd8)}
        test r8, r8
        je reset_camera
        movzx r9d, byte ptr {mem(0x12cece8)}
        test r9d, r9d
        je reset_camera
        cmp r9d, 5
        ja reset_camera
        mov eax, 4
        cmp r9d, eax
        cmova r9d, eax
        movzx ecx, byte ptr {mem(0x12ceb8d)}
        test ecx, ecx
        je tracked_actor
        dec ecx
        jmp preferred_actor
    tracked_actor:
        movzx ecx, byte ptr {mem(0x12ceb8e)}
    preferred_actor:
        cmp ecx, r9d
        jae scan_controlled
        imul rax, rcx, 0x248
        add rax, r8
        cmp word ptr [rax+0x3c], 1
        jne scan_controlled
        movzx edx, byte ptr [rax+0x57]
        dec edx
        cmp edx, 1
        jbe actor_found
    scan_controlled:
        xor ecx, ecx
        mov rax, r8
    scan_next:
        cmp word ptr [rax+0x3c], 1
        jne next_slot
        cmp byte ptr [rax+0x56], 0
        jne next_slot
        movzx edx, byte ptr [rax+0x57]
        dec edx
        cmp edx, 1
        jbe actor_found
    next_slot:
        inc ecx
        add rax, 0x248
        cmp ecx, r9d
        jb scan_next
        movzx ecx, byte ptr {mem(0x12ceb8e)}
        cmp ecx, r9d
        jae reset_camera
        imul rax, rcx, 0x248
        add rax, r8
        cmp word ptr [rax+0x3c], 1
        jne reset_camera
    actor_found:
        mov r8, rax
        mov r9, rax
        mov r10, qword ptr {mem(0x12cece0)}
        test r10, r10
        je frame_pair
        movzx r11d, byte ptr {mem(0x12cece9)}
        test r11d, r11d
        je frame_pair
        cmp r11d, 8
        ja frame_pair
        movzx eax, byte ptr [r8+0x63]
        cmp eax, r11d
        jae pointer_target
        imul rax, rax, 0x248
        add rax, r10
        cmp word ptr [rax+0x3c], 1
        jne pointer_target
        cmp dword ptr [rax+0x2c], 0
        jle pointer_target
        mov r9, rax
        jmp frame_pair
    pointer_target:
        mov rdx, qword ptr [r8]
    pointer_scan:
        cmp rdx, r10
        je pointer_found
        add r10, 0x248
        dec r11d
        jne pointer_scan
        jmp frame_pair
    pointer_found:
        cmp word ptr [rdx+0x3c], 1
        jne frame_pair
        cmp dword ptr [rdx+0x2c], 0
        jle frame_pair
        mov r9, rdx
    frame_pair:
        movsx r10d, word ptr [r8+0x10]
        movsx r11d, word ptr [r9+0x10]
        sar r10d, 4
        sar r11d, 4
        lea ecx, [r10+r11]
        sar ecx, 1
        push rcx
        sub r10d, ecx
        mov eax, r10d
        neg eax
        cmovs eax, r10d
        sub r11d, ecx
        mov edx, r11d
        neg edx
        cmovs edx, r11d
        cmp eax, edx
        cmovl eax, edx
        add eax, 64
        shl eax, 2
        mov edx, dword ptr {mem(data_rva+0x94)}
        cmp eax, edx
        cmovl eax, edx
        movsx edx, word ptr {mem(0x12ceb78)}
        cmp edx, 512
        jl zoom_floor_ready
        cmp edx, 2048
        jg zoom_floor_ready
        cmp eax, edx
        cmovl eax, edx
    zoom_floor_ready:
        pop rcx
        call {bound:#x}
        push rax
        lea rdx, {mem(data_rva+0x2c)}
        mov r8d, 4096
        call {ease:#x}
        mov dword ptr {mem(smooth_x)}, eax
        pop rcx
        lea rdx, {mem(data_rva+0x34)}
        mov r8d, 16384
        call {ease:#x}
        mov ecx, dword ptr {mem(smooth_x)}
        push rax
        mov eax, dword ptr {mem(data_rva+0x94)}
        call {bound:#x}
        pop rax
        cmp ecx, dword ptr {mem(smooth_x)}
        je center_valid
        mov edx, ecx
        shl edx, 8
        mov dword ptr {mem(data_rva+0x2c)}, edx
        mov dword ptr {mem(data_rva+0x30)}, 0
    center_valid:
        mov dword ptr {mem(smooth_x)}, ecx
        call {fit_zoom:#x}
        mov dword ptr {mem(smooth_z)}, eax
        push rcx
        mov ecx, 32
        lea rdx, {mem(data_rva+0x80)}
        mov r8d, 4096
        call {ease:#x}
        mov word ptr {mem(0x12cea9a)}, ax
        mov word ptr {mem(0x12ceaba)}, ax
        pop rcx
        mov eax, dword ptr {mem(smooth_z)}
        mov byte ptr {mem(initialized)}, 1
        neg ecx
        mov word ptr {mem(0x12cea98)}, cx
        mov word ptr {mem(0x12ceab8)}, cx
        mov word ptr {mem(0x12cea9c)}, ax
        mov word ptr {mem(0x12ceabc)}, ax
        jmp camera_done
    native_cinematic:
        # Never touch native summon cameras or their goals. Seed the return
        # motion from the actual final cinematic frame, including height.
        movsx eax, word ptr {mem(0x12cea98)}
        neg eax
        shl eax, 8
        mov dword ptr {mem(data_rva+0x2c)}, eax
        mov dword ptr {mem(data_rva+0x30)}, 0
        movsx eax, word ptr {mem(0x12cea9c)}
        shl eax, 8
        mov dword ptr {mem(data_rva+0x34)}, eax
        mov dword ptr {mem(data_rva+0x38)}, 0
        movsx eax, word ptr {mem(0x12cea9a)}
        shl eax, 8
        mov dword ptr {mem(data_rva+0x80)}, eax
        mov dword ptr {mem(data_rva+0x84)}, 0
        mov byte ptr {mem(initialized)}, 2
        jmp camera_done
    reset_camera:
        mov byte ptr {mem(initialized)}, 0
    camera_done:
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        mov rcx, qword ptr {mem(0x12cea98)}
        jmp 0x10d51c
    ''')
    jump(0x10d515,7,start,'Frame controlled actor and selected target at render handoff')
