from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    AuditLog,
    Category,
    Forecast,
    InventoryItem,
    Notification,
    Organization,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Restaurant,
    Role,
    StockMovement,
    Subscription,
    Supplier,
    Tenant,
)

User = get_user_model()


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "plan_code", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "tenant", "tenant_name", "username", "email", "password", "first_name", "last_name", "phone_number"]
        read_only_fields = ["id", "tenant"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        tenant_name = validated_data.pop("tenant_name", "") or f"{validated_data['username']}'s tenant"
        base_slug = slugify(tenant_name) or slugify(validated_data["username"])
        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        tenant = Tenant.objects.create(name=tenant_name, slug=slug)
        user = User.objects.create_user(tenant=tenant, **validated_data)
        Organization.objects.create(tenant=tenant, name=f"{tenant.name} Organization")
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "tenant", "name", "legal_name", "tax_id", "created_at", "updated_at"]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "tenant", "organization", "name", "timezone", "currency", "address", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "tenant", "code", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "tenant",
            "restaurant",
            "name",
            "contact_name",
            "email",
            "phone",
            "lead_time_days",
            "minimum_order_amount",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "tenant", "restaurant", "name", "parent", "created_at", "updated_at"]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "tenant",
            "category",
            "supplier",
            "sku",
            "name",
            "unit",
            "purchase_unit",
            "unit_conversion_factor",
            "average_unit_cost",
            "shelf_life_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "tenant",
            "restaurant",
            "product",
            "product_name",
            "batch_number",
            "quantity_on_hand",
            "reorder_point",
            "target_stock_level",
            "expires_at",
            "received_at",
            "location",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant", "is_low_stock", "created_at", "updated_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id",
            "tenant",
            "restaurant",
            "inventory_item",
            "product",
            "movement_type",
            "quantity",
            "unit_cost",
            "reason",
            "source_type",
            "source_id",
            "occurred_at",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "tenant", "occurred_at", "created_by", "created_at"]

    def validate(self, attrs):
        inventory_item = attrs.get("inventory_item") or getattr(self.instance, "inventory_item", None)
        restaurant = attrs.get("restaurant") or getattr(self.instance, "restaurant", None)
        product = attrs.get("product") or getattr(self.instance, "product", None)
        if inventory_item and restaurant and inventory_item.restaurant_id != restaurant.id:
            raise serializers.ValidationError("Inventory item does not belong to the selected restaurant.")
        if inventory_item and product and inventory_item.product_id != product.id:
            raise serializers.ValidationError("Inventory item does not belong to the selected product.")
        return attrs


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "tenant", "product", "product_name", "quantity", "unit", "unit_cost", "line_total"]
        read_only_fields = ["id", "tenant", "line_total"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "tenant",
            "restaurant",
            "supplier",
            "order_number",
            "status",
            "expected_delivery_date",
            "approved_by",
            "approved_at",
            "subtotal",
            "tax_total",
            "total",
            "created_by",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant", "approved_by", "approved_at", "subtotal", "total", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        tenant = self.context["request"].user.tenant
        purchase_order = PurchaseOrder.objects.create(tenant=tenant, **validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(tenant=tenant, purchase_order=purchase_order, **item_data)
        purchase_order.recalculate_totals()
        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseOrderItem.objects.create(tenant=instance.tenant, purchase_order=instance, **item_data)
            instance.recalculate_totals()
        return instance


class ForecastSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Forecast
        fields = [
            "id",
            "tenant",
            "restaurant",
            "product",
            "product_name",
            "forecast_date",
            "horizon_days",
            "predicted_quantity",
            "confidence_low",
            "confidence_high",
            "model_name",
            "model_version",
            "created_at",
        ]
        read_only_fields = ["id", "tenant", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "tenant", "restaurant", "user", "channel", "title", "body", "metadata", "read_at", "created_at"]
        read_only_fields = ["id", "tenant", "created_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id",
            "tenant",
            "provider",
            "provider_customer_id",
            "provider_subscription_id",
            "plan_code",
            "status",
            "current_period_start",
            "current_period_end",
            "restaurant_limit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "tenant", "actor_user", "action", "entity_type", "entity_id", "ip_address", "user_agent", "changes", "created_at"]
        read_only_fields = fields
