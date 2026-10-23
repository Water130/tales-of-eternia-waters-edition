"""Spell-local counters and next-gain meters; no invented projectile milestones."""
import struct


def emit_bonus_panel(emit,mem,ui,data,choices,value,text,number,loc,string,payload,state,tabletext,usage):
    from spell_progress_ui import emit_spell_progress
    progress=emit_spell_progress(emit,mem,value)
    from spell_growth_panel import emit_growth_panel
    growth=emit_growth_panel(emit,mem,ui,data,choices,text,string,payload,state,tabletext,usage)
    from mastery_exp_bar import emit_exp_bar
    gauge=emit_exp_bar(emit,mem,'mastery_buff_exp_bar')
    entries=[]
    for i in range(26):entries.append((string(f'+{i}%'),string(f'+{i}%')))
    for i in range(4):entries.append((string(f'+{i} cible'+('s' if i!=1 else '')),string(f'+{i} target'+('s' if i!=1 else ''))))
    payload.extend(b'\0'*((-len(payload))%4));bonuses=state+len(payload)
    for entry in entries:payload.extend(struct.pack('<2I',*entry))
    serial=0
    def phrase(fr,en,x,y,width,color=0xffffffff):
        nonlocal serial
        serial+=1
        return f'''lea rcx, {mem(string(en))}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne bonus_lang_{serial}
            lea rcx, {mem(string(fr))}
        bonus_lang_{serial}:
            mov edx, {x}
            mov r8d, {y}
            mov r9d, {width}
            mov eax, {color}
            call {text:#x}'''
    meter=emit('mastery_spell_meter_rect',f'''
        sub rsp, 0x58
        cvtsi2ss xmm0, ecx
        cvtsi2ss xmm1, edx
        cvtsi2ss xmm3, r8d
        cvtsi2ss xmm2, r9d
        movss dword ptr [rsp+0x20], xmm2
        xorps xmm2, xmm2
        mov dword ptr [rsp+0x30], 0xbf800000
        mov dword ptr [rsp+0x40], 0x40000000
        mov dword ptr [rsp+0x48], r10d
        call 0x24490
        add rsp, 0x58
        ret
    ''')
    return emit('mastery_spell_bonus_panel',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0x38
        mov rbx, rcx
        call {value:#x}
        mov esi, eax
        mov edi, edx
        {loc('casts')}
        mov edx, 160
        mov r8d, 174
        mov r9d, 70
        mov eax, 0xffffad61
        call {text:#x}
        {loc('unknown')}
        test edi, edi
        je count
        movzx ecx, byte ptr {mem(ui+4)}
        mov edx, dword ptr [rbx+4]
        call {usage['catchup']['read_rva']:#x}
        call {number:#x}
    count:
        mov edx, 199
        mov r8d, 174
        mov r9d, 35
        mov eax, 0xffffffff
        call {text:#x}
        mov ecx, 238
        mov edx, 187
        mov r8d, 1
        mov r9d, 46
        mov r10d, 140
        call {meter:#x}
        test edi, edi
        je hidden
        mov eax, dword ptr [rbx+4]
        cmp eax, 63
        jb native
        cmp eax, 66
        jbe bonus
        cmp eax, 70
        jb native
        mov rcx, rbx
        mov edx, esi
        call {growth:#x}
        jmp done
    bonus:
        mov rcx, rbx
        call {progress:#x}
        mov esi, eax
        mov edi, edx
        mov dword ptr [rsp+0x28], r8d
        mov dword ptr [rsp+0x2c], r9d
        cmp dword ptr [rbx+4], 70
        jb buff
        {phrase('Puissance :','Power:',40,190,75)}
        jmp amount
    buff:
        {phrase('Cibles :','Targets:',40,190,75)}
        add esi, 26
    amount:
        lea rbp, {mem(bonuses)}
        lea rbp, [rbp+rsi*8]
        {tabletext('rbp',0)}
        mov edx, 73
        mov r8d, 190
        mov r9d, 100
        mov eax, 0xff70f0a0
        call {text:#x}
        mov eax, esi
        sub eax, 26
        call {number:#x}
        mov edx, 55
        mov r8d, 202
        mov r9d, 18
        mov eax, 0xffffffff
        call {text:#x}
        {phrase('Niv.','Lv.',40,202,14)}
        mov ecx, 76
        mov edx, 202
        mov r8d, 154
        mov r9d, 10
        xor r10d, r10d
        call {gauge:#x}
        mov eax, dword ptr [rsp+0x28]
        imul eax, eax, 154
        xor edx, edx
        mov ecx, 100
        div ecx
        test eax, eax
        je bar_label
        mov r8d, eax
        mov ecx, 76
        mov edx, 202
        mov r9d, 10
        mov r10d, 1
        test edi, edi
        jne fill_buff
        inc r10d
    fill_buff:
        call {gauge:#x}
    bar_label:
        test edi, edi
        je maximum
        {phrase('EXP avant le prochain gain','EXP to next gain',40,213,115)}
        mov eax, dword ptr [rsp+0x2c]
        call {number:#x}
        mov edx, 170
        mov r8d, 213
        mov r9d, 50
        mov eax, 0xffffffff
        call {text:#x}
        jmp state
    maximum:
        {phrase('MAX','MAX',142,202,24)}
    state:
        {loc('on')}
        movzx eax, byte ptr {mem(ui+4)}
        shl eax, 8
        add eax, dword ptr [rbx+4]
        lea rdx, {mem(choices)}
        bt dword ptr [rdx], eax
        jnc option
        {loc('off')}
    option:
        cmp byte ptr {mem(data+0x1a0c)}, 0
        jne state_text
        {loc('globaloff')}
    state_text:
        mov edx, 40
        mov r8d, 227
        mov r9d, 190
        mov eax, 0xffbbbbbb
        call {text:#x}
        jmp done
    native:
        {phrase('Effets natifs conservés.','Native effects preserved.',40,190,190)}
        {phrase('Aucun bonus par utilisation.','No usage bonus.',40,202,190)}
        jmp done
    hidden:
        {phrase('???','???',40,190,190)}
        {phrase('Sort à découvrir.','Spell not yet discovered.',40,202,190)}
    done:
        add rsp, 0x38
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
