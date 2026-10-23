"""Reserved ranges in the shared combat UI state (offsets, end exclusive)."""

SPIRIT_OBJECTS = 0x1800
SPIRIT_VTABLE = 0x1900
SCAN_LABELS = 0x1D00
SCAN_LABELS_END = 0x2000
SCAN_DRAWN = 0x167F

RANGES = {
    'spectacles_drawn_this_frame': (SCAN_DRAWN, SCAN_DRAWN + 1),
    'spectacles_number_text': (0x1680, 0x16C0),
    'spirit_objects': (SPIRIT_OBJECTS, SPIRIT_OBJECTS + 10 * 24),
    'spirit_vtable': (SPIRIT_VTABLE, SPIRIT_VTABLE + 6 * 8),
    'vitality_text': (0x1980, 0x19D8),
    'options_and_callbacks': (0x1A00, 0x1B18),
    'title_logo': (0x1C00, 0x1CB0),
    'spectacles_labels': (SCAN_LABELS, SCAN_LABELS_END),
}
ordered = sorted(RANGES.items(), key=lambda item: item[1][0])
for (left, (_, end)), (right, (start, _)) in zip(ordered, ordered[1:]):
    assert end <= start, f'Overlapping UI storage: {left} / {right}'
