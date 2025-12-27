package web

import (
	"bot-trade/internal/analyzer"
	"bot-trade/internal/database"
	"bot-trade/internal/trader"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

// Server représente le serveur web
type Server struct {
	port           string
	db             *database.PostgresDB
	redis          *redis.Client
	tradingEngine  *trader.TradingEngine
	currentPrice   float64
	lastPrediction *analyzer.Prediction
	mu             sync.RWMutex
	templates      *template.Template
}

// DashboardData représente les données pour le dashboard
type DashboardData struct {
	CurrentPrice   float64                   `json:"current_price"`
	LastPrediction *analyzer.Prediction      `json:"last_prediction"`
	Portfolio      *trader.Portfolio         `json:"portfolio"`
	PortfolioValue float64                   `json:"portfolio_value"`
	Performance    float64                   `json:"performance"`
	RecentTrades   []*database.Trade         `json:"recent_trades"`
	Stats          *database.Stats           `json:"stats"`
	Timestamp      time.Time                 `json:"timestamp"`
}

// NewServer crée une nouvelle instance du serveur web
func NewServer(
	port string,
	db *database.PostgresDB,
	redis *redis.Client,
	tradingEngine *trader.TradingEngine,
) *Server {
	// Chargement des templates HTML
	templates := template.Must(template.ParseGlob("web/templates/*.html"))

	return &Server{
		port:          port,
		db:            db,
		redis:         redis,
		tradingEngine: tradingEngine,
		templates:     templates,
	}
}

// UpdatePrice met à jour le prix actuel
func (s *Server) UpdatePrice(price float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.currentPrice = price
}

// UpdatePrediction met à jour la dernière prédiction
func (s *Server) UpdatePrediction(pred *analyzer.Prediction) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.lastPrediction = pred
}

// Start démarre le serveur web
func (s *Server) Start() error {
	// Routes API
	http.HandleFunc("/api/dashboard", s.handleGetDashboard)
	http.HandleFunc("/api/price", s.handleGetPrice)
	http.HandleFunc("/api/prediction", s.handleGetPrediction)
	http.HandleFunc("/api/portfolio", s.handleGetPortfolio)
	http.HandleFunc("/api/trades", s.handleGetTrades)
	http.HandleFunc("/api/stats", s.handleGetStats)

	// Routes HTML
	http.HandleFunc("/", s.handleDashboardPage)
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("web/static"))))

	// Health check
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	addr := ":" + s.port
	log.Printf("🌐 Serveur web démarré sur http://localhost%s", addr)
	log.Printf("   Dashboard: http://localhost%s/", addr)
	log.Printf("   API: http://localhost%s/api/dashboard", addr)

	return http.ListenAndServe(addr, nil)
}

// handleDashboardPage affiche le dashboard HTML
func (s *Server) handleDashboardPage(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// Récupération des données
	data := s.getDashboardData()

	// Rendu du template
	err := s.templates.ExecuteTemplate(w, "dashboard.html", data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}

// handleGetDashboard retourne toutes les données du dashboard en JSON
func (s *Server) handleGetDashboard(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	data := s.getDashboardData()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// getDashboardData récupère toutes les données du dashboard
func (s *Server) getDashboardData() *DashboardData {
	portfolio := s.tradingEngine.GetPortfolio()
	portfolioValue := s.tradingEngine.GetPortfolioValue(s.currentPrice)
	performance := s.tradingEngine.GetPerformance(s.currentPrice)

	// Récupération des derniers trades
	recentTrades, _ := s.db.GetRecentTrades(portfolio.UserID, 10)

	// Statistiques
	stats, _ := s.db.GetUserStats(portfolio.UserID)

	return &DashboardData{
		CurrentPrice:   s.currentPrice,
		LastPrediction: s.lastPrediction,
		Portfolio:      portfolio,
		PortfolioValue: portfolioValue,
		Performance:    performance,
		RecentTrades:   recentTrades,
		Stats:          stats,
		Timestamp:      time.Now(),
	}
}

// handleGetPrice retourne le prix actuel
func (s *Server) handleGetPrice(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	response := map[string]interface{}{
		"price":     s.currentPrice,
		"timestamp": time.Now(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetPrediction retourne la dernière prédiction
func (s *Server) handleGetPrediction(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.lastPrediction == nil {
		http.Error(w, "Aucune prédiction disponible", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.lastPrediction)
}

// handleGetPortfolio retourne l'état du portefeuille
func (s *Server) handleGetPortfolio(w http.ResponseWriter, r *http.Request) {
	portfolio := s.tradingEngine.GetPortfolio()
	portfolioValue := s.tradingEngine.GetPortfolioValue(s.currentPrice)
	performance := s.tradingEngine.GetPerformance(s.currentPrice)

	response := map[string]interface{}{
		"portfolio":       portfolio,
		"portfolio_value": portfolioValue,
		"performance":     performance,
		"current_price":   s.currentPrice,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetTrades retourne les derniers trades
func (s *Server) handleGetTrades(w http.ResponseWriter, r *http.Request) {
	portfolio := s.tradingEngine.GetPortfolio()
	trades, err := s.db.GetRecentTrades(portfolio.UserID, 20)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(trades)
}

// handleGetStats retourne les statistiques
func (s *Server) handleGetStats(w http.ResponseWriter, r *http.Request) {
	portfolio := s.tradingEngine.GetPortfolio()
	stats, err := s.db.GetUserStats(portfolio.UserID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// RunUpdateLoop lance la boucle de mise à jour des données
func (s *Server) RunUpdateLoop(priceChan <-chan float64, predictionChan <-chan *analyzer.Prediction) {
	log.Println("🔄 Boucle de mise à jour du serveur démarrée")

	for {
		select {
		case price := <-priceChan:
			s.UpdatePrice(price)

		case prediction := <-predictionChan:
			s.UpdatePrediction(prediction)
			
			// Sauvegarde la prédiction en DB
			portfolio := s.tradingEngine.GetPortfolio()
			_ = s.db.SaveAIPrediction("BTCUSDT", prediction.Class, prediction.Confidence)
		}
	}
}
