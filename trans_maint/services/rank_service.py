from django.shortcuts import get_object_or_404
from ..models import MilitaryRank, Employee
from django.db import transaction

class RankService:
    
    @staticmethod
    def list_ranks():
        """عرض كافة الرتب المتاحة"""
        return MilitaryRank.objects.all()

    @staticmethod
    def get_rank(rank_id):
        """جلب بيانات رتبة معينة"""
        return get_object_or_404(MilitaryRank, id=rank_id)

    @staticmethod
    def create_rank(data):
        """إنشاء رتبة جديدة مع حصصها الافتراضية"""
        return MilitaryRank.objects.create(**data)

    @staticmethod
    def update_rank(rank_id, data):
        """تحديث بيانات رتبة موجودة"""
        rank = RankService.get_rank(rank_id)
        for key, value in data.items():
            setattr(rank, key, value)
        rank.save()
        return rank

    @staticmethod
    def delete_rank(rank_id):
        """حذف رتبة (بشرط عدم وجود موظفين مرتبطين بها - يحميه PROTECT في الموديل)"""
        rank = RankService.get_rank(rank_id)
        rank.delete()
        return True

    @staticmethod
    def get_default_quota(rank_id, period_type):
        """
        دالة مساعدة لجلب الحصة الافتراضية لرتبة معينة حسب النوع (أسبوعي/شهري)
        """
        rank = RankService.get_rank(rank_id)
        if period_type == 'weekly':
            return rank.default_weekly_quota
        elif period_type == 'monthly':
            return rank.default_monthly_quota
        return 0.0

    # @staticmethod
    # def sync_rank_quotas(rank_id):
    #     """
    #     تحديث حصص الموظفين التابعين للرتبة الذين لا يملكون (Override).
    #     تستخدم هذه الدالة في حال تعديل القوانين العامة للرتبة.
    #     """
    #     rank = RankService.get_rank(rank_id)
        
    #     # نستخدم atomic لضمان تحديث الجميع أو لا أحد في حال حدوث خطأ
    #     with transaction.atomic():
    #         # تحديث الموظفين الذين ليس لديهم تجاوز (Override) للحصص
    #         affected_rows = Employee.objects.filter(
    #             rank=rank,
    #             weekly_quota_override__isnull=True,
    #             monthly_quota_override__isnull=True
    #         ).update(
    #             # ملاحظة: التحديث هنا لا يغير قيم الحقول في Employee 
    #             # لأن Employee يعتمد منطقياً على حصة الرتبة ما لم يوجد override
    #             # لكن هذه الدالة تفيد في حال كان هناك منطق كاش (Cache) أو عمليات تزامن
    #         )
    #     return affected_rows