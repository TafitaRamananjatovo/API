from datetime import date, timedelta
from statistics import mean
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Smart Inventory AI Service",
    description="Forecasting, waste prediction, recommendations, and analytics APIs.",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DemandObservation(BaseModel):
    observed_on: date
    quantity: float = Field(gt=0)


class ForecastRequest(BaseModel):
    tenant_id: UUID
    restaurant_id: UUID
    product_id: UUID
    horizon_days: int = Field(default=7, ge=1, le=30)
    history: List[DemandObservation]
    supplier_lead_time_days: int = Field(default=1, ge=0, le=60)


class ForecastPoint(BaseModel):
    forecast_date: date
    predicted_quantity: float
    confidence_low: float
    confidence_high: float


class ForecastResponse(BaseModel):
    forecast_id: UUID
    tenant_id: UUID
    restaurant_id: UUID
    product_id: UUID
    model_name: str
    model_version: str
    horizon_days: int
    points: List[ForecastPoint]


class WastePredictionRequest(BaseModel):
    tenant_id: UUID
    restaurant_id: UUID
    product_id: UUID
    quantity_on_hand: float = Field(ge=0)
    daily_average_usage: float = Field(ge=0)
    days_until_expiration: int = Field(ge=0)


class WastePredictionResponse(BaseModel):
    product_id: UUID
    waste_risk: str
    expected_unused_quantity: float
    recommendation: str


class ReplenishmentRequest(BaseModel):
    tenant_id: UUID
    restaurant_id: UUID
    product_id: UUID
    quantity_on_hand: float = Field(ge=0)
    reorder_point: float = Field(ge=0)
    target_stock_level: float = Field(ge=0)
    supplier_lead_time_days: int = Field(default=1, ge=0, le=60)
    daily_average_usage: float = Field(default=0, ge=0)


class ReplenishmentResponse(BaseModel):
    product_id: UUID
    should_order: bool
    recommended_quantity: float
    reason: str


class ProfitabilityRequest(BaseModel):
    tenant_id: UUID
    restaurant_id: UUID
    revenue: float = Field(ge=0)
    food_cost: float = Field(ge=0)
    waste_cost: float = Field(ge=0)


class ProfitabilityResponse(BaseModel):
    restaurant_id: UUID
    revenue: float
    food_cost: float
    waste_cost: float
    gross_profit: float
    gross_margin_percent: float
    waste_percent_of_revenue: float


def moving_average(history: List[DemandObservation]) -> float:
    if not history:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one historical observation is required.")
    ordered = sorted(history, key=lambda item: item.observed_on)
    window = ordered[-min(len(ordered), 14):]
    return mean(item.quantity for item in window)


def seasonality_multiplier(target_date: date) -> float:
    if target_date.weekday() in {4, 5}:
        return 1.15
    if target_date.weekday() == 6:
        return 0.9
    return 1.0


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "smart-inventory-ai"}


@app.post("/api/v1/forecasts/daily", response_model=ForecastResponse)
def daily_forecast(payload: ForecastRequest):
    baseline = moving_average(payload.history)
    start_date = date.today() + timedelta(days=1)
    points = []
    for offset in range(payload.horizon_days):
        forecast_date = start_date + timedelta(days=offset)
        predicted = round(baseline * seasonality_multiplier(forecast_date), 4)
        points.append(
            ForecastPoint(
                forecast_date=forecast_date,
                predicted_quantity=predicted,
                confidence_low=round(predicted * 0.85, 4),
                confidence_high=round(predicted * 1.15, 4),
            )
        )
    return ForecastResponse(
        forecast_id=uuid4(),
        tenant_id=payload.tenant_id,
        restaurant_id=payload.restaurant_id,
        product_id=payload.product_id,
        model_name="moving_average_with_weekend_multiplier",
        model_version="v1",
        horizon_days=payload.horizon_days,
        points=points,
    )


@app.post("/api/v1/forecasts/weekly", response_model=ForecastResponse)
def weekly_forecast(payload: ForecastRequest):
    payload.horizon_days = max(payload.horizon_days, 7)
    return daily_forecast(payload)


@app.post("/api/v1/predictions/waste", response_model=WastePredictionResponse)
def waste_prediction(payload: WastePredictionRequest):
    expected_usage = payload.daily_average_usage * payload.days_until_expiration
    expected_unused = max(payload.quantity_on_hand - expected_usage, 0)
    ratio = expected_unused / payload.quantity_on_hand if payload.quantity_on_hand else 0
    if ratio >= 0.5:
        risk = "high"
        recommendation = "Discount, transfer, or reduce next order immediately."
    elif ratio >= 0.2:
        risk = "medium"
        recommendation = "Review menu usage and reduce replenishment quantity."
    else:
        risk = "low"
        recommendation = "No immediate action required."
    return WastePredictionResponse(
        product_id=payload.product_id,
        waste_risk=risk,
        expected_unused_quantity=round(expected_unused, 4),
        recommendation=recommendation,
    )


@app.post("/api/v1/recommendations/replenishment", response_model=ReplenishmentResponse)
def replenishment_recommendation(payload: ReplenishmentRequest):
    lead_time_buffer = payload.daily_average_usage * payload.supplier_lead_time_days
    trigger_level = payload.reorder_point + lead_time_buffer
    should_order = payload.quantity_on_hand <= trigger_level
    recommended_quantity = max(payload.target_stock_level - payload.quantity_on_hand + lead_time_buffer, 0) if should_order else 0
    reason = "Current stock is above reorder threshold."
    if should_order:
        reason = "Current stock is at or below reorder threshold after supplier lead-time buffer."
    return ReplenishmentResponse(
        product_id=payload.product_id,
        should_order=should_order,
        recommended_quantity=round(recommended_quantity, 4),
        reason=reason,
    )


@app.post("/api/v1/analytics/profitability", response_model=ProfitabilityResponse)
def profitability(payload: ProfitabilityRequest):
    gross_profit = payload.revenue - payload.food_cost - payload.waste_cost
    margin = (gross_profit / payload.revenue * 100) if payload.revenue else 0
    waste_percent = (payload.waste_cost / payload.revenue * 100) if payload.revenue else 0
    return ProfitabilityResponse(
        restaurant_id=payload.restaurant_id,
        revenue=round(payload.revenue, 2),
        food_cost=round(payload.food_cost, 2),
        waste_cost=round(payload.waste_cost, 2),
        gross_profit=round(gross_profit, 2),
        gross_margin_percent=round(margin, 2),
        waste_percent_of_revenue=round(waste_percent, 2),
    )


@app.get("/")
def root():
    return {"message": "Smart Inventory AI Service", "docs": "/swagger"}
