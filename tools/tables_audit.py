import json, os
import hashlib
import struct
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'audit/build-25190541'
BACKUP=Path(os.environ.get('TOE_NATIVE_ORIGINAL', str(Path(__file__).resolve().parents[1]/'backups/build-25190541/GameNative.dll')))
SOURCE=BACKUP  # A verified, owned original is required.
DATA=SOURCE.read_bytes()
assert hashlib.sha256(DATA).hexdigest()=='6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b', 'Original build 25190541 required'
import pefile
_pe=pefile.PE(data=DATA)
META={'sections':[{'raw_offset':s.PointerToRawData,'rva':s.VirtualAddress,
                   'raw_size':s.SizeOfRawData} for s in _pe.sections]}
def raw(rva):
    return next(s['raw_offset']+rva-s['rva'] for s in META['sections'] if s['rva']<=rva<s['rva']+s['raw_size'])
def get(rva,size):return DATA[raw(rva):raw(rva)+size]
def messages(lang='en'):return {x['id']:x['text'] for x in json.loads((OUT/f'messages_{lang}.json').read_text(encoding='utf-8'))}
if __name__=='__main__':
    en=messages();fr=messages('fr');rows=[]
    for i in range(116):
        rva=0x562a50+i*24
        flags,name,kind,desc,ptr=struct.unpack('<4IQ',get(rva,24))
        launch=get(0x551780+i*8,8)
        row=dict(id=i,id_hex=hex(i),metadata_rva=hex(rva),name=en.get(name),name_fr=fr.get(name),name_message_id=name,description=en.get(desc),tp_base=flags&255,flags=hex(flags),aux_pointer=hex(ptr),launch_descriptor_rva=hex(0x551780+i*8),launch_bytes=list(launch),effect_id=launch[0],cast_parameter=launch[1])
        rows.append(row)
    (OUT/'artes_native.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in rows:
        if 43<=r['id']<=100 or r['id']>=112:print(json.dumps(r,ensure_ascii=True))
