from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from ..models import Trip
from .fuel_service import FuelService
from .vehicle_service import VehicleService

class TripService:

    @staticmethod
    def get_trip(trip_id):
        """جلب بيانات الرحلة مع تفاصيل الموظف والمركبة"""
        return get_object_or_404(Trip.objects.select_related('employee', 'vehicle'), id=trip_id)
   

    @staticmethod
    def list_trips(filters=None):
        # استخدام select_related لتحسين الأداء ومنع استعلامات N+1
        queryset = Trip.objects.select_related('employee', 'vehicle', 'employee__rank').all().order_by('-start_date')
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    @staticmethod
    def create_trip_with_quota(data):
        """
        الدالة الهجينة (Hybrid): 
        تنشئ الرحلة وتضيف رصيد الوقود في عملية Atomic واحدة.
        """
        vehicle = data.get('vehicle')
        employee = data.get('employee')
        start_date = data.get('start_date', timezone.now())

        # 1. التحقق من جاهزية المركبة (ليست في ورشة أو رحلة أخرى)
        is_ready, message = VehicleService.check_vehicle_availability(vehicle.id)
        if not is_ready:
            raise ValidationError(f"فشل إنشاء الرحلة: {message}")

        # 2. التحقق من منطقية الرحلة للموظف (ليس لديه رحلة نشطة حالياً)
        active_employee_trip = Trip.objects.filter(employee=employee, end_date__isnull=True).exists()
        if active_employee_trip:
            raise ValidationError("الموظف لديه رحلة نشطة بالفعل، يجب إنهاؤها أولاً.")

        # 3. التنفيذ الذري (Atomic Transaction)
        with transaction.atomic():
            # إنشاء سجل الرحلة
            trip = Trip.objects.create(**data)
            
            # إذا كانت هناك حصة وقود ممنوحة للرحلة، يتم إضافتها كمحفظة وقود فوراً
            if trip.fuel_quota_granted > 0:
                FuelService.add_fuel(
                    employee_id=employee.id,
                    vehicle_id=vehicle.id,
                    quantity=trip.fuel_quota_granted,
                    trip=trip, # ربط المعاملة بالرحلة مباشرة
                    notes=f"دعم وقود تلقائي لرحلة {trip.area}"
                )
            
            return trip

    @staticmethod
    def update_trip(trip_id, data):
        """تحديث بيانات الرحلة"""
        trip = TripService.get_trip(trip_id)
        for key, value in data.items():
            setattr(trip, key, value)
        trip.save()
        return trip

    @staticmethod
    def delete_trip(trip_id):
        """حذف الرحلة (سيتم حذف معاملة الوقود المرتبطة بها تلقائياً بفضل OneToOneField)"""
        trip = TripService.get_trip(trip_id)
        trip.delete()
        return True

    @staticmethod
    def get_trip_duration(trip_id):
        """حساب مدة الرحلة بالساعات (Operational Metric)"""
        trip = TripService.get_trip(trip_id)
        if not trip.end_date:
            return "لا تزال مستمرة"
        
        delta = trip.end_date - trip.start_date
        return round(delta.total_seconds() / 3600, 2)

    @staticmethod
    def get_employee_trip_count(employee_id):
        """إجمالي الرحلات التي قام بها الموظف"""
        return Trip.objects.filter(employee_id=employee_id).count()

    @staticmethod
    def get_vehicle_trip_history(vehicle_id):
        """سجل كامل لتحركات المركبة للأرشفة"""
        return Trip.objects.filter(vehicle_id=vehicle_id).order_by('-start_date')

    @staticmethod
    def end_trip(trip_id):
        """إغلاق الرحلة عند العودة"""
        trip = TripService.get_trip(trip_id)
        trip.end_date = timezone.now()
        trip.save()
        return trip