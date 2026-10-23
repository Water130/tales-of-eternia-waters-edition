"""Elemental names for the live FR/EN catalog; no balance or saved-ID changes."""

NAMES = {
    'Undine': {
        'Économie de mana': ('Flux paisible', 'Tranquil Flow'),
        'Soin préparé': ('Marée bienfaisante', 'Healing Tide'),
        'Soin protecteur': ('Écume protectrice', 'Sheltering Foam'),
    },
    'Sylph': {
        'Récupération après lancement': ('Grâce du zéphyr', "Zephyr's Grace"),
        'Esquive parfaite': ('Corps de vent', 'Windform'),
    },
    'Efreet': {
        'Puissance magique': ('Âme ardente', 'Blazing Soul'),
        'Ferveur magique': ('Braise indomptable', 'Defiant Ember'),
    },
    'Gnome': {
        'Cast protégé': ('Ancrage terrestre', 'Earthen Anchor'),
        'Garde légère': ('Écorce de pierre', 'Stonebark'),
        'Garde complète': ('Cœur de montagne', 'Mountain Heart'),
    },
    'Celsius': {
        'Résistance magique': ('Manteau de givre', 'Frost Mantle'),
        'Esprit limpide': ('Clarté du cristal', 'Crystal Clarity'),
        'Lucidité': ('Esprit de glace', 'Frozen Resolve'),
        'Stase de survie': ('Cocon de glace', 'Ice Cocoon'),
    },
    'Volt': {
        'Critiques magiques': ('Éclat de foudre', 'Lightning Spark'),
        'Éclair de génie': ('Pensée fulgurante', 'Thunder Insight'),
    },
    'Rem': {
        'Soin solidaire': ('Lueur partagée', 'Shared Radiance'),
        'Guérison purifiante': ('Lumière purifiante', 'Cleansing Light'),
        'Régénération': ('Halo régénérant', 'Renewing Halo'),
        'Protection salvatrice': ('Aube salvatrice', 'Saving Dawn'),
    },
    'Shadow': {
        'Absorption de PV': ('Faim des ombres', 'Shadow Hunger'),
        'Absorption de TP': ('Festin nocturne', 'Midnight Feast'),
        'Lien vital': ('Pacte crépusculaire', 'Twilight Pact'),
    },
    'Maxwell': {
        'Mana solidaire': ('Cycle astral', 'Astral Cycle'),
        'Rempart de mana': ('Rempart astral', 'Astral Bulwark'),
        'Partage des ressources': ('Harmonie céleste', 'Celestial Harmony'),
        'Second souffle arcanique': ('Renaissance astrale', 'Astral Rebirth'),
        'Singularité': ('Cœur gravitationnel', 'Gravity Well'),
    },
    'Sekundes': {
        'Don de célérité': ('Souffle du temps', 'Breath of Time'),
        'Mémoire d’incantation': ('Écho temporel', 'Temporal Echo'),
        'Répétition accélérée': ('Spirale du temps', 'Time Spiral'),
    },
}


def rename_faculties(rows):
    for row in rows:
        if row['kind'] != 0:
            continue
        for n in row['nodes']:
            original = n['title'][0]
            n['title'] = NAMES[row['name'][1]][original]
            if original == 'Récupération après lancement':
                n['description'] = (
                    f"Réduit de {n['label'][0][1:]} le délai après un sort réussi, avant que le mage puisse agir à nouveau.",
                    f"Reduces the delay before the mage can act again after a successful cast by {n['label'][1][1:]}.")
