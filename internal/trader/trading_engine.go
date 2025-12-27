package trader

import (
	"bot-trade/internal/analyzer"
	"bot-trade/internal/blockchain"
	"bot-trade/internal/database"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"
)

// TradeType représente le type d'ordre
type TradeType string

const (
	BUY  TradeType = "BUY"
	SELL TradeType = "SELL"
	HOLD TradeType = "HOLD"
)

// Trade représente une transaction
type Trade struct {
	ID             int       `json:"id"`
	UserID         int       `json:"user_id"`
	Symbol         string    `json:"symbol"`
	Type           TradeType `json:"type"`
	Price          float64   `json:"price"`
	Quantity       float64   `json:"quantity"`
	Profit         float64   `json:"profit"`
	BlockchainHash string    `json:"blockchain_hash"`
	ExecutedAt     time.Time `json:"executed_at"`
	PredictionConf float64   `json:"prediction_confidence"`
}

// Portfolio représente le portefeuille de trading
type Portfolio struct {
	UserID         int       `json:"user_id"`
	Balance        float64   `json:"balance"`         // Solde en USD
	BTCHolding     float64   `json:"btc_holding"`     // Quantité de BTC détenue
	InitialBalance float64   `json:"initial_balance"` // Solde initial
	TotalProfit    float64   `json:"total_profit"`    // Profit/Perte total
	TradeCount     int       `json:"trade_count"`     // Nombre de trades
	WinRate        float64   `json:"win_rate"`        // Taux de réussite
	LastTradeAt    time.Time `json:"last_trade_at"`   // Dernier trade
	mu             sync.RWMutex
}

// TradingEngine gère l'exécution des trades
type TradingEngine struct {
	portfolio   *Portfolio
	db          *database.PostgresDB
	blockchain  *blockchain.BlockchainAuditor
	tradesChan  chan *Trade
	minConfidence float64 // Confiance minimum pour trader
	minChange     float64 // Changement minimum requis (%)
	symbol        string
}

// NewTradingEngine crée une nouvelle instance du moteur de trading
func NewTradingEngine(
	userID int,
	initialBalance float64,
	db *database.PostgresDB,
	bc *blockchain.BlockchainAuditor,
	symbol string,
) *TradingEngine {
	portfolio := &Portfolio{
		UserID:         userID,
		Balance:        initialBalance,
		BTCHolding:     0.0,
		InitialBalance: initialBalance,
		TotalProfit:    0.0,
		TradeCount:     0,
		WinRate:        0.0,
	}

	return &TradingEngine{
		portfolio:     portfolio,
		db:            db,
		blockchain:    bc,
		tradesChan:    make(chan *Trade, 100),
		minConfidence: 0.65, // 65% de confiance minimum
		minChange:     1.0,  // 1% de changement minimum
		symbol:        symbol,
	}
}

// ProcessPrediction traite une prédiction de l'IA et décide d'un trade
func (te *TradingEngine) ProcessPrediction(pred *analyzer.Prediction, currentPrice float64) {
	te.portfolio.mu.Lock()
	defer te.portfolio.mu.Unlock()

	log.Printf("📊 Traitement prédiction: %s (conf: %.2f%%, prix: $%.2f)",
		pred.Class, pred.Confidence*100, currentPrice)

	// Vérifie si la confiance est suffisante
	if pred.Confidence < te.minConfidence {
		log.Printf("⏭️  Confiance trop faible (%.2f%% < %.2f%%), HOLD",
			pred.Confidence*100, te.minConfidence*100)
		return
	}

	var trade *Trade

	switch pred.Class {
	case "UP":
		// Signal d'achat: acheter si on a du cash et pas de BTC
		probUp := pred.Probabilities["UP"]
		if probUp > te.minConfidence && te.portfolio.Balance > 0 && te.portfolio.BTCHolding == 0 {
			trade = te.executeBuy(currentPrice, pred.Confidence)
		}

	case "DOWN":
		// Signal de vente: vendre si on a du BTC
		probDown := pred.Probabilities["DOWN"]
		if probDown > te.minConfidence && te.portfolio.BTCHolding > 0 {
			trade = te.executeSell(currentPrice, pred.Confidence)
		}

	case "NEUTRAL":
		// Ne rien faire
		log.Println("➖ Signal NEUTRAL - HOLD")
		return
	}

	// Si un trade a été exécuté
	if trade != nil {
		// Sauvegarde en base de données
		if err := te.db.SaveTrade(trade); err != nil {
			log.Printf("❌ Erreur sauvegarde trade: %v", err)
		}

		// Envoi pour audit blockchain (asynchrone)
		go te.auditTradeOnBlockchain(trade)

		// Envoi dans le canal pour le dashboard
		select {
		case te.tradesChan <- trade:
		default:
			log.Println("⚠️ Canal de trades plein")
		}
	}
}

