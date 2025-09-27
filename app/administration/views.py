from rest_framework import viewsets, generics, status, permissions, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Count
from datetime import timedelta
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import action
from django.http import HttpResponse
import datetime
from django.db.models import Count, Sum, Avg, Q, ExpressionWrapper, F, DecimalField, FloatField
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from app.administration.models import (
    Direction, Group, Teacher, Student, Lesson, Attendance, Payment, Months, Income, Expense, 
    TeacherPayment, Invoice, FinancialReport, Schedule, Classroom, Lead, HomeworkSubmission,
    PaymentNotification, DiscountRegulation
    )
from app.administration.serializers import (
    DirectionSerializer, GroupSerializer, GroupCreateSerializer, TeacherCreateSerializer, TeacherSerializer, StudentCreateSerializer, StudentSerializer, LessonSerializer, AttendanceSerializer, 
    PaymentSerializer, GroupDashboardSerializer, MonthsSerializer, GroupTableSerializer, StudentTableSerializer, TeacherTableSerializer, TeacherPaymentSerializer, ExpenseSerializer, IncomeSerializer, FinancialReportSerializer, InvoiceSerializer,
    ScheduleSerializer, ClassroomSerializer, DailyScheduleSerializer, ScheduleListSerializer, ActiveStudentsSerializer, PopularCoursesSerializer,
    TeacherWorkloadSerializer, MonthlyIncomeSerializer, StudentAttendanceSerializer, PaymentHistorySerializer, LeadSerializer, LeadStatusUpdateSerializer, DashboardStatsSerializer,
    LessonSerializer, HomeworkSubmissionSerializer, PaymentNotificationSerializer, ProfileSerializer,
    TeacherProfileSerializer, StudentProfileSerializer, StudentHomeworkSerializer, HomeworkSubmissionUpdateSerializer, StudentProgressSerializer, DiscountRegulationSerializer
    )
from app.users.models import CustomUser
from app.users.permissions import (
    IsAdminOrManager, IsAdmin, IsTeacher, IsStudent, IsAdminOrTeacher, IsAdminOrReadOnlyForOthers, IsAdminOrReadOnlyForManagersAndTeachers, 
    IsAdminOrTeacherFullAccessOthersReadOnly, IsInAllowedRoles, IsAdminTeacherOrReadOnlyStudent, IsAdminOrStudent, IsManager
    )
from app.utils import render_to_pdf, send_financial_reports_to_manager



class DirectionViewSet(viewsets.ModelViewSet):
    queryset = Direction.objects.all()
    serializer_class = DirectionSerializer
    permission_classes = [IsAdminOrTeacher]


class GroupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = Group.objects.all().select_related('direction')
    

    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return GroupCreateSerializer
        return GroupSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        teacher_id = request.data.get('teacher')
        teacher_user = None
        if teacher_id:
            try:
                teacher_user = CustomUser.objects.get(id=teacher_id, role='Teacher')
            except CustomUser.DoesNotExist:
                return Response(
                    {'teacher': 'Пользователь не найден или не является преподавателем'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        group = serializer.save()

        # Если указан Teacher — добавить группу в его профиль
        teacher_id = request.data.get('teacher')
        if teacher_id:
            try:
                teacher_user = CustomUser.objects.get(id=teacher_id, role='Teacher')
                teacher_add = teacher_user.teacher_add

                # Добавляем группу в профиль преподавателя
                teacher_add.groups.add(group)

                # Добавляем направление группы, если его ещё нет
                if group.direction and group.direction not in teacher_add.directions.all():
                    teacher_add.directions.add(group.direction)

            except (CustomUser.DoesNotExist, Teacher.DoesNotExist):
                pass  # Можно добавить логирование ошибки

        # ✅ Добавление группы и направления в профиль каждого ученика
        student_ids = request.data.get('students', [])
        for student_id in student_ids:
            try:
                student_user = CustomUser.objects.get(id=student_id, role='Student')
                student_add = student_user.student_add

                # Добавляем группу в профиль ученика
                student_add.groups.add(group)

                # Добавляем направление группы, если его ещё нет
                if group.direction and group.direction not in student_add.directions.all():
                    student_add.directions.add(group.direction)

            except (CustomUser.DoesNotExist, Student.DoesNotExist):
                continue

        if group.creation_type == 'auto':
            for month_number in range(1, group.duration_months + 1):
                month = Months.objects.create(
                    group=group,
                    month_number=month_number,
                    title=f"Месяц {month_number}",
                    description=f"Автоматически созданный месяц {month_number}"
                )
                for lesson_number in range(1, group.lessons_per_month + 1):
                    Lesson.objects.create(
                        month=month,
                        order=lesson_number,
                        title=f"Урок {lesson_number}",
                        description=f"Автоматически созданный урок {lesson_number}"
                    )


        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        prev_teacher = instance.teacher
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()

        # Обработка преподавателя
        new_teacher_id = request.data.get('teacher')
        if new_teacher_id:
            try:
                new_teacher_user = CustomUser.objects.get(id=new_teacher_id, role='Teacher')
                teacher_add = new_teacher_user.teacher_add
                teacher_add.groups.add(group)
            except (CustomUser.DoesNotExist, Teacher.DoesNotExist):
                pass

        if prev_teacher and prev_teacher != group.teacher:
            try:
                old_teacher_add = prev_teacher.teacher_add
                old_teacher_add.groups.remove(group)
            except Teacher.DoesNotExist:
                pass

        # ✅ Обработка студентов
        student_ids = request.data.get('students', [])
        if student_ids is not None:
            current_students = set(instance.students.all())
            new_students = set(CustomUser.objects.filter(id__in=student_ids, role='Student'))

            # Удалим группу у студентов, которых больше нет в списке
            for user in current_students - new_students:
                try:
                    student_add = user.student_add
                    student_add.groups.remove(group)
                    if group.direction in student_add.directions.all():
                        student_add.directions.remove(group.direction)
                except Student.DoesNotExist:
                    continue

            # Добавим группу новым студентам
            for user in new_students:
                try:
                    student_add = user.student_add
                    student_add.groups.add(group)
                    if group.direction and group.direction not in student_add.directions.all():
                        student_add.directions.add(group.direction)
                except Student.DoesNotExist:
                    continue

        return Response(serializer.data)


    


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all().select_related('user').prefetch_related('directions', 'groups')
    permission_classes = [IsAdmin]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeacherCreateSerializer
        return TeacherSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()

        # Обработка направлений преподавателя
        if 'directions' in request.data:  # или 'direction_ids' в зависимости от того, что вы отправляете
            direction_ids = request.data.get('directions')  # или get('direction_ids')
            teacher.directions.set(direction_ids)

        # Обработка групп
        new_groups = serializer.validated_data.get('groups', None)
        if new_groups is not None:
            current_user = teacher.user

            for group in new_groups:
                group.teacher = current_user
                group.save()

            old_groups = set(teacher.groups.all())
            new_groups_set = set(new_groups)
            removed_groups = old_groups - new_groups_set
            for group in removed_groups:
                if group.teacher == current_user:
                    group.teacher = None
                    group.save()

        return Response(TeacherSerializer(teacher).data)



    
# views.py
class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = Student.objects.all().select_related('user').prefetch_related('groups', 'directions')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StudentCreateSerializer
        return StudentSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()

        # Синхронизация групп
        new_groups = serializer.validated_data.get('groups', None)
        if new_groups is not None:
            current_user = student.user

            # Добавить пользователя в новые группы
            for group in new_groups:
                group.students.add(current_user)

            # Удалить из удалённых групп
            old_groups = set(student.groups.all())
            new_groups_set = set(new_groups)
            removed_groups = old_groups - new_groups_set
            for group in removed_groups:
                group.students.remove(current_user)

        return Response(StudentSerializer(student).data)    

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrTeacherFullAccessOthersReadOnly, IsAdmin]

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAdminOrTeacher]



