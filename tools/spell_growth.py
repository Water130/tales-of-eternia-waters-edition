"""Shared integer milestones for spell EXP. No floating point drift at caps."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    cap: int
    casts: int

    def value(self, uses):
        return min(self.cap, max(0, uses) * self.cap // self.casts)

    def threshold(self, rank):
        return (rank * self.casts + self.cap - 1) // self.cap

    def progress(self, uses):
        rank = self.value(uses)
        if rank == self.cap:
            return rank, 0, 100, 0
        start, end = self.threshold(rank), self.threshold(rank + 1)
        return rank, end, (uses-start)*100//(end-start), end-uses


POWER = Track(25, 500)
CAST = RECOVERY = CRITICAL = Track(15, 500)
AREA = Track(50, 999)
PROJECTILE_SMALL = Track(3, 999)
PROJECTILE_LARGE = Track(6, 999)
OFFENSIVE = tuple(range(70, 102)) + (112, 113)
# Maximum *additional* projectiles. Wide sprays receive six, single bolts three.
PROJECTILE_CAPS = {70:3,72:3,73:6,75:3,82:3,83:6,89:6,90:3,91:6,93:6,94:6}


def emit_track_progress(emit):
    # ECX uses, EDX cap, R8D maximum uses. Outputs match the existing spell
    # progress contract: rank, next absolute use threshold, %, remaining.
    return emit('mastery_track_progress', '''
        push rbx
        push rsi
        push rdi
        mov r10d, ecx
        mov r11d, edx
        mov r9d, r8d
        cmp ecx, r8d
        jae maximum
        mov eax, ecx
        imul eax, edx
        xor edx, edx
        div r9d
        mov ebx, eax
        imul eax, r9d
        lea eax, [rax+r11-1]
        xor edx, edx
        div r11d
        mov esi, eax
        lea eax, [rbx+1]
        imul eax, r9d
        lea eax, [rax+r11-1]
        xor edx, edx
        div r11d
        mov edi, eax
        sub eax, esi
        mov ecx, eax
        mov eax, r10d
        sub eax, esi
        imul eax, eax, 100
        xor edx, edx
        div ecx
        mov r8d, eax
        mov eax, ebx
        mov edx, edi
        mov r9d, edi
        sub r9d, r10d
        jmp done
    maximum:
        mov eax, r11d
        xor edx, edx
        mov r8d, 100
        xor r9d, r9d
    done:
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')


def emit_actor_uses(emit, mem, data, usage):
    """RCX actor, EDX arte -> EAX completed uses, or zero if disabled/excluded.

    Does not count the in-progress cast. All callers can share the same option,
    per-mage preference, character and side checks.
    """
    return emit('mastery_actor_uses', f'''
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je none
        test rcx, rcx
        je none
        cmp byte ptr [rcx+0x51], 0
        jne none
        movzx eax, byte ptr [rcx+0x4f]
        sub eax, 2
        cmp eax, 1
        ja none
        cmp edx, 70
        jb none
        cmp edx, 101
        jbe offensive
        cmp edx, 112
        je offensive
        cmp edx, 113
        jne none
    offensive:
        add eax, 2
        mov r8d, eax
        shl eax, 8
        add eax, edx
        lea r9, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r9], eax
        jc none
        shl r8d, 7
        add r8d, edx
        lea r9, {mem(usage['live_rva'])}
        movzx eax, word ptr [r9+r8*2]
        lea r9, {mem(usage['catchup']['live_rva'])}
        movzx edx, word ptr [r9+r8*2]
        add eax, edx
        mov edx, 999
        cmp eax, edx
        cmova eax, edx
        ret
    none:
        xor eax, eax
        ret
    ''')


def emit_cast_growth(emit, mem, jump, actor_uses, faculties=None):
    # 112fe9: native spell-specific delay has been computed in DX; EBP is the
    # selected arte, RBX the caster. The native even-frame mask follows us.
    target = emit('mastery_cast_time', f'''
        pushfq
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x28
        movzx r10d, dx
        mov dword ptr [rsp+0x20], r10d
        mov rcx, rbx
        mov edx, ebp
        call {actor_uses:#x}
        mov ecx, 500
        cmp eax, ecx
        cmova eax, ecx
        imul eax, eax, 15
        xor edx, edx
        div ecx
        mov ecx, 100
        sub ecx, eax
        mov eax, dword ptr [rsp+0x20]
        imul eax, ecx
        add eax, 99
        xor edx, edx
        mov ecx, 100
        div ecx
        {f'mov r8d, eax; mov edx, ebp; mov rcx, rbx; call {faculties["cast"]:#x}' if faculties else ''}
        mov word ptr [rsp+0x48], ax
        add rsp, 0x28
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        popfq
        mov eax, 0xffe
        jmp 0x112fee
    ''')
    jump(0x112fe9, 5, target, 'Spell EXP: up to 15% shorter native incantation')
    return target
