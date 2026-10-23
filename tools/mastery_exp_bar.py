"""Vanilla Punch/Kick EXP gauge; coordinates match the 480x270 UI."""


def emit_exp_bar(emit, mem, name='mastery_exp_gradient'):
    # R10D: 0 gray backing, 1 native yellow, 2 muted gold at the cap.
    # Native 251390 draws four shaded rows at x+80/y+15. Match the RGB
    # arguments used by vanilla Punch/Kick at 24072e and 240796.
    return emit(name, '''
        sub rsp, 0x48
        mov dword ptr [rsp+0x30], r8d
        sub ecx, 80
        sub edx, 15
        xor r8d, r8d
        mov r9d, 128
        mov dword ptr [rsp+0x20], 128
        mov dword ptr [rsp+0x28], 128
        test r10d, r10d
        je color_ready
        mov r9d, 192
        mov dword ptr [rsp+0x20], 192
        mov dword ptr [rsp+0x28], 48
        cmp r10d, 2
        jne color_ready
        mov r9d, 160
        mov dword ptr [rsp+0x20], 160
        mov dword ptr [rsp+0x28], 104
    color_ready:
        mov dword ptr [rsp+0x38], 255
        call 0x251390
        add rsp, 0x48
        ret
    ''')
