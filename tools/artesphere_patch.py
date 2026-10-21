"""Three six-command palettes. Build 25190541 only; no save-format changes.

The native six-slot editor is used under a scoped palette exchange. It never
leaves palette B/C in the game's save state between calls. Physical trigger bits
come from 5d4e7/5d501 (input table indices 13 and 16, not action IDs).
"""
import struct

L2, R2 = 0x40000, 0x80000
PROFILE_SIZE = 96


def emit_artesphere(emit, mem, jump, edit, data, symbols, state):
    payload = bytearray(0xf000)
    strings = {}
    cursor = 0x1000
    def string(key, value, wide=False):
        nonlocal cursor
        if wide: cursor = (cursor+1)&~1
        blob = (value+'\0').encode('utf-16-le' if wide else 'utf-8')
        strings[key] = state+cursor
        payload[cursor:cursor+len(blob)] = blob
        cursor += len(blob)
        assert cursor <= 0x2000
        return strings[key]
    for key, fr, en in [
        ('a','Artesphere — Page A','Artesphere — Page A'),
        ('b','Artesphere — Page B','Artesphere — Page B'),
        ('c','Artesphere — Page C','Artesphere — Page C'),
        ('help','L2 : page B / A — R2 : page C / A','L2: page B / A — R2: page C / A'),
        ('helpkeys','Touche page B / C : changer de page','Page B / C key: switch page'),
        ('fail','Affectations du mod : sauvegarde indisponible','Mod assignments: could not save'),
        ('select','Sélect.','Select'),('empty','Aucun','None'),('confirm','Valider','Confirm'),('back','Retour','Back'),
    ]:
        string(key+'_fr',fr); string(key+'_en',en)
    string('names','Reid\0Farah\0Keele\0Meredy\0Chat\0Max\0Rassius')
    name_table = state+0xf00
    offset = strings['names']
    for i, name in enumerate(('Reid','Farah','Keele','Meredy','Chat','Max','Rassius')):
        struct.pack_into('<I',payload,0xf00+i*4,offset)
        offset += len(name)+1
    def loc(name, reg='rcx'):
        return f'''lea {reg}, {mem(strings[name+'_en'])}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne lang_{name}_{reg}
            lea {reg}, {mem(strings[name+'_fr'])}
        lang_{name}_{reg}:'''
    initialized, page, depth, modal = (state+i for i in range(4))
    owner, choice, selected_char, error = (state+i for i in (4,5,6,7))
    profile = state+0x20
    # Each page stores 7*4 directional bytes + 4*4 ally-shortcut bytes.
    # Two 44-byte pages fit in the existing 96-byte transport.
    # New profiles copy native A into B and C once per loaded game.
    init = emit('artesphere_initialize',f'''
        cmp byte ptr {mem(initialized)}, 0
        jne done
        lea rdx, {mem(profile)}
        mov r10d, 2
    palette:
        lea rax, {mem(0x11ca4ba)}
        mov ecx, 7
    next:
        mov r8d, dword ptr [rax]
        mov dword ptr [rdx], r8d
        add rax, 0xd0
        add rdx, 4
        dec ecx
        jne next
        movups xmm0, xmmword ptr {mem(0x11cad3c)}
        movups xmmword ptr [rdx], xmm0
        add rdx, 16
        dec r10d
        jne palette
        mov byte ptr {mem(initialized)}, 1
    done:
        ret
    ''')
    swap = emit('artesphere_exchange',f'''
        lea rax, {mem(0x11ca4ba)}
        lea rdx, {mem(profile)}
        movzx ecx, byte ptr {mem(page)}
        dec ecx
        cmp ecx, 1
        ja done
        imul ecx, ecx, 44
        add rdx, rcx
        mov ecx, 7
    next:
        mov r8d, dword ptr [rax]
        mov r9d, dword ptr [rdx]
        mov dword ptr [rax], r9d
        mov dword ptr [rdx], r8d
        add rax, 0xd0
        add rdx, 4
        dec ecx
        jne next
        movups xmm0, xmmword ptr {mem(0x11cad3c)}
        movups xmm1, xmmword ptr [rdx]
        movups xmmword ptr {mem(0x11cad3c)}, xmm1
        movups xmmword ptr [rdx], xmm0
    done:
        ret
    ''')
    enter = emit('artesphere_enter_editor',f'''
        sub rsp, 0x28
        call {init:#x}
        inc byte ptr {mem(depth)}
        cmp byte ptr {mem(depth)}, 1
        jne done
        cmp byte ptr {mem(page)}, 0
        je done
        call {swap:#x}
    done:
        add rsp, 0x28
        ret
    ''')
    leave = emit('artesphere_leave_editor',f'''
        sub rsp, 0x28
        dec byte ptr {mem(depth)}
        jne done
        cmp byte ptr {mem(page)}, 0
        je done
        call {swap:#x}
    done:
        add rsp, 0x28
        ret
    ''')
    # RCX character index, EDX arte. Do not accept enemy/unlearned IDs.
    learned = emit('artesphere_learned',f'''
        xor eax, eax
        cmp ecx, 6
        ja done
        test edx, edx
        je done
        cmp edx, 255
        ja done
        imul r9d, ecx, 0xd0
        lea r8, {mem(0x11ca49a)}
        add r8, r9
        mov r9d, 32
    next:
        cmp byte ptr [r8], dl
        je found
        inc r8
        dec r9d
        jne next
        ret
    found:
        mov eax, 1
    done:
        ret
    ''')
    direct = emit('artesphere_direct',f'''
        movzx ebx, byte ptr [rax+rbp]
        cmp byte ptr [rbp+0x56], 0
        jne done
        test dword ptr {mem(0x8c9180)}, {L2|R2}
        je done
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        sub rsp, 0x20
        sub eax, 0xac
        cmp eax, 3
        ja invalid
        movzx ecx, byte ptr [rbp+0x4f]
        cmp ecx, 6
        ja invalid
        lea edx, [eax+ecx*4]
        test dword ptr {mem(0x8c9180)}, {R2}
        je palette_b
        add edx, 44
    palette_b:
        lea rax, {mem(profile)}
        movzx ebx, byte ptr [rax+rdx]
        mov edx, ebx
        call {learned:#x}
        test eax, eax
        jne validated
    invalid:
        xor ebx, ebx
    validated:
        add rsp, 0x20
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
    done:
        test ebx, ebx
        jmp 0x114298
    ''')
    jump(0x114292,6,direct,'Page B/C directional artes for controller zero')
    # Native combo paths branch directly to the displaced TEST, not the load.
    combo_test=emit('artesphere_combo_test','test ebx, ebx; jmp 0x114298')
    jump(0x1141c5,5,combo_test,'Preserve combo failure branch over directional lookup')
    jump(0x1141dc,5,combo_test,'Preserve combo result branch over directional lookup')
    # Keep the two native ally commands and their original cast-source tags.
    # R2 selects C, with priority over L2; pressing a page key never casts.
    dispatch = emit('artesphere_dispatch',f'''
        movzx ebp, byte ptr [r10+rax*2+0x91d]
        cmp byte ptr [r14+0x56], 0
        jne original
        test dword ptr {mem(0x8c9180)}, {L2|R2}
        je original
        lea rdx, {mem(profile+28)}
        test dword ptr {mem(0x8c9180)}, {R2}
        je palette_b
        add rdx, 44
    palette_b:
        movzx ecx, byte ptr [rdx+rdi*2]
        movzx ebp, byte ptr [rdx+rdi*2+1]
        test r9d, r9d
        je skip
        sub rsp, 0x40
        mov dword ptr [rsp+0x20], ecx
        mov dword ptr [rsp+0x28], r9d
        dec ecx
        mov edx, ebp
        call {learned:#x}
        mov ecx, dword ptr [rsp+0x20]
        mov r9d, dword ptr [rsp+0x28]
        add rsp, 0x40
        test eax, eax
        je skip
        mov rbx, qword ptr {mem(0x12cecd8)}
        xor edx, edx
        dec ecx
        jmp 0x113420
    original:
        mov rdx, qword ptr [r14+0xf0]
        test ebp, ebp
        jmp 0x1133da
    skip:
        mov r10, qword ptr {mem(0x12cea60)}
        jmp 0x1134b3
    ''')
    jump(0x1133cf,11,dispatch,'Resolve two native shortcuts from selected A/B/C palette')
    guard = emit('artesphere_owner_guard',f'''
        test rbx, rbx
        je skip
        movzx eax, byte ptr [rbx+0x75]
        cmp al, 0xc
        jmp 0x113445
    skip:
        jmp 0x1134b3
    ''')
    jump(0x11343f,6,guard,'Skip shortcuts whose caster is absent')
    from arte_usage_patch import emit_usage
    usage = emit_usage(emit,mem,jump,state)
    from artesphere_storage import emit_storage
    storage = emit_storage(emit,mem,jump,data,state,profile,string,symbols,usage)

    from artesphere_keyboard import emit_keyboard
    keyboard = emit_keyboard(emit,mem,jump,data,state,string,init,symbols.get('skit_shortcut_input'))

    from artesphere_keys_ui import emit_keys_ui
    keyboard['ui']=emit_keys_ui(emit,mem,data,state,string,loc,symbols,keyboard)

    from artesphere_ui import emit_ui
    ui = emit_ui(emit,mem,jump,state,loc,symbols,init,enter,leave,L2,R2)
    return dict(state_rva=state,profile_rva=profile,page_stride=44,
                pages=3,slots_per_page=6,controller_slot=0,page_priority='C then B then A',
                physical_l2=L2,physical_r2=R2,storage=storage,ui=ui,
                keyboard=keyboard,usage=usage),bytes(payload)
