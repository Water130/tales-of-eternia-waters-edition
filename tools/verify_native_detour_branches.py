"""Reject unchanged native branches into the interior of a detour overwrite."""
import bisect
import hashlib
import json
from pathlib import Path
from native_audit import base, code, functions, md, capstone

ROOT = Path(__file__).resolve().parents[1]
from build_profile import OUT as STAGE


def main():
    manifest = json.loads((STAGE/'manifest.json').read_text(encoding='utf-8'))
    edits = sorted(manifest['edits'],key=lambda e:e['rva'])
    starts = [e['rva'] for e in edits]
    def edited(address):
        index = bisect.bisect_right(starts,address)-1
        if index >= 0:
            edit = edits[index]
            if address < edit['rva']+len(bytes.fromhex(edit['patched'])):
                return edit
        return None
    hazards = []
    branches = 0
    for start,end in functions:
        for ins in md.disasm(code(start,end),base+start):
            if not (ins.mnemonic.startswith('j') or ins.mnemonic in ('call','loop','loope','loopne')):
                continue
            if not ins.operands or ins.operands[0].type != capstone.x86.X86_OP_IMM:
                continue
            branches += 1
            site = ins.address-base
            if edited(site):
                continue
            target = ins.operands[0].imm-base
            edit = edited(target)
            if edit and edit['rva'] < target and bytes.fromhex(edit['patched'])[:1] == b'\xe9':
                hazards.append(dict(site=hex(site),target=hex(target),edit=edit['name'],start=hex(edit['rva'])))
    result = dict(patched_sha256=hashlib.sha256((STAGE/'GameNative.dll').read_bytes()).hexdigest(),
                  checked_native_functions=len(functions),checked_direct_branches=branches,
                  branch_hazards=hazards,passed=not hazards,
                  limitation='Direct immediate branches from original unwind-described native functions; not computed jumps or external entry points.')
    (STAGE/'native-branch-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    assert not hazards, 'Native branch enters a patched detour span'


if __name__=='__main__':
    main()
