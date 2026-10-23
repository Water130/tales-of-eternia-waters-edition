"""Concrete option help and bounded, independent left-stick scrolling."""



DETAILS = {

12: (

    "SORTS\nKeele et Meredy progressent séparément. Chaque lancer réussi rapporte 1 EXP. Pour les sorts de Craymel, le mage en retard gagne jusqu'à 3 EXP par lancer, sans dépasser l'autre mage. Les six sorts initiaux sont exclus du rattrapage. Les utilisations réelles servant aux déblocages ne changent pas. À 500 EXP : puissance +25 %, incantation et récupération -15 %, critique +15 points. À 999 EXP : jusqu'à 3 ou 6 projectiles supplémentaires selon le sort, ou zone +50 %. Les soins ne reçoivent pas ces bonus.\n"

    "BUFFS\nÀ 100 / 250 / 500 EXP, les buffs monocibles touchent 1 / 2 / 3 alliés supplémentaires qui ne possèdent pas déjà le buff. Leur durée native est conservée.\n"

    "CRAYMEL\nChaque sort élémentaire réussi rapporte 50 / 200 / 500 EXP selon son rang au Craymel recruté de cet élément. Le total est versé à la victoire et remplace l'EXP automatique. Le niveau du Craymel augmente la puissance et la portée de son invocation. Les facultés de Craymel indiquées « En préparation » ne sont pas encore actives.\n"

    "EXTENSIONS\nMaelstrom demande Ondine niveau 10 et au moins 5/10 de vitalité. Les prérequis de résistance à l'eau sont retirés.",

    "SPELLS\nKeele and Meredy progress independently. Each successful cast earns 1 EXP. For Craymel spells, the trailing mage earns up to 3 EXP per cast without overtaking the other mage. The six starting spells are excluded. Real cast counts for unlock requirements are unchanged. At 500 EXP: power +25%, cast time and recovery -15%, critical chance +15 points. At 999 EXP: up to 3 or 6 extra projectiles depending on the spell, or area +50%. Healing spells do not gain these bonuses.\n"

    "BUFFS\nAt 100 / 250 / 500 EXP, single-target buffs also affect 1 / 2 / 3 allies without that buff. Native duration is retained.\n"

    "CRAYMELS\nEach completed elemental spell grants 50 / 200 / 500 EXP by spell rank to the recruited Craymel of that element. EXP is awarded at victory, replacing automatic EXP. Craymel levels increase summon power and reach. Craymel faculties marked In development are not active yet.\n"

    "EXTENSIONS\nMaelstrom requires level 10 Undine and at least 5/10 vitality. Water-resistance requirements are removed."),

17: (

    "POING ET PIED\nLa branche Poing + Pied accorde 1 attaque normale supplémentaire lorsque les deux maîtrises atteignent le niveau 15, puis 2 au niveau 30, dans les enchaînements au sol.\n"

    "ÉNERGIE\nUne troisième barre apparaît dans Stats. Son niveau correspond au plus bas des niveaux Poing et Pied.\n"

    "Niveau 10 : Guérisseur rend 40 % des PV max au lieu de 30 %.\n"

    "Niveau 15 : Désintoxication rend aussi 25 % des PV max.\n"

    "Niveau 20 : Guérisseur soigne un deuxième allié pour 50 % du soin principal, en priorité celui au plus faible pourcentage de PV.\n"

    "Niveau 25 : Désintoxication retire les mêmes altérations que Rétablissement, hors KO et états non purifiables.\n"

    "Niveau 30 : Guérisseur soigne un troisième allié pour 25 % du soin principal. Renaissance réanime avec 35 % des PV max au lieu de 20 %.\n"

    "Les facultés indiquées « En préparation » dans l'arbre ne modifient pas encore les enchaînements d'artes.",

    "PUNCH AND KICK\nThe Punch + Kick branch grants 1 extra normal attack when both masteries reach level 15 and 2 at level 30 in grounded chains.\n"

    "ENERGY\nA third gauge appears in Stats. Its level is the lower of Punch and Kick.\n"

    "Level 10: Healer restores 40% of max HP instead of 30%.\n"

    "Level 15: Detoxify also restores 25% of max HP.\n"

    "Level 20: Healer also heals a second ally for 50% of the primary heal, prioritizing the lowest HP ratio.\n"

    "Level 25: Detoxify removes the same ailments as Recover, excluding KO and uncleansable states.\n"

    "Level 30: Healer also heals a third ally for 25% of the primary heal. Life revives with 35% of max HP instead of 20%.\n"

    "Faculties marked In development in the tree do not yet change arte chains."),

31: (

    "TRANCHANT ET ESTOC\nLa branche Tranchant + Estoc prolonge les enchaînements d'attaques normales au sol :\n"

    "Niveau 15 : 1 attaque supplémentaire.\nNiveau 30 : 2 attaques supplémentaires au total.\n"

    "Les deux maîtrises doivent atteindre le niveau requis. Les facultés s'activent dès que le niveau requis est atteint et peuvent être désactivées dans Maîtrise.\n"

    "Les facultés d'enchaînement d'artes indiquées « En préparation » ne sont pas encore actives.",

    "SLASH AND THRUST\nThe Slash + Thrust branch extends grounded normal attack chains:\n"

    "Level 15: 1 extra attack.\nLevel 30: 2 extra attacks in total.\n"

    "Both masteries must reach the required level. Faculties activate upon reaching the required level and can be disabled in Mastery.\n"

    "Arte-chain faculties marked In development are not active yet."),

}





