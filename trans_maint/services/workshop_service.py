from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from ..models import Workshop, MaintenanceRequest

class WorkshopService:

    # --- أولاً: إدارة الموردين (Vendor Management) ---

    @staticmethod
    def create_workshop(data):
        """إضافة ورشة جديدة لشبكة مقدمي الخدمة"""
        return Workshop.objects.create(**data)

    @staticmethod
    def update_workshop(workshop_id, data):
        """تحديث بيانات التواصل أو عنوان الورشة"""
        workshop = WorkshopService.get_workshop(workshop_id)
        for key, value in data.items():
            setattr(workshop, key, value)
        workshop.save()
        return workshop

    @staticmethod
    def delete_workshop(workshop_id):
        """
        حذف ورشة من النظام.
        ملاحظة: سيمنع Django الحذف إذا كانت الورشة مرتبطة بطلبات صيانة (بسبب PROTECT/CASCADE في الموديل).
        """
        workshop = WorkshopService.get_workshop(workshop_id)
        workshop.delete()
        return True

    @staticmethod
    def get_workshop(workshop_id):
        """جلب بيانات ورشة محددة"""
        return get_object_or_404(Workshop, id=workshop_id)

    @staticmethod
    def list_workshops():
        """عرض كافة مراكز الخدمة المتعاقد معها"""
        return Workshop.objects.all()

    # --- ثانياً: تقييم الأداء (Performance Evaluation) ---

    @staticmethod
    def get_workshop_total_jobs(workshop_id):
        """
        مقياس استيعاب ضغط العمل:
        حساب إجمالي عمليات الصيانة التي تمت بنجاح داخل هذه الورشة.
        """
        return MaintenanceRequest.objects.filter(
            workshop_id=workshop_id, 
            status='completed'
        ).count()

    @staticmethod
    def get_workshop_total_cost(workshop_id):
        """
        المقياس المالي:
        إجمالي المبالغ المصروفة لهذه الورشة، مما يساعد في تحليل التكاليف السنوي.
        """
        result = MaintenanceRequest.objects.filter(
            workshop_id=workshop_id, 
            status='completed'
        ).aggregate(total_cost=Sum('cost'))
        
        return result['total_cost'] or 0.00