# 🤖 Nexus Trade - Système de Trading Autonome IA + Blockchain

![Version](https://img.shields.io/badge/version-1.0-blue)
![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)

Un système de trading automatisé complet utilisant l'Intelligence Artificielle pour prédire les mouvements de prix du Bitcoin et la Blockchain Ethereum pour garantir la transparence des transactions.

## 📋 Table des Matières

- [Caractéristiques](#-caractéristiques)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Configuration Blockchain](#-configuration-blockchain-optionnelle)
- [Structure du Projet](#-structure-du-projet)
- [Technologies](#-technologies)
- [Performance](#-performance)
- [Licence](#-licence)

## ✨ Caractéristiques

### 🎯 Les 4 Modules Fonctionnels

1. **Module A : L'Observateur** (Data Ingestion)
   - Connexion WebSocket temps réel à Binance
   - Capture des prix Bitcoin seconde par seconde
   - Stockage dans Redis (hot storage) et PostgreSQL (cold storage)

2. **Module B : L'Analyste** (AI Prediction)
   - Modèle GRU (Gated Recurrent Unit) entraîné sur données historiques
   - 30+ indicateurs techniques (RSI, MACD, Bollinger, ATR...)
   - Prédictions toutes les minutes avec <100ms de latence
   - Export ONNX pour inférence ultra-rapide

3. **Module C : Le Trader** (Execution Engine)
   - Décisions automatiques basées sur les prédictions IA
   - Gestion de portefeuille avec calcul P&L
   - Exécution simulée (paper trading) pour tests sans risque

4. **Module D : Le Notaire** (Web3 Audit)
   - Enregistrement de chaque trade sur Ethereum Sepolia
   - Hash cryptographique immuable
   - Traçabilité complète sur blockchain publique

### 🎨 Interface Utilisateur

- Dashboard web temps réel
- Graphiques de performance
- Historique des trades
- Liens vers Etherscan pour vérification blockchain

## 🏗 Architecture

```
┌─────────────────┐
│   BINANCE API   │ WebSocket
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  OBSERVATEUR    │─────▶│    REDIS     │
│   (Go)          │      │ (Hot Storage)│
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   ANALYSTE IA   │─────▶│  POSTGRESQL  │
│(Python→ONNX→Go) │      │(Cold Storage)│
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│     TRADER      │
│   (Go Engine)   │
└────────┬────────┘
         │
         ├─────────────────────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐         ┌──────────────────┐
│   BLOCKCHAIN    │         │   WEB DASHBOARD  │
│ (Sepolia Audit) │         │   (HTTP Server)  │
└─────────────────┘         └──────────────────┘
```

## 📦 Prérequis

### Logiciels Requis

- **Go** 1.21 ou supérieur
- **Python** 3.8 ou supérieur
- **Docker** & Docker Compose
- **Git**

### Services Externes

- Compte Binance (gratuit, pour les données de marché)
- (Optionnel) Compte Alchemy.com pour blockchain Sepolia

## 🚀 Installation

### 1. Cloner le Projet

```bash
git clone https://github.com/your-username/nexus-trade.git
cd nexus-trade
```

### 2. Installer les Dépendances Python

```bash
cd ai
pip install -r requirements.txt
```

### 3. Installer les Dépendances Go

```bash
go mod download
```

### 4. Démarrer les Services (Docker)

```bash
docker-compose up -d
```

Cela démarre:
- PostgreSQL (port 5433)
- Redis (port 6379)

### 5. Configurer les Variables d'Environnement

```bash
cp .env.example .env
# Éditez .env avec vos paramètres
```

### 6. Entraîner le Modèle IA

```bash
cd ai
python train_model.py
```

Cela va:
- Télécharger 30 jours de données historiques Bitcoin
- Créer 30+ features techniques
- Entraîner un modèle GRU
- Exporter en format ONNX

⏱️ Durée estimée: 10-20 minutes selon votre machine

### 7. Lancer le Système

```bash
go run cmd/main.go
```

## 💻 Utilisation

### Dashboard Web

Ouvrez votre navigateur et accédez à:
```
http://localhost:8080
```

Vous verrez:
- Prix Bitcoin en temps réel
- Dernière prédiction de l'IA
- État du portefeuille
- Historique des trades avec liens blockchain

### APIs Disponibles

```bash
# Données complètes du dashboard
curl http://localhost:8080/api/dashboard

# Prix actuel
curl http://localhost:8080/api/price

# Dernière prédiction
curl http://localhost:8080/api/prediction

# État du portefeuille
curl http://localhost:8080/api/portfolio

# Historique des trades
curl http://localhost:8080/api/trades

# Statistiques
curl http://localhost:8080/api/stats
```

## ⛓️ Configuration Blockchain (Optionnelle)

Pour activer l'audit blockchain réel sur Sepolia:

### 1. Créer un Compte Alchemy

1. Allez sur [alchemy.com](https://www.alchemy.com/)
2. Créez un compte gratuit
3. Créez une nouvelle app:
   - Network: Ethereum
   - Chain: Sepolia
4. Copiez l'URL HTTP

### 2. Obtenir une Clé Privée de Test

**⚠️ IMPORTANT: Utilisez uniquement un wallet de test!**

1. Installez MetaMask
2. Créez un nouveau wallet (pour tests uniquement!)
3. Basculez sur le réseau Sepolia
4. Exportez la clé privée (Settings → Security & Privacy → Reveal Private Key)

### 3. Obtenir du Sepolia ETH

1. Allez sur [sepoliafaucet.com](https://sepoliafaucet.com/)
2. Entrez votre adresse de wallet de test
3. Demandez du ETH gratuit

### 4. Configurer le .env

```bash
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
PRIVATE_KEY=your_private_key_without_0x
```

### 5. Vérifier sur Etherscan

Chaque trade sera visible sur:
```
https://sepolia.etherscan.io/tx/[TRANSACTION_HASH]
```

## 📁 Structure du Projet

```
nexus-trade/
├── ai/                          # Module Python IA
│   ├── train_model.py          # Entraînement du modèle GRU
│   ├── test_inference.py       # Test d'inférence ONNX
│   ├── requirements.txt        # Dépendances Python
│   ├── crypto_predictor.onnx   # Modèle exporté (généré)
│   └── model_metadata.json     # Métadonnées (généré)
├── cmd/
│   └── main.go                 # Point d'entrée principal
├── internal/
│   ├── analyzer/               # Module analyse IA
│   │   └── ai_analyzer.go
│   ├── blockchain/             # Module blockchain
│   │   └── auditor.go
│   ├── database/               # Module PostgreSQL
│   │   └── postgres.go
│   ├── ingestion/              # Module ingestion données
│   │   ├── binance/client.go
│   │   └── redis/client.go
│   ├── trader/                 # Module trading
│   │   └── trading_engine.go
│   └── web/                    # Module serveur web
│       └── server.go
├── web/
│   ├── templates/
│   │   └── dashboard.html
│   └── static/                 # Fichiers statiques (CSS/JS)
├── contracts/                  # Smart contracts (futur)
├── docker-compose.yml
├── go.mod
├── .env.example
└── README.md
```

## 🛠 Technologies

### Backend (Go)

- **Goroutines**: Concurrence native pour traiter millions de prix
- **WebSocket**: Connexion temps réel Binance
- **go-ethereum**: Interaction avec blockchain Ethereum
- **PostgreSQL**: Stockage relationnel des trades
- **Redis**: Cache ultra-rapide des prix récents

### IA (Python)

- **TensorFlow/Keras**: Entraînement modèle GRU
- **ONNX**: Format d'export pour inférence rapide
- **TA-Lib / ta**: Calcul indicateurs techniques
- **Pandas/NumPy**: Manipulation de données

### Blockchain

- **Ethereum Sepolia**: Testnet publique
- **Smart Contracts**: Enregistrement hash des trades
- **Etherscan**: Explorer blockchain

### Frontend

- **HTML/CSS/JS**: Dashboard responsive
- **API REST**: Communication backend
- **Auto-refresh**: Mise à jour temps réel

## 📊 Performance

### Métriques Clés

- **Latence IA**: <100ms (objectif atteint)
- **Précision modèle**: 55-70% (selon conditions de marché)
- **Throughput**: 1000+ prix/seconde gérés
- **Uptime**: 99%+ (avec reconnexion automatique)

### Optimisations

1. **ONNX Runtime**: Inférence 10x plus rapide que TensorFlow
2. **Redis**: Accès <1ms aux données récentes
3. **Goroutines**: Traitement parallèle des flux
4. **Connection Pooling**: PostgreSQL optimisé

## 🤝 Contribution

Les contributions sont les bienvenues! Pour contribuer:

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📜 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## ⚠️ Disclaimer

**Ce système est à des fins éducatives et de démonstration uniquement.**

- Ne tradez JAMAIS avec de l'argent réel sans compréhension complète
- Les performances passées ne garantissent pas les résultats futurs
- Le trading de cryptomonnaies comporte des risques importants
- Testez toujours en mode simulation (paper trading) d'abord

## 📞 Contact

Pour questions ou support:
- Issues GitHub: [github.com/your-username/nexus-trade/issues](https://github.com/your-username/nexus-trade/issues)
- Email: your.email@example.com

---

**Développé avec ❤️ par [Votre Nom]**

*Nexus Trade - Trading du futur, aujourd'hui.*
