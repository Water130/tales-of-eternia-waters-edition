"""Successful casts fund native Craymel EXP at victory; no save format change."""

import json

from pathlib import Path





def rewards():

    path=Path(__file__).resolve().parents[1]/'audit/build-25190541/mastery/spell_recipes.json'

    recipes=json.loads(path.read_text())['recipes']

    native=json.loads((path.parents[1]/'artes_native.json').read_text(encoding='utf-8'))

    primary={r['arte']:r['primary'] for r in recipes}

    primary.update({70:0,72:1,75:2,79:3,82:4,86:5,

                    96:2,97:1,98:0,99:6,100:7,101:8,112:5,113:6})

    # Rank comes from the native spell description, NOT its Craymel unlock

    # level (several intermediate spells unlock as soon as a spirit joins).

    # Support/special spells have no native rank: explicitly assign a tier.

    support={54:50,55:200,56:200,57:500,58:500,59:200,60:200,

             61:50,62:200,63:50,64:50,65:50,66:50,67:200,68:500,69:500,

             77:200,96:500,97:500,98:500,99:500,100:500,101:500,112:200,113:500}

    result={}

    for row in native:

        aid=row['id']

        if aid not in primary or not 54<=aid<=113:continue

        desc=row['description']

        amount=50 if desc.startswith('Low-level') else 200 if desc.startswith('Mid-level') else 500 if desc.startswith('High-level') else support[aid]

        result[aid]=(primary[aid],amount)

    return result





def emit_experience(emit,mem,jump,data,state,usage=None,faculties=None):

    pending=state+0x800

    table=rewards()

    cases=''.join(f'cmp esi, {aid}; jne next_{aid}; mov edi, {spirit}; mov ebp, {amount}; jmp award; next_{aid}:\n'

                  for aid,(spirit,amount) in table.items())

    cast=emit('craymel_experience_cast',f'''

        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28

        cmp byte ptr {mem(data+0x1a61)}, 0; je done

        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done

        test rcx, rcx; je done

        cmp byte ptr [rcx+0x51], 0; jne done

        movzx eax, byte ptr [rcx+0x4f]; sub eax, 2; cmp eax, 1; ja done

        mov rbx, qword ptr {mem(0x12cea60)}; test rbx, rbx; je done

        mov esi, edx

        {cases}

        jmp done

    award:

        cmp byte ptr [rbx+rdi*8+0xbb8], 0; je done

        cmp byte ptr [rbx+rdi*8+0xbb9], 30; jae done

        lea rax, {mem(pending)}

        mov ecx, dword ptr [rax+rdi*4]; add ecx, ebp

        mov edx, 0xae0ea; cmp ecx, edx; cmova ecx, edx

        mov dword ptr [rax+rdi*4], ecx

    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret

    ''')

    # Native victory loop already applies ownership, cap, level-ups, result

    # notification and new Fringe availability. Replace ONLY its EXP input.

    victory=emit('craymel_experience_victory',f'''

        cmp byte ptr {mem(data+0x1a61)}, 0

        je native

        push rcx

        lea rcx, {mem(pending)}

        xor edx, edx

        cmp r14d, 10

        jae ready

        xchg edx, dword ptr [rcx+r14*4]

    ready: pop rcx

    native:

        add dword ptr [rsi], edx

        mov eax, dword ptr [rsi]

        mov dword ptr [rsp+0x64], eax

        jmp 0x119d99

    ''')

    jump(0x119d91,8,victory,'Craymel EXP: spend successful elemental casts once at victory, or retain native EXP when disabled')



    # Victory normally skips the EXP block for a KO/petrified mage. Cast EXP

    # belongs to the recruited spirit, so still run its existing award loop;

    # character EXP remains skipped. The result animation calls this only at

    # its award frame (0x58), preventing repeated settlement during display.

    knockout=emit('craymel_experience_ko_owner',f'''

        cmp byte ptr {mem(data+0x1a61)}, 0; je native

        cmp r15d, 2; jb native

        cmp r15d, 3; ja native

        cmp dword ptr [rsp+0x58], 0x58; jne native

        cmp word ptr [r13+0x3c], 1; jne 0x119bf7

        test dword ptr [r13+0x30], 0x4000; jne 0x119bf7

    native:

        cmp word ptr [r13+0x3c], 1

        jmp 0x119a07

    ''')

    jump(0x119a01,6,knockout,'Craymel EXP: retain earned casts when their cage owner finishes KO or petrified')

    # This native zeroing is executed once during battle initialization. It

    # also discards abandoned/fled battle totals and all transient faculties.

    clearing='\n'.join(f'movups {mem(state+i)}, xmm0' for i in range(0,0x830,16))
    if faculties:
        clearing+='\n'+'\n'.join(f'movups {mem(faculties["state_rva"]+i)}, xmm0' for i in range(0,faculties['size'],16))

    from spell_level_notice import snapshot_code
    notices_reset=snapshot_code(mem,state,usage) if usage else ''
    reset=emit('craymel_battle_reset',f'''

        {clearing}
        {notices_reset}

        movups {mem(0x12cea40)}, xmm0

        jmp 0x11c6f6

    ''')

    jump(0x11c6ef,7,reset,'Clear transient Craymel faculties and unclaimed cast EXP at every battle start')

    return dict(cast=cast,pending_rva=pending,rewards=table,flag_rva=data+0x1a61,

                curve='native cumulative thresholds; level 30 cap',settlement='victory only',

                reset=reset,ko_owner=knockout,state_rva=state)





