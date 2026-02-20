from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.db import transaction
from ..models import Accident, Vehicle

class AccidentService:

    # --- أولاً: دورة حياة الحادث (Lifecycle) ---

    @staticmethod
    def create_accident(data):
        """
        إنشاء سجل حادث وتغيير حالة المركبة فوراً لمنع استخدامها.
        """
        vehicle = data.get('vehicle')
        
        with transaction.atomic():
            # 1. إنشاء سجل الحادث
            accident = Accident.objects.create(**data)
            
            # 2. تغيير حالة المركبة إلى (غير نشطة) لضمان السلامة
            # سيؤدي هذا لجعل دالة check_vehicle_availability تعيد False تلقائياً
            vehicle.status = 'inactive'
            vehicle.save()
            
            return accident

    @staticmethod
    def close_accident(accident_id, final_cost=None):
        """
        إغلاق ملف الحادث إدارياً وتحديث التكلفة النهائية.
        """
        accident = AccidentService.get_accident(accident_id)
        accident.status = 'closed'
        if final_cost is not None:
            accident.damage_cost = final_cost
        accident.save()
        return accident

    @staticmethod
    def get_accident(accident_id):
        return get_object_or_404(Accident.objects.select_related('vehicle'), id=accident_id)

    # --- ثانياً: مقاييس المخاطر والسلامة (Risk Metrics) ---

    @staticmethod
    def get_vehicle_accident_history(vehicle_id):
        """السجل الجنائي للمركبة"""
        return Accident.objects.filter(vehicle_id=vehicle_id).order_by('-date_occurred')

    @staticmethod
    def get_total_accident_cost(vehicle_id=None):
        """
        حساب إجمالي الخسائر. 
        إذا تم تمرير vehicle_id يحسب لمركبة واحدة، وإلا يحسب للأسطول كاملاً.
        """
        queryset = Accident.objects.all()
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
            
        result = queryset.aggregate(total=Sum('damage_cost'))
        return result['total'] or 0.00

    @staticmethod
    def list_accidents(filters=None):
        queryset = Accident.objects.select_related('vehicle').all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset