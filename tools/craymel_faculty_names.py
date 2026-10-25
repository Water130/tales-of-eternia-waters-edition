"""Names selected by Water on 2026-10-23; no balance or saved-ID changes."""

NAMES = {
    'Undine': {
        'Économie de mana': ('Économie de mana', 'Mana Economy'),
        'Soin préparé': ('Soin renforcé', 'Enhanced Healing'),
        'Soin protecteur': ('Garde d’Ondine', "Undine's Guard"),
    },
    'Sylph': {
        'Récupération après lancement': ('Mage agile', 'Nimble Mage'),
        'Esquive parfaite': ('Esquive parfaite', 'Perfect Dodge'),
    },
    'Efreet': {
        'Puissance magique': ('Force magique', 'Magic Force'),
        'Ferveur magique': ('Volonté ardente', 'Burning Will'),
    },
    'Gnome': {
        'Cast protégé': ('Garde d’incantation', 'Casting Guard'),
        'Garde légère': ('Concentration', 'Concentration'),
        'Garde complète': ('Inébranlable', 'Unshakable'),
    },
    'Celsius': {
        'Résistance magique': ('Résistance magique', 'Magic Resistance'),
        'Esprit limpide': ('Clarté mentale', 'Mental Clarity'),
        'Lucidité': ('Lucidité', 'Lucidity'),
        'Stase de survie': ('Survie', 'Survival'),
    },
    'Volt': {
        'Critiques magiques': ('Sort critique', 'Critical Spell'),
        'Éclair de génie': ('Incantation éclair', 'Flash Casting'),
    },
    'Rem': {
        'Soin solidaire': ('Soin partagé', 'Shared Healing'),
        'Guérison purifiante': ('Purification', 'Purification'),
        'Régénération': ('Régénération', 'Regeneration'),
        'Protection salvatrice': ('Garde salvatrice', 'Saving Guard'),
    },
    'Shadow': {
        'Absorption de PV': ('Vol de vie', 'Life Steal'),
        'Absorption de TP': ('Vol d’esprit', 'Spirit Steal'),
        'Lien vital': ('Lien vital', 'Vital Link'),
    },
    'Maxwell': {
        'Mana solidaire': ('Don spirituel', 'Spiritual Gift'),
        'Rempart de mana': ('Manteau de mana', 'Mana Coat'),
        'Partage des ressources': ('Partage des ressources', 'Resource Sharing'),
        'Second souffle arcanique': ('Second souffle', 'Second Wind'),
        'Singularité': ('Singularité', 'Singularity'),
    },
    'Sekundes': {
        'Don de célérité': ('Incantation rapide', 'Speed Cast'),
        'Mémoire d’incantation': ('Mémoire d’incantation', 'Spell Memory'),
        'Répétition accélérée': ('Reprise', 'Reprise'),
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
