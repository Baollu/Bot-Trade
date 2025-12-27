.PHONY: help install train run docker-up docker-down clean test

# Variables
GO := go
PYTHON := python3
DOCKER_COMPOSE := docker-compose

help: ## Affiche l'aide
	@echo "Nexus Trade - Commandes disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Installe toutes les dépendances
	@echo "📦 Installation des dépendances Python..."
	cd ai && $(PYTHON) -m pip install -r requirements.txt
	@echo "📦 Installation des dépendances Go..."
	$(GO) mod download
	@echo "✅ Installation terminée"

train: ## Entraîne le modèle IA
	@echo "🤖 Entraînement du modèle IA..."
	cd ai && $(PYTHON) train_model.py
	@echo "✅ Modèle entraîné et exporté"

test-inference: ## Teste l'inférence ONNX
	@echo "🧪 Test d'inférence..."
	cd ai && $(PYTHON) test_inference.py

docker-up: ## Démarre les services Docker (PostgreSQL, Redis)
	@echo "🐳 Démarrage des services Docker..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Services démarrés"
	@echo "   PostgreSQL: localhost:5433"
	@echo "   Redis: localhost:6379"

docker-down: ## Arrête les services Docker
	@echo "🐳 Arrêt des services Docker..."
	$(DOCKER_COMPOSE) down
	@echo "✅ Services arrêtés"

docker-logs: ## Affiche les logs Docker
	$(DOCKER_COMPOSE) logs -f

setup: docker-up install train ## Configuration complète du projet
	@echo ""
	@echo "✅ Configuration terminée!"
	@echo ""
	@echo "Prochaines étapes:"
	@echo "  1. Copiez .env.example vers .env"
	@echo "  2. Configurez vos variables d'environnement"
	@echo "  3. Lancez avec: make run"

run: ## Lance le système
	@echo "🚀 Démarrage de Nexus Trade..."
	$(GO) run cmd/main.go

build: ## Compile l'application
	@echo "🔨 Compilation de l'application..."
	$(GO) build -o bin/nexus-trade cmd/main.go
	@echo "✅ Binaire créé: bin/nexus-trade"

clean: ## Nettoie les fichiers générés
	@echo "🧹 Nettoyage..."
	rm -rf bin/
	rm -rf db/
	rm -f ai/crypto_predictor.onnx
	rm -f ai/model_metadata.json
	rm -f ai/best_model.h5
	@echo "✅ Nettoyage terminé"

clean-db: ## Réinitialise la base de données
	@echo "🗑️  Réinitialisation de la base de données..."
	$(DOCKER_COMPOSE) down -v
	rm -rf db/
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Base de données réinitialisée"

test: ## Lance les tests
	@echo "🧪 Lancement des tests..."
	$(GO) test ./...

fmt: ## Formate le code Go
	@echo "🎨 Formatage du code..."
	$(GO) fmt ./...

lint: ## Vérifie le code
	@echo "🔍 Vérification du code..."
	golangci-lint run

deps-update: ## Met à jour les dépendances
	@echo "⬆️  Mise à jour des dépendances..."
	$(GO) get -u ./...
	$(GO) mod tidy
	cd ai && $(PYTHON) -m pip install --upgrade -r requirements.txt

dev: docker-up ## Mode développement (avec auto-reload)
	@echo "🔧 Mode développement..."
	@echo "Utilisez 'air' pour le hot-reload ou lancez manuellement avec 'make run'"
	$(GO) run cmd/main.go

stats: ## Affiche les statistiques du projet
	@echo "📊 Statistiques du projet:"
	@echo "  Lignes de code Go:"
	@find . -name '*.go' -not -path './vendor/*' | xargs wc -l | tail -1
	@echo "  Lignes de code Python:"
	@find ./ai -name '*.py' | xargs wc -l | tail -1
	@echo "  Nombre de fichiers Go:"
	@find . -name '*.go' -not -path './vendor/*' | wc -l
	@echo "  Nombre de fichiers Python:"
	@find ./ai -name '*.py' | wc -l
