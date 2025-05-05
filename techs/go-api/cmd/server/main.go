package main

import (
    "github.com/gin-gonic/gin"
)

func main() {
    r := gin.Default()

    // Route principale
    r.GET("/", func(c *gin.Context) {
        // Ton handler combiné ici
        c.JSON(200, gin.H{
            "message": "Hello World!",
        })
    })

    // Autres routes ici, sur d'autres chemins
    r.GET("/other", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "message": "Other endpoint",
        })
    })

    r.Run(":8080") // Démarre le serveur sur port 8080
}
