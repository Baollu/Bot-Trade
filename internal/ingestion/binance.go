package ingestion

import (
	"encoding/json"
	"log"
	"strconv"
	"strings"

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
	PriceStr  string `json:"p"`
	Quantity  string `json:"q"`
	Time      int64  `json:"T"`
}

func ConnectBinance() {
	conn, _, err := websocket.DefaultDialer.Dial(binanceBaseURL, nil)
	if err != nil {
		log.Fatal("Error connecting to Binance:", err)
	}
	defer conn.Close()

	log.Println("Connected to Binance server")

	symbol := "btcusdt"
	subscription := SubscribeMessage{
		Method: "SUBSCRIBE",
		Params: []string{symbol + "@trade"},
		ID:     1,
	}

	err = conn.WriteJSON(subscription)
	if err != nil {
		log.Fatal("Error sending subscription:", err)
	}
	log.Printf("Subscription request sent for: %s", symbol)

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			log.Println("Error reading message:", err)
			return
		}

		rawMessage := string(message)

		if !strings.Contains(rawMessage, "\"e\":\"trade\"") {
			continue
		}

		var event TradeEvent
		err = json.Unmarshal(message, &event)
		if err != nil {
			log.Printf("JSON Error: %v | Message: %s", err, rawMessage)
			continue
		}

		price, err := strconv.ParseFloat(event.PriceStr, 64)
		if err != nil {
			log.Println("Error parsing price:", err)
			continue
		}

		log.Printf("💰 PRICE: %.2f $ | ⏱️ Time: %d", price, event.Time)
	}
}
