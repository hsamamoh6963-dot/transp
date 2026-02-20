
from django.db.models import Sum, Q
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import FuelTransaction, Employee, Vehicle

class FuelService:

    # --- أولاً: إنشاء المعاملات (The Ledger) ---

    @staticmethod
    def create_transaction(data):
        """الدالة المركزية لتوحيد تسجيل المعاملات وضمان تكامل البيانات"""
        # يمكن إضافة منطق تدقيق إضافي هنا قبل الحفظ
        return FuelTransaction.objects.create(**data)

    @staticmethod
    def add_fuel(employee_id, vehicle_id, quantity, trip=None, notes=None):
        """تمثل 'الإيداع': إضافة رصيد للموظف (دوري أو طارئ للرحلة)"""
        return FuelService.create_transaction({
            'employee_id': employee_id,
            'vehicle_id': vehicle_id,
            'quantity': quantity,
            'transaction_type': 'addition',
            'trip': trip,
            'notes': notes or "إضافة رصيد وقود للنظام"
        })

    @staticmethod
    def issue_fuel(employee_id, vehicle_id, quantity, notes=None):
        """تمثل 'الشراء': الصرف الفعلي للوقود وخصمه من رصيد الموظف"""
        # 1. التحقق من كفاية الرصيد قبل العملية
        is_sufficient, message = FuelService.validate_sufficient_balance(employee_id, quantity)
        if not is_sufficient:
            raise ValidationError(message)

        # 2. تسجيل المعاملة
        return FuelService.create_transaction({
            'employee_id': employee_id,
            'vehicle_id': vehicle_id,
            'quantity': quantity,
            'transaction_type': 'issue',
            'notes': notes or "عملية صرف وقود فعلية"
        })

    # --- ثانياً: الحسابات (Balance & Analytics) ---

    @staticmethod
    def calculate_employee_balance(employee_id):
        """
        الخوارزمية الحسابية للرصيد المتاح:
        (إجمالي الإضافات) - (إجمالي المسحوبات الفعلية)
        """
        aggregates = FuelTransaction.objects.filter(employee_id=employee_id).aggregate(
            total_added=Sum('quantity', filter=Q(transaction_type='addition')),
            total_issued=Sum('quantity', filter=Q(transaction_type='issue'))
        )
        
        added = aggregates['total_added'] or 0.0
        issued = aggregates['total_issued'] or 0.0
        
        return added - issued

    @staticmethod
    def calculate_vehicle_total_fuel(vehicle_id):
        """إجمالي الوقود الذي استهلكته مركبة معينة (لأغراض مراقبة التكلفة)"""
        result = FuelTransaction.objects.filter(
            vehicle_id=vehicle_id, 
            transaction_type='issue'
        ).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def calculate_period_fuel_usage(start_date, end_date):
        """دالة رقابية لمقارنة الاستهلاك في فترة زمنية محددة"""
        result = FuelTransaction.objects.filter(
            date__range=[start_date, end_date],
            transaction_type='issue'
        ).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    # --- ثالثاً: التحقق والقيود (Validation) ---

    @staticmethod
    def validate_sufficient_balance(employee_id, quantity):
        """حارس البوابة: يرفض العملية إذا كان المطلوب أكبر من المتاح"""
        current_balance = FuelService.calculate_employee_balance(employee_id)
        if current_balance < quantity:
            return False, f"عذراً، الرصيد غير كافٍ. الرصيد الحالي: {current_balance} لتر."
        return True, "الرصيد كافٍ."
    


    @staticmethod
    def list_transactions(filters=None):
        queryset = FuelTransaction.objects.select_related('employee', 'vehicle', 'trip').all().order_by('-date')
        if filters:
            queryset = queryset.filter(**filters)
        return queryset