"""Replace only the two mastery-name meshes inside native victory effects."""
import hashlib,struct
from native_notice_labels import build,LABELS,label_palettes
from native_png_texture import emit_png_texture
from craymel_faculties import preserve

def emit_native_labels(emit,mem,jump,start):
    png,entries=build();blob=bytearray(0x4000)+png
    for (aid,lang,shadow),rect in entries.items():
        struct.pack_into('<4H',blob,0x100+aid*32+lang*16+shadow*8,*rect)
    init,bind=emit_png_texture(emit,mem,start,png,'spell_label_texture')
    assign=emit('spell_label_assign',f'''
        # RCX native label mesh, EDX 0=face / 1=shadow.
        test rcx, rcx; je done
        mov eax, dword ptr {mem(start+0xc4)}; test eax, eax; je done
        dec eax; shl eax, 5; shl edx, 3; add eax, edx
        cmp byte ptr {mem(0x11c9ce8)}, 3; je french
        add eax, 16
    french:
        lea rdx, {mem(start+0x100)}; mov rax, [rdx+rax]
        mov qword ptr [rcx+0x12], rax
        shr rax, 32; movzx eax, ax; shl eax, 2
        mov word ptr [rcx+0x3a], ax
        mov word ptr [rcx+0x42], 0x6000
        mov dword ptr [rcx+0x44], 0x10000400
    done: ret
    ''')
    for site,layer,original,continuation in ((0x11790a,0,0x12ced08,0x117911),(0x1179bd,1,0x12ced10,0x1179c4)):
        hook=emit(f'spell_label_constructor_{layer}',f'''
            {preserve(f'mov rcx, r9; mov edx, {layer}; call {assign:#x}')}
            mov rcx, qword ptr {mem(original)}
            jmp {continuation:#x}
        ''')
        jump(site,7,hook,'Spell notice: replace native mastery label mesh '+str(layer))
    choose=emit('spell_label_bind',f'''
        cmp byte ptr {mem(start+0xc0)}, 0; jne custom
        jmp 0x12b90
    custom: jmp {bind:#x}
    ''')
    # A CALL replacement, so the native renderer continues unchanged.
    bindhook=emit('spell_label_bind_hook',f'''
        call {choose:#x}
        jmp 0x121bae
    ''')
    jump(0x121ba9,5,bindhook,'Spell notice: bind the composed native lettering only for marked label meshes')
    draw=emit('spell_label_mesh_draw',f'''
        cmp edx, 0x5fff; je custom
        jmp 0x121b50
    custom:
        sub rsp, 0x28
        call {init:#x}
        test rax, rax; je done
        mov byte ptr {mem(start+0xc0)}, 1
        mov edx, 14; mov r8d, 1024; mov r9d, 4096
        call 0x121b50
        mov byte ptr {mem(start+0xc0)}, 0
    done: add rsp, 0x28; ret
    ''')
    hook=emit('spell_label_mesh_hook',f'call {draw:#x}; jmp 0x85b24')
    jump(0x85b1f,5,hook,'Spell notice: use the original animated mesh renderer for both localized layers')
    return dict(context_rva=start+0xc4,bind_context_rva=start+0xc0,texture_state_rva=start,
                table_rva=start+0x100,png_rva=start+0x4000,png_bytes=len(png),png_sha256=hashlib.sha256(png).hexdigest(),
                size=[1024,4096],abbreviations=LABELS,element_palettes=label_palettes(),initialize=init,
                native_mesh_renderer=0x121b50,constructor=0x117640),bytes(blob)
