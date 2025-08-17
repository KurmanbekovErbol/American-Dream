import calendar
from django.http import Http404
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import Concat
from rest_framework.decorators import action
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
import datetime
from django.db.models import Count, Sum, Avg, Q
from app.administration.models import (
    Direction, Group, Teacher, Student, Lesson, Attendance, Payment, Months, Income, Expense, 
    TeacherPayment, Invoice, FinancialReport, Schedule, Classroom, Lead, HomeworkSubmission,
    PaymentNotification
    )
from app.administration.serializers import (
    DirectionSerializer, GroupSerializer, GroupCreateSerializer, TeacherCreateSerializer, TeacherSerializer, StudentCreateSerializer, StudentSerializer, LessonSerializer, AttendanceSerializer, 
    PaymentSerializer, GroupDashboardSerializer, MonthsSerializer, GroupTableSerializer, StudentTableSerializer, TeacherTableSerializer, TeacherPaymentSerializer, ExpenseSerializer, IncomeSerializer, FinancialReportSerializer, InvoiceSerializer,
    ScheduleSerializer, ClassroomSerializer, DailyScheduleSerializer, ScheduleListSerializer, ActiveStudentsSerializer, PopularCoursesSerializer,
    TeacherWorkloadSerializer, MonthlyIncomeSerializer, StudentProfileSerializer, StudentAttendanceSerializer, PaymentHistorySerializer, LeadSerializer, LeadStatusUpdateSerializer, DashboardStatsSerializer,
    LessonSerializer, LessonDetailSerializer, HomeworkListSerializer, HomeworkSubmissionSerializer, PaymentNotificationSerializer
    )
from app.users.models import CustomUser
from app.users.permissions import (
    IsAdminOrManager, IsAdmin, IsTeacher, IsStudent, IsAdminOrTeacher, IsAdminOrReadOnlyForOthers, IsAdminOrReadOnlyForManagersAndTeachers, 
    IsAdminOrTeacherFullAccessOthersReadOnly, IsInAllowedRoles, IsTeacherFullAccessStudentReadOnly
    )


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







# ==========================================================================================





class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrTeacherFullAccessOthersReadOnly]

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    pagination_class = [IsTeacher]



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
        'courses',
        'courses__months',
        'courses__months__lessons',
        'courses__months__lessons__attendances',
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
            'courses': [
                {
                    'id': course.id,
                    'course_number': course.course_number,
                    'months': MonthsSerializer(
                        course.months.all().order_by('month_number'),
                        many=True
                    ).data
                }
                for course in instance.courses.all().order_by('course_number')
            ],
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
    """Viewset for displaying group table with month of study"""
    queryset = Group.objects.all().select_related('direction')
    serializer_class = GroupTableSerializer
    filterset_fields = ['direction__name', 'group_name']
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(group_name__icontains=search_query) |
                Q(direction__name__icontains=search_query))
        
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
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]
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
    permission_classes = [IsAdminOrManager]
    queryset = Invoice.objects.all().select_related('student', 'course')
    serializer_class = InvoiceSerializer
    filterset_fields = ['student', 'course', 'status', 'due_date']

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
    permission_classes = [IsAdminOrManager]
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

# class PaymentReminderViewSet(viewsets.ModelViewSet):
#     # permission_classes = [IsAdminOrManager]
#     queryset = PaymentReminder.objects.all().select_related('invoice')
#     serializer_class = PaymentReminderSerializer
#     filterset_fields = ['sent', 'reminder_date']

#     def get_queryset(self):
#         queryset = super().get_queryset()
        
#         # Фильтр по периоду
#         start_date = self.request.query_params.get('start_date')
#         end_date = self.request.query_params.get('end_date')
        
#         if start_date and end_date:
#             queryset = queryset.filter(reminder_date__range=[start_date, end_date])
#         elif start_date:
#             queryset = queryset.filter(reminder_date__gte=start_date)
#         elif end_date:
#             queryset = queryset.filter(reminder_date__lte=end_date)
            
#         return queryset.order_by('reminder_date')

class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.all().select_related('direction', 'student', 'group')
    serializer_class = IncomeSerializer
    filterset_fields = ['direction', 'payment_method', 'date', 'is_full_payment']
    permission_classes = [IsAdminOrManager]

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().select_related('teacher')
    serializer_class = ExpenseSerializer
    filterset_fields = ['category', 'date']
    permission_classes = [IsAdminOrManager]

class TeacherPaymentViewSet(viewsets.ModelViewSet):
    queryset = TeacherPayment.objects.all().select_related('teacher')
    serializer_class = TeacherPaymentSerializer
    filterset_fields = ['teacher', 'date', 'is_paid']
    permission_classes = [IsAdminOrManager]

class FinancialReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    filterset_fields = ['report_type', 'start_date', 'end_date']
    permission_classes = [IsAdminOrManager]

# views.py
class GenerateFinancialReport(APIView):
    # permission_classes = [IsAdmin]
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

