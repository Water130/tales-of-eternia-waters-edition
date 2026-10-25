"""Player-facing descriptions for the approved fighter faculties."""
from fighter_expansion import GATES

# key, tree, FR/EN title, FR/EN benefit, FR/EN description
ENTRIES = [
 ('R2',0,('Balayage ample','Wide Slash'),('Portée +25%','Width +25%'),
  ('Élargit de 25 % la zone du dernier coup normal tranchant pour toucher les ennemis regroupés.',
   'Widens the final normal slash hitbox by 25% to reach clustered enemies.')),
 ('R3',0,('Lame prolongée','Lasting Blade'),('Portée accrue','Longer range'),
  ('Lame sonique se dissipe plus lentement et parcourt une plus grande distance, à la même vitesse. Le projectile disparaît toujours au premier impact.',
   'Sonic Blade dissipates more slowly and travels farther at the same speed. The projectile still ends on its first hit.')),
 ('R4',0,('Brise-garde','Guard Breaker'),('Garde brisée','Guard break'),
  ('Trois attaques normales réussies dans une chaîne préparent le prochain arte tranchant : sa première collision brise une garde ordinaire. Les protections spéciales restent efficaces.',
   'Land three normal attacks in one chain to prepare the next Slash arte: its first collision breaks an ordinary guard. Special protections remain effective.')),
 ('R5',1,('Parade précise','Precise Guard'),('+3 TP','+3 TP'),
  ('Bloquer un coup dans les huit premières images de garde rend 3 TP. Une seule récompense par attaque ennemie, même si elle touche plusieurs fois.',
   'Block within the first eight guard frames to regain 3 TP. Each enemy attack rewards this only once, including multi-hit attacks.')),
 ('R6',1,('Pression rapprochée','Close Pressure'),('Recul -50%','Pushback -50%'),
  ('Les artes purement Estoc repoussent deux fois moins les ennemis légers au sol. Les projections aériennes et les ennemis lourds sont inchangés.',
   'Pure Thrust artes halve grounded pushback against light enemies. Launches and heavy enemies are unaffected.')),
 ('R7',1,("Pas d’allonge",'Step In'),('Garde + avant','Guard + forward'),
  ('Pendant la garde, inclinez la direction vers la cible pour effectuer un court pas en avant. Relâchez la direction avant de recommencer. Garde + Haut conserve le saut.',
   'While guarding, press toward the target for a short forward step. Release the direction before repeating. Guard + Up still jumps.')),
 ('R9',4,('Alternance maîtrisée','Controlled Alternation'),('3e arte -20% TP','3rd arte -20% TP'),
  ('Enchaînez un arte Tranchant puis Estoc, ou l’inverse : le troisième arte physique coûte 20 % de TP en moins. Une fois par chaîne.',
   'Chain a Slash arte into a Thrust arte, or vice versa: the third physical arte costs 20% less TP. Once per chain.')),
 ('R11',4,('Rempart','Bulwark'),('Dégâts -10%','Damage -10%'),
  ('Pendant que Reid garde, les alliés proches subissent 10 % de dégâts physiques en moins. Reid ne bénéficie pas de sa propre protection.',
   'While Reid guards, nearby allies take 10% less physical damage. Reid does not benefit from his own protection.')),
 ('R12',4,('Retour technique','Technical Return'),('Arcane > base','Arcane > basic'),
  ('Permet de revenir d’un arcane à un arte de base une fois par chaîne. La limite de deux artes de base et les autres quotas restent appliqués.',
   'Return from an arcane to a basic arte once per chain. The two-basic-arte limit and other chain quotas still apply.')),
 ('R14',4,('Sang-froid','Composure'),('Super-armure','Super armor'),
  ('Les coups n’interrompent plus Reid pendant l’exécution d’un arcane. Il subit toujours les dégâts et les altérations d’état.',
   'Hits no longer interrupt Reid while executing an arcane arte. Damage and status ailments still apply.')),
 ('F1',2,('Poing préparé','Prepared Fist'),('1 interruption','1 interruption'),
  ('Gardez immobile pendant 20 images pour préparer le prochain arte de Poing : il résiste à une interruption légère. La préparation expire après trois secondes sans garde immobile.',
   'Guard without moving for 20 frames to prepare the next Punch arte: it resists one light interruption. The preparation expires three seconds after stationary guarding ends.')),
 ('F2',2,('Série variée','Varied Sequence'),('Rend 10% TP','Refunds 10% TP'),
  ('Touchez avec trois artes de Poing différents dans une chaîne pour récupérer 10 % des TP dépensés pour les artes de Poing de cette chaîne. Une seule fois par chaîne.',
   'Land three different Punch artes in one chain to regain 10% of the TP spent on its Punch artes. Triggers once per chain.')),
 ('F3',2,('Paume déstabilisante','Staggering Palm'),('Recul +6 images','Hitstun +6 frames'),
  ('Le dernier impact de Double coup de paume ajoute six images de recul à un ennemi léger au sol, une fois par chaîne. Les boss et les cibles protégées sont exclus.',
   'Twin Palm Strike’s final impact adds six hitstun frames to a light grounded enemy, once per chain. Bosses and protected targets are excluded.')),
 ('F4',2,('Paume brisante','Breaking Palm'),('Garde brisée','Guard break'),
  ('Touchez avec trois artes de Poing différents dans une chaîne pour préparer Double coup de paume : sa première collision brise une garde ordinaire. Les protections spéciales restent efficaces.',
   'Land three different Punch artes in one chain to prepare Twin Palm Strike: its first collision breaks an ordinary guard. Special protections remain effective.')),
 ('F6',3,('Ascension maîtrisée','Controlled Ascent'),('Fenêtre +6 images','Window +6 frames'),
  ('Ajoute six images à la fenêtre d’enchaînement après un arte ascendant. L’arte suivant doit être un plongeon compatible, avec une hauteur suffisante.',
   'Adds six frames to the chain-input window after a rising arte. The next arte must be a compatible dive, with sufficient height.')),
 ('F8',6,('Rythme martial','Martial Rhythm'),('Soin : incant. -75%','Heal casting -75%'),
  ('Trois artes réussis alternant Poing et Pied préparent le prochain soin : son incantation est réduite de 75 %. Une préparation à la fois, sans cumul avec Soin d’urgence.',
   'Land three artes alternating Punch and Kick to prepare the next heal: its casting time is reduced by 75%. Holds one preparation and does not stack with Emergency Heal.')),
 ('F10',6,('Retour au combat','Back to Battle'),('Soin > attaque','Heal > attack'),
  ('Après l’application d’un soin, appuyez sur Attaque pendant la récupération pour reprendre immédiatement avec une attaque normale au sol.',
   'After a heal takes effect, press Attack during recovery to resume immediately with a grounded normal attack.')),
 ('F11',5,("Soin d’urgence",'Emergency Heal'),('Incantation -50%','Casting -50%'),
  ('Si Farah a strictement moins de 25 % de ses PV max, Guérisseur s’incante deux fois plus vite. Délai de 15 secondes entre deux déclenchements. Rythme martial a priorité.',
   'When Farah has strictly less than 25% of her max HP, Healer casts twice as fast. Has a 15-second cooldown. Martial Rhythm takes priority.')),
 ('F12',5,('Purification persistante','Lasting Purification'),('Immunité 10 s','Immunity 10 s'),
  ('Quand Désintoxication retire une altération, la cible résiste à cette même altération pendant dix secondes. Ne protège pas contre les autres altérations.',
   'When Detoxify removes an ailment, the target resists that same ailment for ten seconds. Other ailments are not prevented.')),
 ('F13',5,('Renaissance protectrice','Protective Revival'),('Dégâts -25%, 5 s','Damage -25%, 5 s'),
  ('Un allié réanimé par Renaissance subit 25 % de dégâts en moins pendant cinq secondes.',
   'An ally revived by Life takes 25% less damage for five seconds.')),
 ('F14',5,('Élan vital','Vital Momentum'),('Prochain arte -20% TP','Next arte -20% TP'),
  ('Restaurer des PV manquants avec un soin réduit de 20 % le coût du prochain arte physique de Farah. Aucun cumul ni déclenchement sur une cible déjà à pleine vie.',
   'Restoring missing HP with a heal reduces the cost of Farah’s next physical arte by 20%. Does not stack or trigger on a full-HP target.')),
]

def extend(rows,node):
    physical={r['key']:r for r in rows if r['kind']==1}
    for key,tree,title,label,description in ENTRIES:
        pref,char,mask,level=GATES[key]
        r=physical[tree]
        occupied={n['lane'] for n in r['nodes'] if n['required']==level}
        lane=next(i for i in range(4) if i not in occupied)
        r['nodes'].append(node(level,label,title,description,implemented=True,lane=lane,preference=pref))
    # Regulus prototypes are retained in source but suspended in the game.
    for r in physical.values():
        assert len(r['nodes'])<=12
        cells=[(n['required'],n['lane']) for n in r['nodes']]
        assert len(cells)==len(set(cells)), (r['key'],cells)
