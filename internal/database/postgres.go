package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	_ "github.com/lib/pq"
)

// PostgresDB gère la connexion et les requêtes PostgreSQL
type PostgresDB struct {
	db *sql.DB
}

// Trade représente un trade en base de données
type Trade struct {
	ID             int
	UserID         int
	Symbol         string
	Type           string
	Price          float64
	Quantity       float64
	Profit         float64
	BlockchainHash string
	ExecutedAt     time.Time
}

// User représente un utilisateur
type User struct {
	ID             int
	Email          string
	PasswordHash   string
	CurrentBalance float64
	CreatedAt      time.Time
}

// MarketData représente les données de marché
type MarketData struct {
	ID         int
	Symbol     string
	Price      float64
	CapturedAt time.Time
}

// AIPrediction représente une prédiction de l'IA
type AIPrediction struct {
	ID               int
	Symbol           string
	PredictedTrend   string
	ConfidenceScore  float64
	GeneratedAt      time.Time
}

// NewPostgresDB crée une nouvelle connexion à la base de données
func NewPostgresDB() (*PostgresDB, error) {
	// Récupération des variables d'environnement
	dbHost := getEnv("DB_HOST", "localhost")
	dbPort := getEnv("DB_PORT", "5433")
	dbUser := getEnv("DB_USER", "postgres")
	dbPassword := getEnv("DB_PASSWORD", "postgres")
	dbName := getEnv("DB_NAME", "nexus_trade_db")

	// Construction de la chaîne de connexion
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPassword, dbName)

	// Connexion à la base de données
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("erreur ouverture DB: %w", err)
	}

	// Test de la connexion
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("erreur connexion DB: %w", err)
	}

	// Configuration du pool de connexions
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	log.Printf("✅ Connecté à PostgreSQL: %s:%s/%s", dbHost, dbPort, dbName)

	return &PostgresDB{db: db}, nil
}

// getEnv récupère une variable d'environnement avec une valeur par défaut
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

// SaveTrade sauvegarde un trade en base de données
func (db *PostgresDB) SaveTrade(trade *Trade) error {
	query := `
		INSERT INTO trades (user_id, symbol, type, price, quantity, profit, blockchain_hash, executed_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id
	`

	err := db.db.QueryRow(
		query,
		trade.UserID,
		trade.Symbol,
		trade.Type,
		trade.Price,
		trade.Quantity,
		trade.Profit,
		trade.BlockchainHash,
		trade.ExecutedAt,
	).Scan(&trade.ID)

	if err != nil {
		return fmt.Errorf("erreur sauvegarde trade: %w", err)
	}

	log.Printf("💾 Trade sauvegardé en DB (ID: %d)", trade.ID)
	return nil
}

// UpdateTradeBlockchainHash met à jour le hash blockchain d'un trade
func (db *PostgresDB) UpdateTradeBlockchainHash(tradeID int, hash string) error {
	query := `UPDATE trades SET blockchain_hash = $1 WHERE id = $2`

	_, err := db.db.Exec(query, hash, tradeID)
	if err != nil {
		return fmt.Errorf("erreur mise à jour hash: %w", err)
	}

	return nil
}

// GetLastTradeByType récupère le dernier trade d'un type donné
func (db *PostgresDB) GetLastTradeByType(userID int, tradeType string) (*Trade, error) {
	query := `
		SELECT id, user_id, symbol, type, price, quantity, profit, blockchain_hash, executed_at
		FROM trades
		WHERE user_id = $1 AND type = $2
		ORDER BY executed_at DESC
		LIMIT 1
	`

	trade := &Trade{}
	err := db.db.QueryRow(query, userID, tradeType).Scan(
		&trade.ID,
		&trade.UserID,
		&trade.Symbol,
		&trade.Type,
		&trade.Price,
		&trade.Quantity,
		&trade.Profit,
		&trade.BlockchainHash,
		&trade.ExecutedAt,
	)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("erreur récupération trade: %w", err)
	}

	return trade, nil
}

// GetRecentTrades récupère les N derniers trades
func (db *PostgresDB) GetRecentTrades(userID int, limit int) ([]*Trade, error) {
	query := `
		SELECT id, user_id, symbol, type, price, quantity, profit, blockchain_hash, executed_at
		FROM trades
		WHERE user_id = $1
		ORDER BY executed_at DESC
		LIMIT $2
	`

	rows, err := db.db.Query(query, userID, limit)
	if err != nil {
		return nil, fmt.Errorf("erreur récupération trades: %w", err)
	}
	defer rows.Close()

	trades := make([]*Trade, 0)
	for rows.Next() {
		trade := &Trade{}
		err := rows.Scan(
			&trade.ID,
			&trade.UserID,
			&trade.Symbol,
			&trade.Type,
			&trade.Price,
			&trade.Quantity,
			&trade.Profit,
			&trade.BlockchainHash,
			&trade.ExecutedAt,
		)
		if err != nil {
			return nil, err
		}
		trades = append(trades, trade)
	}

	return trades, nil
}

