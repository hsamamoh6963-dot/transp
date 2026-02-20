from django.db.models import Sum, Count, Q
from django.utils import timezone
from ..models import Employee, Vehicle, Trip, Accident, MaintenanceRequest, FuelTransaction

class DashboardService:

    # --- أولاً: المؤشرات التشغيلية (Real-time Operations) ---

    @staticmethod
    def get_total_employees():
        return Employee.objects.filter(is_active=True).count()

    @staticmethod
    def get_total_vehicles():
        return Vehicle.objects.count()

    @staticmethod
    def get_active_trips_count():
        """عدد المركبات/الموظفين في الميدان حالياً"""
        return Trip.objects.filter(end_date__isnull=True).count()

    @staticmethod
    def get_open_accidents_count():
        """عدد ملفات الحوادث التي لم تُغلق بعد"""
        return Accident.objects.filter(status='open').count()

    @staticmethod
    def get_pending_maintenance_count():
        """عدد المركبات المتعطلة وتنتظر الإصلاح"""
        return MaintenanceRequest.objects.filter(status='pending').count()

    # --- ثانياً: التحليل المالي والوقود (Resource Monitoring) ---

    @staticmethod
    def get_total_fuel_issued_today():
        today = timezone.now().date()
        result = FuelTransaction.objects.filter(
            transaction_type='issue',
            date__date=today
        ).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def get_total_fuel_issued_this_month():
        now = timezone.now()
        result = FuelTransaction.objects.filter(
            transaction_type='issue',
            date__year=now.year,
            date__month=now.month
        ).aggregate(total=Sum('quantity'))
        return result['total'] or 0.0

    @staticmethod
    def get_top_consuming_employees(limit=5):
        """تحديد الموظفين الأكثر استهلاكاً (النقاط الساخنة)"""
        return Employee.objects.annotate(
            total_consumption=Sum(
                'fueltransaction__quantity', 
                filter=Q(fueltransaction__transaction_type='issue')
            )
        ).order_by('-total_consumption')[:limit]

    @staticmethod
    def get_low_balance_employees(threshold=10.0):
        """خدمة استباقية: الموظفون الذين رصيدهم أقل من الحد المسموح"""
        # نستخدم annotate لحساب الرصيد (الإضافات - السحوبات) لكل موظف
        employees = Employee.objects.annotate(
            balance=(
                Sum('fueltransaction__quantity', filter=Q(fueltransaction__transaction_type='addition')) or 0.0
            ) - (
                Sum('fueltransaction__quantity', filter=Q(fueltransaction__transaction_type='issue')) or 0.0
            )
        ).filter(balance__lt=threshold)
        return employees

    # --- ثالثاً: الرقابة على الخسائر (Loss Tracking) ---

    @staticmethod
    def get_total_maintenance_cost_this_month():
        now = timezone.now()
        result = MaintenanceRequest.objects.filter(
            status='completed',
            date_reported__year=now.year,
            date_reported__month=now.month
        ).aggregate(total=Sum('cost'))
        return result['total'] or 0.0

    @staticmethod
    def get_total_accident_cost_this_month():
        now = timezone.now()
        result = Accident.objects.filter(
            date_occurred__year=now.year,
            date_occurred__month=now.month
        ).aggregate(total=Sum('damage_cost'))
        return result['total'] or 0.0
    

    # --- رابعاً: خدمات الدعم الاستراتيجي (Strategic Support) ---
    @staticmethod
    def get_general_stats():
        """1️⃣ إحصائيات عامة: الكتل الرئيسية"""
        return {
            'total_employees': Employee.objects.filter(is_active=True).count(),
            'total_vehicles': Vehicle.objects.count(),
            'active_vehicles': Vehicle.objects.filter(status='active').count(),
            'trips_this_month': Trip.objects.filter(
                start_date__month=timezone.now().month,
                start_date__year=timezone.now().year
            ).count(),
            'open_accidents': Accident.objects.filter(status='open').count(),
            'pending_maintenance': MaintenanceRequest.objects.filter(status='pending').count(),
        }

    @staticmethod
    def get_fuel_analytics():
        """2️⃣ إحصائيات الوقود: مراقبة الاستهلاك"""
        now = timezone.now()
        
        # إجمالي الوقود المصروف هذا الشهر
        monthly_issued = FuelTransaction.objects.filter(
            transaction_type='issue',
            date__month=now.month,
            date__year=now.year
        ).aggregate(total=Sum('quantity'))['total'] or 0.0

        # أعلى موظف استهلاكاً هذا الشهر
        top_employee = FuelTransaction.objects.filter(
            transaction_type='issue',
            date__month=now.month
        ).values('employee__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty').first()

        # أعلى مركبة استهلاكاً
        top_vehicle = FuelTransaction.objects.filter(
            transaction_type='issue',
            date__month=now.month
        ).values('vehicle__plate_number').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty').first()

        return {
            'monthly_issued': monthly_issued,
            'top_employee': top_employee,
            'top_vehicle': top_vehicle,
        }

    @staticmethod
    def get_financial_metrics():
        """3️⃣ المقاييس المالية: تكاليف الأزمات"""
        now = timezone.now()
        
        # تكاليف الحوادث المسجلة هذا الشهر
        accident_costs = Accident.objects.filter(
            date_occurred__month=now.month,
            date_occurred__year=now.year
        ).aggregate(total=Sum('damage_cost'))['total'] or 0.0

        # تكاليف الصيانة المكتملة هذا الشهر
        maintenance_costs = MaintenanceRequest.objects.filter(
            status='completed',
            date_reported__month=now.month,
            date_reported__year=now.year
        ).aggregate(total=Sum('cost'))['total'] or 0.0

        return {
            'monthly_accident_costs': accident_costs,
            'monthly_maintenance_costs': maintenance_costs,
            'total_losses': float(accident_costs) + float(maintenance_costs)
        }

    @staticmethod
    def get_last_sync_time():
        """4️⃣ وقت آخر تحديث: لإعطاء طابع لحظي للنظام"""
        # يمكن ببساطة إرجاع الوقت الحالي، أو وقت آخر عملية تسجيل (Trip/Fuel)
        return timezone.now()