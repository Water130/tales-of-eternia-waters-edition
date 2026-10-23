"""Require every isolated test group to pass against the same built DLL."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/combat-test'
GROUPS=('core','mastery','mastery-menu','energy','fringe','craymel-exp','teamup','faculties')


def main():
    digest=hashlib.sha256((STAGE/'GameNative.dll').read_bytes()).hexdigest()
    manifest=json.loads((STAGE/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['patched_sha256']==digest, 'DLL does not match the build manifest'
    checks=[]
    sources=[]
    for group in GROUPS:
        path=STAGE/f'{group}-verification.json'
        raw=path.read_bytes()
        report=json.loads(raw)
        assert report['passed'] is True, f'{group}: tests did not pass'
        assert report['patched_sha256']==digest, f'{group}: stale binary verification'
        assert report['checks'], f'{group}: no executed checks'
        for base in ('180000000:', '7ffb00000000:'):
            assert any(c.startswith(base) for c in report['checks']), f'{group}: missing ASLR base {base}'
        checks.extend(report['checks'])
        sources.append(dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest()))
    result=dict(passed=True,version=manifest['version'],patched_sha256=digest,
                checks=checks,source_reports=sources,runtime_validated=False,
                note='Complete verification split into fresh emulator processes. '
                     'Actual x64 hooks executed at two ASLR bases; GPU rendering '
                     'and gameplay still require user testing. No game automation.')
    (STAGE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,patched_sha256=digest,groups=list(GROUPS),
                         checks=len(checks),runtime_validated=False)))


if __name__=='__main__':
    main()
