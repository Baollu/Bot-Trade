#!/bin/bash

# Nexus Trade - Script de Démarrage Rapide
# Ce script configure et démarre automatiquement le système

set -e  # Arrêt en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║    ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗               ║
║    ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝               ║
║    ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗               ║
║    ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║               ║
║    ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║               ║
║                                                               ║
║            Installation Rapide - v1.0                         ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${GREEN}🚀 Bienvenue dans Nexus Trade!${NC}\n"

# Vérification des prérequis
echo -e "${YELLOW}📋 Vérification des prérequis...${NC}"

command -v go >/dev/null 2>&1 || { echo -e "${RED}❌ Go n'est pas installé. Installez-le depuis https://golang.org/${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ Python3 n'est pas installé.${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker n'est pas installé. Installez-le depuis https://docker.com/${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}❌ Docker Compose n'est pas installé.${NC}"; exit 1; }

echo -e "${GREEN}✅ Tous les prérequis sont installés${NC}\n"

# 1. Démarrage des services Docker
echo -e "${YELLOW}🐳 Démarrage des services Docker (PostgreSQL, Redis)...${NC}"
docker-compose up -d
sleep 5  # Attendre que les services démarrent
echo -e "${GREEN}✅ Services Docker démarrés${NC}\n"

# 2. Installation des dépendances Python
echo -e "${YELLOW}📦 Installation des dépendances Python...${NC}"
cd ai
python3 -m pip install -r requirements.txt --quiet
cd ..
echo -e "${GREEN}✅ Dépendances Python installées${NC}\n"

# 3. Installation des dépendances Go
echo -e "${YELLOW}📦 Installation des dépendances Go...${NC}"
go mod download
echo -e "${GREEN}✅ Dépendances Go installées${NC}\n"

# 4. Configuration du fichier .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️  Création du fichier .env...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Fichier .env créé${NC}"
    echo -e "${YELLOW}   → Vous pouvez éditer .env pour configurer la blockchain${NC}\n"
else
    echo -e "${GREEN}✅ Fichier .env existe déjà${NC}\n"
fi

# 5. Entraînement du modèle IA
echo -e "${YELLOW}🤖 Entraînement du modèle IA...${NC}"
echo -e "${YELLOW}   ⏱️  Cette étape prend environ 10-20 minutes${NC}"
echo -e "${YELLOW}   📊 Téléchargement de 30 jours de données Bitcoin...${NC}\n"

cd ai
python3 train_model.py
cd ..

if [ -f "ai/crypto_predictor.onnx" ]; then
    echo -e "${GREEN}✅ Modèle IA entraîné avec succès${NC}\n"
else
    echo -e "${RED}❌ Erreur lors de l'entraînement du modèle${NC}"
    exit 1
fi

# 6. Résumé
echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════════"
echo "✅ INSTALLATION TERMINÉE AVEC SUCCÈS!"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Prochaines étapes:${NC}\n"
echo -e "1. ${YELLOW}Configurer la blockchain (optionnel):${NC}"
echo -e "   Éditez le fichier .env avec vos clés Sepolia"
echo -e "   (Laissez vide pour mode simulation)\n"

echo -e "2. ${YELLOW}Démarrer le système:${NC}"
echo -e "   ${BLUE}go run cmd/main.go${NC}\n"

echo -e "3. ${YELLOW}Accéder au dashboard:${NC}"
echo -e "   ${BLUE}http://localhost:8080${NC}\n"

echo -e "${GREEN}Autres commandes utiles:${NC}"
echo -e "  ${BLUE}make help${NC}        - Afficher toutes les commandes"
echo -e "  ${BLUE}make run${NC}         - Lancer le système"
echo -e "  ${BLUE}make docker-logs${NC} - Voir les logs Docker"
echo -e "  ${BLUE}make clean${NC}       - Nettoyer les fichiers générés"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Prêt à trader! Bonne chance!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
