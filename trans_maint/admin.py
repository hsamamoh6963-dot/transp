from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MilitaryRank, Employee, Vehicle, Workshop, 
    Trip, FuelTransaction, Accident, MaintenanceRequest
)

# تخصيص عنوان لوحة التحكم
admin.site.site_header = "نظام إدارة وقود وأسطول المركبات"
admin.site.site_title = "الإدارة الفنية"
admin.site.index_title = "لوحة التحكم الرئيسية"

@admin.register(MilitaryRank)
class MilitaryRankAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_weekly_quota', 'default_monthly_quota')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('military_number', 'rank', 'name', 'is_active', 'display_quota_status')
    list_filter = ('rank', 'is_active')
    search_fields = ('name', 'military_number')
    list_editable = ('is_active',)
    
    fieldsets = (
        ("البيانات الأساسية", {
            'fields': ('name', 'military_number', 'rank', 'is_active')
        }),
        ("تخصيص الحصص (Override)", {
            'description': "اترك هذه الحقول فارغة لاستخدام حصة الرتبة الافتراضية",
            'fields': ('weekly_quota_override', 'monthly_quota_override'),
        }),
    )

    def display_quota_status(self, obj):
        if obj.weekly_quota_override or obj.monthly_quota_override:
            return format_html('<span style="color: orange;">حصة مخصصة</span>')
        return format_html('<span style="color: green;">حصة الرتبة</span>')
    display_quota_status.short_description = "نوع الحصة"

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'model', 'vehicle_type', 'owner', 'status_colored')
    list_filter = ('vehicle_type', 'status')
    search_fields = ('plate_number', 'model')
    
    def status_colored(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'red',
            'under_repair': 'orange',
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = "حالة المركبة"

class FuelTransactionInline(admin.TabularInline):
    model = FuelTransaction
    extra = 0
    readonly_fields = ('date',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'employee', 'area', 'trip_type', 'start_date', 'end_date', 'fuel_quota_granted')
    list_filter = ('trip_type', 'start_date', 'vehicle')
    search_fields = ('area', 'employee__name', 'vehicle__plate_number')
    inlines = [FuelTransactionInline]
    date_hierarchy = 'start_date'

@admin.register(FuelTransaction)
class FuelTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'employee', 'vehicle', 'quantity', 'transaction_type_colored', 'trip')
    list_filter = ('transaction_type', 'date')
    search_fields = ('employee__name', 'vehicle__plate_number')
    readonly_fields = ('date',)

    def transaction_type_colored(self, obj):
        color = 'green' if obj.transaction_type == 'addition' else 'red'
        return format_html('<b style="color: {};">{}</b>', color, obj.get_transaction_type_display())
    transaction_type_colored.short_description = "نوع العملية"

@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'date_occurred', 'damage_cost', 'status')
    list_filter = ('status', 'date_occurred')
    search_fields = ('vehicle__plate_number', 'description')
    
    # إجراء سريع لتغيير حالة الحادث
    actions = ['mark_as_closed']

    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_as_closed.short_description = "إغلاق الحوادث المختارة"

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'workshop', 'date_reported', 'cost', 'status')
    list_filter = ('status', 'workshop')
    search_fields = ('vehicle__plate_number', 'reason')

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address')
    search_fields = ('name',)