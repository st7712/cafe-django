from django.contrib import admin
from .models import Drink, DrinkType, Table, Order, StaffUser

@admin.register(StaffUser)
class StaffUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'token') # Co bude vidět v seznamu
    readonly_fields = ('token',)         # Token by se neměl měnit ručně
    
    # Změna hesla v adminu -> zahashování
    def save_model(self, request, obj, form, change):
        # Pokud heslo není hash, zahashujeme ho
        if obj.password and not obj.password.startswith('pbkdf2_sha256$'):
            from django.contrib.auth.hashers import make_password
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)

# Register your models here.
admin.site.register(Drink)
admin.site.register(DrinkType)
admin.site.register(Table)
admin.site.register(Order)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('table', 'drink', 'drink_type', 'status', 'created_at', 'accepted_at')
    list_filter = ('status', 'created_at')
    search_fields = ('table__number', 'drink__name', 'drink_type__name')
    readonly_fields = ('created_at', 'accepted_at')