package main

import (
	"bot-trade/internal/ingestion/binance"
	"bot-trade/internal/ingestion/redis"
	"fmt"
	"os"
	"os/signal"
)

func main() {
	fmt.Println("Server starting...")

	redis.InitRedis()
	go binance.ConnectBinance()

	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)
	<-interrupt
}
