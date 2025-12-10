package main

import (
	"back-end/internal/ingestion"
	"back-end/internal/storage"
	"fmt"
	"os"
	"os/signal"
)

func main() {
	fmt.Println("Server starting...")

	storage.InitRedis()
	go ingestion.ConnectBinance()

	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)
	<-interrupt
}
