package model

type Trade struct {
	Price     float64 `json:"price"`
	Timestamp int64   `json:"timestamp"`
}
