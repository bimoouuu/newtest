# BimouIA

Bot Discord privé : il annonce tes lives et tes publications, et donne des rôles par réaction.

## Fonctionnalités

| Fonction | Fonctionnement |
|---|---|
| Live Twitch | Annonce automatique (vérification chaque minute) |
| Live TikTok | Commande `/live tiktok` |
| Vidéos YouTube | Annonce automatique (flux RSS, toutes les 5 min) |
| Vidéos TikTok | Annonce automatique (API officielle, toutes les 10 min) |
| Rôles par réaction | Commandes `/reactions …` |
| Rôle sub Twitch | Intégration Twitch intégrée à Discord ([voir plus bas](#rôle-sub-twitch)) |

- Toutes les annonces partent dans **un seul salon**, avec la mention **@notifs**.
- Au premier démarrage, les vidéos déjà en ligne sont enregistrées **sans être annoncées**.
- Chaque plateforme ne s'active que si sa configuration est remplie dans `.env`.

## Commandes

Elles sont réservées aux membres qui ont la permission **Gérer les rôles**. Pour changer qui y a accès : Paramètres du serveur → Intégrations → BimouIA.

| Commande | Effet |
|---|---|
| `/reactions creer [salon] [mode]` | Ouvre une fenêtre (titre + texte) et publie l'encadré. Mode : plusieurs rôles possibles, ou un seul à la fois. |
| `/reactions ajouter message emoji role` | Associe un emoji à un rôle. Le message se choisit dans une liste. |
| `/reactions retirer message emoji` | Retire un emoji du message. Les membres gardent le rôle déjà obtenu. |
| `/reactions modifier message [mode]` | Modifie le titre, le texte ou le mode. |
| `/live tiktok` | Annonce ton live TikTok. |

- Un membre qui réagit obtient le rôle. S'il retire sa réaction, il perd le rôle.
- En mode « un seul rôle », réagir sur un autre emoji remplace l'ancien rôle.
- Par sécurité, le bot refuse les rôles gérés par une intégration, les rôles qui donnent des pouvoirs de modération et les rôles égaux ou supérieurs au rôle du modérateur.

## Installation

### 1. Appli Discord

1. Sur <https://discord.com/developers/applications>, clique sur **New Application** et nomme-la « BimouIA ».
2. Dans l'onglet **Bot** :
   - clique sur **Reset Token** et copie le jeton dans `DISCORD_TOKEN` ;
   - décoche **Public Bot**.

   Aucun « Privileged Gateway Intent » n'est nécessaire.
3. Invite le bot avec ce lien, en remplaçant `APP_ID` par l'**Application ID** (onglet General Information) :
   ```
   https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot+applications.commands&permissions=268692544
   ```
   Permissions incluses : voir les salons, envoyer des messages, gérer les messages, intégrer des liens, joindre des fichiers, voir l'historique, ajouter des réactions, gérer les rôles, mentionner les rôles. Le bot ne mentionne jamais que @notifs.
4. Dans Paramètres du serveur → Rôles, place le rôle **BimouIA au-dessus** des rôles qu'il doit donner.
5. Crée le rôle **@notifs**.
6. Active le mode développeur (Paramètres → Avancés). Fais ensuite clic droit → **Copier l'identifiant** sur le serveur, sur le salon des notifications et sur le rôle @notifs.

### 2. Twitch

1. Sur <https://dev.twitch.tv/console/apps>, clique sur **Register Your Application** :
   - OAuth Redirect URL : `http://localhost`
   - Client Type : **Confidential**
2. Copie le **Client ID** et un **New Secret** dans `.env`.
3. `TWITCH_LOGIN` = le nom qui apparaît dans `twitch.tv/<nom>`.

### 3. YouTube

`YOUTUBE_CHANNEL_ID` = l'identifiant qui commence par `UC…`. Il est sur <https://www.youtube.com/account_advanced>. Aucune clé n'est nécessaire.

### 4. TikTok (vidéos automatiques)

1. Sur <https://developers.tiktok.com>, crée une appli et ajoute les produits **Login Kit** et **Display API**, avec les scopes `user.info.basic` et `video.list`.
2. Déclare une adresse de redirection en `https`, sans paramètres (par ex. `https://bybim.fr/tiktok`). La page n'a pas besoin d'exister. Recopie-la à l'identique dans `TIKTOK_REDIRECT_URI`.
3. Une appli neuve est en mode **sandbox** : ajoute ton compte TikTok comme utilisateur test. Si la sandbox ne suffit pas, soumets l'appli à la validation de TikTok.
4. Copie le **Client Key** et le **Client Secret** dans `.env`.
5. Une fois le bot lancé, connecte ton compte (une seule fois) :
   ```
   docker compose run --rm bot python -m bimouia.tiktok_auth
   ```
   Ouvre le lien affiché et autorise l'appli, puis colle l'adresse de la page sur laquelle tu arrives.

### 5. Lancement sur le VPS

```
cp .env.example .env      # puis remplis les valeurs
docker compose up -d --build
docker compose logs -f bot
```

Pour mettre à jour : `git pull && docker compose up -d --build`.

## Rôle sub Twitch

C'est l'intégration Twitch de Discord qui le gère : rien à coder. Il faut être Affilié ou Partenaire Twitch.

1. Discord → Paramètres utilisateur → **Connexions** → Twitch : lie le compte de ta chaîne.
2. Paramètres du serveur → **Intégrations** → Twitch : active la synchronisation. Discord crée le rôle « Twitch Subscriber » et un rôle par palier.
3. Dans les réglages de l'intégration, choisis **Retirer le rôle** à l'expiration et règle le délai de grâce.
4. Les viewers lient leur Twitch dans Paramètres → Connexions. Ils reçoivent le rôle s'ils sont subs, et le perdent quand le sub expire.

## Développement

```
pip install -r requirements-dev.txt
python -m pytest
```
