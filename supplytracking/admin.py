from django.contrib import admin
from supplytracking.models import Delivery

class deliveryAdmin(admin.ModelAdmin):
    """delivery admin """

admin.site.register(Delivery,deliveryAdmin)
