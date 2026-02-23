from django.urls import path
from django.views.generic import RedirectView

from .views import (
     RankListView, 
    EmployeeListView, EmployeeDetailView, 
    VehicleListView, VehicleDetailView,

    TripListView,  TripDetailView, 
    FuelLogListView, FuelAddView, FuelAdjustmentView,
    AccidentListView, AccidentCreateView, AccidentDetailView, AccidentCloseView,

    MaintenanceDashboardView, MaintenanceCreateView, MaintenanceCloseView,
    WorkshopActionView,
    QuotaOverviewView, QuotaAdjustmentView, QuotaHistoryView,
    MainReportView,       DashboardView,
 

)
urlpatterns = [
    path('', RedirectView.as_view(url='dashboard/', permanent=True)),
    #===============================================================
    #  urls for Rank Management - عرض، إضافة، تعديل، حذف الرتب العسكرية
    path('ranks/', RankListView.as_view(), name='rank_list'),
    # path('ranks/create/', RankCreateView.as_view(), name='rank_create'),
    # path('ranks/update/<int:pk>/', RankUpdateView.as_view(), name='rank_update'),
    # path('ranks/delete/<int:pk>/', RankDeleteView.as_view(), name='rank_delete'),

    #===============================================================
    #  urls for Employee Management - عرض، إضافة، تعطيل الموظفين
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    # path('employees/add/', EmployeeCreateView.as_view(), name='employee_create'),
    # path('employees/<int:pk>/deactivate/', EmployeeDeactivateView.as_view(), name='employee_deactivate'),

    #===============================================================
    #  urls for Vehicle Management - عرض، إضافة، تعطيل المركبات

    path('vehicles/', VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/<int:pk>/', VehicleDetailView.as_view(), name='vehicle_detail'),

    #===============================================================
    #  urls for Trip Management - عرض، إضافة، إنهاء الرحلات

    path('trips/', TripListView.as_view(), name='trip_list'),
    path('trips/<int:pk>/', TripDetailView.as_view(), name='trip_detail'),
  
    #===============================================================
    #  urls for Fuel Management - سجل الوقود، الإيداع، والتعديلات
    path('fuel/', FuelLogListView.as_view(), name='fuel_log_list'),
    path('fuel/add/', FuelAddView.as_view(), name='fuel_add'),
    path('fuel/adjust/', FuelAdjustmentView.as_view(), name='fuel_adjustment'),

    #===============================================================
     # urls for Accident Management - عرض، إضافة، إغلاق الحوادث
    path('accidents/', AccidentListView.as_view(), name='accident_list'),
    path('accidents/create/', AccidentCreateView.as_view(), name='accident_create'),
    path('accidents/<int:pk>/detail/', AccidentDetailView.as_view(), name='accident_detail'),
    path('accidents/<int:pk>/close/', AccidentCloseView.as_view(), name='accident_close'),
  
    #===============================================================
    #  urls for Maintenance Management - عرض، إضافة، إغلاق طلبات الصيانة
    path('maintenance/', MaintenanceDashboardView.as_view(), name='maintenance_dashboard'),
    path('maintenance/create/', MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('maintenance/<int:pk>/close/', MaintenanceCloseView.as_view(), name='maintenance_close'),
    path('workshops/manage/', WorkshopActionView.as_view(), name='workshop_add'),
    path('workshops/manage/<int:pk>/', WorkshopActionView.as_view(), name='workshop_edit_delete'),

    #============================================================
    #  urls for Workshop Management - إضافة، تعديل، حذف الورش
    path('quota/overview/', QuotaOverviewView.as_view(), name='quota_overview'),
    path('quota/adjust/', QuotaAdjustmentView.as_view(), name='quota_adjust'),
    path('quota/history/<int:employee_id>/', QuotaHistoryView.as_view(), name='quota_history'),
    #============================================================
    #  urls for Dashboard View - لوحة القيادة والإحصائيات العامة
    path('dashboard/', DashboardView.as_view(), name='admin_dashboard'),

    #============================================================
    #  urls for Main Report View - مركز التقارير والتحليلات المتقدمة

    path('reports/center/', MainReportView.as_view(), name='report_center'),


]