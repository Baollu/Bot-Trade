package main

import (
	"bot-trade/internal/analyzer"
	"bot-trade/internal/blockchain"
	"bot-trade/internal/database"
	"bot-trade/internal/ingestion/binance"
	"bot-trade/internal/ingestion/redis"
	"bot-trade/internal/trader"
	"bot-trade/internal/web"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/joho/godotenv"
)

const (
	INITIAL_BALANCE = 10000.0 // Balance initiale en USD
	WEB_PORT        = "8080"
)

// CryptoConfig représente la configuration pour une crypto
type CryptoConfig struct {
	Symbol         string
	InitialBalance float64
}

// Cryptos à trader (tu peux en ajouter autant que tu veux !)
var CRYPTOS = []CryptoConfig{
	{Symbol: "btcusdt", InitialBalance: 5000.0},   // Bitcoin
	{Symbol: "ethusdt", InitialBalance: 3000.0},   // Ethereum
	{Symbol: "solusdt", InitialBalance: 1000.0},   // Solana
	{Symbol: "adausdt", InitialBalance: 500.0},    // Cardano
	{Symbol: "dogeusdt", InitialBalance: 500.0},   // Dogecoin
}

// TradingSystem représente un système de trading pour une crypto
type TradingSystem struct {
	Symbol         string
	Analyzer       *analyzer.AIAnalyzer
	TradingEngine  *trader.TradingEngine
	PriceChan      chan float64
	PredictionChan chan *analyzer.Prediction
}

func main() {
	fmt.Println(banner())
	log.Println("🚀 Démarrage de Nexus Trade - MULTI-CRYPTO EDITION...")

	// Chargement des variables d'environnement
	if err := godotenv.Load(); err != nil {
		log.Println("⚠️ Fichier .env non trouvé, utilisation des variables système")
	}

	// 1. Initialisation de Redis
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("MODULE A: L'OBSERVATEUR (Data Ingestion)")
	log.Println(strings.Repeat("=", 60))
	
	redis.InitRedis()

	// 2. Connexion à PostgreSQL
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("INITIALISATION - Base de Données")
	log.Println(strings.Repeat("=", 60))
	
	db, err := database.NewPostgresDB()
	if err != nil {
		log.Fatalf("❌ Erreur connexion PostgreSQL: %v", err)
	}
	defer db.Close()

	// Création/récupération d'un utilisateur demo
	user, err := db.GetOrCreateUser("demo@nexustrade.com")
	if err != nil {
		log.Fatalf("❌ Erreur utilisateur: %v", err)
	}
	log.Printf("👤 Utilisateur: %s (ID: %d)", user.Email, user.ID)

	// 3. Initialisation de la Blockchain
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("MODULE D: LE NOTAIRE (Web3 Audit)")
	log.Println(strings.Repeat("=", 60))
	
	bc, err := blockchain.NewBlockchainAuditor()
	if err != nil {
		log.Fatalf("❌ Erreur blockchain: %v", err)
	}
	defer bc.Close()

	// 4. Initialisation des systèmes de trading pour chaque crypto
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("INITIALISATION - SYSTÈMES MULTI-CRYPTO")
	log.Println(strings.Repeat("=", 60))

	var tradingSystems []*TradingSystem
	var wg sync.WaitGroup

	for _, crypto := range CRYPTOS {
		log.Printf("\n🪙 Configuration: %s (Balance: $%.2f)", 
			strings.ToUpper(crypto.Symbol), crypto.InitialBalance)

		// Canaux de communication
		priceChan := make(chan float64, 100)
		predictionChan := make(chan *analyzer.Prediction, 10)

		// Analyseur IA
		aiAnalyzer, err := analyzer.NewAIAnalyzer(redis.Client, crypto.Symbol)
		if err != nil {
			log.Printf("⚠️ Erreur analyseur IA pour %s: %v", crypto.Symbol, err)
			continue
		}

		// Moteur de trading
		tradingEngine := trader.NewTradingEngine(
			user.ID,
			crypto.InitialBalance,
			db,
			bc,
			strings.ToUpper(crypto.Symbol),
		)

		// Sauvegarde du système
		tradingSystems = append(tradingSystems, &TradingSystem{
			Symbol:         crypto.Symbol,
			Analyzer:       aiAnalyzer,
			TradingEngine:  tradingEngine,
			PriceChan:      priceChan,
			PredictionChan: predictionChan,
		})

		log.Printf("✅ Système configuré pour %s", strings.ToUpper(crypto.Symbol))
	}

	// 5. Initialisation du Serveur Web
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("INTERFACE - Dashboard Web Multi-Crypto")
	log.Println(strings.Repeat("=", 60))
	
	// On va agréger tous les systèmes pour le dashboard
	// (pour l'instant on utilise le premier, mais tu peux étendre)
	webServer := web.NewServer(WEB_PORT, db, redis.Client, tradingSystems[0].TradingEngine)

	// 6. Démarrage des goroutines pour chaque crypto
	log.Println("\n" + strings.Repeat("=", 60))
	log.Println("DÉMARRAGE DES SYSTÈMES DE TRADING")
	log.Println(strings.Repeat("=", 60))

	for _, system := range tradingSystems {
		wg.Add(1)
		
		// Lancement du système dans une goroutine
		go func(sys *TradingSystem) {
			defer wg.Done()
			
			log.Printf("🚀 Démarrage du système pour %s", strings.ToUpper(sys.Symbol))

			// Ingestion Binance
			go binance.ConnectBinance(sys.PriceChan, sys.Symbol)
			time.Sleep(1 * time.Second)

			// Analyse IA toutes les minutes
			go sys.Analyzer.RunAnalysisLoop(sys.PredictionChan)

			// Moteur de trading
			go sys.TradingEngine.RunTradingLoop(sys.PredictionChan, sys.PriceChan)

			// Mise à jour du serveur web (seulement pour le premier système pour l'instant)
			// TODO: Étendre le dashboard pour afficher toutes les cryptos
			if sys.Symbol == tradingSystems[0].Symbol {
				go webServer.RunUpdateLoop(sys.PriceChan, sys.PredictionChan)
			}
		}(system)
	}

	// 7. Serveur web
	go func() {
		if err := webServer.Start(); err != nil {
			log.Fatalf("❌ Erreur serveur web: %v", err)
		}
	}()

	// Affichage du résumé de démarrage
	time.Sleep(3 * time.Second)
	printMultiCryptoSummary(tradingSystems)

	// 8. Gestion de l'arrêt gracieux
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	<-sigChan
	log.Println("\n\n🛑 Arrêt du système...")

	// Affichage du résumé final pour chaque crypto
	for _, system := range tradingSystems {
		var currentPrice float64
		select {
		case currentPrice = <-system.PriceChan:
		default:
			currentPrice = 0
		}

		if currentPrice > 0 {
			log.Printf("\n📊 Performance %s:", strings.ToUpper(system.Symbol))
			system.TradingEngine.PrintSummary(currentPrice)
		}
	}

	log.Println("✅ Nexus Trade arrêté proprement")
}

