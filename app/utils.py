import calendar
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
import tempfile
import datetime
from django.db.models import Sum, Count

from app.administration.models import Lesson, TeacherPayment, Teacher, Invoice, Payment
from app.users.models import CustomUser

def render_to_pdf(template_src, context_dict):
    html_string = render_to_string(template_src, context_dict)
    html = HTML(string=html_string, base_url=settings.BASE_DIR)
    result = tempfile.NamedTemporaryFile(delete=True, suffix=".pdf")
    html.write_pdf(target=result.name)
    result.seek(0)
    return result


# # Добавляем в models.py или создаем utils.py

# def calculate_teacher_payments(month, year):
#     """
#     Рассчитывает выплаты преподавателям за указанный месяц/год
#     """
#     # Получаем всех активных преподавателей
#     teachers = CustomUser.objects.filter(role='Teacher', is_active=True)
    
#     # Определяем период
#     start_date = timezone.date(year, month, 1)
#     end_date = timezone.date(year, month, calendar.monthrange(year, month)[1])
    
#     for teacher in teachers:
#         try:
#             teacher_profile = teacher.teacher_add
#             # Получаем все группы преподавателя
#             groups = teacher_profile.groups.all()
            
#             total_lessons = 0
#             total_payment = 0
            
#             # Рассчитываем занятия и выплаты для каждой группы
#             for group in groups:
#                 # Считаем занятия за месяц для этой группы
#                 lessons_count = Lesson.objects.filter(
#                     month__group=group,
#                     date__gte=start_date,
#                     date__lte=end_date
#                 ).count()
                
#                 # Рассчитываем выплату в зависимости от типа оплаты
#                 if teacher_profile.payment_type == 'fixed':
#                     if teacher_profile.payment_period == 'month':
#                         payment = teacher_profile.payment_amount
#                     else:  # per_lesson
#                         payment = teacher_profile.payment_amount * lessons_count
#                 else:  # hourly
#                     payment = teacher_profile.payment_amount * lessons_count * group.lesson_duration
                
#                 total_lessons += lessons_count
#                 total_payment += payment
            
#             # Создаем или обновляем запись о выплате
#             TeacherPayment.objects.update_or_create(
#                 teacher=teacher,
#                 date=end_date,
#                 defaults={
#                     'lessons_count': total_lessons,
#                     'rate': teacher_profile.payment_amount,
#                     'payment': total_payment,
#                     'bonus': 0,  # Можно установить вручную позже
#                     'is_paid': False
#                 }
#             )
            
#         except Teacher.DoesNotExist:
#             continue
    
#     return True




# # utils.py


# def create_invoice(student, month, amount, due_date, discount=0, comment=''):
#     invoice = Invoice.objects.create(
#         student=student,
#         month=month,
#         amount=amount,
#         discount=discount,
#         due_date=due_date,
#         comment=comment
#     )
    
#     # Создаем напоминания (за 3 дня, 1 день и в день оплаты)
#     reminder_dates = [
#         due_date - timedelta(days=3),
#         due_date - timedelta(days=1),
#         due_date
#     ]
    
#     for days, reminder_date in enumerate(reminder_dates, start=1):
#         PaymentReminder.objects.create(
#             invoice=invoice,
#             reminder_date=reminder_date,
#             days_before=days,
#             message=f"""Уважаемый(ая) {student.first_name} {student.last_name},
# Напоминаем, что срок оплаты за курс «{month.name}» {'наступает' if days > 1 else 'истекает'} через {days} {'дня' if days > 1 else 'день'}.

# До {due_date.strftime('%d.%m.%Y')}

# Сумма к оплате: {invoice.final_amount} сом

# Вы можете оплатить удобным для вас способом: наличными, переводом или онлайн

# С уважением,
# American Dream"""
#         )
    
#     return invoice

# def get_daily_finance_summary(date=None):
#     date = date or timezone.now().date()
    
#     payments = Payment.objects.filter(date__date=date)
#     total = payments.aggregate(total=Sum('amount'))['total'] or 0
    
#     by_type = payments.values('payment_type').annotate(
#         total=Sum('amount'),
#         count=Count('id')
#     )
    
#     return {
#         'date': date,
#         'total': total,
#         'by_type': {p['payment_type']: p['total'] for p in by_type},
#         'count': payments.count()
#     }