def emit_help(emit, mem, data, symbols, table, count, hint):

    # Separate from option flags, snapshots, skit input and API pointers.

    state = data + 0x1ae0

    visible = 13

    descriptor = emit('settings_description_info', f'''

        movzx eax, byte ptr {mem(data+0x1a12)}

        mov ah, byte ptr {mem(0x11c9ce8)}

        cmp ax, word ptr {mem(state)}

        je same

        mov word ptr {mem(state)}, ax

        mov word ptr {mem(state+2)}, 0

    same:

        movzx eax, al

        cmp eax, {count}

        jae empty

        shl eax, 4

        lea rcx, {mem(table)}

        add rcx, rax

        cmp byte ptr {mem(0x11c9ce8)}, 3

        je lang

        add rcx, 8

    lang:

        mov edx, dword ptr [rcx+4]

        sub edx, 2

        mov ecx, dword ptr [rcx]

        lea rax, {mem(0)}

        add rcx, rax

        ret

    empty:

        xor ecx, ecx

        xor edx, edx

        ret

    ''')

    input_rva = emit('settings_description_input', f'''

        sub rsp, 0x28

        call {descriptor:#x}

        xor eax, eax

        cmp edx, {visible}

        jbe done

        # Native 19dc42..19dc67 preserves separate stick bits alongside

        # the optional mirrored D-pad bits. Use the repeat bank directly.

        mov ecx, dword ptr {mem(0x8c9188)}

        and ecx, 0x03000000

        je held

        movzx eax, word ptr {mem(state+2)}

        cmp ecx, 0x01000000

        jne down

        test eax, eax

        je consume

        dec eax

        jmp save

    down:

        cmp ecx, 0x02000000

        jne consume

        sub edx, {visible}

        cmp eax, edx

        jae consume

        inc eax

    save:

        mov word ptr {mem(state+2)}, ax

    consume:

        mov eax, 1

        jmp done

    held:

        # Suppress mirrored navigation between repeat ticks, including

        # opposite directions pressed together; never change an option.

        test dword ptr {mem(0x8c9180)}, 0x03000000

        setne al

    done:

        add rsp, 0x28

        ret

    ''')

    draw = emit('settings_description_draw', f'''

        push rbx; push rsi; push rdi; push rbp

        sub rsp, 0x28

        call {descriptor:#x}

        test rcx, rcx

        je done

        mov rsi, rcx

        mov ebp, edx

        mov ecx, dword ptr [rsi]

        lea rax, {mem(0)}

        add rcx, rax

        mov edx, 258

        mov r8d, 63

        mov r9d, -7

        mov eax, 0xffffc080

        call {symbols['settings_text']:#x}

        movzx eax, word ptr {mem(state+2)}

        mov edx, ebp

        sub edx, {visible}

        xor ecx, ecx

        test edx, edx

        cmovl edx, ecx

        cmp eax, edx

        cmova eax, edx

        mov word ptr {mem(state+2)}, ax

        sub ebp, eax

        lea rsi, [rsi+rax*4+8]

        mov edi, {visible}

        cmp edi, ebp

        cmova edi, ebp

        mov ebx, 83

    line:

        test edi, edi

        je hint

        mov ecx, dword ptr [rsi]

        lea rax, {mem(0)}

        add rcx, rax

        mov edx, 258

        mov r8d, ebx

        mov r9d, -7

        mov eax, 0xfffffdfa

        call {symbols['settings_text']:#x}

        add rsi, 4

        add ebx, 10

        dec edi

        jmp line

    hint:

        call {descriptor:#x}

        cmp edx, {visible}

        jbe done

        lea rcx, {mem(hint[0])}

        cmp byte ptr {mem(0x11c9ce8)}, 3

        je hint_lang

        lea rcx, {mem(hint[1])}

    hint_lang:

        mov edx, 258

        mov r8d, 216

        mov r9d, -6

        mov eax, 0xffffc080

        call {symbols['settings_text']:#x}

    done:

        add rsp, 0x28

        pop rbp; pop rdi; pop rsi; pop rbx

        ret

    ''')

    return draw, input_rva, state, visible