class MonthsViewSet(viewsets.ModelViewSet):
    queryset = Months.objects.all()
    serializer_class = MonthsSerializer
    permission_classes = [IsAdmin]

# views.py
class GroupDashboardView(generics.RetrieveAPIView):
    permission_classes = [IsInAllowedRoles]
    queryset = Group.objects.all().select_related(
        'direction', 'teacher'
    ).prefetch_related(
        'students',
        'months',
        'months__lessons',
        'months__lessons__attendances',
    )
    serializer_class = GroupDashboardSerializer
    lookup_field = 'id'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        response_data = {
            'group': {
                'id': instance.id,
                'name': instance.group_name,
                'direction': instance.direction.name if instance.direction else None,
                'teacher': instance.teacher.get_full_name() if instance.teacher else None
            },
            'months': MonthsSerializer(
                instance.months.all().order_by('month_number'),
                many=True
            ).data,
            'students': serializer.data['students'],
            'tabs': {
                'data': 'Основные данные',
                'students': 'Студенты',
                'plans': 'Планы обучения',
                'homework': 'Домашние задания',
                'attendance': 'Посещаемость',
                'stats': 'Статистика'
            },
            'current_tab': request.query_params.get('tab', 'data')
        }
        
        return Response(response_data)





# views.py
class GroupTableViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset для отображения таблицы групп (с месяцем обучения)"""
    serializer_class = GroupTableSerializer
    filterset_fields = ['direction__name', 'group_name']
    permission_classes = [IsAdminOrTeacher]  # если у тебя есть кастомные права

    def get_queryset(self):
        qs = Group.objects.all().select_related('direction')

        user = self.request.user
        if user.role == "Teacher":
            qs = qs.filter(teacher=user)  # только его группы

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(group_name__icontains=search_query) |
                Q(direction__name__icontains=search_query)
            )
        
        direction = request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(direction__name=direction)
            
        group_name = request.query_params.get('group_name')
        if group_name:
            queryset = queryset.filter(group_name__icontains=group_name)
            
        serializer = self.get_serializer(queryset, many=True)
        
        directions = Direction.objects.values_list('name', flat=True).distinct()
        
        response_data = {
            'directions': list(directions),
            'groups': serializer.data,
            'selected_direction': direction,
            'search_query': search_query
        }
        
        return Response(response_data)


# views.py
class StudentTableViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers, IsAdmin]
    serializer_class = StudentTableSerializer

    def get_queryset(self):
        return Student.objects.select_related('user').prefetch_related('groups', 'directions')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )

        direction = request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(groups__direction__name__icontains=direction)

        group_name = request.query_params.get('group')
        if group_name:
            queryset = queryset.filter(groups__group_name__icontains=group_name)

        teacher = request.query_params.get('teacher')
        if teacher:
            queryset = queryset.filter(groups__teacher__last_name__icontains=teacher)

        queryset = queryset.distinct()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        directions = Direction.objects.values_list('name', flat=True).distinct()
        groups = Group.objects.values_list('group_name', flat=True).distinct()

        teachers = CustomUser.objects.filter(
            role='Teacher'
        ).exclude(
            Q(last_name__isnull=True) | Q(last_name='') |
            Q(first_name__isnull=True) | Q(first_name='')
        ).values_list('last_name', 'first_name').distinct()

        teacher_names = [f"{last} {first}" for last, first in teachers]

        response_data = {
            'students': serializer.data,
            'filters': {
                'directions': list(directions),
                'groups': list(groups),
                'teachers': teacher_names,
            },
            'selected_filters': {
                'search': search_query,
                'direction': direction,
                'group': group_name,
                'teacher': teacher
            }
        }

        return Response(response_data)

    



# views.py
class TeacherTableViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = TeacherTableSerializer
    
    def get_queryset(self):
        # Получаем только пользователей с ролью Teacher
        return CustomUser.objects.filter(role='Teacher')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Фильтр по направлению
        direction = request.query_params.get('direction')
        if direction:
            queryset = queryset.filter(
                teacher_add__directions__name__icontains=direction)
            
        # Поиск по имени
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query))

        # Пагинация
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        
        # Получаем доступные направления для фильтра
        directions = Direction.objects.values_list('name', flat=True).distinct()

        response_data = {
            'teachers': serializer.data,
            'filters': {
                'directions': list(directions),
            },
            'selected_filters': {
                'direction': direction,
                'search': search_query
            }
        }
        
        return Response(response_data)
    
# Добавляем к существующим представлениям

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrManager, IsAdmin]
    queryset = Invoice.objects.all().select_related('student', 'months')
    serializer_class = InvoiceSerializer
    filterset_fields = ['student', 'months', 'status', 'due_date']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
        except IntegrityError as e:
            if 'student_id' in str(e):
                return Response(
                    {"detail": "Необходимо указать действительного студента (student_id)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по периоду
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(date_created__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(date_created__gte=start_date)
        elif end_date:
            queryset = queryset.filter(date_created__lte=end_date)
            
        return queryset.order_by('-date_created')

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrManager, IsAdmin]
    queryset = Payment.objects.all().select_related('invoice')
    serializer_class = PaymentSerializer
    filterset_fields = ['payment_type', 'date', 'invoice']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по периоду
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        return queryset.order_by('-date')


class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.all().select_related('direction', 'student', 'group')
    serializer_class = IncomeSerializer
    filterset_fields = ['direction', 'date', 'is_full_payment']
    permission_classes = [IsAdminOrManager, IsAdmin]


class IncomePDFView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request, *args, **kwargs):
        # Получаем все доходы
        incomes = Income.objects.all().select_related('direction', 'student', 'group')

        # Можно посчитать общую сумму

        total_amount = Income.objects.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('cash_amount') + F('transfer_amount') + F('online_amount'),
                    output_field=DecimalField()
                )
            )
        )['total'] or 0

        # Контекст для шаблона
        context = {
            "incomes": incomes,
            "total_amount": total_amount,
        }

        pdf_file = render_to_pdf("reports/income_pdf_template.html", context)
        return HttpResponse(pdf_file, content_type="application/pdf")
    

    

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().select_related('teacher')
    serializer_class = ExpenseSerializer
    filterset_fields = ['category', 'date']
    permission_classes = [IsAdminOrManager, IsAdmin]



class ExpensePDFView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request, *args, **kwargs):
        # Получаем все расходы
        expenses = Expense.objects.all().select_related('teacher')

        # Сериализуем данные
        serializer = ExpenseSerializer(expenses, many=True)

        # Считаем общую сумму
        total_amount = expenses.aggregate(Sum("amount"))["amount__sum"] or 0

        # Контекст для шаблона
        context = {
            "expenses": serializer.data,
            "total_amount": total_amount,
        }

        # Генерация PDF
        pdf_file = render_to_pdf("reports/expense_pdf_template.html", context)

        # Возвращаем PDF
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response['Content-Disposition'] = 'inline; filename="expense_report.pdf"'
        return response




class TeacherPaymentViewSet(viewsets.ModelViewSet):
    queryset = TeacherPayment.objects.all().select_related('teacher')
    serializer_class = TeacherPaymentSerializer
    filterset_fields = ['teacher', 'date', 'is_paid']
    permission_classes = [IsAdminOrManager, IsAdmin]


class TeacherPaymentsPDFView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request, *args, **kwargs):
        payments = TeacherPayment.objects.all()
        total_amount = payments.aggregate(Sum("paid_amount"))["paid_amount__sum"] or 0

        context = {
            "payments": payments,
            "total_amount": total_amount,
        }

        pdf_file = render_to_pdf("reports/teacher_payments.html", context)
        return HttpResponse(pdf_file, content_type="application/pdf")


class FinancialReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    filterset_fields = ['report_type', 'start_date', 'end_date']
    permission_classes = [IsAdminOrManager, IsAdmin]



class FinancialReportPDFView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request, *args, **kwargs):
        # Получаем все отчеты
        reports = FinancialReport.objects.all()

        # Сериализуем их
        serializer = FinancialReportSerializer(reports, many=True)

        context = {
            "reports": serializer.data,
        }

        # Генерация PDF
        pdf_file = render_to_pdf("reports/financial_report_pdf_template.html", context)

        # Возврат PDF
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response['Content-Disposition'] = 'inline; filename="financial_report.pdf"'
        return response



# views.py
class GenerateFinancialReport(APIView):
    permission_classes = [IsAdmin]
    def post(self, request, format=None):
        try:
            report_type = request.data.get('report_type', 'monthly')
            today = timezone.now().date()
            
            # Логика определения дат остается прежней
            if report_type == 'daily':
                start_date = end_date = today
            elif report_type == 'weekly':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif report_type == 'monthly':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            elif report_type == 'yearly':
                start_date = today.replace(month=1, day=1)
                end_date = today.replace(month=12, day=31)
            elif report_type == 'custom':
                start_date = request.data.get('start_date')
                end_date = request.data.get('end_date')
                if not start_date or not end_date:
                    return Response(
                        {'error': 'Для custom отчета нужны start_date и end_date'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Создаем отчет без финансовых показателей (они будут рассчитываться динамически)
            report = FinancialReport.objects.create(
                report_type=report_type,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = FinancialReportSerializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class CalculateTeacherPayments(APIView):
    permission_classes = [IsAdminOrManager, IsAdmin]
    def post(self, request, format=None):
        from datetime import datetime
        import calendar
        from django.utils import timezone
        
        month = request.data.get('month', timezone.now().month)
        year = request.data.get('year', timezone.now().year)
        
        start_date = timezone.make_aware(datetime(year, month, 1))
        end_date = timezone.make_aware(datetime(year, month, calendar.monthrange(year, month)[1]))
        
        teachers = CustomUser.objects.filter(role='Teacher', is_active=True)
        results = []
        
        for teacher in teachers:
            try:
                # Получаем профиль преподавателя
                teacher_profile = Teacher.objects.get(user=teacher)
                
                # Получаем группы, где преподаватель является teacher
                groups = Group.objects.filter(teacher=teacher)
                
                total_lessons = 0
                total_payment = 0
                
                for group in groups:
                    lessons_count = Lesson.objects.filter(
                        month__group=group,
                        date__range=[start_date, end_date]
                    ).count()
                    
                    if teacher_profile.payment_type == 'fixed':
                        if teacher_profile.payment_period == 'month':
                            payment = teacher_profile.payment_amount
                        else:  # per_lesson
                            payment = teacher_profile.payment_amount * lessons_count
                    else:  # hourly
                        payment = teacher_profile.payment_amount * lessons_count * group.lesson_duration
                    
                    total_lessons += lessons_count
                    total_payment += payment
                
                # Создаем или обновляем запись о выплате
                payment, created = TeacherPayment.objects.update_or_create(
                    teacher=teacher,
                    date=end_date,
                    defaults={
                        'lessons_count': total_lessons,
                        'rate': teacher_profile.payment_amount,
                        'payment': total_payment,
                        'bonus': 0,
                        'is_paid': False
                    }
                )
                
                results.append({
                    'teacher_id': teacher.id,
                    'teacher_name': teacher.get_full_name(),
                    'lessons_count': total_lessons,
                    'payment': total_payment,
                    'status': 'created' if created else 'updated'
                })
                
            except Teacher.DoesNotExist:
                results.append({
                    'teacher_id': teacher.id,
                    'error': 'Teacher profile not found'
                })
                continue
        
        return Response({
            'status': 'success',
            'period': f"{start_date.date()} - {end_date.date()}",
            'teachers_processed': len(results),
            'results': results
        }, status=status.HTTP_200_OK)
    



class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAdmin]

class ScheduleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Schedule.objects.all().select_related(
        'classroom', 'group', 'group__direction', 'teacher'
    )
    filterset_fields = ['date', 'classroom', 'group', 'teacher']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ScheduleListSerializer
        return ScheduleSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
            
        return queryset.order_by('classroom', 'start_time')
    

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def next_for_student(self, request):
        user = request.user
        if user.role != "Student":
            return Response({"detail": "Только для студентов"}, status=403)

        now = timezone.now()
        today = now.date()
        current_time = now.time()

        groups = user.student_groups.all()
        if not groups.exists():
            return Response({"detail": "Вы не состоите ни в одной группе"}, status=404)

        # 1️⃣ Ищем ближайшее занятие сегодня (после текущего времени)
        schedule_today = (
            Schedule.objects.filter(
                group__in=groups,
                date=today,
                start_time__gt=current_time
            )
            .select_related("classroom", "group", "teacher", "group__direction")
            .order_by("start_time")
            .first()
        )

        if schedule_today:
            return Response(ScheduleListSerializer(schedule_today).data)

        # 2️⃣ Если на сегодня больше нет — ищем ближайшее в будущем
        schedule_future = (
            Schedule.objects.filter(
                group__in=groups,
                date__gt=today
            )
            .select_related("classroom", "group", "teacher", "group__direction")
            .order_by("date", "start_time")
            .first()
        )

        if schedule_future:
            return Response(ScheduleListSerializer(schedule_future).data)

        return Response({"detail": "Нет ближайших занятий"}, status=404)
    

class DailyScheduleView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request, format=None):
        date_str = request.query_params.get('date')
        
        if not date_str:
            date = timezone.now().date()
        else:
            try:
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = DailyScheduleSerializer({'date': date})
        return Response(serializer.data)
    


class ActiveStudentsAnalytics(APIView):
    permission_classes = [IsAdmin]
    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # 1. Активные сегодня
        active_today = Attendance.objects.filter(
            lesson__date__date=today,
            status__in=['1', 'online']
        ).values('student').distinct().count()
        
        # 2. Ушедшие на этой неделе (по дате ухода)
        left_this_week = CustomUser.objects.filter(
            role="Student",
            is_active=False,
            left_date__range=[week_ago, today]
        ).count()

        
        # 3. Новые ученики (используем date_joined или created_at)
        date_field = 'date_joined' if hasattr(CustomUser, 'date_joined') else 'created_at'
        new_this_week = CustomUser.objects.filter(
            role='Student',
            **{f'{date_field}__gte': week_ago}
        ).count()
        
        # 4. Средний возраст
        avg_age = CustomUser.objects.filter(
            role='Student',
            is_active=True
        ).aggregate(avg_age=Avg('age'))['avg_age'] or 0
        
        # 5. Распределение по направлениям
        directions = Direction.objects.annotate(
            student_count=Count('groups__students', distinct=True)
        ).filter(student_count__gt=0)
        
        total_students = sum(d.student_count for d in directions)
        directions_distribution = {
            d.name: round(d.student_count / total_students * 100, 1)
            for d in directions
        } if total_students > 0 else {}
        
        return Response({
            'active_today': active_today,
            'left_this_week': left_this_week,
            'new_this_week': new_this_week,
            'avg_age': avg_age,
            'directions_distribution': directions_distribution
        })
    

class MonthlyIncomeAnalytics(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        # Получаем год из параметра запроса (по умолчанию текущий год)
        year = request.query_params.get('year', timezone.now().year)
        try:
            year = int(year)
        except ValueError:
            year = timezone.now().year

        months_ru = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]

        # Создаем выражение для суммы всех трёх типов оплаты
        total_expr = ExpressionWrapper(
            F('cash_amount') + F('transfer_amount') + F('online_amount'),
            output_field=DecimalField()
        )

        # Получаем доходы по месяцам
        payments = Payment.objects.filter(
            date__year=year
        ).annotate(
            total_amount=total_expr
        ).values('date__month').annotate(
            monthly_total=Sum('total_amount')
        ).order_by('date__month')

        # Создаем словарь для быстрого доступа к данным по месяцам
        month_data = {p['date__month']: p['monthly_total'] for p in payments}

        # Формируем результат для всех месяцев
        result = []
        for month_num in range(1, 13):
            result.append({
                'year': year,
                'month': months_ru[month_num - 1],
                'month_number': month_num,
                'income': float(month_data.get(month_num, 0))
            })

        return Response(result)
    

from django.db.models import F, Sum, ExpressionWrapper, DecimalField

class MonthlyIncomePDFView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        # Берем год
        year = request.query_params.get('year', timezone.now().year)
        try:
            year = int(year)
        except ValueError:
            year = timezone.now().year

        months_ru = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]

        # Общая сумма платежа = cash + transfer + online
        total_expr = ExpressionWrapper(
            F("cash_amount") + F("transfer_amount") + F("online_amount"),
            output_field=DecimalField()
        )

        # Доходы по месяцам
        payments = (
            Payment.objects.filter(date__year=year)
            .values("date__month")
            .annotate(total=Sum(total_expr))
        )

        month_data = {p['date__month']: p['total'] for p in payments}

        result = []
        total_year = 0
        for month_num in range(1, 13):
            income = month_data.get(month_num, 0) or 0
            total_year += income
            result.append({
                "year": year,
                "month": months_ru[month_num - 1],
                "month_number": month_num,
                "income": income,
            })

        context = {
            "year": year,
            "months": result,
            "total_year": total_year,
        }

        # Генерация PDF
        pdf_file = render_to_pdf("reports/monthly_income.html", context)

        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="monthly_income_{year}.pdf"'
        pdf_file.close()
        return response



class TeacherWorkloadAnalytics(APIView):
    permission_classes = [IsAdmin]
    def get(self, request):
        try:
            period = request.query_params.get('period', 'week')
            
            if period == 'week':
                start_date = timezone.now().date() - timedelta(days=7)
                end_date = timezone.now().date()
            else:  # month
                start_date = timezone.now().date().replace(day=1)
                end_date = timezone.now().date()

            # Получаем всех активных преподавателей
            teachers = CustomUser.objects.filter(
                role='Teacher',
                is_active=True
            )

            result = []
            
            for teacher in teachers:
                # 1. Количество занятий через расписание
                lessons_count = Schedule.objects.filter(
                    teacher=teacher,
                    date__range=[start_date, end_date]
                ).count()

                # 2. Группы преподавателя
                teacher_groups = Group.objects.filter(teacher=teacher)
                
                # 3. Количество учеников в группах преподавателя
                students_count = CustomUser.objects.filter(
                    student_groups__in=teacher_groups
                ).distinct().count()

                # 4. Доход по платежам студентов этих групп
                group_income = Payment.objects.filter(
                    invoice__months__group__in=teacher_groups,
                    date__range=[start_date, end_date]
                ).aggregate(
                    total=Sum(
                        F('cash_amount') + F('transfer_amount') + F('online_amount'),
                        output_field=FloatField()
                    )
                )['total'] or 0

                if lessons_count:  # Добавляем только преподавателей с занятиями
                    result.append({
                        'teacher': teacher.get_full_name(),
                        'lessons_count': lessons_count,
                        'students_count': students_count,
                        'group_income': float(group_income)
                    })

            # Сортируем по количеству занятий (по убыванию)
            result.sort(key=lambda x: x['lessons_count'], reverse=True)

            return Response(result)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )



class TeacherWorkloadPDFView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        period = request.query_params.get('period', 'week')
        
        if period == 'week':
            start_date = timezone.now().date() - timedelta(days=7)
            end_date = timezone.now().date()
        else:  # month
            start_date = timezone.now().date().replace(day=1)
            end_date = timezone.now().date()

        teachers = CustomUser.objects.filter(role='Teacher', is_active=True)
        result = []

        # выражение для суммы платежа
        total_expr = ExpressionWrapper(
            F("cash_amount") + F("transfer_amount") + F("online_amount"),
            output_field=DecimalField()
        )

        for teacher in teachers:
            # 1. Количество занятий
            lessons_count = Schedule.objects.filter(
                teacher=teacher,
                date__range=[start_date, end_date]
            ).count()

            # 2. Группы преподавателя
            teacher_groups = Group.objects.filter(teacher=teacher)

            # 3. Количество учеников
            students_count = CustomUser.objects.filter(
                student_groups__in=teacher_groups
            ).distinct().count()

            # 4. Доход по группам
            group_income = (
                Payment.objects.filter(
                    invoice__months__group__in=teacher_groups,
                    date__range=[start_date, end_date]
                )
                .aggregate(total=Sum(total_expr))['total'] or 0
            )

            if lessons_count:
                result.append({
                    'teacher': teacher.get_full_name(),
                    'lessons_count': lessons_count,
                    'students_count': students_count,
                    'group_income': float(group_income)
                })

        # Сортировка по количеству занятий
        result.sort(key=lambda x: x['lessons_count'], reverse=True)

        context = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'teachers': result,
        }

        # Генерация PDF через BytesIO
        pdf_file = render_to_pdf("reports/teacher_workload.html", context)

        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="teacher_workload_{period}.pdf"'
        pdf_file.close()
        return response



class PopularCoursesAnalytics(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            # Получаем направления с подсчетом студентов и групп
            directions = Direction.objects.annotate(
                num_students=Count('groups__students', distinct=True),
                num_groups=Count('groups', distinct=True)
            ).filter(num_students__gt=0).order_by('-num_students')

            result = []
            for rank, direction in enumerate(directions, start=1):
                # Считаем доход для каждого направления, суммируя все виды оплаты
                income = Payment.objects.filter(
                    invoice__months__group__direction=direction
                ).aggregate(
                    total=Sum(
                        F('cash_amount') + F('transfer_amount') + F('online_amount')
                    )
                )['total'] or 0

                result.append({
                    'rank': rank,
                    'course': direction.name,
                    'students_count': direction.num_students,
                    'groups_count': direction.num_groups,
                    'income': float(income)
                })

            return Response(result)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )
        



class PopularCoursesPDFView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            directions = Direction.objects.annotate(
                num_students=Count('groups__students', distinct=True),
                num_groups=Count('groups', distinct=True)
            ).filter(num_students__gt=0).order_by('-num_students')

            result = []
            for rank, direction in enumerate(directions, start=1):
                income = Payment.objects.filter(
                    invoice__months__group__direction=direction
                ).aggregate(
                    total=Coalesce(
                        Sum(
                            ExpressionWrapper(
                                F('cash_amount') + F('transfer_amount') + F('online_amount'),
                                output_field=DecimalField()  # здесь явно указываем DecimalField
                            )
                        ),
                        0,  # по умолчанию Coalesce возвращает IntegerField для 0, поэтому оборачиваем в Decimal
                        output_field=DecimalField()
                    )
                )['total'] or 0

                result.append({
                    'rank': rank,
                    'course': direction.name,
                    'students_count': direction.num_students,
                    'groups_count': direction.num_groups,
                    'income': float(income)
                })

            context = {'courses': result}
            pdf_file = render_to_pdf("reports/popular_courses.html", context)
            if not pdf_file:
                return HttpResponse("Ошибка при генерации PDF", status=500)

            response = HttpResponse(pdf_file.read(), content_type="application/pdf")
            response['Content-Disposition'] = 'attachment; filename="popular_courses.pdf"'
            pdf_file.close()
            return response

        except Exception as e:
            return HttpResponse(f"Ошибка при формировании отчёта: {e}", status=500)



class StudentAttendanceView(APIView):
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers, IsAdmin]
    def get(self, request, student_id):
        try:
            # Получаем все посещения студента с предзагрузкой связанных данных
            attendances = Attendance.objects.filter(
                student_id=student_id
            ).select_related(
                'lesson__month__group__direction',
                'lesson__month__group__teacher'
            ).order_by('-lesson__date')
            
            if not attendances.exists():
                return Response([])
            
            result = []
            for att in attendances:
                if not att.lesson:
                    continue
                
                # Основные данные
                attendance_data = {
                    'id': att.id,
                    'status': att.status,
                    'status_display': att.get_status_display(),
                    'group': att.lesson.month.group.group_name,
                    'subject': att.lesson.month.group.direction.name
                }
                
                # 1. Пытаемся получить дату из расписания
                schedule = Schedule.objects.filter(
                    group=att.lesson.month.group,
                    date=att.lesson.date
                ).first()
                
                if schedule:
                    attendance_data['date'] = schedule.date.strftime('%d.%m.%Y')
                    attendance_data['teacher'] = schedule.get_teacher_name()
                else:
                    # 2. Если нет расписания, берем дату из урока
                    attendance_data['date'] = att.lesson.date.strftime('%d.%m.%Y') if att.lesson.date else None
                    
                    # 3. Преподавателя берем из группы
                    if att.lesson.month.group.teacher:
                        attendance_data['teacher'] = att.lesson.month.group.teacher.get_full_name()
                    else:
                        attendance_data['teacher'] = None
                
                result.append(attendance_data)
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )

class StudentPaymentsView(APIView):
    permission_classes = [IsAdminOrManager, IsAdmin]

    def get(self, request, student_id):
        payments = Payment.objects.filter(
            invoice__student_id=student_id
        ).select_related('invoice').order_by('-date')
        
        data = []
        for pay in payments:
            # Добавляем отдельные поля оплаты, если есть
            if pay.cash_amount > 0:
                data.append({
                    'id': pay.id,
                    'date': pay.date.strftime('%d.%m.%Y'),
                    'amount': str(pay.cash_amount),
                    'payment_type': 'Наличные',
                    'comment': pay.comment
                })
            if pay.transfer_amount > 0:
                data.append({
                    'id': pay.id,
                    'date': pay.date.strftime('%d.%m.%Y'),
                    'amount': str(pay.transfer_amount),
                    'payment_type': 'Перевод',
                    'comment': pay.comment
                })
            if pay.online_amount > 0:
                data.append({
                    'id': pay.id,
                    'date': pay.date.strftime('%d.%m.%Y'),
                    'amount': str(pay.online_amount),
                    'payment_type': 'Онлайн',
                    'comment': pay.comment
                })
        
        # Можно отсортировать по дате, если нужно
        data.sort(key=lambda x: x['date'], reverse=True)
        
        return Response(data)



class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAdminOrManager, IsAdmin]
    filterset_fields = ['status', 'source']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from and date_to:
            queryset = queryset.filter(created_at__date__range=[date_from, date_to])
        elif date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        elif date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            
        # Поиск по имени, телефону или курсу
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(course__icontains=search)
            )
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadStatusUpdateSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
            
        return Response(LeadSerializer(lead).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        stats = {
            'new': Lead.objects.filter(status='new').count(),
            'in_progress': Lead.objects.filter(status='in_progress').count(),
            'registered': Lead.objects.filter(status='registered').count(),
            'rejected': Lead.objects.filter(status='rejected').count(),
            'total': Lead.objects.count(),
        }
        return Response(stats)
    

class AdminDashboardView(APIView):
    permission_classes = [IsAdminOrManager, IsAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.date()

        try:
            # 1. Новые ученики
            new_students_data = {
                'new_students_24h': CustomUser.objects.filter(
                    role='Student',
                    date_joined__gte=now - timedelta(hours=24)
                ).count(),
                'new_students_week': CustomUser.objects.filter(
                    role='Student',
                    date_joined__gte=today - timedelta(days=7)
                ).count(),
                'new_students_month': CustomUser.objects.filter(
                    role='Student',
                    date_joined__gte=today - timedelta(days=30)
                ).count(),
                'new_students_year': CustomUser.objects.filter(
                    role='Student',
                    date_joined__gte=today - timedelta(days=365)
                ).count(),
            }

            # 2. Последние лиды
            recent_invoices = Lead.objects.order_by('-created_at')[:2].values(
                'name', 'phone', 'email', 'course', 'status', 'comment', 'created_at'
            )

            # 3. Оплаты - ИСПРАВЛЕННАЯ ЧАСТЬ
            # Создаем выражение с правильным output_field
            total_expression = ExpressionWrapper(
                F('cash_amount') + F('transfer_amount') + F('online_amount'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )

            # Агрегация с использованием выражения
            payments_today_agg = Payment.objects.filter(date__date=today).aggregate(
                total=Coalesce(Sum(total_expression), Decimal('0.00'), output_field=DecimalField())
            )
            payments_today = payments_today_agg['total']

            # Альтернативный подход - проще и надежнее:
            payments_today_simple = Payment.objects.filter(date__date=today).aggregate(
                total=Coalesce(
                    Sum('cash_amount') + Sum('transfer_amount') + Sum('online_amount'),
                    Decimal('0.00'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )['total']

            # Используем альтернативный подход для надежности
            payments_today = payments_today_simple

            # Суммы по способам оплаты
            payments_by_method = Payment.objects.filter(date__date=today).aggregate(
                cash_total=Coalesce(Sum('cash_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')),
                transfer_total=Coalesce(Sum('transfer_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')),
                online_total=Coalesce(Sum('online_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')),
            )

            payments_data = {
                'payments_today': {'amount': float(payments_today)},  # Конвертируем в float для JSON
                'payments_by_method': {
                    'cash_total': float(payments_by_method['cash_total']),
                    'transfer_total': float(payments_by_method['transfer_total']),
                    'online_total': float(payments_by_method['online_total'])
                }
            }

            # 4. Предстоящие занятия
            upcoming_classes = Schedule.objects.filter(
                date=today,
                start_time__gte=now.time()
            ).order_by('start_time').select_related(
                'group', 'teacher'
            )[:3].values(
                'group__direction__name',
                'group__group_name',
                'teacher__first_name',
                'teacher__last_name',
                'start_time'
            )

            # 5. Посещаемость
            attendances_today = Attendance.objects.filter(
                lesson__date__date=today
            )

            total_lessons = Lesson.objects.filter(
                date__date=today
            ).count()

            attendance_stats = {
                'present': attendances_today.filter(status='1').count(),
                'online': attendances_today.filter(status='online').count(),
                'absent': attendances_today.filter(status='0').count(),
            }

            total_attendances = sum(attendance_stats.values())

            # Защита от деления на ноль
            total_attendances = total_attendances if total_attendances > 0 else 1

            attendance_data = {
                'total_lessons': total_lessons,
                'present': attendance_stats['present'],
                'present_percent': round(attendance_stats['present'] / total_attendances * 100) if total_attendances else 0,
                'online': attendance_stats['online'],
                'online_percent': round(attendance_stats['online'] / total_attendances * 100) if total_attendances else 0,
                'absent': attendance_stats['absent'],
                'absent_percent': round(attendance_stats['absent'] / total_attendances * 100) if total_attendances else 0,
                'total_students': CustomUser.objects.filter(role='Student', is_active=True).count()
            }

            data = {
                'new_students_24h': new_students_data['new_students_24h'],
                'new_students_week': new_students_data['new_students_week'],
                'new_students_month': new_students_data['new_students_month'],
                'new_students_year': new_students_data['new_students_year'],
                'recent_invoices': list(recent_invoices),  # Конвертируем в list
                'payments_today': payments_data['payments_today'],
                'payments_by_method': payments_data['payments_by_method'],
                'upcoming_classes': list(upcoming_classes),  # Конвертируем в list
                'attendance_stats': attendance_data
            }

            # Если у вас есть сериализатор DashboardStatsSerializer
            # serializer = DashboardStatsSerializer(data)
            # return Response(serializer.data)
            
            # Или просто возвращаем данные
            return Response(data)

        except Exception as e:
            # Логируем ошибку для отладки
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in AdminDashboardView: {str(e)}")
            
            return Response(
                {'error': 'Internal server error', 'details': str(e)}, 
                status=500
            )


class StudentGradesView(APIView):
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers, IsAdmin]
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            
            # Получаем все отправленные работы с предзагрузкой связей
            submissions = HomeworkSubmission.objects.filter(
                lesson__month__group=group
            ).select_related(
                'lesson__month__group',
                'lesson__month',
                'student'
            ).prefetch_related(
                'lesson__month'
            ).order_by('lesson__order')
            
            # Группируем по студентам
            students_data = []
            for student in group.students.all():
                student_submissions = submissions.filter(student=student)
                serializer = HomeworkSubmissionSerializer(student_submissions, many=True)
                
                # Рассчитываем средний балл
                scores = [s.score for s in student_submissions if s.score is not None]
                avg_score = round(sum(scores)/len(scores), 2) if scores else 0
                
                students_data.append({
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'submissions': serializer.data,
                    'average_score': avg_score
                })
            
            # Получаем структуру курсов
            months = group.months.all().prefetch_related('lessons')

            response_data = {
                'group': {
                    'id': group.id,
                    'name': group.group_name,
                    'direction': group.direction.name if group.direction else None
                },
                'months': [{
                    'id': month.id,
                    'month_number': month.month_number,
                    'title': month.title,
                    'lessons': [{
                        'id': lesson.id,
                        'title': lesson.title,
                        'order': lesson.order
                    } for lesson in month.lessons.all().order_by('order')]
                } for month in months.order_by('month_number')],
                'students': students_data
            }
            
            return Response(response_data)
            
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=404)
        


class PaymentNotificationViewSet(viewsets.ModelViewSet):
    queryset = PaymentNotification.objects.all()
    serializer_class = PaymentNotificationSerializer
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers, IsAdmin]



class SendReportsView(APIView):
    permission_classes = [IsAdmin]
    def post(self, request, *args, **kwargs):
        try:
            send_financial_reports_to_manager()
            return Response({"message": "Отчёты успешно отправлены!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class TeacherProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = TeacherProfileSerializer
    queryset = CustomUser.objects.filter(role='Teacher')
    lookup_url_kwarg = 'teacher_id'
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]

class CurrentUserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    


class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    queryset = CustomUser.objects.filter(role='Student')
    lookup_url_kwarg = 'student_id'
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]


class StudentHomeworkViewSet(viewsets.ViewSet):
    permission_classes = [IsStudent]

    

    # GET список или один урок
    def list(self, request):
        user = request.user
        student_groups = user.student_groups.all()
        current_months = Months.objects.filter(group__in=student_groups, month_number__in=[g.current_month for g in student_groups])
        lessons = Lesson.objects.filter(month__in=current_months).exclude(homework_description='').order_by('-date')
        serializer = StudentHomeworkSerializer(lessons, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        user = request.user
        lesson = generics.get_object_or_404(Lesson, pk=pk)
        if lesson.month.group not in user.student_groups.all():
            raise PermissionDenied("Нет доступа")
        serializer = StudentHomeworkSerializer(lesson, context={'request': request})
        return Response(serializer.data)

    # PATCH/PUT HomeworkSubmission
    def partial_update(self, request, pk=None):
        user = request.user
        lesson = generics.get_object_or_404(Lesson, pk=pk)
        submission, created = HomeworkSubmission.objects.get_or_create(lesson=lesson, student=user)
        serializer = HomeworkSubmissionUpdateSerializer(submission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(student=user, lesson=lesson)
        return Response(serializer.data)

    def update(self, request, pk=None):
        user = request.user
        lesson = generics.get_object_or_404(Lesson, pk=pk)
        submission, created = HomeworkSubmission.objects.get_or_create(lesson=lesson, student=user)
        serializer = HomeworkSubmissionUpdateSerializer(submission, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(student=user, lesson=lesson)
        return Response(serializer.data)



class TeacherHomeworkViewSet(viewsets.ModelViewSet):
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != "Teacher":
            raise PermissionDenied("Доступ только для преподавателей.")

        # Находим все группы, где текущий учитель является преподавателем
        groups = Group.objects.filter(teacher=user)

        # Находим все уроки этих групп
        lessons = Lesson.objects.filter(month__group__in=groups)

        # Находим все работы студентов по этим урокам
        return (
            HomeworkSubmission.objects.filter(lesson__in=lessons)
            .select_related("student", "lesson")
            .order_by("-submitted_at")
        )

    def perform_update(self, serializer):
        user = self.request.user
        submission = self.get_object()

        # проверяем что учитель связан с этой группой
        if submission.lesson.month.group.teacher != user:
            raise PermissionDenied("Вы не можете изменять чужие работы.")

        # обновляем только проверочные поля
        serializer.save(
            status=serializer.validated_data.get("status", submission.status),
            score=serializer.validated_data.get("score", submission.score),
            teacher_comment=serializer.validated_data.get(
                "teacher_comment", submission.teacher_comment
            ),
        )


class StudentProgressView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentProgressSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != 'Student':
            return Lesson.objects.none()

        # Получаем все уроки, где студент состоит в группе
        lessons = Lesson.objects.filter(month__group__in=user.student_groups.all()).order_by('date')

        # Подготавливаем данные для сериализатора
        progress_list = []
        for lesson in lessons:
            # Получаем посещаемость
            attendance = Attendance.objects.filter(lesson=lesson, student=user).first()
            # Получаем домашнее задание
            homework = HomeworkSubmission.objects.filter(lesson=lesson, student=user).first()
            
            progress_list.append({
                'lesson': lesson,
                'attendance': attendance or Attendance(status='0'),
                'homework': homework or HomeworkSubmission(status='black', score=None)
            })
        return progress_list
    


class DiscountRegulationViewSet(viewsets.ModelViewSet):
    queryset = DiscountRegulation.objects.all()
    serializer_class = DiscountRegulationSerializer