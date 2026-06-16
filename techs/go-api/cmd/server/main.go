package main

import (
	"net/http"
	"os"
	"sync"
	"time"

	_ "github.com/TafitaRamananjatovo/API/techs/go-api/docs"
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

type EventEnvelope struct {
	EventID      string                 `json:"event_id" binding:"required"`
	EventType    string                 `json:"event_type" binding:"required"`
	EventVersion int                    `json:"event_version" binding:"required"`
	TenantID     string                 `json:"tenant_id" binding:"required"`
	RestaurantID string                 `json:"restaurant_id"`
	OccurredAt   time.Time              `json:"occurred_at"`
	Producer     string                 `json:"producer"`
	Payload      map[string]interface{} `json:"payload"`
}

type Notification struct {
	ID           string                 `json:"id"`
	TenantID     string                 `json:"tenant_id"`
	RestaurantID string                 `json:"restaurant_id,omitempty"`
	UserID       string                 `json:"user_id,omitempty"`
	Channel      string                 `json:"channel"`
	Title        string                 `json:"title"`
	Body         string                 `json:"body"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	Read         bool                   `json:"read"`
	CreatedAt    time.Time              `json:"created_at"`
}

type ReportRequest struct {
	TenantID      string `json:"tenant_id" binding:"required"`
	RestaurantID  string `json:"restaurant_id" binding:"required"`
	ReportType    string `json:"report_type" binding:"required"`
	FromDate      string `json:"from_date" binding:"required"`
	ToDate        string `json:"to_date" binding:"required"`
	RequestedByID string `json:"requested_by_id"`
}

type ReportJob struct {
	ID        string    `json:"id"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	CreatedAt time.Time `json:"created_at"`
}

type Store struct {
	mu            sync.RWMutex
	events        []EventEnvelope
	notifications []Notification
	reports        []ReportJob
}

func main() {
	store := &Store{}
	router := setupRouter(store)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	router.Run(":" + port)
}

func setupRouter(store *Store) *gin.Engine {
	router := gin.Default()
	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	router.GET("/healthz", healthz)

	v1 := router.Group("/api/v1")
	v1.POST("/events", store.ingestEvent)
	v1.GET("/events", store.listEvents)
	v1.GET("/notifications", store.listNotifications)
	v1.POST("/notifications", store.createNotification)
	v1.POST("/reports", store.createReport)
	v1.GET("/reports", store.listReports)
	v1.GET("/ws/restaurants/:restaurant_id", websocketInfo)

	return router
}

func healthz(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "smart-inventory-go"})
}

func (s *Store) ingestEvent(c *gin.Context) {
	var event EventEnvelope
	if err := c.ShouldBindJSON(&event); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if event.OccurredAt.IsZero() {
		event.OccurredAt = time.Now().UTC()
	}

	s.mu.Lock()
	s.events = append(s.events, event)
	if event.EventType == "StockLow" || event.EventType == "ExpirationApproaching" || event.EventType == "WasteDetected" {
		s.notifications = append(s.notifications, Notification{
			ID:           event.EventID,
			TenantID:     event.TenantID,
			RestaurantID: event.RestaurantID,
			Channel:      "in_app",
			Title:        event.EventType,
			Body:         "Inventory event requires attention.",
			Metadata:     event.Payload,
			CreatedAt:    time.Now().UTC(),
		})
	}
	s.mu.Unlock()

	c.JSON(http.StatusAccepted, gin.H{"status": "accepted", "event_id": event.EventID})
}

func (s *Store) listEvents(c *gin.Context) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c.JSON(http.StatusOK, s.events)
}

func (s *Store) createNotification(c *gin.Context) {
	var notification Notification
	if err := c.ShouldBindJSON(&notification); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if notification.ID == "" {
		notification.ID = time.Now().UTC().Format("20060102150405.000000000")
	}
	if notification.CreatedAt.IsZero() {
		notification.CreatedAt = time.Now().UTC()
	}
	if notification.Channel == "" {
		notification.Channel = "in_app"
	}

	s.mu.Lock()
	s.notifications = append(s.notifications, notification)
	s.mu.Unlock()

	c.JSON(http.StatusCreated, notification)
}

func (s *Store) listNotifications(c *gin.Context) {
	tenantID := c.Query("tenant_id")
	s.mu.RLock()
	defer s.mu.RUnlock()
	filtered := make([]Notification, 0, len(s.notifications))
	for _, notification := range s.notifications {
		if tenantID == "" || notification.TenantID == tenantID {
			filtered = append(filtered, notification)
		}
	}
	c.JSON(http.StatusOK, filtered)
}

func (s *Store) createReport(c *gin.Context) {
	var request ReportRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	job := ReportJob{
		ID:        time.Now().UTC().Format("report-20060102150405.000000000"),
		Status:    "queued",
		Message:   "Report job accepted for asynchronous processing.",
		CreatedAt: time.Now().UTC(),
	}

	s.mu.Lock()
	s.reports = append(s.reports, job)
	s.mu.Unlock()

	c.JSON(http.StatusAccepted, job)
}

func (s *Store) listReports(c *gin.Context) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	c.JSON(http.StatusOK, s.reports)
}

func websocketInfo(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"restaurant_id": c.Param("restaurant_id"),
		"message":       "WebSocket gateway placeholder. Upgrade this endpoint with a websocket adapter for production.",
	})
}
