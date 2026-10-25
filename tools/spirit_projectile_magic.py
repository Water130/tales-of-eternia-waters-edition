"""Ordinary spells using the original Ondine spear and Sylph arrow sprites."""
import struct
from custom_effect_identity import step_guard
SPELLS=((144,24,70,15381,24,100,1,0,0,0,0),(145,24,72,15383,18,80,2,0,0,0,0))
NAMES={144:('Aqualaser','Aqualaser'),145:('Flèche du vent','Wind Arrow')}
DESCRIPTIONS={144:("Projette cinq lances d'eau en ligne droite. Chaque lance inflige des dégâts magiques d'eau.",
                  "Fires five water spears in a straight line. Each spear deals water magic damage."),
              145:("Décoche trois flèches de vent vers la cible. Chaque flèche inflige des dégâts magiques de vent.",
                  "Fires three wind arrows toward the target. Each arrow deals wind magic damage.")}
RECIPES=tuple((a,3,t,0,e,msg,tp,NAMES[a][1]) for a,e,t,msg,tp,*_ in SPELLS)

def prepare(pe,state,payload):
    rows=[]
    for i,aid in enumerate((144,145)):
        off=0x6000+i*0x100
        payload[off:off+16]=struct.pack('<HhhhHhhh',0,-3,8,0,512,-1,0,0)
        impact=bytearray(pe.get_data(0x57c878,22))
        struct.pack_into('<4h',impact,0,-24,-16,24,16)
        impact[8:12]=bytes((0x80,1+i,2,12));impact[15:18]=bytes((0,0,8))
        struct.pack_into('<H',impact,18,100 if aid==144 else 120)
        payload[off+0x20:off+0x36]=impact
        rows.append(dict(id=aid,script=state+off,impact=state+off+0x20,runtime_validated=False))
    return rows

def prepare_spark(pe,state,payload):
    # Six native collisions, totaling 1400 nominal power. Enemy data is untouched.
    impact=bytearray(pe.get_data(0x57d968,22))*2
    struct.pack_into('<H',impact,18,233)
    struct.pack_into('<H',impact,40,235)
    script=bytearray(pe.get_data(0x57dbf0,280))
    assert struct.unpack_from('<4h',script,29*8)==(88,-7,0,0)
    struct.pack_into('<h',script,29*8+6,1)
    payload[0xa000:0xa02c]=impact
    payload[0xa040:0xa158]=script
    return dict(id=112,script=state+0xa040,impact=state+0xa000,power=1400,cast_ticks=240)


