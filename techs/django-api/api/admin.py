from django.contrib import admin

from .models import (
    AuditLog,
    Category,
    CustomUser,
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

admin.site.register(Tenant)
admin.site.register(CustomUser)
admin.site.register(Organization)
admin.site.register(Restaurant)
admin.site.register(Role)
admin.site.register(Supplier)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(InventoryItem)
admin.site.register(StockMovement)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(Forecast)
admin.site.register(Notification)
admin.site.register(Subscription)
admin.site.register(AuditLog)
