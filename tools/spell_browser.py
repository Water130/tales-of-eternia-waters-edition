"""Native Fringe catalogue and read-only availability for both mages."""
import json
import struct
from pathlib import Path

PAGE_ORDER = (0, 1, 2, 6, 8, 3, 4, 5, 7, 9)
STARTERS = (70, 72, 75, 79, 82, 86)


def arrange(rows):
    source=Path(__file__).resolve().parents[1]/'audit/build-25190541/mastery/spell_recipes.json'
    recipes={r['arte']:r for r in json.loads(source.read_text())['recipes'] if r['arte']<102}
    for aid,spirit,owner in ((70,0,2),(72,1,2),(75,2,2),(79,3,3),(82,4,3),(86,5,3)):
        recipes[aid]=dict(arte=aid,primary=spirit,secondary=spirit,level=0,secondary_level=0,innate=owner)
    spells=[]
    for r in rows:
        if r['kind']==2 and r['key'] in recipes:
            r['recipe']=recipes[r['key']]
            spells.append(r)
    spells.sort(key=lambda r:(PAGE_ORDER.index(r['recipe']['primary']),r['recipe']['level'],r['key']))
    return [r for r in rows if r['kind']!=2]+spells


def emit_availability(emit,mem,ui,learned):
    return emit('mastery_spell_availability',f'''
        push rbx
        sub rsp, 0x20
        mov ebx, ecx
        mov edx, ecx
        movzx ecx, byte ptr {mem(ui+4)}
        call {learned:#x}
        test eax, eax
        jne accessible
        # Starter names are visible to both mages before their spirit joins.
        {'; '.join(f'cmp ebx, {aid}; je known' for aid in STARTERS)}
        lea rdx, {mem(0x11cb0b8)}
        bt dword ptr [rdx], ebx
        setc al
        movzx eax, al
        jmp done
    known:
        mov eax, 1
        jmp done
    accessible:
        mov eax, 2
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')

def emit_browser(emit,mem,ui,rows,payload,state,string,lineblock,lookup,availability,text,frame,icon,tabletext,loc,bonus):
    spells=[r for r in rows if r['kind']==2]
    spirits=sorted((r for r in rows if r['kind']==0),key=lambda r:r['key'])
    descriptors=[]
    for r in spells:
        rec=r['recipe'];a,b=rec['primary'],rec['secondary'];l1,l2=rec['level'],rec['secondary_level']
        blocks=[]
        for visibility in range(4):
            for lang in range(2):
                name=lambda key,bit:spirits[key]['name'][lang] if visibility&bit else '???'
                if 'innate' in rec:
                    owner=('Keele','Meredy')[rec['innate']-2]
                    lines=[f'Sort initial de {owner}.' if lang==0 else f'{owner} starting spell.']
                else:
                    lines=[f"{name(a,1)} — {'niveau' if lang==0 else 'level'} {l1}"]
                    if a!=b:lines.append(f"{name(b,2)} — {'niveau' if lang==0 else 'level'} {l2}")
                    lines.append('Principal : chez ce mage.' if lang==0 else 'Primary: assigned to this mage.')
                    lines.append(('Partenaire : chez l’autre mage.' if lang==0 else 'Partner: assigned to the other mage.') if a!=b else ('Apprentissage par Fringe.' if lang==0 else 'Learn through Fringe.'))
                blocks.append(lineblock(lines))
        descriptors.append((a,b,l1,l2,*blocks))
    payload.extend(b'\0'*((-len(payload))%4))
    recipes=state+len(payload)
    for d in descriptors:payload.extend(struct.pack('<12I',*d))
    groups=[]
    for i in PAGE_ORDER:
        ids=[j for j,r in enumerate(spells) if r['recipe']['primary']==i]
        groups.append((min(ids),len(ids)))
    names=[(string(spirits[i]['name'][0]),string(spirits[i]['name'][1])) for i in PAGE_ORDER]
    payload.extend(b'\0'*((-len(payload))%4))
    group_table=state+len(payload)
    for g,n in zip(groups,names):payload.extend(struct.pack('<4I',*g,*n))
    spirit_order=state+len(payload)
    payload.extend(bytes(PAGE_ORDER))
    # Pure lookup: selected spell ordinal -> group number and descriptor.
    group=emit('mastery_spell_group',f'''
        movzx eax, byte ptr {mem(ui+1)}
        xor ecx, ecx
        lea rdx, {mem(group_table)}
    next:
        mov r8d, dword ptr [rdx]
        add r8d, dword ptr [rdx+4]
        cmp eax, r8d
        jb done
        add rdx, 16
        inc ecx
        cmp ecx, 9
        jb next
    done:
        ret
    ''')
    nav=emit('mastery_spell_browser_input',f'''
        push rbx
        sub rsp, 0x20
        mov ebx, edx
        call {group:#x}
        mov r9d, eax
        sub r9d, dword ptr [rdx]
        test ebx, 0x80
        je right
        test ecx, ecx
        je done
        sub rdx, 16
        jmp across
    right:
        test ebx, 0x20
        je up
        cmp ecx, 9
        jae done
        add rdx, 16
    across:
        mov ecx, dword ptr [rdx+4]
        dec ecx
        cmp r9d, ecx
        cmova r9d, ecx
        mov eax, dword ptr [rdx]
        add eax, r9d
        jmp selected
    up:
        test ebx, 0x10
        je down
        test r9d, r9d
        je done
        dec eax
        jmp selected
    down:
        test ebx, 0x40
        je done
        inc r9d
        cmp r9d, dword ptr [rdx+4]
        jae done
        inc eax
    selected:
        mov byte ptr {mem(ui+1)}, al
        mov byte ptr {mem(ui+2)}, 0
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')
    # Draw ten horizontally browsable columns, five at once. Each has its own
    # vertical viewport; all entries, including unavailable ones, are selectable.
    draw=emit('mastery_spell_browser_draw',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        push r15
        sub rsp, 0x38
        call {group:#x}
        mov dword ptr [rsp+0x28], ecx
        mov eax, 0
        mov edx, 5
        cmp ecx, 5
        cmovae eax, edx
        mov ecx, eax
        mov edi, ecx
        lea rcx, {mem(string('Page 1 / 2'))}
        test edi, edi
        je page_label
        lea rcx, {mem(string('Page 2 / 2'))}
    page_label:
        mov edx, 207
        mov r8d, 47
        mov r9d, 66
        mov eax, 0xffbbbbbb
        call {text:#x}
        mov ebp, 34
        mov r14d, 5
    column:
        lea rbx, {mem(group_table)}
        mov eax, edi
        shl eax, 4
        add rbx, rax
        mov ecx, ebp
        mov edx, 57
        mov r8d, 79
        mov r9d, 109
        call {frame:#x}
        lea rax, {mem(spirit_order)}
        movzx ecx, byte ptr [rax+rdi]
        mov dword ptr [rsp+0x30], ecx
        lea edx, [rbp+4]
        mov r8d, 61
        mov r9d, 0xff000000
        lea rax, {mem(0x11cafd8)}
        cmp byte ptr [rax+rcx*8], 0
        je silhouette
        mov r9d, 0xffffffff
    silhouette:
        call {icon:#x}
        {loc('unknown')}
        lea rax, {mem(0x11cafd8)}
        mov edx, dword ptr [rsp+0x30]
        cmp byte ptr [rax+rdx*8], 0
        je name
        {tabletext('rbx',8)}
    name:
        lea edx, [rbp+23]
        mov r8d, 65
        mov r9d, 53
        mov eax, 0xffffad61
        call {text:#x}
        xor r12d, r12d
        cmp edi, dword ptr [rsp+0x28]
        jne rows
        movzx r12d, byte ptr {mem(ui+1)}
        sub r12d, dword ptr [rbx]
        sub r12d, 2
        xor eax, eax
        cmp r12d, eax
        cmovl r12d, eax
        mov eax, dword ptr [rbx+4]
        sub eax, 5
        xor ecx, ecx
        cmp eax, ecx
        cmovl eax, ecx
        cmp r12d, eax
        cmova r12d, eax
    rows:
        mov esi, 84
        mov r13d, 5
    row:
        cmp r12d, dword ptr [rbx+4]
        jae next_column
        test r13d, r13d
        je next_column
        mov eax, dword ptr [rbx]
        add eax, r12d
        mov dword ptr [rsp+0x20], eax
        cmp al, byte ptr {mem(ui+1)}
        jne lookup
        lea ecx, [rbp+2]
        lea edx, [rsi-2]
        mov r8d, 75
        mov r9d, 16
        call {frame:#x}
    lookup:
        mov eax, dword ptr [rsp+0x20]
        xor edx, edx
        call {lookup:#x}
        mov r15, rcx
        mov ecx, dword ptr [rcx+4]
        call {availability:#x}
        mov dword ptr [rsp+0x24], eax
        {loc('unknown')}
        cmp dword ptr [rsp+0x24], 0
        je spell_name
        {tabletext('r15',12)}
    spell_name:
        lea edx, [rbp+7]
        mov r8d, esi
        mov r9d, 65
        mov eax, 0xff999999
        cmp dword ptr [rsp+0x24], 2
        jne color
        mov eax, 0xffffffff
    color:
        call {text:#x}
        add esi, 17
        inc r12d
        dec r13d
        jmp row
    next_column:
        inc edi
        add ebp, 82
        dec r14d
        jne column
        mov ecx, 34
        mov edx, 171
        mov r8d, 407
        mov r9d, 69
        call {frame:#x}
        movzx eax, byte ptr {mem(ui+1)}
        xor edx, edx
        call {lookup:#x}
        call {bonus:#x}
        # Requirements remain readable in the right bonus pane, even for ???.
        movzx eax, byte ptr {mem(ui+1)}
        imul eax, eax, 48
        lea rbx, {mem(recipes)}
        add rbx, rax
        lea rdx, {mem(0x11cafd8)}
        mov ecx, dword ptr [rbx]
        xor esi, esi
        cmp byte ptr [rdx+rcx*8], 0
        setne sil
        mov ecx, dword ptr [rbx+4]
        xor eax, eax
        cmp byte ptr [rdx+rcx*8], 0
        setne al
        lea esi, [rsi+rax*2]
        lea rbx, [rbx+rsi*8+16]
        {tabletext('rbx',0)}
        mov rbx, rcx
        mov edi, dword ptr [rbx]
        add rbx, 4
        mov esi, 190
    requirement:
        test edi, edi
        je done
        mov ecx, dword ptr [rbx]
        lea rax, {mem(0)}
        add rcx, rax
        mov edx, 246
        mov r8d, esi
        mov r9d, 188
        mov eax, 0xffffffff
        call {text:#x}
        add rbx, 4
        add esi, 9
        dec edi
        jmp requirement
    done:
        add rsp, 0x38
        pop r15
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    return dict(input=nav,draw=draw,availability=availability,groups=groups,recipes=recipes,group_table=group_table,page_order=PAGE_ORDER,starter_spells=STARTERS)