def emit_exp_progress(emit,mem,name='craymel_exp_progress'):

    # ECX native Craymel id -> EAX 0..10000, EDX current EXP in level,

    # R8 next-level requirement (0 at MAX), R9 current level.

    return emit(name,f'''

        push rbx; push rsi; push rdi; sub rsp, 0x30

        xor esi, esi; xor edi, edi; xor r8d, r8d; xor r9d, r9d

        cmp ecx, 9; ja empty

        lea rbx, {mem(0x11cafd8)}; lea rbx, [rbx+rcx*8]

        cmp byte ptr [rbx], 0; je empty

        movzx esi, byte ptr [rbx+1]; cmp esi, 1; jb empty

        cmp esi, 30; ja empty; je maximum

        lea ecx, [rsi*2+3]; call 0x928f0

        xor edx, edx; cmp esi, 1; cmove eax, edx

        mov edi, eax

        lea ecx, [rsi*2+5]; call 0x928f0

        sub eax, edi; mov r8d, eax; test eax, eax; je empty

        mov eax, dword ptr [rbx+4]; sub eax, edi

        xor edx, edx; cmp eax, edx; cmovl eax, edx

        cmp eax, r8d; cmova eax, r8d; mov edi, eax

        imul rax, rax, 10000; xor edx, edx; div r8

        mov edx, edi; mov r9d, esi; jmp done

    maximum: mov eax, 10000; xor edx, edx; xor r8d, r8d; mov r9d, 30; jmp done

    empty: xor eax, eax; xor edx, edx; xor r8d, r8d; xor r9d, r9d

    done: add rsp, 0x30; pop rdi; pop rsi; pop rbx; ret

    ''')





def emit_cage_gauge(emit,mem,jump,data,progress):

    # Native selected-spirit panel: total EXP at (237,85), level at (255,77).

    # Add a 92px gauge to its right, in the same drawing layer and fade alpha.

    gauge=emit('craymel_cage_exp_gauge',f'''

        push rbx; push rsi; sub rsp, 0x48

        mov esi, edx

        call {progress:#x}

        test r9d, r9d; je done

        imul eax, eax, 49; xor edx, edx; mov ecx, 10000; div ecx

        mov ebx, eax

        mov ecx, 170; mov edx, 64; mov r8d, 0x601; mov r9d, 128

        mov dword ptr [rsp+0x20], 128; mov dword ptr [rsp+0x28], 128

        mov dword ptr [rsp+0x30], 49; mov dword ptr [rsp+0x38], esi

        call 0x251390

        test ebx, ebx; je done

        mov ecx, 170; mov edx, 64; mov r8d, 0x601; mov r9d, 192

        mov dword ptr [rsp+0x20], 192; mov dword ptr [rsp+0x28], 48

        mov dword ptr [rsp+0x30], ebx; mov dword ptr [rsp+0x38], esi

        call 0x251390

    done: add rsp, 0x48; pop rsi; pop rbx; ret

    ''')

    from craymel_faculties import preserve

    draw=emit('craymel_cage_exp_draw',preserve(f'''

        cmp byte ptr {mem(data+0x1a61)}, 0; je done

        sub rsp, 0x60

        movdqu [rsp], xmm0; movdqu [rsp+0x10], xmm1; movdqu [rsp+0x20], xmm2

        movdqu [rsp+0x30], xmm3; movdqu [rsp+0x40], xmm4; movdqu [rsp+0x50], xmm5

        sub rsp, 0x20

        mov ecx, r14d; mov edx, r15d; call {gauge:#x}

        add rsp, 0x20

        movdqu xmm0, [rsp]; movdqu xmm1, [rsp+0x10]; movdqu xmm2, [rsp+0x20]

        movdqu xmm3, [rsp+0x30]; movdqu xmm4, [rsp+0x40]; movdqu xmm5, [rsp+0x50]

        add rsp, 0x60

    done:

    ''')+'''\nmov ecx, dword ptr [rsp+0xb0]; jmp 0x243e91''')

    jump(0x243e8a,7,draw,'Craymel cage: native-style current-level EXP gauge on the selected spirit')

    number=emit('craymel_cage_level_position',f'''

        cmp byte ptr {mem(data+0x1a61)}, 0; je native

        mov eax, 0x436a0000

        movd xmm2, eax

    native:

        call 0xceb0

        jmp 0x243d67

    ''')

    jump(0x243d62,5,number,'Craymel cage: level immediately before its EXP gauge')

    return dict(draw=draw,gauge=gauge,progress=progress,rect=[250,79,49,4],native_layer=0x601,level_x=234)