# class SendPaymentReminders(APIView):
#     # permission_classes = [IsAdminOrManager]
#     def post(self, request, format=None):
#         today = timezone.now().date()
#         reminders = PaymentReminder.objects.filter(
#             reminder_date=today,
#             sent=False
#         ).select_related('invoice', 'invoice__student')
        
#         for reminder in reminders:
#             try:
#                 send_mail(
#                     'Напоминание об оплате',
#                     reminder.message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [reminder.invoice.student.email],
#                     fail_silently=False,
#                 )
#                 reminder.sent = True
#                 reminder.save()
#             except Exception as e:
#                 continue
        
#         return Response(
#             {'sent': reminders.count()},
#             status=status.HTTP_200_OK
#         )

class CalculateTeacherPayments(APIView):
    permission_classes = [IsAdminOrManager]
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
                        month__course__group=group,
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
    # permission_classes = [IsAdmin]
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
    

class DailyScheduleView(APIView):
    # permission_classes = [IsAdmin]
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
        
        # 2. Ушедшие на этой неделе
        active_last_week = Attendance.objects.filter(
            lesson__date__date__range=[week_ago, today - timedelta(days=1)],
            status__in=['1', 'online']
        ).values_list('student_id', flat=True).distinct()
        
        left_this_week = 0
        if active_last_week:
            still_active = Attendance.objects.filter(
                lesson__date__date__range=[today - timedelta(days=6), today],
                status__in=['1', 'online'],
                student_id__in=active_last_week
            ).distinct().count()
            
            left_this_week = len(active_last_week) - still_active
        
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

        # Получаем доходы по месяцам для указанного года
        payments = Payment.objects.filter(
            date__year=year
        ).values('date__month').annotate(
            total=Sum('amount')
        ).order_by('date__month')

        # Создаем словарь для быстрого доступа к данным по месяцам
        month_data = {p['date__month']: p['total'] for p in payments}

        # Формируем результат для всех месяцев
        result = []
        for month_num in range(1, 13):
            result.append({
                'year': year,
                'month': months_ru[month_num - 1],
                'month_number': month_num,
                'income': str(month_data.get(month_num, 0))
            })

                
        return Response(result)

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
                    invoice__course__group__in=teacher_groups,
                    date__range=[start_date, end_date]
                ).aggregate(total=Sum('amount'))['total'] or 0

                if lessons_count > 0:  # Добавляем только преподавателей с занятиями
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
                # Для каждого направления отдельно считаем доход
                income = Payment.objects.filter(
                    invoice__course__group__direction=direction
                ).aggregate(total=Sum('amount'))['total'] or 0
                
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
        




class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    queryset = CustomUser.objects.filter(role='Student')
    lookup_url_kwarg = 'student_id'
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]
    
    # Разрешаем доступ без аутентификации
    authentication_classes = []