// executeBuy exécute un ordre d'achat
func (te *TradingEngine) executeBuy(price, confidence float64) *Trade {
	// Calcul de la quantité à acheter (utilise 95% du solde pour garder une marge)
	amountToInvest := te.portfolio.Balance * 0.95
	quantity := amountToInvest / price

	trade := &Trade{
		UserID:         te.portfolio.UserID,
		Symbol:         te.symbol,
		Type:           BUY,
		Price:          price,
		Quantity:       quantity,
		Profit:         0.0,
		ExecutedAt:     time.Now(),
		PredictionConf: confidence,
	}

	// Mise à jour du portefeuille
	te.portfolio.Balance -= amountToInvest
	te.portfolio.BTCHolding += quantity
	te.portfolio.TradeCount++
	te.portfolio.LastTradeAt = time.Now()

	log.Printf("💰 BUY: %.6f BTC @ $%.2f (total: $%.2f)",
		quantity, price, amountToInvest)
	log.Printf("   Portefeuille: $%.2f USD + %.6f BTC",
		te.portfolio.Balance, te.portfolio.BTCHolding)

	return trade
}

// executeSell exécute un ordre de vente
func (te *TradingEngine) executeSell(price, confidence float64) *Trade {
	// Vend tout le BTC détenu
	quantity := te.portfolio.BTCHolding
	saleAmount := quantity * price

	// Calcul du profit (différence avec le dernier achat)
	lastBuyPrice := te.getLastBuyPrice()
	profit := (price - lastBuyPrice) * quantity

	trade := &Trade{
		UserID:         te.portfolio.UserID,
		Symbol:         te.symbol,
		Type:           SELL,
		Price:          price,
		Quantity:       quantity,
		Profit:         profit,
		ExecutedAt:     time.Now(),
		PredictionConf: confidence,
	}

	// Mise à jour du portefeuille
	te.portfolio.Balance += saleAmount
	te.portfolio.BTCHolding = 0.0
	te.portfolio.TotalProfit += profit
	te.portfolio.TradeCount++
	te.portfolio.LastTradeAt = time.Now()

	// Mise à jour du taux de réussite
	te.updateWinRate(profit > 0)

	log.Printf("💵 SELL: %.6f BTC @ $%.2f (total: $%.2f)",
		quantity, price, saleAmount)
	log.Printf("   Profit: $%.2f | Total: $%.2f",
		profit, te.portfolio.TotalProfit)
	log.Printf("   Portefeuille: $%.2f USD + %.6f BTC",
		te.portfolio.Balance, te.portfolio.BTCHolding)

	return trade
}

// getLastBuyPrice récupère le prix du dernier achat depuis la DB
func (te *TradingEngine) getLastBuyPrice() float64 {
	lastTrade, err := te.db.GetLastTradeByType(te.portfolio.UserID, "BUY")
	if err != nil || lastTrade == nil {
		return 0.0
	}
	return lastTrade.Price
}

// updateWinRate met à jour le taux de réussite
func (te *TradingEngine) updateWinRate(isWin bool) {
	// Cette fonction devrait compter les trades gagnants vs perdants
	// Pour simplifier, on fait une estimation
	wins, err := te.db.CountWinningTrades(te.portfolio.UserID)
	if err != nil {
		return
	}

	if te.portfolio.TradeCount > 0 {
		te.portfolio.WinRate = float64(wins) / float64(te.portfolio.TradeCount)
	}
}

