# BAM — assistant vocal personnel

Cadrage validé avec l'utilisateur. Toute évolution de ce cadrage se valide avec lui avant d'être codée.

## Rôle

- Assistant vocal en français, usage **interne uniquement**.
- Tourne **uniquement sur le PC Windows** de l'utilisateur (pas de VPS).
- Démarre avec Windows, puis **attend les consignes**. Il n'agit jamais de sa propre initiative.
- Réveil : « **Salut BAM** ».
- Répond **à voix haute** (voix française masculine) et affiche l'échange dans un **petit panneau** : icône dans la barre des tâches, panneau ouvrable/fermable, lecture seule (pas de saisie texte).
- Sur ordre explicite, il exécute. Sinon, il propose.

## Matériel cible

- Windows, 96 Go de RAM, RTX 5070 12 Go, bon micro.
- RTX 5070 (Blackwell) : CTranslate2 ≥ 4.8.2 et CUDA 12.8 requis pour faster-whisper sur GPU.

## Stack validée

| Rôle | Brique |
|---|---|
| Langage | Python |
| Écoute micro | RealtimeSTT (MIT) |
| Mot de réveil | openWakeWord, modèle « Salut BAM » entraîné en français |
| Voix → texte | faster-whisper sur GPU, en local |
| Voix de BAM | Piper (GPL-3.0, sans impact tant que BAM reste interne), voix française masculine |
| Cerveau | API Claude, modèle Sonnet 5.5 (`claude-sonnet-5-5`), SDK officiel `anthropic` |
| Mail + agenda | API Gmail + API Google Agenda (gratuites) |
| Stockage | SQLite |

## Budget

- API Claude : environ 20 €/mois, validé. Crédits prépayés, recharge automatique désactivée.
- Tout le reste : gratuit et open source. Rien de payant sans accord explicite de l'utilisateur.

## Données sensibles

- Tout est stocké sur le PC.
- Pour les données business (clients, banque) : calculs en local, seuls des totaux anonymes partent vers Claude (pas de noms, pas d'IBAN).
- Aucun secret (clé API, jetons OAuth, `.env`) ne doit être commité.

## Plan V1

1. **Socle vocal** : « Salut BAM » → transcription → réponse Claude → voix Piper. Tests sur le PC.
2. **Interface** : icône barre des tâches + panneau d'historique (charte byBim) + lancement au démarrage de Windows.
3. **Mail + agenda** (1 compte Gmail) : résumer, écrire, répondre, transférer, trier, supprimer. Exécution sur ordre explicite.
   - Envoyer, transférer, supprimer : BAM résume l'action en une phrase et attend « oui » avant d'exécuter.
   - Résumer, écrire un brouillon, trier : exécution directe.
   - Supprimer = mettre à la corbeille (récupérable), jamais de suppression définitive.
4. **Mesure des coûts API** pendant la première semaine.

## Backlog (après la V1)

- **À rappeler à l'utilisateur à la fin de la V1** : suivi business via l'ERP/SaaS (erp.bybim.fr) et e-devis — CA du mois, devis en attente, factures impayées, progression vers l'objectif annuel.
- Passer de 1 à 10 comptes mail.
- Tâches et rappels, brief quotidien, mémoire des projets et décisions, rédaction.
- Surveillance VPS / Coolify / Gitea, veille : mises de côté.

## Idées proposées, non validées (ne pas coder sans accord)

- Réponses vocales courtes + cache des prompts pour réduire le coût API.
- Commandes simples (heure, agenda du jour) traitées en local sans appeler Claude.
- Compteur de dépense API dans le panneau.
- Onde de voix rouge #E7000B animée quand BAM écoute ou parle (à ajouter à la charte si validée).

## Règles de travail

1. Questions avant d'agir. On code seulement quand tout est clair.
2. L'utilisateur demande A, on fait A. Toute idée en plus est proposée et validée avant.
3. Un désaccord se règle par le débat, pas en codant.
4. Rien de payant sans accord.
- Réponses en français, simples et précises.
- Code propre et optimisé, commentaires en français, commits concis.

## Charte byBim (interface)

- Fonds : #0D0D0D (principal), #09090B (panneau), #050505 (surface profonde).
- Accent rouge : #E7000B (foncé #9F0712, clair #FF6467). Il ponctue, jamais de grandes surfaces.
- Texte : #FFFFFF, #F0F0F0 (courant), #D4D4D8 (secondaire), #52525C (discret). Bordures : #27272A.
- Typo unique : Avenir (Black/Heavy titres, Regular/Book corps, Light grands chiffres).
- Logo toujours monochrome, jamais déformé, incliné, ni avec contour ou ombre.
