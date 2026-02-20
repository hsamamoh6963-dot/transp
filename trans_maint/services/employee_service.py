from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q
from django.utils import timezone
from ..models import Employee, FuelTransaction, MilitaryRank

class EmployeeService:

    # --- أولاً: العمليات الأساسية (CRUD) ---

    @staticmethod
    def create_employee(data):
        """إنشاء موظف جديد بعد التأكد من صحة البيانات"""
        # الـ Model يقوم بالتحقق من فرادة الرقم العسكري عبر unique=True
        return Employee.objects.create(**data)

    @staticmethod
    def update_employee(employee_id, data):
        """تحديث بيانات الموظف"""
        employee = EmployeeService.get_employee(employee_id)
        for key, value in data.items():
            setattr(employee, key, value)
        employee.save()
        return employee

    @staticmethod
    def deactivate_employee(employee_id):
        """تعطيل الموظف بدلاً من حذفه للحفاظ على سجلات المعاملات"""
        employee = EmployeeService.get_employee(employee_id)
        employee.is_active = False
        employee.save()
        return employee

    @staticmethod
    def get_employee(employee_id):
        """جلب موظف معين مع رتبته"""
        return get_object_or_404(Employee.objects.select_related('rank'), id=employee_id)

    @staticmethod
    def list_employees(filters=None):
        """قائمة الموظفين مع إمكانية الفلترة (مثلاً: الرتبة، النشطين)"""
        queryset = Employee.objects.select_related('rank').all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    # --- ثانياً: منطق الحصص (Quota Logic) ---

    @staticmethod
    def get_effective_weekly_quota(employee_id):
        """تطبيق خوارزمية الاختيار: الـ Override أولاً ثم الرتبة"""
        employee = EmployeeService.get_employee(employee_id)
        if employee.weekly_quota_override is not None:
            return employee.weekly_quota_override
        return employee.rank.default_weekly_quota

    @staticmethod
    def get_effective_monthly_quota(employee_id):
        """تطبيق خوارزمية الاختيار للحصة الشهرية"""
        employee = EmployeeService.get_employee(employee_id)
        if employee.monthly_quota_override is not None:
            return employee.monthly_quota_override
        return employee.rank.default_monthly_quota

    # --- ثالثاً: الدوال التحليلية (Analytics) ---

    @staticmethod
    def get_employee_total_additions(employee_id, start_date=None, end_date=None):
        """حساب إجمالي الحصص المضافة للموظف (Periodic + Trip Support)"""
        filters = Q(employee_id=employee_id, transaction_type='addition')
        if start_date and end_date:
            filters &= Q(date__range=[start_date, end_date])
            
        result = FuelTransaction.objects.filter(filters).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def get_employee_total_consumption(employee_id, start_date=None, end_date=None):
        """حساب إجمالي ما استهلكه (صرفه) الموظف فعلياً"""
        filters = Q(employee_id=employee_id, transaction_type='issue')
        if start_date and end_date:
            filters &= Q(date__range=[start_date, end_date])
            
        result = FuelTransaction.objects.filter(filters).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def get_employee_current_balance(employee_id):
        """كشف حساب لحظي: (الإضافات - المصروفات)"""
        additions = EmployeeService.get_employee_total_additions(employee_id)
        consumption = EmployeeService.get_employee_total_consumption(employee_id)
        return additions - consumption