def wire(emit,mem,jump,pe,relocate,info):
    rows=info['spirit_magic'];water,wind=rows
    # Borrow only the resource queue entry of Spark Wave, never its behavior.
    # Texture comes from the embedded atlas, with no dependency on the boss.
    # Resolved by the builder from the native initializer table for effect 24.
    init_site=struct.unpack('<Q',pe.get_data(0x4e9420+24*8,8))[0]-pe.OPTIONAL_HEADER.ImageBase
    frame_site=struct.unpack('<Q',pe.get_data(0x4e9900+24*8,8))[0]-pe.OPTIONAL_HEADER.ImageBase
    choices='\n'.join(f'cmp eax, {r["id"]}; jne next_{r["id"]}; lea rax, {mem(r["script"])}; mov qword ptr [rcx+0x10], rax; ret; next_{r["id"]}:' for r in rows)
    spark=info['approved_spark']
    native_init=emit('spark_native_initialize',relocate(pe.get_data(init_site,7),init_site)+f'; jmp {init_site+7:#x}')
    init=emit('spirit_magic_initialize',f'''
        sub rsp, 0x28; call {info['identity']['lookup']:#x}; add rsp, 0x28
        {choices}
        cmp eax, 112; jne native
        push rbx; sub rsp, 0x20; mov rbx, rcx
        call {native_init:#x}
        lea rax, {mem(spark['script'])}; mov qword ptr [rbx+0x10], rax
        lea rax, {mem(spark['impact'])}; mov qword ptr [rbx+0x78], rax
        add rsp, 0x20; pop rbx; ret
    native:
        {relocate(pe.get_data(init_site,7),init_site)}
        jmp {init_site+7:#x}
    ''')
    jump(init_site,7,init,'Private water spears and wind arrows: identity-specific initialization')
    # Each projectile is allocated only with room for a collision record.
    spawn=emit('spirit_magic_projectile',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx; mov rdi, r8
        lea rax, {mem(0x12cee48)}; mov ecx, 60
    free: cmp byte ptr [rax+0x20], 0; je create
        add rax, 0x30; dec ecx; jne free; jmp done
    create:
        lea rcx, {mem(0x5932fa)}; call 0x8b7e0
        test rax, rax; je done
        cmp rax, qword ptr {mem(0x12cec20)}; je done
        mov rdx, rax; mov r8, qword ptr [rbx]
        movsx ecx, byte ptr [rbx+0x30]; imul ecx, -320
        mov word ptr [rdx+0x2a], cx
        mov ax, word ptr [rbx+0x20]; add ax, cx; mov word ptr [rdx], ax
        mov ax, word ptr [rbx+0x28]; sub ax, 512; mov word ptr [rdx+2], ax
        mov dword ptr [rdx+0x8], 1; mov word ptr [rdx+0xc], 48
        mov word ptr [rdx+0x2c], 0; mov dword ptr [rdx+0x32], 0
        mov word ptr [rdx+0x26], 0; mov byte ptr [rdx+0x28], 0
        mov byte ptr [rdx+9], 1; mov word ptr [rdx+0xe], 0x20
        mov word ptr [rdx+0x14], 3968
        mov dword ptr [rdx+0x1c], 0; mov word ptr [rdx+0x20], 0
        xor eax, eax
        cmp esi, 144; je water
        mov eax, 448; mov dword ptr [rdx+0x16], 0x00600100
        mov dword ptr [rdx+0x3a], 0x01800400
        cmp byte ptr [rbx+0x30], 0; jge uv
        add eax, 256; jmp uv
    water:
        # Ondine motion 9: four flowing spear frames, two ticks per frame.
        mov word ptr [rdx+0xa], 0x10
        mov dword ptr [rdx+0x1c], 0x00040002; mov word ptr [rdx+0x20], 8
        mov dword ptr [rdx+0x16], 0x00400070
        mov dword ptr [rdx+0x3a], 0x010001c0
        cmp byte ptr [rbx+0x30], 0; jge uv
        mov word ptr [rdx+0x14], 4032
    uv:
        mov word ptr [rdx+0x12], ax
        mov dword ptr [rdx+0x22], 0x00808080; mov dword ptr [rdx+0x3e], 0
        mov word ptr [rdx+0x42], 0x6000; mov dword ptr [rdx+0x44], 0x10000400
        mov word ptr [rdx+0x48], 0
        mov ecx, 5; mov r9, rdi; call 0x116580
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    frame=emit('spirit_magic_frame',f'''
        push rax
        lea rax, {mem(water['script'])}; cmp qword ptr [rcx+0x10], rax; je owned
        lea rax, {mem(wind['script'])}; cmp qword ptr [rcx+0x10], rax; je owned
        pop rax
        {relocate(pe.get_data(frame_site,6),frame_site)}
        jmp {frame_site+6:#x}
    owned: pop rax
        cmp word ptr [rcx+0x3a], 2; je done
        {step_guard(info,'done')}
        movzx eax, word ptr [rcx+0x38]; cmp eax, 64; jae release
        cmp eax, 16; ja done
        test eax, 3; jne done
        lea r8, {mem(water['impact'])}; mov edx, 144
        lea rax, {mem(water['script'])}; cmp qword ptr [rcx+0x10], rax; je spawn
        test word ptr [rcx+0x38], 7; jne done
        lea r8, {mem(wind['impact'])}; mov edx, 145
    spawn: jmp {spawn:#x}
    release: jmp 0x115ee0
    done: ret
    ''')
    jump(frame_site,6,frame,'Private water/wind spell frame, bounded projectiles and release')
    info['spirit_magic_runtime']=dict(initialize=init,frame=frame,projectile=spawn,
                                    native_initialize=init_site,native_frame=frame_site)
