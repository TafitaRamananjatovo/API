package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	_ "github.com/TafitaRamananjatovo/API/techs/go-api/docs" // This will be the import path to your generated swagger docs
)

// User represents user data structure
type User struct {
	ID       string `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
}

// @title Go API with Swagger
// @version 1.0
// @description This is a sample server with Swagger documentation.
// @host localhost:8080
// @BasePath /api/v1
func main() {
	r := gin.Default()
	v1 := r.Group("/api/v1")
	
	// Use the swagger middleware
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	
	// Setup API routes
	v1.GET("/users", getUsers)
	v1.GET("/users/:id", getUserByID)
	v1.POST("/users", createUser)
	v1.PUT("/users/:id", updateUser)
	v1.DELETE("/users/:id", deleteUser)
	
	r.Run(":8080")
}

// Mock database
var users = []User{
	{ID: "1", Username: "john_doe", Email: "john@example.com"},
	{ID: "2", Username: "jane_doe", Email: "jane@example.com"},
}

// getUsers godoc
// @Summary Get all users
// @Description Get a list of all users
// @Tags users
// @Accept json
// @Produce json
// @Success 200 {array} User
// @Router /users [get]
func getUsers(c *gin.Context) {
	c.JSON(http.StatusOK, users)
}

// getUserByID godoc
// @Summary Get a user by ID
// @Description Get a specific user by their ID
// @Tags users
// @Accept json
// @Produce json
// @Param id path string true "User ID"
// @Success 200 {object} User
// @Failure 404 {object} map[string]string
// @Router /users/{id} [get]
func getUserByID(c *gin.Context) {
	id := c.Param("id")
	
	for _, user := range users {
		if user.ID == id {
			c.JSON(http.StatusOK, user)
			return
		}
	}
	
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}

// createUser godoc
// @Summary Create a new user
// @Description Create a new user with the provided information
// @Tags users
// @Accept json
// @Produce json
// @Param user body User true "User object"
// @Success 201 {object} User
// @Router /users [post]
func createUser(c *gin.Context) {
	var newUser User
	if err := c.ShouldBindJSON(&newUser); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	// In a real app, you would generate an ID and save to a database
	users = append(users, newUser)
	c.JSON(http.StatusCreated, newUser)
}

// updateUser godoc
// @Summary Update a user
// @Description Update a user's information by their ID
// @Tags users
// @Accept json
// @Produce json
// @Param id path string true "User ID"
// @Param user body User true "User object"
// @Success 200 {object} User
// @Failure 404 {object} map[string]string
// @Router /users/{id} [put]
func updateUser(c *gin.Context) {
	id := c.Param("id")
	var updatedUser User
	
	if err := c.ShouldBindJSON(&updatedUser); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	for i, user := range users {
		if user.ID == id {
			updatedUser.ID = id
			users[i] = updatedUser
			c.JSON(http.StatusOK, updatedUser)
			return
		}
	}
	
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}

// deleteUser godoc
// @Summary Delete a user
// @Description Delete a user by their ID
// @Tags users
// @Accept json
// @Produce json
// @Param id path string true "User ID"
// @Success 204 {object} nil
// @Failure 404 {object} map[string]string
// @Router /users/{id} [delete]
func deleteUser(c *gin.Context) {
	id := c.Param("id")
	
	for i, user := range users {
		if user.ID == id {
			// Remove the user by replacing it with the last user and truncating the slice
			users[i] = users[len(users)-1]
			users = users[:len(users)-1]
			c.Status(http.StatusNoContent)
			return
		}
	}
	
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}