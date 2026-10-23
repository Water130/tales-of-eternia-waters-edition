"""Read-only enemy HP display using the native saved Monster Compendium.

Build 25190541: the Spectacles panel commits bit 2 of master+CF8+species
at 923BE. Encounter discovery sets bit 1 at 826D1. Enemy actor+4F is an
encounter index, translated through 12D0F33, never itself a species ID.
No extra save data or scan state is maintained by this feature.
"""
from combat_ui_layout import SCAN_LABELS, SCAN_LABELS_END, SCAN_DRAWN


def scan_labels():
    pairs=[('???','???'),('PV','HP'),('Rs :','Rs:'),('Fb :','Wk:'),('—','—'),
           ('Eau','Water'),('Vent','Wind'),('Feu','Fire'),('Terre','Earth'),('Glace','Ice'),
           ('Foudre','Volt'),('Lumière','Light'),('Ténèbres','Dark'),('Élémental','Element'),('Temps','Time')]
    import struct
    blob=bytearray(len(pairs)*8)
    for i,pair in enumerate(pairs):
        for lang,s in enumerate(pair):
            struct.pack_into('<I',blob,i*8+lang*4,SCAN_LABELS+len(blob))
            blob.extend(s.encode('utf-8')+b'\0')
    assert len(blob)<=SCAN_LABELS_END-SCAN_LABELS
    return bytes(blob)


def emit_scan_hp(emit, mem, jump, data, ratio, gauge):
    native_panel = emit('ui_native_spectacles_visible', f'''
        mov byte ptr {mem(data+SCAN_DRAWN)}, 1
        call 0x91ca0
        jmp 0xd4198
    ''')
    jump(0xd4193,5,native_panel,'Suppress R1 information until the native Spectacles window has finished drawing')
    eligible = emit('ui_scanned_enemy_hp', f'''
        xor eax, eax
        xor r11d, r11d
        cmp byte ptr {mem(data+0x1a4b)}, 0
        je done
        test rcx, rcx
        je done
        cmp byte ptr [rcx+0x51], 1
        jne done
        cmp word ptr [rcx+0x3c], 1
        jne done
        cmp dword ptr [rcx+0x2c], 0
        jle done
        movzx edx, byte ptr [rcx+0x4f]
        cmp edx, 8
        jae done
        cmp dl, byte ptr {mem(0x12cece9)}
        jae done
        lea r8, {mem(0x12d0f33)}
        movzx edx, byte ptr [r8+rdx]
        mov r8, qword ptr {mem(0x12cea60)}
        test r8, r8
        je done
        test byte ptr [r8+rdx+0xcf8], 2
        je done
        mov r8, qword ptr [rcx+0xe8]
        test r8, r8
        je done
        mov edx, dword ptr [r8+0x18]
        test edx, edx
        jle done
        mov ecx, dword ptr [rcx+0x2c]
        mov r11d, 1
        jmp {ratio:#x}
    done:
        ret
    ''')
    from scan_target_panel import emit_target_panel
    panel=emit_target_panel(emit,mem,data,eligible)
    # RCX actor, RDX fresh projected-foot anchor. The companion anchor at +100
    # stores the projected native frame top (actor+82), captured before HUD use.
    draw = emit('ui_draw_scanned_enemy_hp', f'''
        push rbx
        push rsi
        sub rsp, 0x28
        mov rbx, rdx
        mov rsi, rcx
        call {eligible:#x}
        test r11d, r11d
        je done
        imul eax, eax, 28
        shr eax, 16
        mov r9d, eax
        mov ecx, dword ptr [rbx+8]
        sub ecx, 94
        cmp ecx, -79
        jl done
        cmp ecx, 371
        jg done
        mov edx, dword ptr [rbx+0x10c]
        sub edx, 22
        cmp edx, -15
        jl done
        cmp edx, 202
        jg done
        mov r8d, 28
        mov eax, 0x60c8ec
        mov word ptr {mem(0x11ce684)}, 0x1fd
        call {gauge:#x}
        mov rcx, rsi
        mov rdx, rbx
        call {panel:#x}
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')
    return draw