// CountWinningTrades compte le nombre de trades gagnants
func (db *PostgresDB) CountWinningTrades(userID int) (int, error) {
	query := `SELECT COUNT(*) FROM trades WHERE user_id = $1 AND profit > 0`

	var count int
	err := db.db.QueryRow(query, userID).Scan(&count)
	if err != nil {
		return 0, err
	}

	return count, nil
}

// SaveMarketData sauvegarde des données de marché
func (db *PostgresDB) SaveMarketData(symbol string, price float64) error {
	query := `INSERT INTO market_data (symbol, price, captured_at) VALUES ($1, $2, $3)`

	_, err := db.db.Exec(query, symbol, price, time.Now())
	if err != nil {
		return fmt.Errorf("erreur sauvegarde market data: %w", err)
	}

	return nil
}

// SaveAIPrediction sauvegarde une prédiction de l'IA
func (db *PostgresDB) SaveAIPrediction(symbol, trend string, confidence float64) error {
	query := `
		INSERT INTO ai_predictions (symbol, predicted_trend, confidence_score, generated_at)
		VALUES ($1, $2, $3, $4)
	`

	_, err := db.db.Exec(query, symbol, trend, confidence, time.Now())
	if err != nil {
		return fmt.Errorf("erreur sauvegarde prédiction: %w", err)
	}

	return nil
}

// GetOrCreateUser récupère ou crée un utilisateur de démo
func (db *PostgresDB) GetOrCreateUser(email string) (*User, error) {
	// Vérifie si l'utilisateur existe
	query := `SELECT id, email, current_balance, created_at FROM users WHERE email = $1`

	user := &User{}
	err := db.db.QueryRow(query, email).Scan(
		&user.ID,
		&user.Email,
		&user.CurrentBalance,
		&user.CreatedAt,
	)

	if err == nil {
		return user, nil
	}

	if err != sql.ErrNoRows {
		return nil, fmt.Errorf("erreur récupération user: %w", err)
	}

	// Crée l'utilisateur s'il n'existe pas
	insertQuery := `
		INSERT INTO users (email, password_hash, current_balance, created_at)
		VALUES ($1, $2, $3, $4)
		RETURNING id
	`

	err = db.db.QueryRow(
		insertQuery,
		email,
		"demo_hash", // Hash temporaire pour la démo
		10000.0,     // Balance initiale de 10,000$
		time.Now(),
	).Scan(&user.ID)

	if err != nil {
		return nil, fmt.Errorf("erreur création user: %w", err)
	}

	user.Email = email
	user.CurrentBalance = 10000.0
	user.CreatedAt = time.Now()

	log.Printf("✅ Utilisateur créé: %s (ID: %d)", email, user.ID)

	return user, nil
}

// UpdateUserBalance met à jour le solde d'un utilisateur
func (db *PostgresDB) UpdateUserBalance(userID int, balance float64) error {
	query := `UPDATE users SET current_balance = $1 WHERE id = $2`

	_, err := db.db.Exec(query, balance, userID)
	if err != nil {
		return fmt.Errorf("erreur mise à jour balance: %w", err)
	}

	return nil
}

// GetTotalProfit calcule le profit total d'un utilisateur
func (db *PostgresDB) GetTotalProfit(userID int) (float64, error) {
	query := `SELECT COALESCE(SUM(profit), 0) FROM trades WHERE user_id = $1`

	var totalProfit float64
	err := db.db.QueryRow(query, userID).Scan(&totalProfit)
	if err != nil {
		return 0, err
	}

	return totalProfit, nil
}

// Close ferme la connexion à la base de données
func (db *PostgresDB) Close() error {
	if db.db != nil {
		return db.db.Close()
	}
	return nil
}

// Stats représente les statistiques globales
type Stats struct {
	TotalTrades    int     `json:"total_trades"`
	TotalProfit    float64 `json:"total_profit"`
	WinRate        float64 `json:"win_rate"`
	AvgProfitTrade float64 `json:"avg_profit_trade"`
}

// GetUserStats récupère les statistiques d'un utilisateur
func (db *PostgresDB) GetUserStats(userID int) (*Stats, error) {
	stats := &Stats{}

	// Nombre total de trades
	err := db.db.QueryRow(`SELECT COUNT(*) FROM trades WHERE user_id = $1`, userID).Scan(&stats.TotalTrades)
	if err != nil {
		return nil, err
	}

	// Profit total
	err = db.db.QueryRow(`SELECT COALESCE(SUM(profit), 0) FROM trades WHERE user_id = $1`, userID).Scan(&stats.TotalProfit)
	if err != nil {
		return nil, err
	}

	// Taux de réussite
	var winningTrades int
	err = db.db.QueryRow(`SELECT COUNT(*) FROM trades WHERE user_id = $1 AND profit > 0`, userID).Scan(&winningTrades)
	if err != nil {
		return nil, err
	}

	if stats.TotalTrades > 0 {
		stats.WinRate = float64(winningTrades) / float64(stats.TotalTrades) * 100
		stats.AvgProfitTrade = stats.TotalProfit / float64(stats.TotalTrades)
	}

	return stats, nil
}
