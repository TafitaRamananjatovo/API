package main

import (
    "fmt"
    "log"
    "net/http"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "{\"message\": \"Welcome to Go API\"}")
    })

    log.Println("Starting Go API server on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}