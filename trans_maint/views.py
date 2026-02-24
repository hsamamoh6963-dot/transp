
from urllib import request
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Count, Sum ,F, ExpressionWrapper, FloatField ,Q
from django.db import models
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import QuerySet

from .models import Vehicle ,Trip, Workshop 
 


from .services.rank_service import RankService
from .services.employee_service import EmployeeService
from .services.fuel_service import FuelService
from .services.trip_service import TripService
from .services.vehicle_service import VehicleService
from .services.accident_service import AccidentService
from .services.maintenance_service import MaintenanceService
from .services.workshop_service import WorkshopService
from .services.dashboard_service import DashboardService
from .services.report_service import ReportService


#===============================================================
# 1️⃣ Views for Military Ranks Management - عرض، إضافة، تعديل، حذف الرتب
#===============================================================

# 1️⃣ Rank List View - عرض دليل الرتب
class RankListView(View):
    template_name = 'modules/ranks/rank_list.html'

    def get(self, request):
        # جلب كل الرتب باستخدام الخدمة
        ranks = RankService.list_ranks()
        
        context = {
            'ranks': ranks,
            'total_ranks': ranks.count(),
            # إحصائية سريعة لمتوسط الحصص (اختياري)
            'avg_weekly': sum(r.default_weekly_quota for r in ranks) / ranks.count() if ranks.exists() else 0
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        rank_id = request.POST.get('rank_id')
        
        # تجهيز البيانات من الفورم
        data = {
            'name': request.POST.get('name'),
            'default_weekly_quota': request.POST.get('default_weekly_quota', 0.0),
            'default_monthly_quota': request.POST.get('default_monthly_quota', 0.0),
        }

        try:
            if action == 'create':
                RankService.create_rank(data)
                messages.success(request, "تم إضافة الرتبة الجديدة بنجاح.")
            
            elif action == 'update':
                RankService.update_rank(rank_id, data)
                messages.success(request, "تم تحديث بيانات الرتبة والحصص بنجاح.")
            
            elif action == 'delete':
                # الخدمة محمية بـ PROTECT في الموديل، ستفشل إذا وجد موظفون
                RankService.delete_rank(rank_id)
                messages.success(request, "تم حذف الرتبة نهائياً.")

        except Exception as e:
            # معالجة خطأ الحذف المرتبط بموظفين بشكل ودود
            if "PROTECT" in str(e) or "protected" in str(e).lower():
                messages.error(request, "لا يمكن حذف الرتبة لوجود موظفين مسجلين بها.")
            else:
                messages.error(request, f"حدث خطأ: {str(e)}")

        return redirect('rank_list')






#===============================================================
# 2️⃣ Views for Employee Management - عرض، إضافة، تعطيل الموظفين
#===============================================================
    

class EmployeeListView(View):
    template_name = 'modules/employees/employee_list.html'

    def get(self, request):
        # الفلترة والبحث
        filters = {}
        if request.GET.get('rank'):
            filters['rank_id'] = request.GET.get('rank')
        if request.GET.get('search'):
            filters['name__icontains'] = request.GET.get('search')
        
        context = {
            'employees': EmployeeService.list_employees(filters),
            'ranks': RankService.list_ranks(), # لعرضها في قائمة الفلترة والفورم
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        employee_id = request.POST.get('employee_id')
        
        # تجهيز البيانات مع معالجة الـ Override (إما قيمة أو None)
        data = {
            'name': request.POST.get('name'),
            'military_number': request.POST.get('military_number'),
            'rank_id': request.POST.get('rank'),
            'weekly_quota_override': request.POST.get('weekly_override') or None,
            'monthly_quota_override': request.POST.get('monthly_override') or None,
        }

        try:
            if action == 'create':
                EmployeeService.create_employee(data)
                messages.success(request, "تم إضافة الموظف بنجاح.")
            elif action == 'update':
                EmployeeService.update_employee(employee_id, data)
                messages.success(request, "تم تحديث بيانات الموظف.")
            elif action == 'deactivate':
                EmployeeService.deactivate_employee(employee_id)
                messages.warning(request, "تم تعطيل حساب الموظف.")
        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")

        return redirect('employee_list')
    
# 2️⃣ Employee Detail View - العرض الشامل (Aggregator)
class EmployeeDetailView(View):
    template_name = 'modules/employees/employee_detail.html'

    def get(self, request, pk):
        # 1. طلب البيانات من الخدمات المختلفة (توزيع المسؤوليات)
        employee = EmployeeService.get_employee(pk)
        
        # 2. بيانات المحفظة المالية (Fuel Service)
        balance = FuelService.calculate_employee_balance(employee.id)
        total_consumption = EmployeeService.get_employee_total_consumption(employee.id)
        
        # 3. بيانات الحركة والمخاطر (Trip & Accident Services)
        trips = TripService.list_trips({'employee_id': employee.id})
        # نفترض وجود خدمة للحوادث تم بناؤها سابقاً
        # accidents = AccidentService.get_vehicle_accident_history(...) 

        # 4. تجهيز حقيبة البيانات (Context) بنظام الـ Tabs
        context = {
            'employee': employee,
            'balance': balance,
            'total_consumption': total_consumption,
            'trips': trips,
            'effective_weekly': EmployeeService.get_effective_weekly_quota(employee.id),
            'effective_monthly': EmployeeService.get_effective_monthly_quota(employee.id),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        action = request.POST.get('action')
        try:
            if action == 'activate':
                employee = EmployeeService.get_employee(pk)
                employee.is_active = True
                employee.save()
                messages.success(request, "تم إعادة تنشيط الموظف بنجاح.")
            elif action == 'deactivate':
                EmployeeService.deactivate_employee(pk)
                messages.warning(request, "تم تعطيل حساب الموظف.")
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
        
        return redirect('employee_detail', pk=pk)


#===============================================================
# 3️⃣ Views for Vehicle Management - عرض، إضافة، تعطيل المركبات
#===============================================================


# 1️⃣ Vehicle List View - البحث الذكي والفلترة
class VehicleListView(View):
    template_name = 'modules/vehicles/vehicle_list.html'

    def get(self, request):
        # قراءة الفلاتر والبحث برقم اللوحة
        filters = {}
        
        plate_search = request.GET.get('plate_search')
        if plate_search:
            filters['plate_number__icontains'] = plate_search

        status = request.GET.get('status', 'active')
        if status == 'all':
        # إذا اختار "الكل" لا نضيف فلتر الحالة (سيجلب الجميع)
            pass 
        elif status:
            # إذا اختار حالة محددة (active أو inactive)
            filters['status'] = status
        else:
            # الحالة الافتراضية عند فتح الصفحة لأول مرة
            filters['status'] = 'active'

        # استدعاء الخدمة مع select_related لبيانات المالك (السائق الحالي)
        vehicles = VehicleService.list_vehicles(filters)
        
        context = {
            'vehicles': vehicles,
            'status_options': ['active', 'inactive', 'under_repair'],
            'employees': EmployeeService.list_employees({'is_active': True}),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # تمييز العملية: هل هي تحديث لمركبة موجودة أم إضافة جديدة؟
        vehicle_id = request.POST.get('vehicle_id') 
        action = request.POST.get('action') # 'save' أو 'deactivate'

        try:
            if vehicle_id:
                vehicle = VehicleService.get_vehicle(vehicle_id)
                # قيد أمني: إذا كانت السيارة تحت الصيانة، لا يمكن تغيير حالتها يدوياً من هنا
                if vehicle.status == 'under_repair' and action == 'deactivate':
                    messages.error(request, "لا يمكن تعطيل مركبة وهي قيد الإصلاح في الورشة.")
                    return redirect('vehicle_list')
                
            if action == 'deactivate':
                VehicleService.update_vehicle(vehicle_id, {'status': 'inactive'})
                messages.warning(request, "تم إخراج المركبة من الخدمة.")
            else:
                data = {
                    'plate_number': request.POST.get('plate_number'),
                    'vehicle_type': request.POST.get('vehicle_type'),
                    'model': request.POST.get('model'),
                    'status': request.POST.get('status'),
                    'owner_id': request.POST.get('owner'),
                }
                if data['status'] == 'under_repair' and (not vehicle_id or vehicle.status != 'under_repair'):
                    messages.error(request, "حالة 'تحت الصيانة' يتم تعيينها تلقائياً من قسم الورش أو الحوادث فقط.")
                    return redirect('vehicle_list')
                
                if vehicle_id: # تحديث
                    VehicleService.update_vehicle(vehicle_id, data)
                    messages.success(request, "تم تحديث بيانات المركبة بنجاح.")
                else: # إضافة جديدة
                    VehicleService.create_vehicle(data)
                    messages.success(request, "تمت إضافة المركبة الجديدة للأسطول.")
                    
        except Exception as e:
            messages.error(request, f"خطأ في تنفيذ العملية: {str(e)}")
            
        return redirect('vehicle_list')


# 2️⃣ Vehicle Detail View - العرض التحليلي بنظام الـ Tabs
class VehicleDetailView(View):
    template_name = 'modules/vehicles/vehicle_detail.html'

    # داخل دالة get في VehicleDetailView
    def get(self, request, pk):
        # استخدام select_related لجلب بيانات المالك (السائق) مرة واحدة
        vehicle = VehicleService.get_vehicle(pk) 

        context = {
            'vehicle': vehicle,
            'total_fuel': VehicleService.get_vehicle_total_fuel(pk),
            'trip_count': VehicleService.get_vehicle_trip_count(pk),
            'maintenance_cost': VehicleService.get_vehicle_total_maintenance_cost(pk),
            'accident_cost': VehicleService.get_vehicle_total_accident_cost(pk),
            
            # التعديل هنا: استخدام prefetch_related (داخلياً) أو الفلترة المباشرة مع التحسين
            'recent_trips': vehicle.trips.select_related('employee').all().order_by('-start_date')[:5],
            'recent_maintenance': vehicle.maintenancerequest_set.all().order_by('-date_reported')[:5],
            'recent_accidents': vehicle.accident_set.all().order_by('-date_occurred')[:5],
        }   
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        action = request.POST.get('action')
        vehicle = VehicleService.get_vehicle(pk)
        
        try:
            if action == 'activate':
                vehicle.status = 'active'
                vehicle.save()
                messages.success(request, f"تم إعادة تنشيط المركبة {vehicle.plate_number} بنجاح.")
            elif action == 'deactivate':
                vehicle.status = 'inactive'
                vehicle.save()
                messages.warning(request, f"تم إيقاف تنشيط المركبة {vehicle.plate_number}.")
        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")
            
        return redirect('vehicle_detail', pk=pk)
    

#===============================================================
# 4️⃣ Views for Trip Management - عرض، إضافة، إنهاء الرحلات
#===============================================================


# 1️⃣ Trip List View - تحليل النشاط الميداني
class TripListView(View): # الاسم الجديد المقترح للـ TripListView
    template_name = 'modules/trip/trip_list.html'

    def get(self, request):
        # 1. تجميع الفلاتر
        filters = {}
        status = request.GET.get('status', 'active') # الافتراضي: الرحلات القائمة
        
        if status == 'active':
            filters['end_date__isnull'] = True
        elif status == 'closed':
            filters['end_date__isnull'] = False

        if request.GET.get('employee'):
            filters['employee_id'] = request.GET.get('employee')

        # 2. تنفيذ الاستعلام
        trips = TripService.list_trips(filters)

        # 3. بيانات المودالات (Modals Data)
        context = {
            'trips': trips,
            'employees': EmployeeService.list_employees({'is_active': True}),
            'available_vehicles': VehicleService.list_vehicles({'status': 'active'}),
            'status_selected': status, # لنعرف أي زر فلتر مفعل في الـ HTML
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        
        try:
            if action == 'create':
                # 1. جلب الـ IDs من الفورم
                vehicle_id = request.POST.get('vehicle')
                employee_id = request.POST.get('employee')

                # 2. تحويل الـ IDs إلى كائنات (Objects) حقيقية
                # هذا ما تحتاجه السيرفس لكي لا يظهر خطأ 'NoneType'
                from .models import Vehicle, Employee
                vehicle_obj = get_object_or_404(Vehicle, id=vehicle_id)
                employee_obj = get_object_or_404(Employee, id=employee_id)

                # 3. تجهيز البيانات وتمرير الكائنات بدلاً من الـ IDs
                data = {
                    'vehicle': vehicle_obj,    # نمرر الكائن نفسه
                    'employee': employee_obj,  # نمرر الكائن نفسه
                    'area': request.POST.get('area'),
                    'trip_type': request.POST.get('trip_type'),
                    'fuel_quota_granted': float(request.POST.get('fuel_quota', 0) or 0),
                    'start_date': timezone.now(),
                }

                # استدعاء السيرفس الآن سيعمل لأنها ستجد vehicle.id و employee.id
                TripService.create_trip_with_quota(data)
                messages.success(request, "تم بدء الرحلة بنجاح.")

            elif action == 'close':
                trip_id = request.POST.get('trip_id')
                TripService.end_trip(trip_id)
                messages.success(request, "تم إغلاق الرحلة.")

        except Exception as e:
            messages.error(request, f"حدث خطأ: {str(e)}")

        return redirect('trip_list')
    

# 4️⃣ Trip Detail View - العرض الشامل للرحلة
class TripDetailView(View):
    template_name = 'modules/trip/trip_detail.html'

    def get(self, request, pk):
        # جلب الرحلة مع بيانات المركبة والموظف وعملية الوقود المرتبطة في استعلام واحد
        trip = get_object_or_404(
            Trip.objects.select_related('vehicle', 'employee', 'fuel_transaction'), 
            id=pk
        )
        
        # جلب الحوادث المرتبطة بهذه الرحلة فقط
        accidents = trip.accident_set.all() 
        
        # حساب المدة الزمنية
        duration = TripService.get_trip_duration(pk)
        
        context = {
            'trip': trip,
            'accidents': accidents,
            'duration': duration,
        }
        return render(request, self.template_name, context)
    

#===============================================================
# 5️⃣ Views for Fuel Management - سجل الوقود، الإيداع، والتعديلات
#===============================================================


# 1️⃣ Fuel Log List - السجل العام والرقابة
class FuelLogListView(View):
    template_name = 'modules/fuel/fuel.html'

    def get(self, request):
        # تجهيز الفلاتر المتقدمة
        filters = {}
        
        # البحث عن موظف معين (بالاسم أو الرقم العسكري)
        employee_search = request.GET.get('employee_search')
        if employee_search:
            filters['employee__name__icontains'] = employee_search
            
        # فلترة حسب المركبة
        if request.GET.get('vehicle'):
            filters['vehicle_id'] = request.GET.get('vehicle')
            
        # فلترة حسب الحالة (نوع المعاملة: إضافة/صرف)
        if request.GET.get('type'):
            filters['transaction_type'] = request.GET.get('type')

        # فلترة حسب التاريخ (نطاق زمني)
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if start_date and end_date:
            # نستخدم __date للوصول للجزء الخاص بالتاريخ فقط في DateTimeField
            # ونستخدم __gte (أكبر من أو يساوي) و __lte (أصغر من أو يساوي) لضمان الدقة
            filters['date__date__gte'] = start_date
            filters['date__date__lte'] = end_date
        elif start_date:
            filters['date__date'] = start_date

                # استدعاء الحركات بناءً على الفلاتر
        logs = FuelService.list_transactions(filters)
        
        # ميزة "التجميع" (Grouping) للاحصائيات السريعة في الواجهة
        summary = logs.aggregate(
            total_issued=Sum('quantity', filter=models.Q(transaction_type='issue')),
            total_added=Sum('quantity', filter=models.Q(transaction_type='addition'))
        )

        context = {
            'transactions': logs,           # غيرنا 'logs' إلى 'transactions'
            'fuel_stats': {                 # غيرنا 'summary' إلى 'fuel_stats'
                'monthly_issued': summary['total_issued'] or 0,
                'total_additions': summary['total_added'] or 0,
                'top_employee': logs.values('employee__name').annotate(total=Sum('quantity')).order_by('-total').first()
            },
            'vehicles': VehicleService.list_vehicles(),
            'employees': EmployeeService.list_employees({'is_active': True}),
        }
        return render(request, self.template_name, context)

# 2️⃣ Fuel Add View - الإيداع المستقل (خارج الرحلة)
class FuelAddView(View):
       
    def post(self, request):
        try:
            # قراءة نوع المعاملة من الفورم
            t_type = request.POST.get('transaction_type')
            qty = float(request.POST.get('quantity'))
            emp_id = request.POST.get('employee')
            veh_id = request.POST.get('vehicle')
            notes = request.POST.get('notes') # في الـ HTML الحقل اسمه notes وليس reason

            if t_type == 'issue':
                FuelService.issue_fuel(emp_id, veh_id, qty, notes)
            else:
                FuelService.add_fuel(emp_id, veh_id, qty, notes=notes)

            messages.success(request, "تم تسجيل العملية بنجاح.")
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
        
        return redirect('fuel_log_list')
    
# 3️⃣ Fuel Adjustment View - إدارة الاستثناءات وتصحيح الأخطاء
class FuelAdjustmentView(View):
  
    def post(self, request):
        adj_type = request.POST.get('adjustment_type') # 'addition' or 'issue'
        employee_id = request.POST.get('employee')
        vehicle_id = request.POST.get('vehicle') # 
        quantity = float(request.POST.get('quantity'))
        reason = request.POST.get('reason')

        if not reason:
            messages.error(request, "يجب ذكر سبب التعديل للرقابة الإدارية.")
            return self.get(request)

        try:
            if adj_type == 'issue':
                # التأكد من أن التعديل بالخصم لا يؤدي لرصيد سالب
                is_ok, msg = FuelService.validate_sufficient_balance(employee_id, quantity)
                if not is_ok:
                    raise ValueError(msg)
                FuelService.issue_fuel(employee_id, vehicle_id, quantity, notes=f"تعديل إداري: {reason}")
            else:
                FuelService.add_fuel(employee_id, vehicle_id, quantity, notes=f"تعديل إداري: {reason}")
            
            messages.warning(request, "تم تنفيذ التعديل الإداري بنجاح.")
        except Exception as e:
            messages.error(request, f"فشل التعديل: {str(e)}")
            
        return redirect('fuel_log_list') # العودة للسجل الرئيسي
#===============================================================
# 6️⃣ Views for Accident Management - عرض، إضافة، إغلاق الحوادث
#===============================================================



# 1️⃣ Accident List View - الرقابة والبحث المتقدم
class AccidentListView(View):
    template_name = 'modules/accidents/accident_list.html'

    def get(self, request):
        # تجهيز الفلاتر المتقدمة (البحث والفلترة المالية)
        filters = {}
        
        # البحث برقم اللوحة أو اسم الموظف
        plate = request.GET.get('plate_number')
        emp_name = request.GET.get('employee_name')
        if plate:
            filters['vehicle__plate_number__icontains'] = plate
        if emp_name:
            filters['trip__employee__name__icontains'] = emp_name
            
        # فلترة حسب الحالة (مفتوح/مغلق)
        if request.GET.get('status'):
            filters['status'] = request.GET.get('status')
            
        # فلترة ذكية حسب التكلفة (مثلاً: الحوادث التي تكلفتها أكبر من X)
        min_cost = request.GET.get('min_cost')
        if min_cost:
            filters['damage_cost__gte'] = min_cost

        accidents = AccidentService.list_accidents(filters)
        active_trips = TripService.list_trips({'end_date__isnull': True})
        
        context = {
            'accidents': accidents,
            'active_trips': active_trips,
            'total_damages': AccidentService.get_total_accident_cost(),
            
        }
        return render(request, self.template_name, context)

# 2️⃣ Accident Create View - موثق الحدث (Trigger View)
class AccidentCreateView(View):
    template_name = 'modules/accidents/accident_form.html'

    def get(self, request):
        # لا نظهر إلا الرحلات النشطة أو التي انتهت مؤخراً لربط الحادث بها
        context = {
            'active_trips': TripService.list_trips({'end_date__isnull': True}),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        trip_id = request.POST.get('trip')
        try:
            # جلب الرحلة للتأكد من وجودها قبل البدء
            trip = TripService.get_trip(trip_id)
            raw_cost = request.POST.get('damage_cost') or '0'
            
            data = {
                'trip': trip,           # أصبح مدعوماً الآن في الموديل
                'vehicle': trip.vehicle,
                'description': request.POST.get('description'),
                'damage_cost': float(raw_cost), # تم التعديل ليطابق الموديل
                'date_occurred': request.POST.get('date'),
                'status': 'open',
                }
            
            # الخدمة ستقوم بإنشاء الحادث وتغيير حالة المركبة لـ "خارج الخدمة" فوراً
            AccidentService.create_accident(data)
            messages.warning(request, "تم تسجيل الحادث وإخراج المركبة من الخدمة التشغيلية فوراً.")
            return redirect('accident_list')
            
        except Exception as e:
            messages.error(request, f"فشل تسجيل الحادث: {str(e)}")
            return render(request, self.template_name, {'active_trips': TripService.list_trips({'end_date__isnull': True})})

# 3️⃣ Accident Detail View - العرض الشامل والربط بالصيانة
class AccidentDetailView(View):
    template_name = 'modules/accidents/accident_detail.html'

    def get(self, request, pk):
        accident = AccidentService.get_accident(pk)
        context = {
            'accident': accident,
            'vehicle_history': AccidentService.get_vehicle_accident_history(accident.vehicle.id)
        }
        return render(request, self.template_name, context)

# 4️⃣ Accident Close View - الإغلاق المالي والإداري
class AccidentCloseView(View):
    def post(self, request, pk):
        final_cost = request.POST.get('final_cost')
        if not final_cost:
            messages.error(request, "يجب إدخال التكلفة النهائية لإغلاق ملف الحادث.")
            return redirect('accident_detail', pk=pk)

        try:
            AccidentService.close_accident(pk, final_cost=float(final_cost))
            messages.success(request, "تم إغلاق ملف الحادث وتوثيق التكاليف النهائية.")
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
            
        return redirect('accident_list')
    




#===============================================================
# 7️⃣ Views for Maintenance Management - عرض، إضافة، إغلاق طلبات الصيانة
#===============================================================

# 1️⃣ Maintenance & Workshop Dashboard - لوحة التحكم الشاملة
class MaintenanceDashboardView(View):
    template_name = 'modules/maintenance/maintenance_dashboard.html'

    def get(self, request):
        # --- قسم الصيانة ---
        m_filters = {}
        # البحث برقم اللوحة
        plate = request.GET.get('plate_number')
        if plate:
            m_filters['vehicle__plate_number__icontains'] = plate
        
        # الفلترة حسب الزمن (نطاق تاريخ)
        start = request.GET.get('start_date')
        end = request.GET.get('end_date')
        if start and end:
            m_filters['date_reported__range'] = [start, end]
            
        # الفلترة حسب الحالة
        if request.GET.get('status'):
            m_filters['status'] = request.GET.get('status')

        maintenance_requests = MaintenanceService.list_maintenance_requests(m_filters)

        # --- قسم الورش (Vendors) ---
        w_filters = {}
        workshops = WorkshopService.list_workshops()
        
        # فلترة الورش حسب "ضغط العمل" (عدد السيارات الحالية)
        # ملاحظة: يتم هذا الجزء عبر annotate في الـ Service لضمان الأداء
        workshops = Workshop.objects.annotate(
        current_jobs_count=Count(
            'maintenancerequest', 
            filter=Q(maintenancerequest__status='pending')
        )
    )
            
        context = {
            'requests': maintenance_requests,
            'workshops': workshops,
            'vehicles': Vehicle.objects.filter(status__in=['active', 'under_repair']),
            'total_maintenance_cost': MaintenanceService.get_total_maintenance_cost(), # استدعاء الخدمة المكتوبة
            'stats': {
                        'inactive_vehicles': Vehicle.objects.filter(status__in=['inactive', 'under_repair']).count(),
                    }
        }
        return render(request, self.template_name, context)

# 2️⃣ Maintenance Create View - فتح أمر الإصلاح
class MaintenanceCreateView(View):
    def post(self, request):
        vehicle_instance = get_object_or_404(Vehicle, id=request.POST.get('vehicle'))
        raw_cost = request.POST.get('cost') or '0' 
        data = {
            'vehicle': vehicle_instance,
            'workshop_id': request.POST.get('workshop'),
            'accident_ref_id': request.POST.get('accident_id') or None, # الربط بالحادث إن وجد
            'reason': request.POST.get('reason'),
            'cost': float(raw_cost) ,
        }
        try:
            MaintenanceService.create_maintenance_request(data)
            messages.success(request, "تم إرسال المركبة للصيانة وتحديث حالتها.")
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
        return redirect('maintenance_dashboard')

# 3️⃣ Maintenance Close View - مفتاح العودة للخدمة
class MaintenanceCloseView(View):
    def post(self, request, pk):
        actual_cost = request.POST.get('actual_cost')
        try:
            MaintenanceService.complete_maintenance_request(pk, actual_cost=float(actual_cost))
            messages.success(request, "اكتملت الصيانة. المركبة الآن متاحة للرحلات.")
        except Exception as e:
            messages.error(request, f"فشل الإغلاق: {str(e)}")
        return redirect('maintenance_dashboard')

# 4️⃣ Workshop Management (CRUD) - إدارة الورش
class WorkshopActionView(View):
    def post(self, request, pk=None):
        action = request.POST.get('action')
        
        if action == 'delete':
            try:
                WorkshopService.delete_workshop(pk)
                messages.warning(request, "تم إزالة الورشة من النظام.")
            except Exception:
                messages.error(request, "لا يمكن حذف ورشة لها سجلات صيانة سابقة.")
        
        elif action == 'create' or action == 'update':
            data = {
                'name': request.POST.get('name'),
                'address': request.POST.get('address'),
                'phone': request.POST.get('phone'),
            }
            if pk:
                WorkshopService.update_workshop(pk, data)
                messages.success(request, "تم تحديث بيانات الورشة.")
            else:
                WorkshopService.create_workshop(data)
                messages.success(request, "تم إضافة ورشة جديدة.")
                
        return redirect('maintenance_dashboard')

#===============================================================
# 8️⃣ Views for Quota Management - لوحة مراقبة الحصص، تعديل الأ
#===============================================================

#  1️⃣ Quota Overview - لوحة مراقبة الحصص (Analytic View)
class QuotaOverviewView(View):
    template_name = 'quota/quota_overview.html'

    def get(self, request):
        # البحث عن موظف معين
        filters = {}
        search = request.GET.get('search')
        if search:
            filters['name__icontains'] = search
            
        employees = EmployeeService.list_employees(filters)
        
        # تجهيز البيانات التحليلية لكل موظف
        quota_data = []
        for emp in employees:
            balance = FuelService.calculate_employee_balance(emp.id)
            total_added = EmployeeService.get_employee_total_additions(emp.id)
            
            # حساب نسبة الاستهلاك لتمثيلها شريط تقدم (Progress Bar)
            usage_pct = 0
            if total_added > 0:
                usage_pct = ((total_added - balance) / total_added) * 100

            quota_data.append({
                'employee': emp,
                'monthly_quota': EmployeeService.get_effective_monthly_quota(emp.id),
                'balance': balance,
                'usage_pct': round(usage_pct, 1)
            })

        context = {'quota_data': quota_data}
        return render(request, self.template_name, context)

# 2️⃣ Quota Adjustment - تعديل الأرصدة والاستثناءات (The Audit View)
class QuotaAdjustmentView(View):
    template_name = 'quota/adjustment_form.html'

    def get(self, request):
        # عرض الموظفين النشطين فقط لعمل التعديلات
        context = {
            'employees': EmployeeService.list_employees({'is_active': True}),
            'ranks': RankService.list_ranks() # لتعديل حصص الرتب أيضاً
        }
        return render(request, self.template_name, context)

    def post(self, request):
        target_type = request.POST.get('target_type') # 'employee' or 'rank'
        reason = request.POST.get('reason')
        amount = float(request.POST.get('amount', 0))

        if not reason:
            messages.error(request, "لا يمكن تعديل الحصص دون ذكر مبرر إداري رسمي.")
            return self.get(request)

        try:
            if target_type == 'employee':
                emp_id = request.POST.get('employee_id')
                # تسجيل الحركة كـ 'addition' (حصة استثنائية)
                FuelService.add_fuel(emp_id, None, amount, notes=f"تعديل حصة: {reason}")
                messages.success(request, f"تمت إضافة {amount} لتر كحصة استثنائية للموظف.")
            
            elif target_type == 'rank':
                # تعديل الحصة الافتراضية للرتبة (تعديل سياسات)
                rank_id = request.POST.get('rank_id')
                RankService.update_rank(rank_id, {'default_monthly_quota': amount})
                messages.warning(request, "تم تحديث الحصة الافتراضية للرتبة؛ سيؤثر هذا على جميع التابعين لها.")

            return redirect('quota_overview')
        except Exception as e:
            messages.error(request, f"فشل التعديل: {str(e)}")
            return self.get(request)

# 3️⃣ Quota History - سجل التدقيق والمراجعة
class QuotaHistoryView(View):
    template_name = 'quota/quota_history.html'

    def get(self, request, employee_id):
        employee = EmployeeService.get_employee(employee_id)
        # جلب كافة الحركات (إضافات، سحب رحلات، تعديلات إدارية)
        history = FuelService.list_transactions({'employee_id': employee_id})
        
        context = {
            'employee': employee,
            'history': history
        }
        return render(request, self.template_name, context)


#===============================================================
#
#===============================================================


# 📊 Dashboard View - مركز العمليات والقرار الاستراتيجي
class DashboardView(View):
    template_name = 'dashboard.html'

    def get(self, request):
        """
        الـ View هنا لا يحسب أي أرقام، بل يطلب "الحقيبة الجاهزة"
        من الـ DashboardService لضمان سرعة التحميل وفصل المسؤوليات.
        """
        
        # 1️⃣ استدعاء المؤشرات التشغيلية والمالية (Operational & Financial Stats)
        general_stats = DashboardService.get_general_stats()
        fuel_analytics = DashboardService.get_fuel_analytics()
        financial_metrics = DashboardService.get_financial_metrics()

        # 2️⃣ استدعاء التنبيهات (The Proactive Alerts)
        # هذا الجزء هو "العين الساهرة" التي تحمي العمليات الميدانية
        alerts = {
            'low_balance_employees': DashboardService.get_low_balance_employees(threshold=15.0),
            'pending_maintenance': DashboardService.get_pending_maintenance_count(),
            'open_accidents': DashboardService.get_open_accidents_count(),
            'long_running_trips': DashboardService.get_active_trips_count(), # يمكن فلترتها للرحلات التي تجاوزت 24 ساعة
        }

        # 3️⃣ استدعاء بيانات الرسوم البيانية (Charts Data)
        # نطلب البيانات مهيأة بصيغة تناسب مكتبات الـ Charts مثل (Chart.js)
        charts_data = {
            'fuel_by_rank': ReportService.QuotaReports.get_over_consumption_report(),
            'monthly_spending': ReportService.AssetReports.get_accident_cost_summary(
                start_date="2026-01-01", end_date="2026-12-31"
            )
        }

        # 4️⃣ تجميع "حقيبة البيانات" الشاملة (Context Aggregation)
        context = {
            'stats': general_stats,
            'fuel': fuel_analytics,
            'finance': financial_metrics,
            'alerts': alerts,
            'charts': charts_data,
            'last_updated': DashboardService.get_last_sync_time() # لإظهار وقت آخر تحديث للبيانات
        }

        return render(request, self.template_name, context)
    


#===============================================================
# 📈 Main Report View - مركز التقارير والتحليلات المتقدمة
#===============================================================

class MainReportView(View):
    template_name = 'modules/reports/report_center.html'

    def get(self, request):
        """1️⃣ عرض نموذج اختيار المعايير (GET)"""
        context = {
            'employees': EmployeeService.list_employees({'is_active': True}),
            'vehicles': VehicleService.list_vehicles(),
            'report_types': [
                ('fuel', 'تقرير استهلاك الوقود'),
                ('trips', 'تقرير النشاط الميداني (الرحلات)'),
                ('accidents', 'تقرير خسائر الحوادث'),
                ('maintenance', 'تقرير تكاليف الصيانة'),
                ('unused_quota', 'حصص غير مستخدمة'),
            ]
        }
        
        # إذا كان هناك طلب فلترة في الـ GET، نقوم بتنفيذ المرحلة 2
        report_type = request.GET.get('report_type')
        if report_type:
            return self.process_report(request, context)
            
        return render(request, self.template_name, context)

    def process_report(self, request, context):
        """2️⃣ تنفيذ التقرير (قراءة المعايير واستدعاء الخدمة)"""
        report_type = request.GET.get('report_type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        results = None
        
        # تنفيذ التقرير بناءً على النوع المختار
        if report_type == 'fuel':
            emp_id = request.GET.get('employee')
            veh_id = request.GET.get('vehicle')
            results = ReportService.FuelReports.get_detailed_consumption_report(
                start_date, end_date, emp_id, veh_id
            )
            context['report_title'] = "تقرير استهلاك الوقود التفصيلي"

        elif report_type == 'trips':
            results = ReportService.TripReports.get_trip_statistics(start_date, end_date)
            context['report_title'] = "إحصائيات النشاط والرحلات"

        elif report_type == 'accidents':
            results = ReportService.AssetReports.get_accident_cost_summary(start_date, end_date)
            context['report_title'] = "تقرير الخسائر الناتجة عن الحوادث"

        elif report_type == 'maintenance':
            # تقرير الصيانة المفتوحة لا يحتاج نطاق زمني عادة لكننا سنلتزم بالفلترة
            results = ReportService.AssetReports.get_open_maintenance_report(start_date, end_date)
            context['report_title'] = "سجل المركبات قيد الإصلاح حالياً"

        elif report_type == 'over_consumption':
            results = ReportService.QuotaReports.get_over_consumption_report(threshold_percent=90)
            context['report_title'] = "تحذير: تجاوز حصة الاستهلاك (90% فأكثر)"

        elif report_type == 'unused_quota':
            results = ReportService.QuotaReports.get_unused_quota_report()
            context['report_title'] = "تقرير الموظفين غير النشطين (توفير الموارد)"


        # 3️⃣ معالجة العرض والتصفح (Pagination)
        if isinstance(results, QuerySet):
            # حل مشكلة UnorderedObjectListWarning بإضافة ترتيب افتراضي
            results = results.order_by('-id') 
            
            paginator = Paginator(results, 15)
            page_number = request.GET.get('page')
            context['report_results'] = paginator.get_page(page_number)
            context['is_queryset'] = True # علامة للـ HTML لتشغيل حلقة for
        else:
            # إذا كانت النتائج Dict (مثل تقارير trips و accidents) أو List مخصصة
            context['report_results'] = results
            context['is_queryset'] = False # علامة للـ HTML لعرض الإحصائيات مباشرة

        context['filtered'] = True
        return render(request, self.template_name, context)