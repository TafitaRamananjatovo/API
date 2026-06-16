from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    CategoryViewSet,
    ForecastViewSet,
    InventoryItemViewSet,
    LoginView,
    LogoutView,
    NotificationViewSet,
    OrganizationViewSet,
    ProductViewSet,
    PurchaseOrderViewSet,
    RegisterView,
    RestaurantViewSet,
    RoleViewSet,
    StockMovementViewSet,
    SubscriptionViewSet,
    SupplierViewSet,
    TenantViewSet,
    UserProfileView,
)

router = DefaultRouter()
router.register("tenants", TenantViewSet, basename="tenant")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("roles", RoleViewSet, basename="role")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("inventory-items", InventoryItemViewSet, basename="inventory-item")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("forecasts", ForecastViewSet, basename="forecast")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/profile/", UserProfileView.as_view(), name="profile"),
    path("v1/", include(router.urls)),
]
