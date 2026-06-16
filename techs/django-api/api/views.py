from django.contrib.auth import authenticate
from django.db.models import F
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import (
    AuditLog,
    Category,
    Forecast,
    InventoryItem,
    Notification,
    Organization,
    Product,
    PurchaseOrder,
    Restaurant,
    Role,
    StockMovement,
    Subscription,
    Supplier,
    Tenant,
)
from .serializers import (
    AuditLogSerializer,
    CategorySerializer,
    ForecastSerializer,
    InventoryItemSerializer,
    LoginSerializer,
    NotificationSerializer,
    OrganizationSerializer,
    ProductSerializer,
    PurchaseOrderSerializer,
    RestaurantSerializer,
    RoleSerializer,
    StockMovementSerializer,
    SubscriptionSerializer,
    SupplierSerializer,
    TenantSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"user": UserSerializer(user).data, "token": token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            user = authenticate(username=username, password=password)
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"user": UserSerializer(user).data, "token": token.key})
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    serializer_class = LoginSerializer

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_200_OK)


class UserProfileView(APIView):
    serializer_class = UserSerializer

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id", "name", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = getattr(self.request.user, "tenant", None)
        if self.request.user.is_superuser:
            return queryset
        if tenant is None:
            return queryset.none()
        return queryset.filter(tenant=tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class TenantViewSet(TenantScopedViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        tenant = getattr(self.request.user, "tenant", None)
        return self.queryset.filter(id=tenant.id) if tenant else self.queryset.none()

    def perform_create(self, serializer):
        serializer.save()


class OrganizationViewSet(TenantScopedViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class RestaurantViewSet(TenantScopedViewSet):
    queryset = Restaurant.objects.select_related("organization", "tenant")
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        organization_id = self.request.query_params.get("organization_id")
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        return queryset


class RoleViewSet(TenantScopedViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    search_fields = ["code", "name"]


class SupplierViewSet(TenantScopedViewSet):
    queryset = Supplier.objects.select_related("restaurant", "tenant")
    serializer_class = SupplierSerializer
    search_fields = ["name", "email", "phone"]

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant_id")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset


class CategoryViewSet(TenantScopedViewSet):
    queryset = Category.objects.select_related("restaurant", "parent", "tenant")
    serializer_class = CategorySerializer


class ProductViewSet(TenantScopedViewSet):
    queryset = Product.objects.select_related("category", "supplier", "tenant")
    serializer_class = ProductSerializer
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "sku", "average_unit_cost", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get("category_id")
        supplier_id = self.request.query_params.get("supplier_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        return queryset


class InventoryItemViewSet(TenantScopedViewSet):
    queryset = InventoryItem.objects.select_related("restaurant", "product", "tenant")
    serializer_class = InventoryItemSerializer
    search_fields = ["product__name", "batch_number", "location"]
    ordering_fields = ["quantity_on_hand", "expires_at", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant_id")
        low_stock = self.request.query_params.get("low_stock")
        expires_before = self.request.query_params.get("expires_before")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if low_stock in {"1", "true", "True"}:
            queryset = queryset.filter(quantity_on_hand__lte=F("reorder_point"))
        if expires_before:
            queryset = queryset.filter(expires_at__lte=expires_before)
        return queryset


class StockMovementViewSet(TenantScopedViewSet):
    queryset = StockMovement.objects.select_related("restaurant", "product", "inventory_item", "tenant")
    serializer_class = StockMovementSerializer
    search_fields = ["reason", "product__name"]
    ordering_fields = ["occurred_at", "created_at"]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant_id")
        movement_type = self.request.query_params.get("movement_type")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        return queryset


class PurchaseOrderViewSet(TenantScopedViewSet):
    queryset = PurchaseOrder.objects.prefetch_related("items").select_related("restaurant", "supplier", "tenant")
    serializer_class = PurchaseOrderSerializer
    search_fields = ["order_number", "supplier__name"]
    ordering_fields = ["created_at", "expected_delivery_date", "total"]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant_id")
        po_status = self.request.query_params.get("status")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if po_status:
            queryset = queryset.filter(status=po_status)
        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        order = self.get_object()
        order.status = PurchaseOrder.APPROVED
        order.approved_by = request.user
        order.approved_at = timezone.now()
        order.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        AuditLog.objects.create(
            tenant=order.tenant,
            actor_user=request.user,
            action="purchase_order.approved",
            entity_type="PurchaseOrder",
            entity_id=order.id,
        )
        return Response(self.get_serializer(order).data)


class ForecastViewSet(TenantScopedViewSet):
    queryset = Forecast.objects.select_related("restaurant", "product", "tenant")
    serializer_class = ForecastSerializer
    http_method_names = ["get", "post", "head", "options"]
    ordering_fields = ["forecast_date", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant_id")
        product_id = self.request.query_params.get("product_id")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


class NotificationViewSet(TenantScopedViewSet):
    queryset = Notification.objects.select_related("restaurant", "user", "tenant")
    serializer_class = NotificationSerializer
    ordering_fields = ["created_at", "read_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        unread = self.request.query_params.get("unread")
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user__in=[self.request.user, None])
        if unread in {"1", "true", "True"}:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)


class SubscriptionViewSet(TenantScopedViewSet):
    queryset = Subscription.objects.select_related("tenant")
    serializer_class = SubscriptionSerializer
    search_fields = ["plan_code", "status"]


class AuditLogViewSet(TenantScopedViewSet):
    queryset = AuditLog.objects.select_related("actor_user", "tenant")
    serializer_class = AuditLogSerializer
    http_method_names = ["get", "head", "options"]
    search_fields = ["action", "entity_type"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset
