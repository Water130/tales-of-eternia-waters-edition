"""Exercise the public PS 5.1 installer only against disposable game fixtures."""
from pathlib import Path
import json, shutil, subprocess, tempfile
from build_share_package import ROOT, STAGE, FILES, fingerprints, read_json, sha

assert shutil.disk_usage(ROOT).free>5*1024**3+64*1024**2
original=(ROOT/'backups/build-25190541/GameNative.dll').read_bytes()
patched=(ROOT/'build/combat-test/GameNative.dll').read_bytes()
payload=read_json(STAGE/'Support/patch.json')
before=fingerprints();checks=[]
powershell=Path(r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe')
assert powershell.is_file()
quote=lambda s:"'"+str(s).replace("'","''")+"'"

workspace=Path(tempfile.mkdtemp(prefix='share-package-',dir=ROOT/'build')).resolve()
assert workspace.is_relative_to((ROOT/'build').resolve())
try:
    package=workspace/'Package with spaces';package.mkdir()
    for name in FILES:
        (package/name).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(STAGE/name,package/name)
    game=workspace/'Steam Library'/'Test game é'
    target=game/'Tales of Eternia Remastered_Data/Plugins/x86_64/GameNative.dll'
    target.parent.mkdir(parents=True)
    backup=target.with_name(target.name+'.toe-combat-original')
    stage=target.with_name(target.name+'.toe-combat-stage')
    target.write_bytes(original)

    def invoke(action,mode='Full',dry=False,running=False,path=None,prompt=False,answer='Y'):
        # Mock the process query in this child PowerShell process only. Tests
        # neither depend on nor touch the user's real running game.
        result="[pscustomobject]@{ProcessName='Tales of Eternia Remastered'}" if running else ''
        command="function Get-Process { [CmdletBinding()] param([string]$Name) "+result+" }; "
        if prompt:
            command+="function Read-Host { param([string]$Prompt) Write-Host ('PROMPT: ' + $Prompt); return "+quote(answer)+" }; "
        command+='& '+quote(package/'Support/Patch-Mod.ps1')
        command+=' -Action '+action+' -Mode '+mode+' -GameDir '+quote(path or game)
        if dry:command+=' -DryRun'
        if prompt:command+=' -Prompt'
        proc=subprocess.run([str(powershell),'-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-Command',command],
                            capture_output=True,text=True,errors='replace',timeout=60)
        return proc.returncode,proc.stdout+proc.stderr

    def ok(action,**kwargs):
        code,output=invoke(action,**kwargs)
        assert code==0,(action,kwargs,output)
        return output

    def refused(action,expected,**kwargs):
        state={p:sha(p.read_bytes()) for p in target.parent.iterdir() if p.is_file()}
        code,output=invoke(action,**kwargs)
        assert code!=0 and expected in output,(action,expected,code,output)
        assert state=={p:sha(p.read_bytes()) for p in target.parent.iterdir() if p.is_file()}, 'refusal changed game files'

    assert 'Original' in ok('Status')
    ok('Install',dry=True)
    assert target.read_bytes()==original and not backup.exists() and not stage.exists()
    checks.append('Status and dry-run: original file untouched, no backup/stage created; spaces and Unicode in paths')
    refused('Install','Close Tales',running=True)
    checks.append('Running-game guard rejects writes (simulated process query, fixture only)')
    for answer in ('N','','something else'):
        assert 'Cancelled. No files changed.' in ok('Install',prompt=True,answer=answer)
        assert target.read_bytes()==original and not backup.exists() and not stage.exists()
    checks.append('Install confirmation: No, empty and invalid answers cancel without creating or changing files')
    assert "Install Water's Edition in this folder? [Y/N]" in ok('Install',prompt=True,answer='y')
    assert target.read_bytes()==patched and backup.read_bytes()==original and not stage.exists()
    checks.append('Yes confirmation installs the exact tested DLL and stores an exact original backup')
    stamp=target.stat().st_mtime_ns
    assert 'already installed' in ok('Install') and target.stat().st_mtime_ns==stamp
    checks.append('Repeated installation is idempotent')
    ok('Install',mode='Compatibility')
    assert sha(target.read_bytes())==payload['profiles']['Compatibility']['sha256']
    assert backup.read_bytes()==original
    assert 'Compatibility' in ok('Status')
    ok('Install')
    assert target.read_bytes()==patched and backup.read_bytes()==original
    checks.append('Full -> Compatibility -> Full switching uses the original backup and produces verified hashes')
    refused('Uninstall','Close Tales',running=True)
    assert 'Cancelled. No files changed.' in ok('Uninstall',prompt=True,answer='n')
    assert target.read_bytes()==patched and backup.read_bytes()==original and not stage.exists()
    checks.append('Uninstall cancellation leaves the installed mod and original backup intact')
    assert "Uninstall Water's Edition from this folder? [Y/N]" in ok('Uninstall',prompt=True,answer='YES')
    assert target.read_bytes()==original and backup.read_bytes()==original
    assert 'already restored' in ok('Uninstall')
    checks.append('Uninstall restores the original byte-for-byte, preserves its backup and is idempotent')
    unknown=bytearray(original);unknown[128]^=1;target.write_bytes(unknown)
    refused('Install','Unsupported or modified DLL')
    refused('Uninstall','Unsupported or modified DLL')
    checks.append('Unknown DLL / Steam-update / other-mod hashes cannot be overwritten by install or uninstall')
    target.write_bytes(original);backup.write_bytes(unknown)
    refused('Install','original backup has an unexpected hash')
    checks.append('Corrupted or unrelated backup is preserved and blocks installation')
    backup.unlink();target.write_bytes(patched)
    refused('Uninstall','Original backup missing')
    refused('Install','Original backup missing')
    checks.append('Missing-original-backup guard protects already modified installations')
    target.write_bytes(original)
    stage.write_bytes(b'preexisting staging file')
    refused('Install','staging file from another operation')
    stage.unlink()
    checks.append('An existing staging file is never overwritten or deleted')
    altered=json.loads(json.dumps(payload));altered['profiles']['Full']['sha256']='0'*64
    (package/'Support/patch.json').write_text(json.dumps(altered),encoding='ascii')
    refused('Install','Patch reconstruction failed')
    assert not backup.exists()
    altered=json.loads(json.dumps(payload));altered['profiles']['Full']['runs'][0][0]=-1
    (package/'Support/patch.json').write_text(json.dumps(altered),encoding='ascii')
    refused('Install','Invalid patch range')
    (package/'Support/patch.json').write_bytes((STAGE/'Support/patch.json').read_bytes())
    checks.append('Corrupt payload/hash/range fails before creating a backup or replacing the game DLL')
    refused('Install','was not found',path=workspace/'Not a game')
    checks.append('Wrong game folder rejected')
    for name in FILES:
        data=(STAGE/name).read_bytes()
        data.decode('ascii')
        assert b'TestUser' not in data.lower() and b'c:\\users\\' not in data.lower()
        assert not name.lower().endswith(('.dll','.exe','.png','.tim','.sav'))
    for line in (STAGE/'Support/SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1);assert sha((STAGE/name).read_bytes())==digest
    assert before==fingerprints()
    checks.append('All public files ASCII/English; checksums valid; no full game binary, original game art, save or personal paths')
    assert sorted(n for n in FILES if '/' not in n)==['Install.cmd','README.txt','Uninstall.cmd']
    for name in ('Install.cmd','Uninstall.cmd'):
        launcher=(STAGE/name).read_text(encoding='ascii')
        assert '"%~dp0Support\\Patch-Mod.ps1"' in launcher
        assert '-Action '+Path(name).stem+' -Prompt' in launcher
        assert 'Press any key to close this window.' in launcher
    for name in ('Support/Status.cmd','Support/Compatibility-Mode.cmd'):
        assert '"%~dp0Patch-Mod.ps1"' in (STAGE/name).read_text(encoding='ascii')
    checks.append('Easy package exposes only Install/Uninstall and a short README; all launchers resolve the bundled script and use English prompts')
    report=dict(passed=True,files=before,checks=checks,host='Windows PowerShell 5.1',
                test_scope='Disposable fixtures; process presence simulated. Real game installation never modified.')
    (ROOT/'build/shareable-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=True,checks=checks),indent=2))
finally:
    # Only this newly created fixture tree; never game, saves, sources or history.
    assert workspace.is_relative_to((ROOT/'build').resolve()) and workspace.name.startswith('share-package-')
    assert not (workspace/'KEEP_STORAGE').exists()
    shutil.rmtree(workspace)
