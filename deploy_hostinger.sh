#!/bin/bash
# ════════════════════════════════════════════════════════════
#  RADAR ODAS — Script de déploiement Hostinger VPS
#  Usage : bash deploy_hostinger.sh
#  À lancer depuis le répertoire racine du projet sur le VPS
# ════════════════════════════════════════════════════════════

set -e  # Arrêt immédiat en cas d'erreur

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="/home/$(whoami)/sentinel"
BACKEND_DIR="$PROJECT_DIR/backend"

echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   RADAR ODAS — Déploiement en cours...   ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"

# 1. Mise à jour du code
echo -e "\n${YELLOW}[1/5] Pull GitHub...${NC}"
cd "$PROJECT_DIR"
git pull origin main
echo -e "${GREEN}✓ Code mis à jour${NC}"

# 2. Installation des dépendances Python
echo -e "\n${YELLOW}[2/5] Installation des dépendances...${NC}"
cd "$BACKEND_DIR"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dépendances installées${NC}"

# 3. Migrations base de données
echo -e "\n${YELLOW}[3/5] Migrations BDD...${NC}"
python manage.py migrate --no-input
echo -e "${GREEN}✓ Migrations appliquées${NC}"

# 4. Collecte des fichiers statiques
echo -e "\n${YELLOW}[4/5] Collecte des statiques...${NC}"
python manage.py collectstatic --no-input --clear
echo -e "${GREEN}✓ Statiques collectés${NC}"

# 5. Redémarrage de gunicorn
echo -e "\n${YELLOW}[5/5] Redémarrage du service...${NC}"
sudo systemctl restart gunicorn-radar
sleep 2

# Vérification du statut
if systemctl is-active --quiet gunicorn-radar; then
    echo -e "${GREEN}✓ Gunicorn actif${NC}"
else
    echo -e "${RED}✗ Gunicorn ne répond pas — vérifiez : sudo journalctl -u gunicorn-radar -n 50${NC}"
    exit 1
fi

# Rechargement nginx (si config modifiée)
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx rechargé${NC}"
fi

echo -e "\n${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Déploiement terminé avec succès !   ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}\n"
