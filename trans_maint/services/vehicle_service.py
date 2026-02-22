from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from django.utils import timezone
from ..models import Vehicle, FuelTransaction, MaintenanceRequest, Accident, Trip

class VehicleService:

    # --- أولاً: العمليات الأساسية (CRUD) ---

    @staticmethod
    def create_vehicle(data):
        """إضافة مركبة جديدة للأسطول"""
        return Vehicle.objects.create(**data)

    @staticmethod
    def update_vehicle(vehicle_id, data):
        """تحديث بيانات مركبة (مثل تغيير الحالة أو المالك)"""
        vehicle = VehicleService.get_vehicle(vehicle_id)
        for key, value in data.items():
            setattr(vehicle, key, value)
        vehicle.save()
        return vehicle

    @staticmethod
    def delete_vehicle(vehicle_id):
        """
        حذف مركبة. 
        ملاحظة: ستفشل العملية تلقائياً إذا كانت مرتبطة بسجلات أخرى بسبب PROTECT.
        """
        vehicle = VehicleService.get_vehicle(vehicle_id)
        vehicle.delete()
        return True

    @staticmethod
    def get_vehicle(vehicle_id):
        """جلب بيانات مركبة معينة مع بيانات المالك"""
        return get_object_or_404(Vehicle.objects.select_related('owner'), id=vehicle_id)

    @staticmethod
    def list_vehicles(filters=None):
        """قائمة المركبات مع فلترة متقدمة"""
        queryset = Vehicle.objects.select_related('owner').all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    # --- ثانياً: التحليل التشغيلي والمالي ---

    @staticmethod
    def get_vehicle_total_fuel(vehicle_id):
        """إجمالي كمية الوقود التي استهلكتها هذه المركبة تاريخياً"""
        result = FuelTransaction.objects.filter(
            vehicle_id=vehicle_id, 
            transaction_type='issue'
        ).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def get_vehicle_total_maintenance_cost(vehicle_id):
        """إجمالي مبالغ الصيانة المصروفة على المركبة"""
        result = MaintenanceRequest.objects.filter(
            vehicle_id=vehicle_id,
            status='completed' # نحسب التكاليف المكتملة فقط
        ).aggregate(total=Sum('cost'))
        return result['total'] or 0.0

    @staticmethod
    def get_vehicle_total_accident_cost(vehicle_id):
        """إجمالي تكاليف إصلاح الحوادث المسجلة"""
        result = Accident.objects.filter(vehicle_id=vehicle_id).aggregate(total=Sum('damage_cost'))
        return result['total'] or 0.0

    @staticmethod
    def get_vehicle_trip_count(vehicle_id):
        """عدد الرحلات التي قامت بها المركبة"""
        return Trip.objects.filter(vehicle_id=vehicle_id).count()

    # --- ثالثاً: خدمات التحقق (Availability) ---

    @staticmethod
    def check_vehicle_availability(vehicle_id):
        """
        دالة فحص الجاهزية قبل إنشاء رحلة جديدة.
        تتحقق من: الحالة العامة، الصيانة المفتوحة، والرحلات الحالية.
        """
        vehicle = VehicleService.get_vehicle(vehicle_id)
        
        if vehicle.status == 'under_repair':
            return False, "المركبة قيد الإصلاح في الورشة ولا يمكنها الخروج في رحلة."
        
        # 1. فحص الحالة الإدارية
        if vehicle.status != 'active':
            return False, "المركبة غير نشطة حالياً."

        # 2. فحص إذا كانت في صيانة قيد المعالجة
        has_active_maintenance = MaintenanceRequest.objects.filter(
            vehicle_id=vehicle_id, 
            status='pending'
        ).exists()
        if has_active_maintenance:
            return False, "المركبة موجودة في الورشة للصيانة."

        # 3. فحص إذا كانت في رحلة لم تنتهِ بعد (end_date is null)
        is_in_trip = Trip.objects.filter(
            vehicle_id=vehicle_id, 
            end_date__isnull=True
        ).exists()
        if is_in_trip:
            return False, "المركبة في رحلة عمل حالياً."

        return True, "المركبة جاهزة للاستخدام."