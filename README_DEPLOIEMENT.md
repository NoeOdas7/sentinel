# 🛡️ SENTINEL — Guide de déploiement

## Plateforme de veille anti-droits · Centre ODAS

---

## 📋 Prérequis
- Python 3.11+
- PostgreSQL 14+
- Git
- (Optionnel) Node.js 18+ pour le frontend Vue.js

---

## 🚀 Installation locale

### 1. Cloner et configurer
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Éditez .env avec vos valeurs
```

### 2. Base de données
```bash
# Créer la base PostgreSQL
createdb sentinel_db
# Ou via psql :
psql -U postgres -c "CREATE DATABASE sentinel_db;"
psql -U postgres -c "CREATE USER sentinel_user WITH PASSWORD 'votre_mdp';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE sentinel_db TO sentinel_user;"
```

### 3. Migrations et superuser
```bash
python manage.py migrate
python manage.py createsuperuser
# Renseignez email, nom_complet, mot de passe
```

### 4. Lancer
```bash
python manage.py runserver
# API : http://localhost:8000/api/v1/
# Admin : http://localhost:8000/admin/
# Docs : http://localhost:8000/api/docs/
```

### 5. Frontend
```bash
# Ouvrir frontend/index.html dans le navigateur
# Ou le déployer sur Netlify (drag & drop)
```

---

## ☁️ Déploiement Railway (Backend)

### Variables d'environnement Railway
```
SECRET_KEY=<clé-secrète-50-caractères-minimum>
DEBUG=False
ALLOWED_HOSTS=.railway.app,.up.railway.app
DATABASE_URL=<auto-injecté-par-railway>
EMAIL_HOST_USER=votre@gmail.com
EMAIL_HOST_PASSWORD=<mot-de-passe-application-gmail>
DEFAULT_FROM_EMAIL=SENTINEL ODAS <votre@gmail.com>
FRONTEND_URL=https://votre-sentinel.netlify.app
OTP_EXPIRY_SECONDS=600
CORS_ALLOWED_ORIGINS=https://votre-sentinel.netlify.app
```

### Étapes Railway
1. `npm install -g @railway/cli`
2. `railway login`
3. `cd sentinel && railway init`
4. Dans Railway Dashboard → New → Add PostgreSQL
5. `railway up`

---

## 📧 Configuration Gmail OTP

1. Activez la validation en 2 étapes sur votre compte Google
2. Allez sur myaccount.google.com → Sécurité → Mots de passe des applications
3. Générez un mot de passe pour "SENTINEL"
4. Utilisez ce mot de passe dans EMAIL_HOST_PASSWORD

---

## 🌍 Frontend sur Netlify

1. Allez sur netlify.com
2. Drag & drop le fichier `frontend/index.html`
3. Votre URL sera du type : https://sentinel-odas.netlify.app

Pour pointer vers l'API Railway, editez la variable `API` dans index.html :
```javascript
const API = 'https://votre-backend.railway.app/api/v1';
```

---

## 🔑 Accès admin par défaut

Après `createsuperuser` :
- URL Admin : http://localhost:8000/admin/
- Approuver les membres : Admin → Membres → Sélectionner → Approuver

---

## 📡 Endpoints API principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| /api/v1/auth/login/ | POST | Étape 1 : email + mdp |
| /api/v1/auth/verify-otp/ | POST | Étape 2 : code OTP |
| /api/v1/auth/resend-otp/ | POST | Renvoyer le code |
| /api/v1/auth/register/ | POST | Demande d'accès |
| /api/v1/auth/profile/ | GET/PATCH | Profil utilisateur |
| /api/v1/auth/invite/ | POST | Inviter un membre |
| /api/v1/auth/members/ | GET | Liste des membres |
| /api/v1/signals/ | GET | Liste signalements |
| /api/v1/signals/create/ | POST | Nouveau signalement |
| /api/v1/signals/dashboard/ | GET | Stats tableau de bord |
| /api/v1/actors/ | GET | Liste acteurs |
| /api/v1/actors/network/ | GET | Données graphe |
| /api/v1/resources/ | GET | Ressources publiées |

Documentation complète : http://localhost:8000/api/docs/

---

## 🔐 Authentification

Toutes les requêtes sécurisées nécessitent le header :
```
Authorization: Bearer <token>
```

Le token est retourné par /api/v1/auth/verify-otp/ et expire après 7 jours.

---

## 📞 Support

Centre ODAS — Réseau SENTINEL  
Plateforme développée pour la veille des mouvements anti-droits en Afrique francophone.