// auditTradeOnBlockchain enregistre le trade sur la blockchain
func (te *TradingEngine) auditTradeOnBlockchain(trade *Trade) {
	hash, err := te.blockchain.RecordTrade(trade)
	if err != nil {
		log.Printf("❌ Erreur audit blockchain: %v", err)
		return
	}

	trade.BlockchainHash = hash

	// Mise à jour en DB avec le hash
	if err := te.db.UpdateTradeBlockchainHash(trade.ID, hash); err != nil {
		log.Printf("❌ Erreur mise à jour hash: %v", err)
	}

	log.Printf("⛓️  Trade audité sur blockchain: %s", hash)
}

// GetPortfolio retourne l'état actuel du portefeuille
func (te *TradingEngine) GetPortfolio() *Portfolio {
	te.portfolio.mu.RLock()
	defer te.portfolio.mu.RUnlock()

	// Copie du portefeuille pour éviter les race conditions
	p := &Portfolio{
		UserID:         te.portfolio.UserID,
		Balance:        te.portfolio.Balance,
		BTCHolding:     te.portfolio.BTCHolding,
		InitialBalance: te.portfolio.InitialBalance,
		TotalProfit:    te.portfolio.TotalProfit,
		TradeCount:     te.portfolio.TradeCount,
		WinRate:        te.portfolio.WinRate,
		LastTradeAt:    te.portfolio.LastTradeAt,
	}

	return p
}

// GetPortfolioValue calcule la valeur totale du portefeuille
func (te *TradingEngine) GetPortfolioValue(currentPrice float64) float64 {
	te.portfolio.mu.RLock()
	defer te.portfolio.mu.RUnlock()

	return te.portfolio.Balance + (te.portfolio.BTCHolding * currentPrice)
}

// GetPerformance calcule la performance en %
func (te *TradingEngine) GetPerformance(currentPrice float64) float64 {
	te.portfolio.mu.RLock()
	defer te.portfolio.mu.RUnlock()

	currentValue := te.GetPortfolioValue(currentPrice)
	if te.portfolio.InitialBalance == 0 {
		return 0.0
	}

	return ((currentValue - te.portfolio.InitialBalance) / te.portfolio.InitialBalance) * 100
}

// RunTradingLoop lance la boucle de trading
func (te *TradingEngine) RunTradingLoop(predictionChan <-chan *analyzer.Prediction, priceChan <-chan float64) {
	log.Println("💹 Moteur de trading démarré")
	log.Printf("   Solde initial: $%.2f", te.portfolio.InitialBalance)
	log.Printf("   Confiance min: %.0f%%", te.minConfidence*100)
	log.Printf("   Changement min: %.1f%%", te.minChange)

	var currentPrice float64

	for {
		select {
		case price := <-priceChan:
			currentPrice = price

		case prediction := <-predictionChan:
			if currentPrice > 0 {
				te.ProcessPrediction(prediction, currentPrice)
			}
		}
	}
}

// GetTradesChannel retourne le canal des trades
func (te *TradingEngine) GetTradesChannel() <-chan *Trade {
	return te.tradesChan
}

// PrintSummary affiche un résumé de performance
func (te *TradingEngine) PrintSummary(currentPrice float64) {
	te.portfolio.mu.RLock()
	defer te.portfolio.mu.RUnlock()

	currentValue := te.GetPortfolioValue(currentPrice)
	performance := te.GetPerformance(currentPrice)

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("📊 RÉSUMÉ DE PERFORMANCE")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Printf("Solde initial:     $%.2f\n", te.portfolio.InitialBalance)
	fmt.Printf("Valeur actuelle:   $%.2f\n", currentValue)
	fmt.Printf("Profit/Perte:      $%.2f (%.2f%%)\n", currentValue-te.portfolio.InitialBalance, performance)
	fmt.Printf("Nombre de trades:  %d\n", te.portfolio.TradeCount)
	fmt.Printf("Taux de réussite:  %.1f%%\n", te.portfolio.WinRate*100)
	fmt.Printf("Position actuelle: $%.2f USD + %.6f BTC\n", te.portfolio.Balance, te.portfolio.BTCHolding)
	fmt.Println(strings.Repeat("=", 60))
}