class StudentAttendanceView(APIView):
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]
    def get(self, request, student_id):
        try:
            # Получаем все посещения студента с предзагрузкой связанных данных
            attendances = Attendance.objects.filter(
                student_id=student_id
            ).select_related(
                'lesson__month__course__group__direction',
                'lesson__month__course__group__teacher'
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
                    'group': att.lesson.month.course.group.group_name,
                    'subject': att.lesson.month.course.group.direction.name
                }
                
                # 1. Пытаемся получить дату из расписания
                schedule = Schedule.objects.filter(
                    group=att.lesson.month.course.group,
                    date=att.lesson.date
                ).first()
                
                if schedule:
                    attendance_data['date'] = schedule.date.strftime('%d.%m.%Y')
                    attendance_data['teacher'] = schedule.get_teacher_name()
                else:
                    # 2. Если нет расписания, берем дату из урока
                    attendance_data['date'] = att.lesson.date.strftime('%d.%m.%Y') if att.lesson.date else None
                    
                    # 3. Преподавателя берем из группы
                    if att.lesson.month.course.group.teacher:
                        attendance_data['teacher'] = att.lesson.month.course.group.teacher.get_full_name()
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
    permission_classes = [IsAdminOrManager]
    def get(self, request, student_id):
        payments = Payment.objects.filter(
            invoice__student_id=student_id
        ).select_related('invoice').order_by('-date')
        
        data = [{
            'id': pay.id,
            'date': pay.date.strftime('%d.%m.%Y'),
            'amount': str(pay.amount),
            'payment_type': pay.get_payment_type_display(),
            'comment': pay.comment
        } for pay in payments]
        
        return Response(data)
    


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAdminOrManager]
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
    permission_classes = [IsAdminOrManager]
    
    def get(self, request):
        now = timezone.now()
        today = now.date()
        
        # 1. Новые ученики
        new_students_data = {
            'new_students_24h': CustomUser.objects.filter(
                role='Student',
                date_joined__gte=now - timedelta(hours=24))
                .count(),
            'new_students_week': CustomUser.objects.filter(
                role='Student',
                date_joined__gte=today - timedelta(days=7))
                .count(),
            'new_students_month': CustomUser.objects.filter(
                role='Student',
                date_joined__gte=today - timedelta(days=30))
                .count(),
            'new_students_year': CustomUser.objects.filter(
                role='Student',
                date_joined__gte=today - timedelta(days=365))
                .count(),
        }
        
        # 2. Последние лиды
        recent_invoices = Invoice.objects.order_by('-date_created')[:2].values(
            'student__first_name', 'student__last_name', 'date_created', 'course__group__group_name', 'status', 'comment'
        )
        
        # 3. Оплаты
        payments_today = Payment.objects.filter(
            date__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        payments_by_method = Payment.objects.filter(
            date__date=today
        ).values('payment_type').annotate(
            total=Sum('amount')
        )
        
        payments_data = {
            'payments_today': {'amount': payments_today},
            'payments_by_method': {
                method['payment_type']: method['total'] 
                for method in payments_by_method
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
        
        # 5. Посещаемость (обновленная логика)
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
            'recent_invoices': recent_invoices,
            'payments_today': payments_data['payments_today'],
            'payments_by_method': payments_data['payments_by_method'],
            'upcoming_classes': upcoming_classes,
            'attendance_stats': attendance_data
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)
    




class HomeworkListView(generics.ListAPIView):
    serializer_class = HomeworkListSerializer
    permission_classes = [IsTeacherFullAccessStudentReadOnly]
    
    def get_queryset(self):
        # Получаем уроки, где есть домашние задания
        return Lesson.objects.exclude(homework_description='').order_by('-date')

class LessonDetailView(generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonDetailSerializer
    permission_classes = [IsTeacherFullAccessStudentReadOnly]

class HomeworkSubmissionView(generics.CreateAPIView):
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsStudent]
    
    def perform_create(self, serializer):
        lesson_id = self.kwargs.get('lesson_id')
        lesson = generics.get_object_or_404(Lesson, pk=lesson_id)
        serializer.save(student=self.request.user, lesson=lesson)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class MyHomeworkSubmissionsView(generics.ListAPIView):
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsTeacherFullAccessStudentReadOnly]
    
    def get_queryset(self):
        return HomeworkSubmission.objects.filter(
            student=self.request.user
        ).order_by('-submitted_at')
    




class TeacherHomeworkListView(generics.ListAPIView):
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsTeacherFullAccessStudentReadOnly]
    
    def get_queryset(self):
        # Получаем группы, где текущий пользователь является преподавателем
        teacher_groups = Group.objects.filter(teacher=self.request.user)
        
        # Получаем ДЗ из этих групп
        return HomeworkSubmission.objects.filter(
            lesson__month__course__group__in=teacher_groups
        ).select_related(
            'student',
            'lesson',
            'lesson__month',
            'lesson__month__course',
            'lesson__month__course__group'
        ).order_by('-submitted_at')

class HomeworkReviewView(generics.UpdateAPIView):
    queryset = HomeworkSubmission.objects.all()
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsTeacherFullAccessStudentReadOnly]

    def get_object(self):
        obj = super().get_object()
        # Проверяем, что текущий пользователь - преподаватель группы этого ДЗ
        if not obj.lesson.month.course.group.teacher == self.request.user:
            raise PermissionDenied("Вы не являетесь преподавателем этой группы")
        return obj

    def perform_update(self, serializer):
        instance = self.get_object()
        
        # Проверяем, что статус изменяется на допустимый
        new_status = serializer.validated_data.get('status')
        valid_statuses = ['reviewed', 'accepted', 'rejected']
        if new_status and new_status not in valid_statuses:
            raise serializers.ValidationError(
                {'status': f"Допустимые статусы: {', '.join(valid_statuses)}"}
            )
        
        # Сохраняем обновленные данные
        serializer.save()




class StudentGradesView(APIView):
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            
            # Получаем все отправленные работы с предзагрузкой связей
            submissions = HomeworkSubmission.objects.filter(
                lesson__month__course__group=group
            ).select_related(
                'lesson__month__course__group',
                'lesson__month',
                'student'
            ).prefetch_related(
                'lesson__month__course'
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
            courses = group.courses.all().prefetch_related(
                'months',
                'months__lessons'
            )
            
            response_data = {
                'group': {
                    'id': group.id,
                    'name': group.group_name,
                    'direction': group.direction.name if group.direction else None
                },
                'courses': [{
                    'id': course.id,
                    'course_number': course.course_number,
                    'months': [{
                        'id': month.id,
                        'month_number': month.month_number,
                        'title': month.title,
                        'lessons': [{
                            'id': lesson.id,
                            'title': lesson.title,
                            'order': lesson.order
                        } for lesson in month.lessons.all().order_by('order')]
                    } for month in course.months.all().order_by('month_number')]
                } for course in courses.order_by('course_number')],
                'students': students_data
            }
            
            return Response(response_data)
            
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=404)
        


class PaymentNotificationViewSet(viewsets.ModelViewSet):
    queryset = PaymentNotification.objects.all()
    serializer_class = PaymentNotificationSerializer
    permission_classes = [IsAdminOrReadOnlyForManagersAndTeachers]