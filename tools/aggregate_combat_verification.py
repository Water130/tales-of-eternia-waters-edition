"""Require every isolated test group to pass against the same built DLL."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
from build_profile import OUT as STAGE
GROUPS=('core','mastery','mastery-menu','energy','fringe','craymel-exp','teamup','faculties','mastery-badges','farah-artes','expansion','custom-artes','camera-floor','camera','casting')


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
    for group in ('tidal-presentation','tidal-recoil'):
        path=STAGE/f'{group}-verification.json'
        raw=path.read_bytes()
        report=json.loads(raw)
        assert report['passed'] is True and report['sha256']==digest, f'{group}: failed or stale binary'
        assert report['cases']>0 and report['results'], f'{group}: no native executions'
        assert {r['base'] for r in report['results']}=={'0x180000000','0x7ffb00000000'}, f'{group}: missing ASLR coverage'
        checks.append(f"{group}: {report['cases']} native execution cases; GPU appearance requires user testing")
        sources.append(dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest()))
    branch_path=STAGE/'native-branch-audit.json'
    branch_raw=branch_path.read_bytes()
    branches=json.loads(branch_raw)
    assert branches['passed'] and not branches['branch_hazards'], 'Native branch enters an overwritten detour span'
    assert branches['patched_sha256']==digest, 'Stale native branch audit; run verify_native_detour_branches.py'
    checks.append(f"Native direct-branch audit: {branches['checked_native_functions']} functions, {branches['checked_direct_branches']} branches; no detour-interior targets")
    sources.append(dict(file=branch_path.name,sha256=hashlib.sha256(branch_raw).hexdigest()))
    font_path=STAGE/'hp-tp-font/verification.json'
    font=json.loads(font_path.read_text(encoding='utf-8'))
    assert font['passed'] and font['damage_digits_unchanged'] and font['outside_pixels_unchanged']
    assert hashlib.sha256((font_path.parent/font['file']).read_bytes()).hexdigest()==font['patched_sha256']
    installer=json.loads((STAGE/'installer-verification.json').read_text(encoding='utf-8-sig'))
    assert installer['passed'] and installer['real_game_modified'] is False
    sources.append(dict(file='hp-tp-font/verification.json',sha256=hashlib.sha256(font_path.read_bytes()).hexdigest()))
    checks.append('FR HP/TP: owned EN glyph strip; all pixels outside strip and serialized metadata unchanged; native catalog CRC=0')
    checks.append('Installer: install, repeat, full restore, unknown-asset rejection and injected-failure rollback passed')
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
