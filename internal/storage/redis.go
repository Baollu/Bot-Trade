package storage

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
)

var Rdb *redis.Client

func InitRedis() {
	Rdb = redis.NewClient(&redis.Options{
		Addr:     "localhost:6379",
		Password: "",
		DB:       0,
	})

	ctx := context.Background()
	_, err := Rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatal("Impossible to connect to Redis:", err)
	}
	log.Println("Connected to Redis")
}
