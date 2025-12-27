package analyzer

import (
	"bot-trade/internal/ingestion/model"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
	"gonum.org/v1/gonum/stat"
)

// Prediction représente une prédiction du modèle IA
type Prediction struct {
	Timestamp    time.Time          `json:"timestamp"`
	Class        string             `json:"class"`          // NEUTRAL, UP, DOWN
	ClassID      int                `json:"class_id"`       // 0, 1, 2
	Probabilities map[string]float64 `json:"probabilities"` // Probabilités par classe
	Confidence   float64            `json:"confidence"`     // Confiance max
	LatencyMs    float64            `json:"latency_ms"`     // Temps d'inférence
	PriceAtPred  float64            `json:"price_at_pred"`  // Prix au moment de la prédiction
}

// ModelMetadata contient les métadonnées du modèle ONNX
type ModelMetadata struct {
	SequenceLength int      `json:"sequence_length"`
	Features       []string `json:"features"`
	Classes        []string `json:"classes"`
	ScalerMean     []float64 `json:"scaler_mean"`
	ScalerScale    []float64 `json:"scaler_scale"`
	ModelType      string   `json:"model_type"`
	Version        string   `json:"version"`
}

// AIAnalyzer gère l'analyse des prix avec le modèle IA
type AIAnalyzer struct {
	redisClient  *redis.Client
	metadata     *ModelMetadata
	ctx          context.Context
	symbol       string
}

// NewAIAnalyzer crée une nouvelle instance de l'analyseur IA
func NewAIAnalyzer(redisClient *redis.Client, symbol string) (*AIAnalyzer, error) {
	// Chargement des métadonnées du modèle
	metadata, err := loadModelMetadata("ai/model_metadata.json")
	if err != nil {
		return nil, fmt.Errorf("erreur chargement métadonnées: %w", err)
	}

	log.Printf("✅ Métadonnées du modèle chargées: %s v%s", metadata.ModelType, metadata.Version)
	log.Printf("   Séquence: %d minutes | Features: %d", metadata.SequenceLength, len(metadata.Features))

	return &AIAnalyzer{
		redisClient: redisClient,
		metadata:    metadata,
		ctx:         context.Background(),
		symbol:      symbol,
	}, nil
}

// loadModelMetadata charge les métadonnées du modèle depuis le fichier JSON
func loadModelMetadata(path string) (*ModelMetadata, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var metadata ModelMetadata
	if err := json.Unmarshal(data, &metadata); err != nil {
		return nil, err
	}

	return &metadata, nil
}

// AnalyzePrices analyse les derniers prix et génère une prédiction
func (a *AIAnalyzer) AnalyzePrices() (*Prediction, error) {
	start := time.Now()

	// Récupération des derniers prix depuis Redis
	prices, err := a.getRecentPrices(a.metadata.SequenceLength)
	if err != nil {
		return nil, fmt.Errorf("erreur récupération prix: %w", err)
	}

	if len(prices) < a.metadata.SequenceLength {
		return nil, fmt.Errorf("pas assez de données: %d/%d", len(prices), a.metadata.SequenceLength)
	}

	// Extraction des features techniques
	features := a.extractTechnicalFeatures(prices)

	// Normalisation avec le scaler du modèle
	featuresNormalized := a.normalizeFeatures(features)

	// Simulation de prédiction (à remplacer par ONNX Runtime en production)
	// Pour l'instant, on simule basé sur les features
	prediction := a.simulatePrediction(featuresNormalized, prices[len(prices)-1])

	// Calcul de la latence
	prediction.LatencyMs = float64(time.Since(start).Milliseconds())

	log.Printf("🤖 Prédiction: %s (confiance: %.2f%%, latence: %.2fms)",
		prediction.Class, prediction.Confidence*100, prediction.LatencyMs)

	return prediction, nil
}

// getRecentPrices récupère les N derniers prix depuis Redis
func (a *AIAnalyzer) getRecentPrices(n int) ([]float64, error) {
	key := fmt.Sprintf("market_data:%s", a.symbol)
	values, err := a.redisClient.LRange(a.ctx, key, int64(-n), -1).Result()
	if err != nil {
		return nil, err
	}

	prices := make([]float64, 0, len(values))
	for _, v := range values {
		var price float64
		fmt.Sscanf(v, "%f", &price)
		prices = append(prices, price)
	}

	return prices, nil
}

// extractTechnicalFeatures extrait les features techniques des prix
func (a *AIAnalyzer) extractTechnicalFeatures(prices []float64) [][]float64 {
	sequence := make([][]float64, 0, len(prices))

	for i := range prices {
		windowPrices := prices[0 : i+1]
		features := a.computeFeatures(windowPrices)
		sequence = append(sequence, features)
	}

	return sequence
}

