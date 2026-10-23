"""Per-caster victory notices, using the menu's authoritative spell level.

The native victory routine ticks every frame at 119E7C. Its award frame is 88.
Snapshot counters at battle entry; compare only at victory, never on loading.
Native mastery sprite IDs are deliberately untouched: their atlas has no spells.
"""
import json
import struct
from pathlib import Path
from spell_growth import OFFENSIVE, PROJECTILE_CAPS

SHORT = {
    70: ('Lisière aqua', 'Aqua Edge'), 73: ('Estocade aér.', 'Air Thrust'),
    77: ('Mur de flammes', 'Flame Wall'), 81: ('Élan terrestre', 'Ground Dasher'),
    82: ('Épines de glace', 'Ice Needles'), 83: ('Lance-glace', 'Freeze Lancer'),
    87: ('Lame tonnerre', 'Thunder Blade'), 90: ('Lance sacrée', 'Holy Lance'),
    92: ('Hurlement sang.', 'Bloody Howling'), 93: ('Météores', 'Meteor Swarm'),
    94: ('Étoile filante', 'Shooting Star'), 101: ('Maître éléments', 'Element Master'),
    112: ("Vague étinc.", 'Spark Wave'), 113: ('Épée lumineuse', 'Prism Sword'),
}


def snapshot_code(mem, state, usage):
    # Only Keele/Meredy have these levels. Preserve every native input/flag.
    return f'''
        pushfq; push rax; push rcx; push rdx; push r8; push r9
        lea r8, {mem(usage['catchup']['live_rva']+2*256)}
        lea rax, {mem(usage['live_rva']+2*256)}
        lea rdx, {mem(state+0x900)}
        xor ecx, ecx
    snapshot:
        movzx r9d, word ptr [rax+rcx]
        add r9w, word ptr [r8+rcx]
        mov word ptr [rdx+rcx], r9w
        add ecx, 2; cmp ecx, 512; jb snapshot
        xor eax, eax
        lea rdx, {mem(state+0xb00)}
        mov ecx, 0x110
    clear_notices:
        mov byte ptr [rdx+rcx-1], al
        dec ecx; jne clear_notices
        pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq
    '''


