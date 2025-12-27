package binance

import (
	"bot-trade/internal/ingestion/redis"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

const binanceBaseURL = "wss://stream.binance.com:9443/ws"

type SubscribeMessage struct {
	Method string   `json:"method"`
	Params []string `json:"params"`
	ID     int      `json:"id"`
}

type TradeEvent struct {
	EventType string `json:"e"`
	EventTime int64  `json:"E"`
	Symbol    string `json:"s"`  // Symbole de la crypto
	PriceStr  string `json:"p"`
	Quantity  string `json:"q"`
	Time      int64  `json:"T"`
}

// ConnectBinance se connecte à Binance pour un symbole spécifique
func ConnectBinance(priceChan chan<- float64, symbol string) {
	conn, _, err := websocket.DefaultDialer.Dial(binanceBaseURL, nil)
	if err != nil {
		log.Printf("❌ Erreur connexion Binance pour %s: %v", symbol, err)
		return
	}
	defer conn.Close()

	log.Printf("✅ Connecté à Binance WebSocket pour %s", strings.ToUpper(symbol))

	subscription := SubscribeMessage{
		Method: "SUBSCRIBE",
		Params: []string{strings.ToLower(symbol) + "@trade"},
		ID:     1,
	}

	err = conn.WriteJSON(subscription)
	if err != nil {
		log.Printf("❌ Erreur envoi souscription pour %s: %v", symbol, err)
		return
	}
	log.Printf("📡 Abonnement actif: %s@trade", strings.ToUpper(symbol))

	ctx := context.Background()
	redisKey := fmt.Sprintf("market_data:%s", strings.ToLower(symbol))

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			log.Printf("❌ Erreur lecture message pour %s: %v", symbol, err)
			// Tentative de reconnexion après 5 secondes
			time.Sleep(5 * time.Second)
			go ConnectBinance(priceChan, symbol)
			return
		}

		rawMessage := string(message)

		if !strings.Contains(rawMessage, "\"e\":\"trade\"") {
			continue
		}

		var event TradeEvent
		err = json.Unmarshal(message, &event)
		if err != nil {
			log.Printf("⚠️ JSON Error pour %s: %v", symbol, err)
			continue
		}

		price, err := strconv.ParseFloat(event.PriceStr, 64)
		if err != nil {
			log.Printf("⚠️ Erreur parsing prix pour %s: %v", symbol, err)
			continue
		}

		// Stockage dans Redis avec clé spécifique à la crypto
		if redis.Client != nil {
			err = redis.Client.RPush(ctx, redisKey, price).Err()
			if err != nil {
				log.Printf("⚠️ Redis Push Error pour %s: %v", symbol, err)
			} else {
				// Garde seulement les 1000 derniers prix
				redis.Client.LTrim(ctx, redisKey, -1000, -1)
			}
		}

		// Envoi dans le canal de prix
		select {
		case priceChan <- price:
		default:
			// Canal plein, on ignore ce prix
		}

		// Log occasionnel pour ne pas spammer
		if event.Time%30000 == 0 {
			log.Printf("💰 %s: $%.4f", strings.ToUpper(symbol), price)
		}
	}
}

// ConnectMultipleCryptos se connecte à plusieurs cryptos en une seule connexion
// Plus efficace que plusieurs connexions séparées
func ConnectMultipleCryptos(cryptoChannels map[string]chan<- float64) {
	conn, _, err := websocket.DefaultDialer.Dial(binanceBaseURL, nil)
	if err != nil {
		log.Printf("❌ Erreur connexion Binance multi-crypto: %v", err)
		return
	}
	defer conn.Close()

	log.Println("✅ Connecté à Binance WebSocket (mode multi-crypto)")

	// Construction de la liste des streams
	var streams []string
	for symbol := range cryptoChannels {
		streams = append(streams, strings.ToLower(symbol)+"@trade")
	}

	subscription := SubscribeMessage{
		Method: "SUBSCRIBE",
		Params: streams,
		ID:     1,
	}

	err = conn.WriteJSON(subscription)
	if err != nil {
		log.Printf("❌ Erreur souscription multi-crypto: %v", err)
		return
	}
	
	log.Printf("📡 Abonnement actif pour %d cryptos: %v", len(streams), streams)

	ctx := context.Background()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			log.Printf("❌ Erreur lecture: %v", err)
			time.Sleep(5 * time.Second)
			go ConnectMultipleCryptos(cryptoChannels)
			return
		}

		rawMessage := string(message)
		if !strings.Contains(rawMessage, "\"e\":\"trade\"") {
			continue
		}

		var event TradeEvent
		err = json.Unmarshal(message, &event)
		if err != nil {
			continue
		}

		price, err := strconv.ParseFloat(event.PriceStr, 64)
		if err != nil {
			continue
		}

		symbol := strings.ToLower(event.Symbol)
		
		// Stockage Redis
		if redis.Client != nil {
			redisKey := fmt.Sprintf("market_data:%s", symbol)
			redis.Client.RPush(ctx, redisKey, price)
			redis.Client.LTrim(ctx, redisKey, -1000, -1)
		}

		// Envoi au canal approprié
		if priceChan, ok := cryptoChannels[symbol]; ok {
			select {
			case priceChan <- price:
			default:
			}
		}
	}
}
