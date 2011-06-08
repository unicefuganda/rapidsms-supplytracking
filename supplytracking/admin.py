from django.contrib import admin
from supplytracking.models import Delivery,DeliveryBackLog

class deliveryAdmin(admin.ModelAdmin):
    """delivery admin """

class deliverylogAdmin(admin.ModelAdmin):
    """delivery backlog  admin """

admin.site.register(Delivery,deliveryAdmin)
admin.site.register(DeliveryBackLog,deliverylogAdmin)
