# 🚀 Démarrage Rapide - Nexus Trade

Guide ultra-rapide pour lancer le système en moins de 30 minutes.

## ⚡ Installation Automatique

### Option 1: Script Automatique (Recommandé)

```bash
./start.sh
```

Ce script va:
- ✅ Vérifier les prérequis (Go, Python, Docker)
- ✅ Démarrer PostgreSQL et Redis
- ✅ Installer les dépendances
- ✅ Entraîner le modèle IA (10-20 min)
- ✅ Configurer le projet

### Option 2: Makefile

```bash
make setup    # Installation complète
make run      # Lancer le système
```

## 📦 Installation Manuelle (5 étapes)

### 1. Services Docker

```bash
docker-compose up -d
```

### 2. Dépendances Python

```bash
cd ai
pip install -r requirements.txt
```

### 3. Dépendances Go

```bash
go mod download
```

### 4. Configuration

```bash
cp .env.example .env
# Éditez .env si vous voulez activer la blockchain
```

### 5. Entraînement IA

```bash
cd ai
python train_model.py
```

## 🎯 Lancement

```bash
go run cmd/main.go
```

Ou avec Make:

```bash
make run
```

## 🌐 Accès au Dashboard

Ouvrez votre navigateur:
```
http://localhost:8080
```

Vous verrez:
- 💰 Prix Bitcoin en temps réel
- 🤖 Prédictions IA toutes les minutes
- 💼 État du portefeuille
- 📜 Historique des trades avec liens blockchain

## 🧪 Test sans Entraînement

Si vous voulez juste tester le système sans entraîner le modèle:

```bash
# Le système fonctionnera en mode "simulation" avec des prédictions basiques
# basées sur des indicateurs techniques simples (RSI, etc.)
go run cmd/main.go
```

## ⛓️ Configuration Blockchain (Optionnel)

### Rapide

1. Allez sur [alchemy.com](https://alchemy.com) → Créez un compte
2. Créez une app Sepolia → Copiez l'URL HTTP
3. Créez un wallet MetaMask de test → Exportez la clé privée
4. Obtenez du Sepolia ETH: [sepoliafaucet.com](https://sepoliafaucet.com)

Éditez `.env`:
```bash
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
PRIVATE_KEY=your_private_key_without_0x
```

### Sans Blockchain

Laissez `.env` sans ces variables → Le système fonctionnera en mode "mock" avec des hash simulés.

## 🎛️ Commandes Utiles

```bash
make help           # Voir toutes les commandes
make docker-logs    # Logs Docker
make clean          # Nettoyer
make test           # Tests
make build          # Compiler
```

## 📊 Dashboard

Le dashboard affiche en temps réel:

- **Prix actuel**: Bitcoin en USD
- **Prédiction IA**: Hausse/Baisse/Neutre + confiance
- **Portefeuille**: 
  - Valeur totale
  - USD disponibles
  - BTC détenus
  - Performance (%)
- **Statistiques**:
  - Nombre de trades
  - Profit total
  - Taux de réussite
  - Profit moyen
- **Historique**: Liste des 20 derniers trades avec liens blockchain

## 🤖 Fonctionnement du Trading

Le système trade automatiquement quand:
- ✅ Confiance de l'IA > 65%
- ✅ Mouvement prédit > 1%

Décisions:
- **Prédiction HAUSSE** → Achète du BTC (si cash disponible)
- **Prédiction BAISSE** → Vend du BTC (si BTC détenus)
- **Prédiction NEUTRE** → Attend

## 📈 Performance IA

Le modèle GRU utilise 30+ indicateurs techniques:
- RSI (14 et 7 périodes)
- MACD + Signal + Divergence
- Bollinger Bands
- ATR (Average True Range)
- EMA et SMA
- Stochastic Oscillator
- OBV (On-Balance Volume)
- Momentum et Rate of Change

**Précision attendue**: 55-70% selon les conditions de marché

## ⚠️ Important

- 💸 Mode SIMULATION uniquement (paper trading)
- 📚 À des fins ÉDUCATIVES
- ⚡ Ne jamais trader de l'argent réel sans tests extensifs
- 🧪 Toujours tester pendant plusieurs mois en simulation

## 🐛 Dépannage

### Le système ne démarre pas

```bash
# Vérifier que Docker est lancé
docker ps

# Redémarrer les services
docker-compose down
docker-compose up -d
```

### Pas de données

```bash
# Vérifier Redis
redis-cli ping
# Doit retourner: PONG

# Vérifier PostgreSQL
docker exec -it nexus_db psql -U postgres -c "SELECT 1"
```

### Modèle IA absent

```bash
cd ai
python train_model.py
```

### Port 8080 déjà utilisé

Changez le port dans `cmd/main.go`:
```go
const WEB_PORT = "8081"  // Au lieu de 8080
```

## 📞 Besoin d'Aide ?

- 📖 README complet: `README.md`
- 🚀 Déploiement: `DEPLOYMENT.md`
- 🤝 Contribution: `CONTRIBUTING.md`
- 🐛 Issues GitHub: [lien vers votre repo]

## 🎉 C'est Parti !

Une fois lancé, vous devriez voir:

```
╔═══════════════════════════════════════════════════════════════╗
║                    NEXUS TRADE v1.0                           ║
╚═══════════════════════════════════════════════════════════════╝

✅ SYSTÈME OPÉRATIONNEL

🤖 Modules actifs:
   [✓] Observateur    - Ingestion de données Binance
   [✓] Analyste       - Prédictions IA toutes les minutes
   [✓] Trader         - Exécution automatique des ordres
   [✓] Notaire        - Audit blockchain sur Sepolia
   [✓] Dashboard      - Interface web en temps réel

🌐 Dashboard: http://localhost:8080
```

**Bon trading ! 🚀💰**