func banner() string {
	return `
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║    ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗             ║
║    ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝             ║
║    ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗             ║
║    ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║             ║
║    ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║             ║
║    ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝             ║
║                                                               ║
║         ████████╗██████╗  █████╗ ██████╗ ███████╗           ║
║         ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝           ║
║            ██║   ██████╔╝███████║██║  ██║█████╗             ║
║            ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝             ║
║            ██║   ██║  ██║██║  ██║██████╔╝███████╗           ║
║            ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝           ║
║                                                               ║
║     Système Multi-Crypto propulsé par IA v2.0                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
`
}

func printMultiCryptoSummary(systems []*TradingSystem) {
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("✅ SYSTÈME MULTI-CRYPTO OPÉRATIONNEL")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println()
	fmt.Printf("🪙 Cryptomonnaies tradées: %d\n", len(systems))
	fmt.Println()
	
	for i, sys := range systems {
		portfolio := sys.TradingEngine.GetPortfolio()
		fmt.Printf("  %d. %s - Balance initiale: $%.2f\n", 
			i+1, strings.ToUpper(sys.Symbol), portfolio.InitialBalance)
	}
	
	fmt.Println()
	fmt.Println("🤖 Modules actifs (par crypto):")
	fmt.Println("   [✓] Observateur    - Ingestion données Binance")
	fmt.Println("   [✓] Analyste       - Prédictions IA/minute")
	fmt.Println("   [✓] Trader         - Exécution auto ordres")
	fmt.Println("   [✓] Notaire        - Audit blockchain Sepolia")
	fmt.Println()
	fmt.Println("🌐 Accès au Dashboard:")
	fmt.Println("   → http://localhost:" + WEB_PORT)
	fmt.Println()
	fmt.Println("📊 Capital total investi:")
	total := 0.0
	for _, sys := range systems {
		total += sys.TradingEngine.GetPortfolio().InitialBalance
	}
	fmt.Printf("   → $%.2f USD\n", total)
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("Appuyez sur Ctrl+C pour arrêter le système")
	fmt.Println(strings.Repeat("=", 60))
}
