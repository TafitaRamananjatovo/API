from decimal import Decimal

from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=120, unique=True)
    plan_code = models.CharField(max_length=80, default="starter")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    tenant = models.ForeignKey(Tenant, null=True, blank=True, on_delete=models.PROTECT, related_name="users")
    phone_number = models.CharField(max_length=15, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )


class TenantOwnedModel(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class Organization(TenantOwnedModel):
    name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=220, blank=True)
    tax_id = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="uniq_org_tenant_name"),
        ]

    def __str__(self):
        return self.name


class Restaurant(TenantOwnedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=180)
    timezone = models.CharField(max_length=80, default="UTC")
    currency = models.CharField(max_length=3, default="USD")
    address = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "organization", "name"], name="uniq_restaurant_org_name"),
        ]

    def __str__(self):
        return self.name


class Role(TenantOwnedModel):
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_role_tenant_code"),
        ]

    def __str__(self):
        return self.name


class Supplier(TenantOwnedModel):
    restaurant = models.ForeignKey(Restaurant, null=True, blank=True, on_delete=models.CASCADE, related_name="suppliers")
    name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    lead_time_days = models.PositiveIntegerField(default=1)
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "restaurant", "name"], name="uniq_supplier_restaurant_name"),
        ]

    def __str__(self):
        return self.name


class Category(TenantOwnedModel):
    restaurant = models.ForeignKey(Restaurant, null=True, blank=True, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")

    class Meta:
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "restaurant", "name"], name="uniq_category_restaurant_name"),
        ]

    def __str__(self):
        return self.name


class Product(TenantOwnedModel):
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    sku = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=180)
    unit = models.CharField(max_length=30)
    purchase_unit = models.CharField(max_length=30, blank=True)
    unit_conversion_factor = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    average_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "sku"], name="uniq_product_tenant_sku"),
        ]

    def __str__(self):
        return self.name


class InventoryItem(TenantOwnedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="inventory_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventory_items")
    batch_number = models.CharField(max_length=100, blank=True)
    quantity_on_hand = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    reorder_point = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    target_stock_level = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    expires_at = models.DateField(null=True, blank=True)
    received_at = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "restaurant", "product"]),
            models.Index(fields=["tenant", "restaurant", "expires_at"]),
        ]

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_point

    def __str__(self):
        return f"{self.restaurant} - {self.product}"


class StockMovement(TenantOwnedModel):
    INITIAL = "initial"
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    WASTE = "waste"
    TRANSFER = "transfer"
    RETURN = "return"
    MOVEMENT_TYPES = [
        (INITIAL, "Initial"),
        (PURCHASE, "Purchase"),
        (SALE, "Sale"),
        (ADJUSTMENT, "Adjustment"),
        (WASTE, "Waste"),
        (TRANSFER, "Transfer"),
        (RETURN, "Return"),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="stock_movements")
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    reason = models.TextField(blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("CustomUser", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "restaurant", "-occurred_at"]),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                item = InventoryItem.objects.select_for_update().get(pk=self.inventory_item_id)
                item.quantity_on_hand = (item.quantity_on_hand or Decimal("0")) + self.quantity
                item.save(update_fields=["quantity_on_hand", "updated_at"])


class PurchaseOrder(TenantOwnedModel):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    STATUSES = [
        (DRAFT, "Draft"),
        (PENDING_APPROVAL, "Pending approval"),
        (APPROVED, "Approved"),
        (ORDERED, "Ordered"),
        (RECEIVED, "Received"),
        (CANCELLED, "Cancelled"),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="purchase_orders")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    order_number = models.CharField(max_length=80)
    status = models.CharField(max_length=30, choices=STATUSES, default=DRAFT)
    expected_delivery_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey("CustomUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_orders")
    approved_at = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey("CustomUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="purchase_orders")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "order_number"], name="uniq_po_tenant_number"),
        ]
        indexes = [
            models.Index(fields=["tenant", "restaurant", "status", "-created_at"]),
        ]

    def recalculate_totals(self):
        subtotal = sum((item.line_total for item in self.items.all()), Decimal("0"))
        self.subtotal = subtotal
        self.total = subtotal + (self.tax_total or Decimal("0"))
        self.save(update_fields=["subtotal", "total", "updated_at"])


class PurchaseOrderItem(TenantOwnedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_order_items")
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    unit = models.CharField(max_length=30)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = (self.quantity or Decimal("0")) * (self.unit_cost or Decimal("0"))
        super().save(*args, **kwargs)


class Forecast(TenantOwnedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="forecasts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="forecasts")
    forecast_date = models.DateField()
    horizon_days = models.PositiveIntegerField(default=1)
    predicted_quantity = models.DecimalField(max_digits=14, decimal_places=4)
    confidence_low = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    confidence_high = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    model_name = models.CharField(max_length=120, default="moving_average")
    model_version = models.CharField(max_length=80, default="v1")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "restaurant", "product", "forecast_date", "horizon_days", "model_version"],
                name="uniq_forecast_version",
            ),
        ]


class Notification(TenantOwnedModel):
    restaurant = models.ForeignKey(Restaurant, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey("CustomUser", null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=30, default="in_app")
    title = models.CharField(max_length=180)
    body = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)


class Subscription(TenantOwnedModel):
    provider = models.CharField(max_length=60, default="manual")
    provider_customer_id = models.CharField(max_length=160, blank=True)
    provider_subscription_id = models.CharField(max_length=160, blank=True)
    plan_code = models.CharField(max_length=80)
    status = models.CharField(max_length=40, default="trialing")
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    restaurant_limit = models.PositiveIntegerField(default=1)


class AuditLog(TenantOwnedModel):
    actor_user = models.ForeignKey("CustomUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120)
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True)


@receiver(post_save, sender=CustomUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
