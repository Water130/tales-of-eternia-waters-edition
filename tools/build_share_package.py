"""Stage English distribution files or zip a verified package. Never installs."""
from pathlib import Path
import argparse, base64, hashlib, json, shutil, struct, zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/shareable'
SOURCE=ROOT/'build/combat-test'
TEMPLATES=ROOT/'tools/release'
VERSION='0.12.13'
NAME=f'Tales-of-Eternia-Waters-Edition-{VERSION}-Easy-Install'
FILES=['Install.cmd','Uninstall.cmd','README.txt','Support/Patch-Mod.ps1',
       'Support/patch.json','Support/Mod-details.txt','Support/SHARE.txt',
       'Support/Compatibility-Mode.cmd','Support/Status.cmd','Support/SHA256SUMS.txt']
sha=lambda data:hashlib.sha256(data).hexdigest()
read_json=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))

def fingerprints():
    return {name:sha((STAGE/name).read_bytes()) for name in FILES}

def delta(original,result):
    runs=[];i=0
    while i<len(result):
        if i<len(original) and original[i]==result[i]:
            i+=1;continue
        start=i
        while i<len(result) and (i>=len(original) or original[i]!=result[i]):i+=1
        runs.append([start,base64.b64encode(result[start:i]).decode('ascii')])
    rebuilt=bytearray(original)+bytearray(len(result)-len(original))
    for offset,encoded in runs:
        value=base64.b64decode(encoded);rebuilt[offset:offset+len(value)]=value
    assert bytes(rebuilt)==result
    return dict(sha256=sha(result),result_size=len(result),runs=runs)

def stage():
    manifest=read_json(SOURCE/'manifest.json');tests=read_json(SOURCE/'verification.json')
    assert manifest['version']==f'combat-test-{VERSION}'
    original=(ROOT/'backups/build-25190541/GameNative.dll').read_bytes()
    patched=(SOURCE/'GameNative.dll').read_bytes()
    assert sha(original)==manifest['original_sha256']
    assert sha(patched)==manifest['patched_sha256']==tests['patched_sha256'] and tests['passed']
    assert shutil.disk_usage(ROOT).free>5*1024**3+len(patched)*4
    fallback=bytearray(patched);profile=manifest['without_spell_overlap']
    for edit in manifest['edits']:
        if edit['name'] in profile['reverted_edits']:
            data=bytes.fromhex(edit['original']);offset=edit['offset']
            fallback[offset:offset+len(data)]=data
    struct.pack_into('<I',fallback,profile['checksum_offset'],profile['checksum'])
    assert sha(fallback)==profile['sha256']
    STAGE.mkdir(parents=True,exist_ok=True)
    (STAGE/'Support').mkdir(exist_ok=True)
    for source,dest in [('Patch-Mod.ps1','Support/Patch-Mod.ps1'),
                        ('README.txt','Support/Mod-details.txt'),
                        ('SHARE.txt','Support/SHARE.txt'),
                        ('QUICK_START.txt','README.txt')]:
        data=(TEMPLATES/source).read_text(encoding='utf-8-sig')
        data.encode('ascii')  # All public scripts and prose are English / PS 5.1-safe.
        (STAGE/dest).write_bytes(data.replace('\r\n','\n').replace('\n','\r\n').encode('ascii'))
    payload=dict(format=1,name="Tales of Eternia - Water's Edition",version=f'{VERSION}-test',
                 steam_build=manifest['steam_build'],base_sha256=sha(original),base_size=len(original),
                 profiles=dict(Full=delta(original,patched),Compatibility=delta(original,bytes(fallback))))
    (STAGE/'Support/patch.json').write_text(json.dumps(payload,separators=(',',':')),encoding='ascii')
    for name,action in [('Install.cmd','Install -Prompt'),
                        ('Support/Compatibility-Mode.cmd','Install -Mode Compatibility -Prompt'),
                        ('Uninstall.cmd','Uninstall -Prompt'),('Support/Status.cmd','Status')]:
        script_path='Patch-Mod.ps1' if name.startswith('Support/') else 'Support\\Patch-Mod.ps1'
        script=("@echo off\r\nsetlocal\r\ntitle Water's Edition - "+action.split()[0]+
                '\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0'+script_path+'" -Action '+action+
                '\r\nset "patchExit=%errorlevel%"\r\necho.\r\necho Press any key to close this window.\r\npause >nul\r\nexit /b %patchExit%\r\n')
        (STAGE/name).write_bytes(script.encode('ascii'))
    hashes={name:sha((STAGE/name).read_bytes()) for name in FILES if name!='Support/SHA256SUMS.txt'}
    (STAGE/'Support/SHA256SUMS.txt').write_text(''.join(f'{value}  {name}\n' for name,value in hashes.items()),encoding='ascii')
    print(json.dumps(dict(stage=str(STAGE),files=len(FILES),bytes=sum((STAGE/n).stat().st_size for n in FILES),
                         full_sha256=sha(patched),compatibility_sha256=sha(fallback)),indent=2))

def package():
    verified=read_json(ROOT/'build/shareable-verification.json')
    assert verified['passed'] and verified['files']==fingerprints(), 'Run package tests on these exact files before zipping.'
    target=ROOT/'release';target.mkdir(exist_ok=True)
    assert shutil.disk_usage(target).free>5*1024**3+sum((STAGE/n).stat().st_size for n in FILES)
    archive=target/(NAME+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:z.write(STAGE/name,NAME+'/'+name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert sorted(z.namelist())==sorted(NAME+'/'+n for n in FILES)
        for name in FILES:assert z.read(NAME+'/'+name)==(STAGE/name).read_bytes()
        for info in z.infolist():
            content=z.read(info).lower()
            assert b'ghp_' not in content and b'github_pat_' not in content
            assert b'c:\\users\\' not in content and b'c:/users/' not in content
    digest=sha(archive.read_bytes())
    (target/(NAME+'.sha256')).write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    report=dict(path=str(archive),sha256=digest,bytes=archive.stat().st_size,
                package_files=FILES,passed=True,includes_complete_game_files=False,
                fixture_tests=verified['checks'],game_installation_modified=False)
    (ROOT/'build/shareable-release.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--zip',action='store_true')
    package() if parser.parse_args().zip else stage()
