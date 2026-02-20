from django.db import models

# 1️⃣ الرتب العسكرية
class MilitaryRank(models.Model):
    name = models.CharField(max_length=100, verbose_name="الرتبة")
    default_weekly_quota = models.FloatField(default=0.0, verbose_name="الحصة الأسبوعية الافتراضية")
    default_monthly_quota = models.FloatField(default=0.0, verbose_name="الحصة الشهرية الافتراضية")

    def __str__(self):
        return self.name

# 2️⃣ الموظف (العسكري)
class Employee(models.Model):
    name = models.CharField(max_length=255, verbose_name="الاسم")
    military_number = models.CharField(max_length=50, unique=True, verbose_name="الرقم العسكري")
    rank = models.ForeignKey(MilitaryRank, on_delete=models.PROTECT, related_name="employees", verbose_name="الرتبة")
    
    # لتخصيص حصة معينة لموظف بعيداً عن حصة الرتبة (Override)
    weekly_quota_override = models.FloatField(null=True, blank=True, verbose_name="تجاوز الحصة الأسبوعية")
    monthly_quota_override = models.FloatField(null=True, blank=True, verbose_name="تجاوز الحصة الشهرية")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    def __str__(self):
        return f"{self.rank.name} / {self.name}"

# 3️⃣ المركبة
class Vehicle(models.Model):
    OWNERSHIP_CHOICES = [('company', 'ملكية المؤسسة'), ('private', 'ملك خاص')]
    STATUS_CHOICES = [('active', 'نشطة'), ('inactive', 'غير نشطة')]

    plate_number = models.CharField(max_length=50, unique=True, verbose_name="رقم اللوحة")
    model = models.CharField(max_length=100, verbose_name="الموديل")
    vehicle_type = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES, verbose_name="نوع الملكية")
    
    # تم ربط المالك بجدول الموظفين مباشرة (حل مشكلة المالك المجهول)
    owner = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_vehicles", verbose_name="المالك (إذا كان خاصاً)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="الحالة")

    def __str__(self):
        return self.plate_number

# 4️⃣ الورشة
class Workshop(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم الورشة")
    address = models.TextField(blank=True, null=True, verbose_name="العنوان")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="الهاتف")

    def __str__(self):
        return self.name

# 5️⃣ الرحلة
class Trip(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trips")
    trip_type = models.CharField(max_length=100, verbose_name="نوع الرحلة")
    area = models.CharField(max_length=255, null=True, blank=True, verbose_name="المنطقة/الجهة")
    start_date = models.DateTimeField(verbose_name="تاريخ ووقت البدء")
    end_date = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ ووقت العودة")
    fuel_quota_granted = models.FloatField(default=0.0, verbose_name="الكمية الممنوحة للرحلة")

    def __str__(self):
        return f"رحلة {self.vehicle.plate_number} - {self.area}"

# 6️⃣ حركات الوقود (نظام المعاملات)
class FuelTransaction(models.Model):
    TYPE_CHOICES = [('issue', 'صرف'), ('addition', 'إضافة')]
    
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, verbose_name="الموظف المستلم")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, verbose_name="المركبة")
    # ربط اختياري بالرحلة (لحل مشكلة التكرار والتضارب)
    trip = models.OneToOneField(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name="fuel_transaction")
    
    quantity = models.FloatField(verbose_name="الكمية")
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='issue')
    date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ العملية")
    notes = models.TextField(blank=True, null=True)

# 7️⃣ الحوادث
class Accident(models.Model):
    STATUS_CHOICES = [('open', 'مفتوح'), ('closed', 'مغلق')]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    
    date_occurred = models.DateTimeField(verbose_name="تاريخ وقوع الحادث")
    description = models.TextField(verbose_name="وصف الحادث")
    damage_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="تكلفة الإصلاح")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

# 8️⃣ طلب الصيانة
class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [('pending', 'قيد المعالجة'), ('completed', 'مكتمل')]
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE)
    # ربط الصيانة بالحادث (اختياري)
    accident_ref = models.ForeignKey(Accident, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_repairs")
    
    reason = models.TextField(verbose_name="سبب الصيانة")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_reported = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')