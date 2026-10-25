"""One gameplay revision; only experimental access differs between editions."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = '0.14.30'
EDITION = os.environ.get('TOE_EDITION', 'R').upper()
if EDITION not in ('R', 'T'):
    raise ValueError('TOE_EDITION must be R (release) or T (test)')
TEST_EDITION = EDITION == 'T'
VERSION = REVISION + EDITION
OUT = ROOT / ('build/combat-test' if TEST_EDITION else 'build/combat-release')
