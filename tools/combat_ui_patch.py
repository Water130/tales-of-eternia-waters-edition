"""Native battle gauges, build 25190541. Display-only state lives in .tedata.

PV/PT reuse the HUD's own two underlines. Casts follow rendered sprite feet.
Item gauge reads 12cea5a; the execution hook captures its actual 90/26-tick span.
No gameplay timer, save field, cooldown or rendering template is enlarged.
"""


def emit_combat_ui(emit, mem, jump, edit, data_rva):
    # Keep both native X/Y calculations, including Y=220+bounce. Only the
    # victory digits' render depth changes: 506 is in front of the gauges at
    # 507. Restore the scratch depth immediately, including between the two
    # native text passes, so subsequent UI rendering keeps its original layer.
    victory = emit('ui_victory_tp_foreground', f'''
        sub rsp, 0x58
        mov r10, qword ptr [rsp+0x80]
        mov qword ptr [rsp+0x20], r10
        mov r10, qword ptr [rsp+0x88]
        mov qword ptr [rsp+0x28], r10
        mov r10, qword ptr [rsp+0x90]
        mov qword ptr [rsp+0x30], r10
        mov r10, qword ptr [rsp+0x98]
        mov qword ptr [rsp+0x38], r10
        movzx r10d, word ptr {mem(0x11ce684)}
        mov word ptr [rsp+0x40], r10w
        mov word ptr {mem(0x11ce684)}, 506
        call 0x1114a0
        mov r10w, word ptr [rsp+0x40]
        mov word ptr {mem(0x11ce684)}, r10w
        add rsp, 0x58
        ret
    ''')
    import struct
    for at in (0x11a449,0x11a48d):
        edit(at,b'\xe8'+struct.pack('<i',victory-at-5),
             'Draw victory TP gain in front of gauges without moving its native animation')
    # Match the miniature group's screen-space anchor. The native pad helper
    # applies a second widescreen transform, which cannot align with this HUD.
    pad = emit('ui_fast_cast_pad', f'''
        push rsi
        push rdi
        push rbp
        sub rsp, 0x48
        mov edi, r8d
        shl edi, 4
        and edi, 0xf0
        movzx ebp, byte ptr [rbx+0x4e]
        mov esi, -35
        xor r10d, r10d
        mov r11, qword ptr {mem(0x12cecd8)}
        mov r9, qword ptr {mem(0x12cea60)}
        test r11, r11
        je own_anchor
        test r9, r9
        je own_anchor
    previous_slot:
        cmp r10d, ebp
        jae own_anchor
        movzx edx, byte ptr [r11+0x4f]
        sub edx, 2
        cmp edx, 1
        ja next_slot
        add edx, 3
        xor ecx, ecx
        xor eax, eax
    count_previous:
        cmp byte ptr [r9+rcx*8+0xbb8], dl
        jne next_count
        cmp byte ptr [r9+rcx*8+0xbb9], 0
        je next_count
        inc eax
    next_count:
        inc ecx
        cmp ecx, 10
        jb count_previous
        test eax, eax
        je next_slot
        imul edx, r10d, 48
        sub edx, 35
        cmp esi, edx
        cmovl esi, edx
        imul eax, eax, 14
        lea esi, [rsi+rax+2]
    next_slot:
        inc r10d
        add r11, 0x248
        jmp previous_slot
    own_anchor:
        cmp byte ptr [rbx+0x4f], 2
        jne pad_space_done
        cmp esi, -35
        je pad_space_done
        add esi, 18
    pad_space_done:
        imul eax, ebp, 48
        sub eax, 35
        cmp esi, eax
        cmovl esi, eax
        # First miniature starts at anchor+83; the pad is 16 units wide.
        # A two-unit gap stays constant at every resolution and party slot.
        lea ecx, [rsi+65]
        mov edx, 250
        mov r8d, 510
        mov r9d, edi
        mov dword ptr [rsp+0x20], 16
        mov dword ptr [rsp+0x28], -1
        mov word ptr [rsp+0x30], 0
        movzx eax, byte ptr {mem(0x12ceb7e)}
        xor edx, edx
        mov r10d, 120
        div r10d
        cmp edx, 60
        setge al
        movzx eax, al
        mov dword ptr [rsp+0x38], eax
        mov edx, 250
        call 0x140c0
        add rsp, 0x48
        pop rbp
        pop rdi
        pop rsi
        jmp 0xd53aa
    ''')
    jump(0xd53a5, 5, pad, 'Move fast-cast direction pad left of Craymel indicators')
    hpstate = data_rva+0x1000
    casts = data_rva+0x1100
    item = data_rva+0x1200
    tick = item+4
    label = data_rva+0x1340
    anchors = data_rva+0x1400  # 13 * (owner pointer, final screen X/Y); consumed each frame.

    def save_ui(offset=0x50):
        return '\n'.join(f'movdqu xmm0, xmmword ptr {mem(0x11ce620+i)}; '
                         f'movdqu xmmword ptr [rsp+{offset+i}], xmm0' for i in range(0, 0xa0, 16))

    def restore_ui(offset=0x50):
        return '\n'.join(f'movdqu xmm0, xmmword ptr [rsp+{offset+i}]; '
                         f'movdqu xmmword ptr {mem(0x11ce620+i)}, xmm0' for i in range(0, 0xa0, 16))

    frame = emit('ui_frame_guard', f'''
        mov eax, dword ptr {mem(0x12cea40)}
        cmp eax, dword ptr {mem(tick)}
        jb reset
        cmp byte ptr {mem(0x12d0ef7)}, 6
        je keep
    reset:
        lea r8, {mem(hpstate)}
        xor edx, edx
        mov ecx, 0x41
    clear:
        mov qword ptr [r8], rdx
        add r8, 8
        dec ecx
        jne clear
        lea r8, {mem(anchors)}
        mov ecx, 26
    clear_anchors:
        mov qword ptr [r8], rdx
        add r8, 8
        dec ecx
        jne clear_anchors
    keep:
        mov dword ptr {mem(tick)}, eax
        ret
    ''')

    # Private ABI: x,y,width,height in ECX,EDX,R8D,R9D; RGB in EAX.
    rect = emit('ui_rectangle', f'''
        mov r10, qword ptr {mem(0x644a58)}
        test r10, r10
        je no_buffer
        cmp dword ptr [r10+0x2000008], 0x1ffffcc
        ja no_buffer
        mov word ptr {mem(0x11ce640)}, cx
        mov word ptr {mem(0x11ce648)}, cx
        add ecx, r8d
        mov word ptr {mem(0x11ce644)}, cx
        mov word ptr {mem(0x11ce64c)}, cx
        mov word ptr {mem(0x11ce642)}, dx
        mov word ptr {mem(0x11ce646)}, dx
        add edx, r9d
        mov word ptr {mem(0x11ce64a)}, dx
        mov word ptr {mem(0x11ce64e)}, dx
        mov dword ptr {mem(0x11ce670)}, eax
        mov dword ptr {mem(0x11ce674)}, eax
        mov dword ptr {mem(0x11ce678)}, eax
        mov dword ptr {mem(0x11ce67c)}, eax
        mov word ptr {mem(0x11ce680)}, 0
        mov word ptr {mem(0x11ce682)}, 0
        jmp 0x11f610
    no_buffer:
        ret
    ''')
    # x,y,capacity,fill in ECX,EDX,R8D,R9D, RGB in EAX.
    def emit_gauge(name, height):
        return emit(name, f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        sub rsp, 0x20
        mov ebx, ecx
        mov ebp, edx
        mov esi, r8d
        mov edi, r9d
        mov r12d, eax
        dec ecx
        dec edx
        add r8d, 2
        mov r9d, {height+2}
        mov eax, 0x18100e
        call {rect:#x}
        mov ecx, ebx
        mov edx, ebp
        mov r8d, esi
        mov r9d, {height}
        mov eax, 0x382820
        call {rect:#x}
        test edi, edi
        jle done
        cmp edi, esi
        cmova edi, esi
        mov ecx, ebx
        mov edx, ebp
        mov r8d, edi
        mov r9d, {height}
        mov eax, r12d
        call {rect:#x}
    done:
        add rsp, 0x20
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
        ''')
    gauge = emit_gauge('ui_gauge', 3)
    cast_gauge = emit_gauge('ui_cast_gauge', 2)
    # Signed current/max -> unsigned Q16 fraction, all invalid inputs clamp.
    ratio = emit('ui_ratio', '''
        xor eax, eax
        test ecx, ecx
        jle done
        test edx, edx
        jle done
        cmp ecx, edx
        cmovg ecx, edx
        mov r8d, edx
        mov eax, ecx
        shl rax, 16
        xor edx, edx
        div r8
    done:
        ret
    ''')

    # Actor RCX, metric EDX (0 HP / 1 TP); return smoothed width in EAX.
    fill = emit('ui_hud_fraction', f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x20
        xor eax, eax
        movzx r8d, byte ptr [rcx+0x4e]
        cmp r8d, 4
        jae done
        cmp edx, 1
        ja done
        mov r9, qword ptr [rcx+0xe8]
        test r9, r9
        je done
        mov rsi, rcx
        movzx edi, byte ptr [rcx+0x4f]
        inc edi
        shl r8d, 5
        shl edx, 4
        add r8d, edx
        lea rbx, {mem(hpstate)}
        add rbx, r8
        test edx, edx
        jne tp
        mov ecx, dword ptr [rsi+0x2c]
        mov edx, dword ptr [r9+0x18]
        jmp fraction
    tp:
        movsx ecx, word ptr [rsi+0x34]
        movsx edx, word ptr [r9+0x1c]
    fraction:
        call {ratio:#x}
        cmp qword ptr [rbx], rsi
        jne initial
        cmp dword ptr [rbx+8], edi
        jne initial
        mov ecx, dword ptr [rbx+12]
        cmp byte ptr {mem(0x12ceb7a)}, 0
        jne paused
        sub eax, ecx
        mov edx, eax
        sar edx, 3
        test edx, edx
        jne step
        test eax, eax
        je paused
        mov edx, 1
    step:
        add ecx, edx
    paused:
        mov eax, ecx
    initial:
        mov qword ptr [rbx], rsi
        mov dword ptr [rbx+8], edi
        mov dword ptr [rbx+12], eax
        imul eax, eax, 31
        shr eax, 16
    done:
        add rsp, 0x20
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    for metric, site, y, color in [(0,0xd1aa5,220,0x78db54),(1,0xd1b38,235,0xffad50)]:
        fn = emit(f'ui_hud_bar_{metric}', f'''
            sub rsp, 0xf0
            {save_ui()}
            mov rcx, rbx
            mov edx, {metric}
            call {fill:#x}
            mov r9d, eax
            movzx ecx, byte ptr [rbx+0x4e]
            imul ecx, ecx, 48
            sub ecx, 20
            mov edx, {y}
            mov r8d, 31
            mov eax, {color}
            mov word ptr {mem(0x11ce684)}, 0x1fb
            call {gauge:#x}
            {restore_ui()}
            add rsp, 0xf0
            jmp {site+5:#x}
        ''')
        jump(site,5,fn,f'Animated {"HP" if metric==0 else "TP"} gauge in party portrait HUD')

    from hud_layout_patch import emit_hud_layout
    emit_hud_layout(emit, mem, jump, edit, data_rva, rect, save_ui, restore_ui)

    # Return private cast record for a verified actor pointer, otherwise NULL.
    slot = emit('ui_cast_slot', f'''
        xor eax, eax
        test rcx, rcx
        je done
        movzx r9d, byte ptr [rcx+0x51]
        cmp r9d, 1
        ja done
        lea r8, {mem(0x12cecd8)}
        mov r8, qword ptr [r8+r9*8]
        test r8, r8
        je done
        mov rax, rcx
        sub rax, r8
        jb invalid
        cmp rax, 0x1240
        jae invalid
        xor edx, edx
        mov r10d, 0x248
        div r10
        test edx, edx
        jne invalid
        lea r8, {mem(0x12cece8)}
        movzx r8d, byte ptr [r8+r9]
        cmp eax, r8d
        jae invalid
        test r9d, r9d
        jne enemy
        cmp eax, 5
        jae invalid
        jmp record
    enemy:
        cmp eax, 8
        jae invalid
        add eax, 5
    record:
        shl eax, 4
        lea r8, {mem(casts)}
        add rax, r8
        ret
    invalid:
        xor eax, eax
    done:
        ret
    ''')
    capture = emit('ui_capture_cast_duration', f'''
        mov word ptr [rbx+0x8c], dx
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        mov rcx, rbx
        call {slot:#x}
        test rax, rax
        je done
        mov qword ptr [rax], rbx
        movzx edx, word ptr [rsp+32]
        mov dword ptr [rax+8], edx
    done:
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        jmp 0x112fff
    ''')
    jump(0x112ff8,7,capture,'Capture adjusted native cast duration for progress gauge')

    # This call belongs only to the battlefield actor renderer (mode 0).
    # actor+7a is overwritten later by HUD portraits: capture it here instead.
    # The world uses 1.5*x,1.5*y-20 when enabled; HUD quads use x+80,y+16.
    # Convert with the sprite renderer's own helpers BEFORE the world flag clears.
    anchor = emit('ui_capture_cast_anchor', f'''
        call 0x80090
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x20
        mov rcx, rbx
        call {slot:#x}
        test rax, rax
        je done
        lea r11, [rax+{anchors-casts}]
        mov qword ptr [r11], rbx
        movsx ecx, word ptr [rbx+0x7a]
        call 0x11e3d0
        mov dword ptr [r11+8], eax
        movsx ecx, word ptr [rbx+0x7c]
        call 0x11e430
        mov dword ptr [r11+12], eax
    done:
        add rsp, 0x20
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        jmp 0x81534
    ''')
    jump(0x8152f,5,anchor,'Capture actual battlefield sprite feet in final screen coordinates')

    castdraw = emit('ui_cast_bars', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        sub rsp, 0x100
        {save_ui()}
        mov al, byte ptr {mem(0x573c3e)}
        mov byte ptr [rsp+0xf0], al
        mov byte ptr {mem(0x573c3e)}, 0
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        xor edi, edi
    actor_loop:
        mov ecx, edi
        xor edx, edx
        cmp edi, 5
        jb group
        sub ecx, 5
        inc edx
    group:
        lea r8, {mem(0x12cece8)}
        movzx r8d, byte ptr [r8+rdx]
        cmp ecx, r8d
        jae next_actor
        lea r8, {mem(0x12cecd8)}
        mov rbx, qword ptr [r8+rdx*8]
        test rbx, rbx
        je next_actor
        imul ecx, ecx, 0x248
        add rbx, rcx
        lea r12, {mem(casts)}
        mov eax, edi
        shl eax, 4
        add r12, rax
        cmp qword ptr [r12+{anchors-casts}], rbx
        jne next_actor
        cmp word ptr [rbx+0x3c], 1
        jne inactive
        cmp dword ptr [rbx+0x2c], 0
        jle inactive
        movsx ebp, word ptr [rbx+0x8c]
        test ebp, ebp
        jle inactive
        cmp qword ptr [r12], rbx
        jne init
        mov esi, dword ptr [r12+8]
        cmp esi, 4
        jg known
    init:
        mov qword ptr [r12], rbx
        mov dword ptr [r12+8], ebp
        mov esi, ebp
    known:
        cmp ebp, 4
        jle full
        sub esi, 4
        jle next_actor
        sub ebp, 4
        mov ecx, esi
        sub ecx, ebp
        mov edx, esi
        call {ratio:#x}
        imul eax, eax, 20
        shr eax, 16
        jmp width_ready
    full:
        mov eax, 20
    width_ready:
        mov esi, eax
        mov ecx, dword ptr [r12+{anchors-casts+8}]
        sub ecx, 90
        cmp ecx, -79
        jl next_actor
        cmp ecx, 379
        jg next_actor
        mov edx, dword ptr [r12+{anchors-casts+12}]
        sub edx, 12
        cmp edx, -15
        jl next_actor
        cmp edx, 202
        jg next_actor
        mov eax, 0xe67fe8
        mov r8d, 20
        mov r9d, esi
        mov word ptr {mem(0x11ce684)}, 0x1fd
        call {cast_gauge:#x}
        jmp next_actor
    inactive:
        mov qword ptr [r12], 0
        mov dword ptr [r12+8], 0
    next_actor:
        inc edi
        cmp edi, 13
        jb actor_loop
    done:
        lea r8, {mem(anchors)}
        mov ecx, 13
    clear_anchors:
        mov qword ptr [r8], 0
        add r8, 16
        dec ecx
        jne clear_anchors
        {restore_ui()}
        mov al, byte ptr [rsp+0xf0]
        mov byte ptr {mem(0x573c3e)}, al
        add rsp, 0x100
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    wrapper = emit('ui_cast_render_hook', f'''
        call 0x11ce10
        call {castdraw:#x}
        jmp 0xd4593
    ''')
    jump(0xd458e,5,wrapper,'Draw cast progress below projected caster feet')

    capture_item = emit('ui_capture_item_cooldown', f'''
        mov word ptr {mem(0x12cea5a)}, ax
        mov word ptr {mem(item)}, ax
        mov word ptr {mem(item+2)}, 1
        jmp 0xd5adb
    ''')
    jump(0xd5ad4,7,capture_item,'Capture native item cooldown length when the item executes')

    item_status = emit('ui_item_status', f'''
        xor eax, eax
        xor r11d, r11d
        mov r10d, 0x60c8f0
        movsx edx, word ptr {mem(0x12cea5a)}
        test edx, edx
        jle expired
        cmp word ptr {mem(item+2)}, 0
        je done
        test byte ptr {mem(0x12d0f02)}, 8
        jne done
        cmp word ptr {mem(0x12d0eb2)}, 100
        je done
        mov r8, qword ptr {mem(0x12cecd8)}
        test r8, r8
        je done
        movzx r9d, byte ptr {mem(0x12cece8)}
        cmp r9d, 5
        ja done
    pending:
        test r9d, r9d
        je cooldown
        cmp word ptr [r8+0xbe], 0
        jne expired
        add r8, 0x248
        dec r9d
        jmp pending
    cooldown:
        movzx r8d, word ptr {mem(item)}
        cmp r8d, 4
        jbe done
        cmp edx, r8d
        ja done
        mov ecx, edx
        mov eax, r8d
        sub eax, ecx
        shl eax, 6
        xor edx, edx
        div r8d
        mov r11d, 1
        ret
    expired:
        mov word ptr {mem(item+2)}, 0
    done:
        ret
    ''')
    itemdraw = emit('ui_item_bar', f'''
        sub rsp, 0xf8
        {save_ui()}
        cmp byte ptr {mem(data_rva+0x1a06)}, 0
        je done
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        call {item_status:#x}
        test r11d, r11d
        je done
        mov r9d, eax
        mov eax, r10d
        mov ecx, 128
        mov edx, 42
        mov r8d, 64
        mov word ptr {mem(0x11ce684)}, 0x1fb
        call {gauge:#x}
        lea rcx, {mem(label)}
        cmp byte ptr {mem(0x11c9ce8)}, 3
        je item_language_ready
        lea rcx, {mem(label+6)}
    item_language_ready:
        mov eax, 231
        cvtsi2ss xmm1, eax
        mov eax, 45
        cvtsi2ss xmm2, eax
        mov eax, 510
        cvtsi2ss xmm3, eax
        mov dword ptr [rsp+0x20], 0x40e00000
        mov dword ptr [rsp+0x28], 0xffe0e8f0
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x40], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
    done:
        {restore_ui()}
        add rsp, 0xf8
        ret
    ''')
    wrapper = emit('ui_hud_frame_hook', f'''
        call {frame:#x}
        call 0xd18d0
        call {itemdraw:#x}
        jmp 0xd4174
    ''')
    jump(0xd416f,5,wrapper,'Reset private gauge state between battles and draw active item cooldown')
    return dict(hud='compact 48-unit slots; right-aligned native 12x12 digits fitting 9999 in shortened 31x3 gauges with unchanged right edge; lowered HUD, native formation; all owned spirits below portraits with 10x10 atlas miniatures and vitality text',
                cast='20x2 pink-violet bar centered 4 screen units below actual rendered feet; full at <=4 ticks',
                item='top center above battle menu; visible only after execution, while native 12cea5a recharges',
                visual_validation=False)
