from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.db import transaction
from ..models import MaintenanceRequest, Vehicle

class MaintenanceService:

    # --- أولاً: العمليات الأساسية (Operational Flow) ---

    @staticmethod
    def create_maintenance_request(data):
        """
        إنشاء طلب صيانة (دوري أو ناتج عن حادث).
        عند فتح الطلب، يتم قفل المركبة برمجياً لضمان عدم خروجها في رحلات.
        """
        vehicle = data.get('vehicle')
        
        with transaction.atomic():
            # 1. إنشاء سجل الصيانة (يربط بـ accident_ref إذا وجد)
            request = MaintenanceRequest.objects.create(**data)
            
            # 2. تغيير حالة المركبة لضمان عدم استخدامها (Safety Lock)
            # حتى لو كانت active، نحولها لـ inactive أو نعتمد على وجود طلب pending
            vehicle.status = 'under_repair'
            vehicle.save()
            
            return request

    @staticmethod
    def complete_maintenance_request(request_id, actual_cost):
        """
        إكمال الصيانة: تسجيل التكلفة الفعلية وإعادة المركبة للخدمة.
        """
        request = MaintenanceService.get_maintenance_request(request_id)
        
        with transaction.atomic():
            request.status = 'completed'
            request.cost = actual_cost
            request.save()
            
            # إعادة تفعيل المركبة (فتح القفل) لتصبح متاحة للـ Trip Service
            vehicle = request.vehicle
            vehicle.status = 'active'
            vehicle.save()
            
        return request

    @staticmethod
    def update_maintenance_request(request_id, data):
        request = MaintenanceService.get_maintenance_request(request_id)
        for key, value in data.items():
            setattr(request, key, value)
        request.save()
        return request

    @staticmethod
    def get_maintenance_request(request_id):
        return get_object_or_404(MaintenanceRequest.objects.select_related('vehicle', 'workshop'), id=request_id)

    @staticmethod
    def list_maintenance_requests(filters=None):
        queryset = MaintenanceRequest.objects.select_related('vehicle', 'workshop', 'accident_ref').all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    # --- ثانياً: ذكاء الصيانة (Maintenance Intelligence) ---

    @staticmethod
    def get_vehicle_maintenance_history(vehicle_id):
        """تحليل السجل الفني للمركبة لاكتشاف الأعطال المتكررة"""
        return MaintenanceRequest.objects.filter(vehicle_id=vehicle_id).order_by('-date_reported')

    @staticmethod
    def get_total_maintenance_cost(vehicle_id=None):
        """حساب المصاريف التشغيلية (OpEx) للمركبة أو للأسطول كاملًا"""
        queryset = MaintenanceRequest.objects.filter(status='completed')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
            
        result = queryset.aggregate(total_cost=Sum('cost'))
        return result['total_cost'] or 0.0