def emit_notices(emit, mem, jump, data, state, strings, symbols, usage):
    native=json.loads((Path(__file__).resolve().parents[1]/'audit/build-25190541/artes_native.json').read_text(encoding='utf-8'))
    byid={r['id']:r for r in native}
    # Bit 7 marks a passive-only gain. Spell IDs remain below 128.
    blob=bytearray(256*8)
    labels={};passive_labels={}
    for aid in OFFENSIVE:
        row=byid[aid]
        names=SHORT.get(aid,(row['name_fr'],row['name']))
        labels[aid]=[names[0]+'  Niv. +',names[1]+'  Lv. UP']
        for lang,text in enumerate(labels[aid]):
            struct.pack_into('<I',blob,aid*8+lang*4,strings+len(blob))
            blob.extend(text.encode('utf-8')+b'\0')
        passive_labels[aid]=[names[0]+'  Bonus niv. +',names[1]+'  Bonus Lv. UP']
        for lang,text in enumerate(passive_labels[aid]):
            struct.pack_into('<I',blob,(aid|128)*8+lang*4,strings+len(blob))
            blob.extend(text.encode('utf-8')+b'\0')
    ids=strings+len(blob);blob.extend(bytes(OFFENSIVE))
    # Sum integer ranks, before the overall level's rounding. Recovery and
    # critical use the same thresholds as casting; counting them once suffices
    # to detect their simultaneous increase. All tracks are monotonic.
    caps='\n'.join(f'cmp r11d, {aid}; jne cap_{aid}; mov ecx, {cap}; jmp shape; cap_{aid}:'
                   for aid,cap in PROJECTILE_CAPS.items())
    rank=emit('spell_notice_passive_ranks',f'''
        mov r11d, edx
        mov r8d, 999; cmp ecx, r8d; cmovb r8d, ecx
        mov eax, 500; cmp r8d, eax; cmovb eax, r8d
        mov r9d, eax
        xor edx, edx; mov ecx, 20; div ecx
        mov r10d, eax
        mov eax, r9d; imul eax, eax, 15
        xor edx, edx; mov ecx, 500; div ecx
        add r10d, eax
        mov ecx, 50
        {caps}
    shape:
        mov eax, r8d; imul eax, ecx
        xor edx, edx; mov ecx, 999; div ecx
        add eax, r10d; ret
    ''')
    prepare=emit('spell_notice_prepare',f'''
        push rbx; push rbp; push rsi; push rdi; push r12
        sub rsp, 0x30
        cmp byte ptr {mem(state+0xc02)}, 0; jne done
        mov byte ptr {mem(state+0xc02)}, 1
        cmp byte ptr {mem(data+0x1a0c)}, 0; je done
        xor ebx, ebx
    caster:
        xor esi, esi
    spell:
        lea rax, {mem(ids)}; movzx edi, byte ptr [rax+rsi]
        mov eax, ebx; shl eax, 8; lea eax, [rax+rdi*2]
        lea rdx, {mem(usage['live_rva']+512)}
        movzx ebp, word ptr [rdx+rax]
        lea rdx, {mem(usage['catchup']['live_rva']+512)}
        movzx ecx, word ptr [rdx+rax]
        add ebp, ecx
        lea rdx, {mem(state+0x900)}
        movzx ecx, word ptr [rdx+rax]
        cmp ebp, ecx; jbe next
        mov dword ptr [rsp+0x20], ecx
        mov edx, edi; call {rank:#x}
        mov r12d, eax
        mov ecx, ebp; mov edx, edi
        call {rank:#x}
        cmp eax, r12d; jbe next
        mov ecx, dword ptr [rsp+0x20]; mov edx, edi
        call {symbols['mastery_spell_total_level']:#x}
        mov r12d, eax
        mov ecx, ebp; mov edx, edi
        call {symbols['mastery_spell_total_level']:#x}
        cmp eax, r12d; ja enqueue
        or edi, 128
    enqueue:
        lea rdx, {mem(state+0xc00)}
        movzx ecx, byte ptr [rdx+rbx]
        mov eax, ebx; shl eax, 7; add eax, ecx
        lea r8, {mem(state+0xb00)}
        mov byte ptr [r8+rax], dil
        inc byte ptr [rdx+rbx]
    next:
        inc esi; cmp esi, {len(OFFENSIVE)}; jb spell
        inc ebx; cmp ebx, 2; jb caster
    done:
        add rsp, 0x30
        pop r12; pop rdi; pop rsi; pop rbp; pop rbx; ret
    ''')
    draw=emit('spell_notice_draw',f'''
        push rbx; push rbp; push rsi; push rdi; push r12
        sub rsp, 0x60
        cmp ecx, 88; jb done
        cmp byte ptr {mem(data+0x1a0c)}, 0; je done
        cmp byte ptr {mem(state+0xc02)}, 0; je done
        mov ebp, ecx; sub ebp, 88
        cmp qword ptr {mem(0x644a10)}, 0; je done
        cmp qword ptr {mem(0x644a18)}, 0; je done
        xor ebx, ebx
    caster:
        lea rax, {mem(state+0xc00)}
        movzx edi, byte ptr [rax+rbx]
        test edi, edi; je next
        mov rsi, qword ptr {mem(0x12cecd8)}
        test rsi, rsi; je done
        movzx ecx, byte ptr {mem(0x12cece8)}
        cmp ecx, 5; ja done
        lea eax, [rbx+2]
    actor:
        test ecx, ecx; je next
        cmp byte ptr [rsi+0x4f], al; je found
        add rsi, 0x248; dec ecx; jmp actor
    found:
        # Same projected sprite position as the native level-up effects.
        movsx ecx, word ptr [rsi+0x7a]
        call 0x11e3d0
        sub eax, 58
        mov edx, 4; cmp eax, edx; cmovl eax, edx
        mov edx, 356; cmp eax, edx; cmovg eax, edx
        mov r12d, eax
        movsx ecx, word ptr [rsi+0x82]
        call 0x11e430
        sub eax, 22
        mov edx, 8; cmp eax, edx; cmovl eax, edx
        mov edx, 190; cmp eax, edx; cmovg eax, edx
        mov esi, eax
        mov eax, ebp; xor edx, edx; mov ecx, 90; div ecx
        xor edx, edx; div edi
        mov eax, ebx; shl eax, 7; add eax, edx
        lea rcx, {mem(state+0xb00)}
        movzx eax, byte ptr [rcx+rax]
        lea rdx, {mem(strings)}; lea rdx, [rdx+rax*8]
        mov ecx, dword ptr [rdx+4]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne localized
        mov ecx, dword ptr [rdx]
    localized:
        lea rax, {mem(0)}; add rcx, rax
        cvtsi2ss xmm1, r12d; cvtsi2ss xmm2, esi
        mov eax, 0x43ff8000; movd xmm3, eax
        mov dword ptr [rsp+0x20], 0x40e00000
        mov dword ptr [rsp+0x28], 0xff99ffff
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x40], 0x42e80000
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
    next:
        inc ebx; cmp ebx, 2; jb caster
    done:
        add rsp, 0x60
        pop r12; pop rdi; pop rsi; pop rbp; pop rbx; ret
    ''')
    # Full volatile register, flags and SSE preservation around a native frame.
    saves='\n'.join(f'movdqu [rsp+{0x20+i*16:#x}], xmm{i}' for i in range(6))
    restores='\n'.join(f'movdqu xmm{i}, [rsp+{0x20+i*16:#x}]' for i in range(6))
    # Only this native award continuation commits the comparison. The broader
    # result renderer can also be entered without a victory (escape/abort).
    commit=emit('spell_notice_award_hook',f'''
        pushfq; push rax; push rcx; push rdx
        push r8; push r9; push r10; push r11
        sub rsp, 0x80
        {saves}
        call {prepare:#x}
        {restores}
        add rsp, 0x80
        pop r11; pop r10; pop r9; pop r8
        pop rdx; pop rcx; pop rax; popfq
        mov r15d, dword ptr [rsp+0x60]
        jmp 0x119e30
    ''')
    jump(0x119e2b,5,commit,'Commit spell level notices only after a native victory reward')
    hook=emit('spell_notice_victory_hook',f'''
        pushfq; push rax; push rcx; push rdx
        push r8; push r9; push r10; push r11
        sub rsp, 0x80
        {saves}
        mov ecx, dword ptr [rsp+0x118]
        call {draw:#x}
        {restores}
        add rsp, 0x80
        pop r11; pop r10; pop r9; pop r8
        pop rdx; pop rcx; pop rax; popfq
        mov r13d, dword ptr [rsp+0x5c]
        jmp 0x119e81
    ''')
    jump(0x119e7c,5,hook,'Show localized per-caster spell level gains during the native victory sequence')
    return dict(state_rva=state+0x900,queue_rva=state+0xb00,counts_rva=state+0xc00,
                strings_rva=strings,labels=labels,passive_labels=passive_labels,
                passive_flag=128,award_frame=88,cycle_frames=90,
                separate_casters=True,language='game language: FR or EN',
                style='native font above caster; original mastery effects unchanged',
                runtime_validated=False),bytes(blob)
