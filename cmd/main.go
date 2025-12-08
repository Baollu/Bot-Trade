package main

import (
	"back-end/internal/ingestion"
	"fmt"
	"os"
	"os/signal"
)

func main() {
	fmt.Println("Server starting...")

	go ingestion.ConnectBinance()

	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)
	<-interrupt
}
