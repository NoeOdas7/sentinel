# RADAR ODAS — Guide de déploiement sur Hostinger VPS

## Prérequis

- Hostinger VPS Ubuntu 22.04 ou 24.04
- Accès SSH root ou sudo
- Domaine pointé vers l'IP du VPS (DNS A record)
- Compte GitHub avec accès au repo `NoeOdas7/sentinel`

---

## Étape 1 — Connexion et préparation du serveur

```bash
# Se connecter au VPS
ssh root@IP_VPS_HOSTINGER

# Créer un utilisateur dédié (recommandé)
adduser odas
usermod -aG sudo odas
su - odas
```

---

## Étape 2 — Installation des dépendances système

```bash
sudo apt update && sudo apt upgrade -y

# Python, pip, git, nginx
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Vérifier la version Python (doit être 3.11+)
python3 --version
```

---

## Étape 3 — Cloner le projet

```bash
cd ~
git clone https://github.com/NoeOdas7/sentinel.git sentinel
cd sentinel
```

---

## Étape 4 — Configurer l'environnement Python

```bash
cd ~/sentinel/backend

# Installer les dépendances directement (sans venv, plus simple sur VPS)
pip install -r requirements.txt

# OU avec un virtualenv :
# python3 -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt
```

---

## Étape 5 — Configurer les variables d'environnement

```bash
# Copier le template et l'éditer
cp ~/sentinel/backend/.env.hostinger ~/sentinel/backend/.env
nano ~/sentinel/backend/.env
```

**Valeurs à remplir obligatoirement :**

| Variable | Valeur |
|---|---|
| `SECRET_KEY` | Générer : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ALLOWED_HOSTS` | `votre-domaine.com,www.votre-domaine.com,IP_VPS` |
| `CORS_ALLOWED_ORIGINS` | `https://votre-domaine.com,https://www.votre-domaine.com` |
| `FRONTEND_URL` | `https://votre-domaine.com` |
| `EMAIL_HOST_USER` | `noreply@votre-domaine.com` (email Hostinger créé dans hPanel) |
| `EMAIL_HOST_PASSWORD` | Mot de passe de l'email Hostinger |

> La `DATABASE_URL` Supabase est déjà configurée dans `.env.hostinger` — rien à changer.

---

## Étape 6 — Initialiser la base de données

```bash
cd ~/sentinel/backend
python3 manage.py migrate --no-input
python3 manage.py collectstatic --no-input

# Créer un superuser admin (optionnel, si pas déjà en BDD)
python3 manage.py createsuperuser
```

---

## Étape 7 — Configurer le service Gunicorn (systemd)

```bash
# Copier le fichier service
sudo cp ~/sentinel/gunicorn-radar.service /etc/systemd/system/

# Éditer et remplacer USER_VPS par votre nom d'utilisateur réel (ex: odas)
sudo nano /etc/systemd/system/gunicorn-radar.service

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-radar
sudo systemctl start gunicorn-radar

# Vérifier que ça tourne
sudo systemctl status gunicorn-radar
```

---

## Étape 8 — Configurer Nginx

```bash
# Copier la config nginx
sudo cp ~/sentinel/nginx_hostinger.conf /etc/nginx/sites-available/radar

# Éditer et remplacer :
#   - "votre-domaine.com" → votre vrai domaine
#   - "USER_VPS" → votre nom d'utilisateur
sudo nano /etc/nginx/sites-available/radar

# Activer le site
sudo ln -s /etc/nginx/sites-available/radar /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Désactiver le site par défaut

# Tester et recharger
sudo nginx -t
sudo systemctl reload nginx
```

---

## Étape 9 — SSL avec Let's Encrypt

```bash
# Générer le certificat (remplacer votre-domaine.com)
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com

# Le renouvellement automatique est configuré par certbot
# Tester : sudo certbot renew --dry-run
```

---

## Étape 10 — Test final

```bash
# Accéder à : https://votre-domaine.com
# Vérifier les logs si problème :
sudo journalctl -u gunicorn-radar -f        # Logs gunicorn
sudo tail -f /var/log/nginx/radar_error.log  # Logs nginx
```

---

## Déploiements futurs (mise à jour du code)

Après chaque `git push` depuis votre machine locale, sur le VPS :

```bash
cd ~/sentinel
bash deploy_hostinger.sh
```

---

## Créer un email Hostinger pour l'envoi d'OTP

1. Se connecter à **hPanel** (panel.hostinger.com)
2. Aller dans **Emails** → **Comptes email**
3. Créer `noreply@votre-domaine.com`
4. Copier le mot de passe dans `.env` → `EMAIL_HOST_PASSWORD`

> Le serveur SMTP Hostinger est `smtp.hostinger.com:587` (TLS)

---

## Dépannage

| Problème | Commande |
|---|---|
| Gunicorn ne démarre pas | `sudo journalctl -u gunicorn-radar -n 100` |
| Nginx 502 Bad Gateway | Vérifier que gunicorn tourne sur le port 8000 : `ss -tlnp \| grep 8000` |
| Erreur collectstatic | `python3 manage.py collectstatic --no-input` dans `backend/` |
| 500 Internal Server Error | `DEBUG=True` temporairement pour voir l'erreur |
| Certificat SSL expiré | `sudo certbot renew` |
