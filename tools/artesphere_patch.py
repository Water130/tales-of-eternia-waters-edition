"""Two seven-command palettes. Build 25190541 only; no save-format changes.

The native six-slot editor is used under a scoped palette exchange. It never
leaves palette B in the game's save state between calls. Physical trigger bits
come from 5d4e7/5d501 (input table indices 13 and 16, not action IDs).
"""
import struct

L2, R2 = 0x40000, 0x80000
PROFILE_SIZE = 96


def emit_artesphere(emit, mem, jump, edit, data, symbols, state):
    payload = bytearray(0x2000)
    strings = {}
    cursor = 0x1000
    def string(key, value, wide=False):
        nonlocal cursor
        if wide: cursor = (cursor+1)&~1
        blob = (value+'\0').encode('utf-16-le' if wide else 'utf-8')
        strings[key] = state+cursor
        payload[cursor:cursor+len(blob)] = blob
        cursor += len(blob)
        assert cursor <= len(payload)
        return strings[key]
    for key, fr, en in [
        ('a','Artesphere — Page A','Artesphere — Page A'),
        ('b','Artesphere — Page B','Artesphere — Page B'),
        ('trigger','/','/'),
        ('help','L2 / touche Page : changer de page','L2 / Page key: switch page'),
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
    profile, extra = state+0x20, state+0x60
    # Default page B is a copy of current native commands, once per loaded game.
    init = emit('artesphere_initialize',f'''
        cmp byte ptr {mem(initialized)}, 0
        jne done
        lea rax, {mem(0x11ca4ba)}
        lea rdx, {mem(profile)}
        mov ecx, 7
    next:
        mov r8d, dword ptr [rax]
        mov dword ptr [rdx], r8d
        add rax, 0xd0
        add rdx, 4
        dec ecx
        jne next
        movups xmm0, xmmword ptr {mem(0x11cad3c)}
        movups xmmword ptr {mem(profile+28)}, xmm0
        mov byte ptr {mem(initialized)}, 1
    done:
        ret
    ''')
    swap = emit('artesphere_exchange',f'''
        lea rax, {mem(0x11ca4ba)}
        lea rdx, {mem(profile)}
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
        movups xmm1, xmmword ptr {mem(profile+28)}
        movups xmmword ptr {mem(0x11cad3c)}, xmm1
        movups xmmword ptr {mem(profile+28)}, xmm0
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
        test dword ptr {mem(0x8c9180)}, {L2}
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
    jump(0x114292,6,direct,'Page B directional artes for controller zero')
    # Native combo paths branch directly to the displaced TEST, not the load.
    combo_test=emit('artesphere_combo_test','test ebx, ebx; jmp 0x114298')
    jump(0x1141c5,5,combo_test,'Preserve combo failure branch over directional lookup')
    jump(0x1141dc,5,combo_test,'Preserve combo result branch over directional lookup')
    # Expand the native ally dispatcher, preserving its TP/state/action checks.
    # R2 is edge-triggered and uses its own cast source tag (0x100).
    dispatch = emit('artesphere_dispatch',f'''
        cmp edi, 2
        jne normal
        cmp byte ptr [r14+0x56], 0
        jne skip
        mov r9d, dword ptr {mem(0x8c9184)}
        and r9d, {R2}
        je skip
        movzx eax, byte ptr [r14+0x4f]
        cmp eax, 6
        ja skip
        imul eax, eax, 4
        test dword ptr {mem(0x8c9180)}, {L2}
        je extra_a
        add eax, 2
    extra_a:
        lea rdx, {mem(extra)}
        movzx ecx, byte ptr [rdx+rax]
        movzx ebp, byte ptr [rdx+rax+1]
        jmp custom
    normal:
        movzx ebp, byte ptr [r10+rax*2+0x91d]
        cmp byte ptr [r14+0x56], 0
        jne original
        test dword ptr {mem(0x8c9180)}, {L2}
        je original
        lea rdx, {mem(profile+28)}
        movzx ecx, byte ptr [rdx+rdi*2]
        movzx ebp, byte ptr [rdx+rdi*2+1]
    custom:
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
    jump(0x1133cf,11,dispatch,'Resolve seven-slot commands without indexing past native pairs')
    edit(0x1134bb,b'\x03','Third shortcut iteration',False)
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
    tag = emit('artesphere_cast_tag',f'''
        cmp edi, 2
        jne normal
        mov r15w, 0x100
    normal:
        mov word ptr [rbx+0xa4], r15w
        jmp 0x113547
    ''')
    jump(0x11353f,8,tag,'Capture R2 source independently of subsequent page changes')

    from artesphere_storage import emit_storage
    storage = emit_storage(emit,mem,jump,data,state,profile,string,symbols)

    from artesphere_keyboard import emit_keyboard
    keyboard = emit_keyboard(emit,mem,jump,data,state,string,init)

    from artesphere_keys_ui import emit_keys_ui
    keyboard['ui']=emit_keys_ui(emit,mem,data,state,string,loc,symbols,keyboard)

    from artesphere_ui import emit_ui
    ui = emit_ui(emit,mem,jump,edit,state,profile,extra,strings,loc,symbols,
                 init,enter,leave,name_table,L2,R2)
    for i,value in enumerate((20.,132.,135.25,139.5,142.5)):
        struct.pack_into('<f',payload,0xc60+i*4,value)
    return dict(state_rva=state,profile_rva=profile,extra_rva=extra,
                pages=2,slots_per_page=7,controller_slot=0,
                physical_l2=L2,physical_r2=R2,storage=storage,ui=ui,
                keyboard=keyboard),bytes(payload)
