import os
import django
import random
from faker import Faker
from django.utils import timezone

# إعداد بيئة Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # استبدل your_project_name باسم مجلد إعداداتك
django.setup()

from trans_maint.models import ( # استبدل your_app_name باسم تطبيقك
    MilitaryRank, Employee, Vehicle, Workshop, 
    Trip, FuelTransaction, Accident, MaintenanceRequest
)

fake = Faker(['ar_SA']) # استخدام اللغة العربية (السعودية) لبيانات واقعية

def seed_db():
    print("🚀 بدء عملية توزيع البيانات الوهمية...")

    # 1. الرتب العسكرية
    ranks_names = ['ملازم', 'نقيب', 'رائد', 'مقدم', 'عقيد', 'عميد']
    ranks = []
    for name in ranks_names:
        rank, _ = MilitaryRank.objects.get_or_create(
            name=name,
            default_weekly_quota=random.uniform(50.0, 100.0),
            default_monthly_quota=random.uniform(200.0, 400.0)
        )
        ranks.append(rank)
    print(f"✅ تم إنشاء {len(ranks)} رتب عسكرية.")

    # 2. الموظفون
    employees = []
    for _ in range(10):
        emp = Employee.objects.create(
            name=fake.name(),
            military_number=fake.unique.random_number(digits=8),
            rank=random.choice(ranks),
            is_active=True
        )
        employees.append(emp)
    print(f"✅ تم إنشاء {len(employees)} موظف.")

    # 3. المركبات
    vehicles = []
    for _ in range(8):
        v = Vehicle.objects.create(
            plate_number=f"{fake.unique.random_int(1000, 9999)} {fake.random_element(['أ', 'ب', 'ج'])}{fake.random_element(['د', 'ر', 'س'])}",
            model=fake.year(),
            vehicle_type=random.choice(['company', 'private']),
            owner=random.choice(employees) if random.random() > 0.5 else None,
            status='active'
        )
        vehicles.append(v)
    print(f"✅ تم إنشاء {len(vehicles)} مركبة.")

    # 4. الورش
    workshops = []
    for _ in range(3):
        w = Workshop.objects.create(
            name=f"ورشة {fake.company()}",
            address=fake.address(),
            phone=fake.phone_number()
        )
        workshops.append(w)
    print(f"✅ تم إنشاء {len(workshops)} ورشة.")

    # 5. الرحلات والحركات
    for _ in range(15):
        start = fake.date_time_this_month(before_now=True, after_now=False, tzinfo=timezone.get_current_timezone())
        trip = Trip.objects.create(
            vehicle=random.choice(vehicles),
            employee=random.choice(employees),
            trip_type=random.choice(['دورية', 'مهمة رسمية', 'نقل إمداد']),
            area=fake.city(),
            start_date=start,
            fuel_quota_granted=random.uniform(20.0, 60.0)
        )
        
        # إنشاء حركة وقود مرتبطة بالرحلة
        FuelTransaction.objects.create(
            employee=trip.employee,
            vehicle=trip.vehicle,
            trip=trip,
            quantity=trip.fuel_quota_granted,
            transaction_type='issue'
        )
    print("✅ تم إنشاء الرحلات وحركات الوقود.")

    # 6. الحوادث والصيانة
    for _ in range(5):
        acc = Accident.objects.create(
            vehicle=random.choice(vehicles),
            date_occurred=fake.date_time_this_year(tzinfo=timezone.get_current_timezone()),
            description=fake.sentence(),
            damage_cost=random.randint(500, 5000),
            status=random.choice(['open', 'closed'])
        )
        
        # إنشاء طلب صيانة مرتبط بالحادث أحياناً
        MaintenanceRequest.objects.create(
            vehicle=acc.vehicle,
            workshop=random.choice(workshops),
            accident_ref=acc,
            reason=f"إصلاح أضرار حادث: {acc.description[:30]}",
            cost=acc.damage_cost + 200,
            status='completed'
        )
    print("✅ تم إنشاء سجلات الحوادث والصيانة.")
    print("🏁 اكتملت العملية بنجاح!")

if __name__ == '__main__':
    seed_db()