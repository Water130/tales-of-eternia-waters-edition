"""Five native EXP meters (six for Eruption) and a level from earned ranks."""
import struct
from spell_growth import PROJECTILE_CAPS, HYBRID_AREA_PROJECTILES, emit_track_progress
from mastery_exp_bar import emit_exp_bar


def emit_growth_panel(emit, mem, ui, data, choices, text, string, payload, state, tabletext, usage):
    progress = emit_track_progress(emit)
    gradient = emit_exp_bar(emit, mem, 'mastery_spell_exp_gradient')
    from mastery_badges import emit_text_width
    width = emit_text_width(emit,mem)
    from mastery_rich_text import encode_runs, emit_rich_text
    compact = emit_rich_text(emit,mem,'mastery_spell_compact_bonus',left=True)
    rows = [('Puissance','Power',40,190),('Incantation','Casting',40,205),
            ('Récupération','Recovery',40,220),('Critique','Critical',246,190),
            ('Zone','Area',246,205),('Projectiles','Projectiles',246,205),
            ('Projectiles','Projectiles',246,220)]
    labels=[]
    for index,(fr,en,x,y) in enumerate(rows):
        pairs=[]
        for i in range(51):
            amount=('-' if index in (1,2) else '+')+str(i)+('' if index in (5,6) else '%')
            pairs.append(tuple(encode_runs(label+(' : ' if lang==0 else ': ')+amount,payload,state,string) for lang,label in enumerate((fr,en))))
        payload.extend(b'\0'*((-len(payload))%4))
        pointer=state+len(payload)
        for pair in pairs:payload.extend(struct.pack('<2I',*pair))
        labels.append((pointer,pointer,x,y))
    # The game's font lacks U+2212 and renders a filled-circle fallback.
    amounts=[(string(f'+{i}%'),string(f'-{i}%'),string(f'+{i}')) for i in range(51)]
    levels=[(string(f'Niv. {i}'),string(f'Lv. {i}')) for i in range(51)]
    maximum=string('MAX')
    off=[string('Maîtrise désactivée'),string('Mastery disabled')]
    on=[string('Maîtrise activée'),string('Mastery enabled')]
    catchup=[string('Rattrapage EXP x3'),string('Catch-up EXP x3')]
    globaloff=[string('Progression magique désactivée'),string('Magic progression disabled')]
    payload.extend(b'\0'*((-len(payload))%4))
    labels_rva=state+len(payload)
    for entry in labels:payload.extend(struct.pack('<4I',*entry))
    amounts_rva=state+len(payload)
    for entry in amounts:payload.extend(struct.pack('<3I',*entry))
    levels_rva=state+len(payload)
    for entry in levels:payload.extend(struct.pack('<2I',*entry))
    geometry=state+len(payload)
    payload.extend(bytes(50 if i in HYBRID_AREA_PROJECTILES else PROJECTILE_CAPS.get(i,50) for i in range(128)))
    # Sum of five normalized earned ranks, in 0..50000. Level 30 requires
    # every track's cap; all tracks now finish at 500 credited uses.
    total=emit('mastery_spell_total_level',f'''
        push rbx
        push rsi
        push rdi
        mov esi, ecx
        mov ebx, edx
        mov eax, 500
        cmp ecx, eax
        cmova ecx, eax
        mov eax, ecx
        xor edx, edx
        mov edi, 20
        div edi
        imul r8d, eax, 400
        imul eax, ecx, 15
        xor edx, edx
        mov edi, 500
        div edi
        imul eax, eax, 2000
        add r8d, eax
        mov eax, 500
        cmp esi, eax
        cmova esi, eax
        lea rax, {mem(geometry)}
        movzx ecx, byte ptr [rax+rbx]
        mov eax, esi
        imul eax, ecx
        xor edx, edx
        mov edi, 500
        div edi
        imul eax, eax, 10000
        xor edx, edx
        div ecx
        add r8d, eax
        cmp ebx, 76
        jne five_tracks
        # Sixth track: normalize all six equally back into the 0..50000
        # header contract. Neither area nor projectiles replaces the other.
        imul eax, esi, {PROJECTILE_CAPS[76]}
        xor edx, edx
        mov ecx, 500
        div ecx
        imul eax, eax, 10000
        xor edx, edx
        mov ecx, {PROJECTILE_CAPS[76]}
        div ecx
        add eax, r8d
        imul eax, eax, 5
        xor edx, edx
        mov ecx, 6
        div ecx
        mov r8d, eax
    five_tracks:
        mov eax, r8d
        imul eax, eax, 29
        xor edx, edx
        mov ecx, 50000
        div ecx
        inc eax
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    row=emit('mastery_spell_track_row',f'''
        push rbx
        push rsi
        push rdi
        push rbp
        sub rsp, 0x38
        mov dword ptr [rsp+0x2c], r9d
        mov dword ptr [rsp+0x30], edx
        call {progress:#x}
        mov dword ptr [rsp+0x20], eax
        mov dword ptr [rsp+0x24], r8d
        mov dword ptr [rsp+0x28], edx
        mov eax, dword ptr [rsp+0x2c]
        cmp eax, 4
        jne label
        cmp dword ptr [rsp+0x30], 50
        je label
        inc eax
    label:
        shl eax, 4
        lea rbx, {mem(labels_rva)}
        add rbx, rax
        mov esi, dword ptr [rbx+8]
        mov edi, dword ptr [rbx+12]
        mov ecx, dword ptr [rbx]
        lea rax, {mem(0)}
        add rcx, rax
        mov eax, dword ptr [rsp+0x20]
        lea rbx, [rcx+rax*8]
        {tabletext('rbx',0)}
        mov edx, esi
        mov r8d, edi
        mov r9d, 92
        call {compact:#x}
        mov eax, dword ptr [rsp+0x20]
        lea rbx, {mem(levels_rva)}
        lea rbx, [rbx+rax*8]
        {tabletext('rbx',0)}
        lea edx, [rsi+96]
        mov r8d, edi
        mov r9d, 27
        mov eax, 0xffeeeeee
        call {text:#x}
        lea ecx, [rsi+121]
        lea edx, [rdi-1]
        mov r8d, 65
        xor r10d, r10d
        call {gradient:#x}
        mov eax, dword ptr [rsp+0x24]
        imul eax, eax, 65
        xor edx, edx
        mov ecx, 100
        div ecx
        test eax, eax
        je bar_done
        mov r8d, eax
        lea ecx, [rsi+121]
        lea edx, [rdi-1]
        mov r10d, 1
        cmp dword ptr [rsp+0x28], 0
        jne fill
        inc r10d
    fill:
        call {gradient:#x}
    bar_done:
        cmp dword ptr [rsp+0x28], 0
        jne done
        lea rcx, {mem(maximum)}
        lea edx, [rsi+142]
        mov r8d, edi
        mov r9d, 25
        mov eax, 0xffffffff
        call {text:#x}
    done:
        add rsp, 0x38
        pop rbp
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    code=[]
    for index,cap in enumerate((25,15,15,15,50)):
        code.append(f'''
            mov ecx, esi
            mov edx, {cap}
            mov r8d, 500
            mov r9d, {index}
            {f'lea rax, {mem(geometry)}; movzx edx, byte ptr [rax+rbx]' if index==4 else ''}
            call {row:#x}
        ''')
    panel=emit('mastery_spell_growth_panel',f'''
        push rbx
        push rsi
        push rdi
        push rbp
        sub rsp, 0x38
        mov rbp, rcx
        mov ebx, dword ptr [rcx+4]
        mov esi, edx
        {tabletext('rbp',12)}
        mov r9d, 90
        call {width:#x}
        lea ebp, [rax+43]
        mov ecx, esi
        mov edx, ebx
        call {total:#x}
        mov edi, r8d
        lea rcx, {mem(levels_rva)}
        lea rcx, [rcx+rax*8]
        mov eax, dword ptr [rcx+4]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne level_text
        mov eax, dword ptr [rcx]
    level_text:
        lea rcx, {mem(0)}
        add rcx, rax
        mov edx, ebp
        mov r8d, 174
        mov r9d, 26
        mov eax, 0xffffad61
        call {text:#x}
        add ebp, 26
        mov ecx, ebp
        mov edx, 173
        mov r8d, 80
        xor r10d, r10d
        call {gradient:#x}
        imul eax, edi, 80
        xor edx, edx
        mov ecx, 50000
        div ecx
        test eax, eax
        je tracks
        mov r8d, eax
        mov ecx, ebp
        mov edx, 173
        mov r10d, 1
        cmp edi, 50000
        jne total_fill
        inc r10d
    total_fill:
        call {gradient:#x}
        cmp edi, 50000
        jne tracks
        lea rcx, {mem(maximum)}
        lea edx, [rbp+28]
        mov r8d, 174
        mov r9d, 24
        mov eax, 0xffffffff
        call {text:#x}
    tracks:
        {''.join(code)}
        cmp ebx, 76
        jne status
        mov ecx, esi
        mov edx, {PROJECTILE_CAPS[76]}
        mov r8d, 500
        mov r9d, 6
        call {row:#x}
    status:
        movzx eax, byte ptr {mem(ui+4)}
        shl eax, 8
        add eax, ebx
        lea rdx, {mem(choices)}
        bt dword ptr [rdx], eax
        jc disabled
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je global_disabled
        movzx ecx, byte ptr {mem(ui+4)}
        mov edx, ebx
        call {usage['catchup']['next_rva']:#x}
        lea ecx, [rsi+1]
        cmp eax, ecx
        jbe ordinary_exp
        lea rcx, {mem(catchup[1])}
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne catchup_text
        lea rcx, {mem(catchup[0])}
    catchup_text:
        mov edx, 320; mov r8d, 182; mov r9d, 115
        mov eax, 0xffbbbbbb; call {text:#x}
        jmp ordinary_exp
    ordinary_exp:
        lea rcx, {mem(on[1])}
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne on_text
        lea rcx, {mem(on[0])}
    on_text:
        mov eax, 0xffffffff
        jmp status_text
    disabled:
        lea rcx, {mem(off[1])}
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne off_text
        lea rcx, {mem(off[0])}
        jmp off_text
    global_disabled:
        lea rcx, {mem(globaloff[1])}
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne off_text
        lea rcx, {mem(globaloff[0])}
    off_text:
        mov eax, 0xff999999
    status_text:
        mov edx, 320
        mov r8d, 174
        mov r9d, 115
        call {text:#x}
    done:
        add rsp, 0x38
        pop rbp
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    return panel
