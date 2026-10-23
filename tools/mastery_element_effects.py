"""Small animated native-vector motifs, confined to the spirit root card."""
import math
import struct
from mastery_tree_layout import ribbon


def emit_element_effects(emit,mem,ui,payload,state,draw,colors):
    entries=[]
    for spirit in range(10):
        for phase in range(8):
            t=phase/8*math.tau
            paths=[]
            if spirit==0:  # water: two waves and rising bubbles
                paths += [[(102+i*2,150+k*3+math.sin(i*.7+t)*1.1) for i in range(25)] for k in range(2)]
                for i in range(3):
                    x=105+i*20;y=134-((phase*2+i*7)%22)
                    paths.append([(x+1.7*math.cos(a*math.tau/12),y+1.7*math.sin(a*math.tau/12)) for a in range(13)])
            elif spirit==1:  # wind: two tapering spirals
                for x in (106,147):
                    paths.append([(x+(4-i*.12)*math.sin(i*.8+t),112+i*.7) for i in range(24)])
                paths.append([(103+i*2,151+math.sin(i*.3+t)*1.5) for i in range(24)])
            elif spirit==2:  # fire: three flickering tongues
                for x in (105,126,148):
                    paths.append([(x,153),(x-3,150),(x-2,145),(x+math.sin(t)*2,140),(x+1,147),(x+4,150),(x,153)])
            elif spirit in (3,4):  # earth crystals / ice shards
                for i,x in enumerate((105,125,147)):
                    h=6+math.sin(t+i)*2
                    paths.append([(x-3,153),(x-2,147),(x,153-h),(x+3,147),(x+3,153),(x-3,153)])
            elif spirit==5:  # electricity
                for x in (105,147):
                    d=math.sin(t)*2
                    paths.append([(x,112),(x-3+d,122),(x+2,122),(x-1,132),(x+4+d,141)])
            elif spirit in (6,7):  # rays / crescent shadow
                for x in (105,147):
                    if spirit==6:
                        paths += [[(x-3,123),(x+3,123)],[(x,120),(x,126)]]
                    else:
                        paths.append([(x+4*math.cos(a*.2+t),125+6*math.sin(a*.2+t)) for a in range(18)])
            else:  # elemental orbits / time dial
                paths.append([(127+23*math.cos(a*math.tau/32+t),126+17*math.sin(a*math.tau/32+t)) for a in range(33)])
                if spirit==9:paths.append([(127,110),(127,126),(137+math.sin(t)*2,130)])
            records=[]
            for points in paths:
                payload.extend(b'\0'*((-len(payload))%4))
                address=state+len(payload)
                for width in (.9,.65):
                    for xy in ribbon(points,width):payload.extend(struct.pack('<2f',*xy))
                records.append((address,len(points)*2))
            payload.extend(b'\0'*((-len(payload))%4))
            address=state+len(payload)
            payload.extend(struct.pack('<I',len(records)))
            for r in records:payload.extend(struct.pack('<2I',*r))
            entries.append(address)
    table=state+len(payload)
    payload.extend(struct.pack('<80I',*entries))
    return emit('mastery_element_motif',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        cmp ecx, 9; ja done
        mov edi, ecx
        mov eax, dword ptr {mem(ui+0x1c0)}; inc eax
        cmp eax, 96; jb clock_ready; xor eax, eax
    clock_ready:
        mov dword ptr {mem(ui+0x1c0)}, eax
        xor edx, edx; mov ecx, 12; div ecx
        lea eax, [rax+rdi*8]
        lea rdx, {mem(table)}; mov eax, dword ptr [rdx+rax*4]
        lea rsi, {mem(0)}; add rsi, rax
        mov ebx, dword ptr [rsi]; add rsi, 4
    path:
        mov ecx, dword ptr [rsi]; lea rax, {mem(0)}; add rcx, rax
        mov edx, dword ptr [rsi+4]
        lea rax, {mem(colors)}; mov r10d, dword ptr [rax+rdi*4]
        call {draw:#x}
        add rsi, 8; dec ebx; jne path
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
