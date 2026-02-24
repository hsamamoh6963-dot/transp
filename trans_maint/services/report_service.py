from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import datetime
from ..models import Employee, Vehicle, Trip, Accident, MaintenanceRequest, FuelTransaction

class ReportService:

    @staticmethod
    def _parse_dates(start_date, end_date):
        """دالة داخلية لتحويل النصوص إلى تواريخ واعية (Aware)"""
        if isinstance(start_date, str) and start_date:
            start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        if isinstance(end_date, str) and end_date:
            # نجعل نهاية اليوم هي الساعة 23:59:59 لضمان شمول كل العمليات في ذلك اليوم
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        
        return start_date, end_date

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

            start, end = ReportService._parse_dates(start_date, end_date)

            queryset = FuelTransaction.objects.filter(
                transaction_type='issue', )
            
            if start and end:
                queryset = queryset.filter(date__range=[start, end])

            if employee_id:
                queryset = queryset.filter(employee_id=employee_id)
            if vehicle_id:
                queryset = queryset.filter(vehicle_id=vehicle_id)
            
            return queryset.select_related('employee', 'vehicle', 'trip')

    # 2️⃣ Trip Report Service: تحليل النشاط الميداني
    class TripReports:
        @staticmethod
        def get_trip_statistics(start_date, end_date):
            start, end = ReportService._parse_dates(start_date, end_date)
            
            queryset = Trip.objects.all()
            if start and end:
                queryset = queryset.filter(start_date__range=[start, end])
            
            total_trips = queryset.count()
            vehicle_count = Vehicle.objects.count() or 1 # حماية من القسمة على صفر
            
            return {
                "total_trips": total_trips,
                "top_destinations": queryset.values('area').annotate(count=Count('id')).order_by('-count')[:5],
                "avg_trips_per_vehicle": round(total_trips / vehicle_count, 2)
            }

    # 3️⃣ Accident & Maintenance Reports: تحليل جودة الأصول والخسائر
    class AssetReports:
        @staticmethod
        def get_accident_cost_summary(start_date, end_date):
            start, end = ReportService._parse_dates(start_date, end_date)
            
            queryset = Accident.objects.all()
            if start and end:
                queryset = queryset.filter(date_occurred__range=[start, end])
                
            return queryset.aggregate(
                total_cost=Sum('damage_cost'),
                accident_count=Count('id')
            )

        @staticmethod
        def get_open_maintenance_report(start_date=None, end_date=None):
            """تقرير المتابعة والضغط على الورش مع دعم الفلترة الزمنية"""
            # نبدأ بالمركبات المعلقة (قيد المعالجة)
            queryset = MaintenanceRequest.objects.filter(status='pending').select_related('vehicle', 'workshop')
            
            # تحويل التواريخ باستخدام الدالة المساعدة التي أنشأناها سابقاً
            start, end = ReportService._parse_dates(start_date, end_date)
            
            if start and end:
                # الفلترة بناءً على تاريخ الإبلاغ (date_reported)
                queryset = queryset.filter(date_reported__range=[start.date(), end.date()])
            
            return queryset.order_by('-date_reported')
        
        
    # 4️⃣ Quota Report Service: الرقابة والامتثال
    class QuotaReports:
        @staticmethod
        def get_over_consumption_report(threshold_percent=90):
            """نسخة محسنة جداً للأداء (بدون حلقات تكرارية بطيئة)"""
            # نجلب استهلاك كل موظف وإجمالي الإضافات في طلب واحد (Query)
            employees = Employee.objects.filter(is_active=True).annotate(
                total_added=Sum('fueltransaction__quantity', filter=Q(fueltransaction__transaction_type='addition')),
                total_issued=Sum('fueltransaction__quantity', filter=Q(fueltransaction__transaction_type='issue'))
            )
            
            over_list = []
            for emp in employees:
                added = emp.total_added or 0
                issued = emp.total_issued or 0
                
                if added > 0:
                    consumption_pct = (issued / added) * 100
                    if consumption_pct >= threshold_percent:
                        over_list.append({
                            "employee": emp.name,
                            "consumption_pct": round(consumption_pct, 2),
                            "remaining": round(added - issued, 2)
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