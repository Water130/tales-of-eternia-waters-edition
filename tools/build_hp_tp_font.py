"""Copy only the ten native EN HP/TP glyphs into the owned FR battle bundle.

The 480x48 RGBA strip is copied losslessly. Damage figures, other glyphs,
texture metadata and all serialized objects retain their original bytes.
No game resource is downloaded or shipped by this source script.
"""
from pathlib import Path
import hashlib
import json
import sys
import struct
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/pydeps'))
import UnityPy
from UnityPy.streams import EndianBinaryReader
from zarc_audit import ROOT as GAME

from build_profile import OUT as STAGE
OUT = STAGE / 'hp-tp-font'
BACKUP = ROOT / 'backups/build-25190541/hp-tp-font'
FR_HASH = 'dc71f69e962189e9e7c83fca06c9466f63f50b2a69159b54b7eb8f6d3a68f0d7'
RECT = (0, 800, 480, 848)
sha = lambda b: hashlib.sha256(b).hexdigest()


def load_texture(raw):
    env = UnityPy.load(raw)
    bundle = next(iter(env.files.values()))
    textures = [o.parse_as_object() for o in env.objects if o.type.name == 'Texture2D']
    assert len(textures) == 1
    tex = textures[0]
    assert (tex.m_Name, tex.m_Width, tex.m_Height, tex.m_TextureFormat,
            tex.m_MipCount) == ('jef1_ui_00', 1024, 1024, 4, 1)
    return env, bundle, tex


def main():
    paths=[]
    for key in ('0x08010034','0x08010036'):
        matches=list((GAME/'Tales of Eternia Remastered_Data/StreamingAssets/aa/StandaloneWindows64').glob('*_assets_'+key+'_*.bundle'))
        assert len(matches)==1, (key, 'Required owned resource missing or ambiguous')
        paths.append(matches[0])
    en_raw = paths[0].read_bytes()
    original_path = Path(os.environ['TOE_FONT_ORIGINAL']) if os.environ.get('TOE_FONT_ORIGINAL') else BACKUP / paths[1].name
    fr_raw = original_path.read_bytes() if original_path.exists() else paths[1].read_bytes()
    assert sha(fr_raw) == FR_HASH, 'Unknown French source bundle; refusing to overwrite another mod'
    # This build uses local LoadFromFileAsync with the catalog's CRC. Confirm
    # that the FR resource has CRC=0; no catalog/checksum bypass is needed.
    catalog = (GAME / 'Tales of Eternia Remastered_Data/StreamingAssets/aa/catalog.bin').read_bytes()
    hash_id, _, crc, size, _ = struct.unpack_from('<5I', catalog, 0xb54c05)
    assert catalog[hash_id:hash_id + 16].hex() == '2f5ba85385ed9112aa6b5e3b7e26860e'
    assert crc == 0 and size == len(fr_raw), 'Different Addressables metadata; inspect before patching'
    en_env, _, en = load_texture(en_raw)
    fr_env, bundle, fr = load_texture(fr_raw)
    assert sha(en.image.tobytes()) == '2ca6516d9bad3311113160746cd43e5c30afb4b5e1b292442066a3a8633b347a'
    old_pixels = fr.image.tobytes()
    donor_pixels = en.image.tobytes()
    stream_name = fr.m_StreamData.path.rsplit('/', 1)[1]
    stream = bytearray(bundle.files[stream_name].bytes)
    donor = en.get_image_data()
    assert fr.m_StreamData.offset == en.m_StreamData.offset == 0
    assert len(stream) == len(donor) == 1024 * 1024 * 4
    # Unity RGBA32 storage is bottom-up; decoded images are top-down.
    pitch = 1024 * 4
    for y in range(800, 848):
        start = (1023 - y) * pitch
        stream[start:start + 480 * 4] = donor[start:start + 480 * 4]
    original_files = {}
    for name, node in list(bundle.files.items()):
        raw = node.reader.bytes if hasattr(node, 'reader') else node.bytes
        original_files[name] = bytes(raw)
        reader = EndianBinaryReader(bytes(stream) if name == stream_name else raw)
        reader.flags = node.flags
        bundle.files[name] = reader
    result = bundle.save(packer='lz4')
    checked_env, checked_bundle, checked = load_texture(result)
    assert checked_bundle.files.keys() == original_files.keys()
    for name, raw in original_files.items():
        node = checked_bundle.files[name]
        reread = node.reader.bytes if hasattr(node, 'reader') else node.bytes
        assert reread == (bytes(stream) if name == stream_name else raw)
    # Independent decoded-pixel verification covers every pixel, not only glyphs.
    pixels = checked.image.tobytes()
    changed = 0
    for y in range(1024):
        for x in range(1024):
            pos = (y * 1024 + x) * 4
            inside = 800 <= y < 848 and x < 480
            expected = donor_pixels if inside else old_pixels
            assert pixels[pos:pos + 4] == expected[pos:pos + 4], (x, y)
            changed += pixels[pos:pos + 4] != old_pixels[pos:pos + 4]
    assert changed > 0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / paths[1].name).write_bytes(result)
    record = dict(passed=True, scope='HP/TP digits only; French locale',
                  target_relative=paths[1].relative_to(GAME).as_posix(),
                  file=paths[1].name, original_sha256=sha(fr_raw), patched_sha256=sha(result),
                  donor_sha256=sha(en_raw), rect=RECT, changed_pixels=changed,
                  outside_pixels_unchanged=True, damage_digits_unchanged=True,
                  serialized_metadata_unchanged=True, runtime_validated=False)
    record.update(catalog_crc=crc, catalog_unchanged=True)
    (OUT / 'verification.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