// computeFeatures calcule les features techniques pour une fenêtre de prix
func (a *AIAnalyzer) computeFeatures(prices []float64) []float64 {
	features := make([]float64, len(a.metadata.Features))

	if len(prices) == 0 {
		return features
	}

	currentPrice := prices[len(prices)-1]

	// Price features
	features[0] = currentPrice // close

	if len(prices) > 1 {
		features[1] = (currentPrice - prices[len(prices)-2]) / prices[len(prices)-2] // returns
		features[2] = math.Log(currentPrice / prices[len(prices)-2])                  // log_returns
	}

	// Volatility
	if len(prices) >= 20 {
		features[3] = stat.StdDev(prices[len(prices)-20:], nil) // volatility
	}

	// RSI (simplifié)
	if len(prices) >= 14 {
		features[5] = a.calculateRSI(prices, 14)
	} else {
		features[5] = 50.0
	}

	if len(prices) >= 7 {
		features[6] = a.calculateRSI(prices, 7)
	} else {
		features[6] = 50.0
	}

	// SMA
	if len(prices) >= 20 {
		features[16] = stat.Mean(prices[len(prices)-20:], nil)
	} else {
		features[16] = currentPrice
	}

	// Volume (simulé)
	features[21] = 1000.0

	return features
}

// calculateRSI calcule le Relative Strength Index
func (a *AIAnalyzer) calculateRSI(prices []float64, period int) float64 {
	if len(prices) < period+1 {
		return 50.0
	}

	gains := 0.0
	losses := 0.0

	for i := len(prices) - period; i < len(prices); i++ {
		change := prices[i] - prices[i-1]
		if change > 0 {
			gains += change
		} else {
			losses -= change
		}
	}

	avgGain := gains / float64(period)
	avgLoss := losses / float64(period)

	if avgLoss == 0 {
		return 100.0
	}

	rs := avgGain / avgLoss
	rsi := 100.0 - (100.0 / (1.0 + rs))

	return rsi
}

// normalizeFeatures normalise les features avec le scaler du modèle
func (a *AIAnalyzer) normalizeFeatures(features [][]float64) [][]float64 {
	normalized := make([][]float64, len(features))

	for i, feat := range features {
		normalized[i] = make([]float64, len(feat))
		for j, val := range feat {
			if j < len(a.metadata.ScalerMean) && a.metadata.ScalerScale[j] != 0 {
				normalized[i][j] = (val - a.metadata.ScalerMean[j]) / a.metadata.ScalerScale[j]
			} else {
				normalized[i][j] = val
			}
		}
	}

	return normalized
}

// simulatePrediction simule une prédiction (à remplacer par ONNX Runtime)
func (a *AIAnalyzer) simulatePrediction(features [][]float64, currentPrice float64) *Prediction {
	// Calcul de tendance basé sur RSI et momentum
	lastFeatures := features[len(features)-1]
	
	// Index approximatifs (à ajuster selon les vrais index)
	rsi14 := lastFeatures[5]
	rsi7 := lastFeatures[6]

	var classID int
	var class string
	probabilities := make(map[string]float64)

	// Logique simplifiée de prédiction
	if rsi14 > 70 && rsi7 > 75 {
		// Surachat -> probable correction
		classID = 2
		class = "DOWN"
		probabilities["NEUTRAL"] = 0.2
		probabilities["UP"] = 0.1
		probabilities["DOWN"] = 0.7
	} else if rsi14 < 30 && rsi7 < 25 {
		// Survente -> probable rebond
		classID = 1
		class = "UP"
		probabilities["NEUTRAL"] = 0.2
		probabilities["UP"] = 0.7
		probabilities["DOWN"] = 0.1
	} else {
		// Neutre
		classID = 0
		class = "NEUTRAL"
		probabilities["NEUTRAL"] = 0.6
		probabilities["UP"] = 0.2
		probabilities["DOWN"] = 0.2
	}

	// Trouver la confiance max
	confidence := 0.0
	for _, prob := range probabilities {
		if prob > confidence {
			confidence = prob
		}
	}

	return &Prediction{
		Timestamp:     time.Now(),
		Class:         class,
		ClassID:       classID,
		Probabilities: probabilities,
		Confidence:    confidence,
		PriceAtPred:   currentPrice,
	}
}

// RunAnalysisLoop lance la boucle d'analyse toutes les minutes
func (a *AIAnalyzer) RunAnalysisLoop(predictionChan chan<- *Prediction) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	log.Println("🤖 Analyseur IA démarré - Analyse toutes les minutes")

	for {
		select {
		case <-ticker.C:
			prediction, err := a.AnalyzePrices()
			if err != nil {
				log.Printf("⚠️ Erreur analyse: %v", err)
				continue
			}

			// Envoie la prédiction au canal
			select {
			case predictionChan <- prediction:
			default:
				log.Println("⚠️ Canal de prédiction plein, prédiction ignorée")
			}
		}
	}
}
