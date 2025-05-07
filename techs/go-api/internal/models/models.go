package main

// You can move this to a separate models package in a larger project

// Response represents a standard API response
type Response struct {
	Status  string      `json:"status" example:"success"`
	Message string      `json:"message" example:"Operation completed successfully"`
	Data    interface{} `json:"data,omitempty"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Status  string `json:"status" example:"error"`
	Message string `json:"message" example:"An error occurred"`
	Code    int    `json:"code" example:"404"`
}

// Item represents an example data item
type Item struct {
	ID          string `json:"id" example:"123e4567-e89b-12d3-a456-426614174000"`
	Name        string `json:"name" example:"Example Item"`
	Description string `json:"description" example:"This is an example item"`
	CreatedAt   string `json:"created_at" example:"2023-01-01T12:00:00Z"`
}

// CreateItemRequest represents the request body for creating a new item
type CreateItemRequest struct {
	Name        string `json:"name" binding:"required" example:"New Item"`
	Description string `json:"description" example:"Description of the new item"`
}

// UpdateItemRequest represents the request body for updating an item
type UpdateItemRequest struct {
	Name        string `json:"name" example:"Updated Item Name"`
	Description string `json:"description" example:"Updated description"`
}