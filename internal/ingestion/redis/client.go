package redis

import (
	"context"
	"fmt"
	"log"

	go_redis "github.com/redis/go-redis/v9"
)

var Client *go_redis.Client

func InitRedis() {
	Client = go_redis.NewClient(&go_redis.Options{
		Addr:     "localhost:6379",
		Password: "",
		DB:       0,
	})

	_, err := Client.Ping(context.Background()).Result()
	if err != nil {
		log.Fatalf("Could not connect to Redis: %v", err)
	}
	fmt.Println("Redis initialized and connected")
}
