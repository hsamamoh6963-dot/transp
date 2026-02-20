from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from ..models import Employee, Vehicle, Trip, Accident, MaintenanceRequest, FuelTransaction

class ReportService:

    # 1️⃣ Fuel Report Service: تحليل الطاقة والموارد
    class FuelReports:
        @staticmethod
        def get_consumption_summary(filters=None):
            """تحليل استهلاك الوقود العام حسب الموظف أو المركبة"""
            queryset = FuelTransaction.objects.filter(transaction_type='issue')
            if filters:
                queryset = queryset.filter(**filters)
            
            by_employee = queryset.values('employee__name').annotate(total=Sum('quantity')).order_by('-total')
            by_vehicle = queryset.values('vehicle__plate_number').annotate(total=Sum('quantity')).order_by('-total')
            
            return {"by_employee": by_employee, "by_vehicle": by_vehicle}

        @staticmethod
        def get_monthly_summary(year, month):
            """تقرير المطابقة الشهري"""
            return FuelTransaction.objects.filter(
                date__year=year, date__month=month
            ).values('transaction_type').annotate(total=Sum('quantity'))
        
        @staticmethod
        def get_detailed_consumption_report(start_date, end_date, employee_id=None, vehicle_id=None):
            """تقرير تفصيلي للاستهلاك حسب الفرد أو المركبة لفترة زمنية"""
            queryset = FuelTransaction.objects.filter(
                transaction_type='issue',
                date__range=[start_date, end_date]
            )
            if employee_id:
                queryset = queryset.filter(employee_id=employee_id)
            if vehicle_id:
                queryset = queryset.filter(vehicle_id=vehicle_id)
            
            return queryset.select_related('employee', 'vehicle', 'trip')

    # 2️⃣ Trip Report Service: تحليل النشاط الميداني
    class TripReports:
        @staticmethod
        def get_trip_statistics(start_date, end_date):
            """تحليل متوسط الرحلات والوجهات الأكثر تردداً"""
            queryset = Trip.objects.filter(start_date__range=[start_date, end_date])
            stats = {
                "total_trips": queryset.count(),
                "top_destinations": queryset.values('area').annotate(count=Count('id')).order_by('-count')[:5],
                "avg_trips_per_vehicle": queryset.count() / (Vehicle.objects.count() or 1)
            }
            return stats

    # 3️⃣ Accident & Maintenance Reports: تحليل جودة الأصول والخسائر
    class AssetReports:
        @staticmethod
        def get_accident_cost_summary(start_date, end_date):
            """تقرير الخسائر المادية الموجه للقيادة"""
            return Accident.objects.filter(
                date_occurred__range=[start_date, end_date]
            ).aggregate(
                total_cost=Sum('damage_cost'),
                accident_count=Count('id')
            )

        @staticmethod
        def get_open_maintenance_report():
            """تقرير المتابعة والضغط على الورش (المركبات العالقة)"""
            return MaintenanceRequest.objects.filter(status='pending').select_related('vehicle', 'workshop')

    # 4️⃣ Quota Report Service: الرقابة والامتثال
    class QuotaReports:
        @staticmethod
        def get_over_consumption_report(threshold_percent=90):
            """كشف الموظفين الذين استهلكوا معظم حصتهم (تجاوز الـ 90%)"""
            # ملاحظة: هذا التقرير يتطلب دالة حسابية لمقارنة الاستهلاك بالرصيد المضاف
            all_employees = Employee.objects.all()
            over_list = []
            for emp in all_employees:
                # نستخدم الخدمات السابقة التي بنيناها للحساب
                from .employee_service import EmployeeService
                balance = EmployeeService.get_employee_current_balance(emp.id)
                added = EmployeeService.get_employee_total_additions(emp.id)
                
                if added > 0:
                    consumption_pct = ((added - balance) / added) * 100
                    if consumption_pct >= threshold_percent:
                        over_list.append({
                            "employee": emp.name,
                            "consumption_pct": round(consumption_pct, 2),
                            "remaining": balance
                        })
            return over_list

        @staticmethod
        def get_unused_quota_report():
            """تقرير توفير الموارد: الموظفون الذين لا يستهلكون حصصهم"""
            # الموظفون الذين لديهم رصيد عالي ولم يجروا عمليات صرف (issue) مؤخراً
            three_months_ago = timezone.now() - timezone.timedelta(days=90)
            active_spenders = FuelTransaction.objects.filter(
                transaction_type='issue', 
                date__gte=three_months_ago
            ).values_list('employee_id', flat=True)
            
            return Employee.objects.exclude(id__in=active_spenders).values('name', 'rank__name')