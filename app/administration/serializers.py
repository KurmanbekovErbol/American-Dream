from rest_framework import serializers
import datetime
from django.utils import timezone
from django.db.models import Sum, Avg

from app.administration.models import (
    Direction, Group, Teacher, Student, Lesson, Attendance, Payment, 
    Months, TeacherPayment, Income, Expense, Invoice,
    FinancialReport, Course, Schedule, Classroom, Lead, HomeworkSubmission, 
    PaymentNotification
    )
from app.users.models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'age', 'telegram', 'is_active', 'role']

class DirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = ['id', 'name']

class GroupShortSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Group
        fields = ['id', 'group_name']

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = HomeworkSubmission
        fields = [
            'id', 'lesson', 'lesson_title', 'student', 'student_name', 
            'group_name', 'project_links', 'files', 'submitted_at',
            'status', 'score', 'teacher_comment'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name()
    
    def get_group_name(self, obj):
        return obj.lesson.month.course.group.group_name
class LessonDetailSerializer(serializers.ModelSerializer):
    homework_submissions = HomeworkSubmissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'date', 'lesson_links',
            'homework_links', 'lesson_recording', 'homework_deadline',
            'homework_description', 'homework_requirements', 'homework_submissions'
        ]

class HomeworkListSerializer(serializers.ModelSerializer):
    has_submission = serializers.SerializerMethodField()
    submission_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'date', 'homework_deadline',
            'has_submission', 'submission_status'
        ]
    
    def get_has_submission(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.homework_submissions.filter(student=request.user).exists()
        return False
    
    def get_submission_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            submission = obj.homework_submissions.filter(student=request.user).first()
            return submission.status if submission else 'not_submitted'
        return 'not_submitted'


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'course_number']

class MonthsSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    
    class Meta:
        model = Months
        fields = '__all__'

class CourseWithMonthsSerializer(serializers.ModelSerializer):
    months = MonthsSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'course_number', 'months']

class GroupSerializer(serializers.ModelSerializer):
    direction = DirectionSerializer()
    teacher = CustomUserSerializer(read_only=True)
    students = CustomUserSerializer(many=True, read_only=True)
    months = MonthsSerializer(many=True, read_only=True)
    current_course = serializers.IntegerField(read_only=True)
    current_month = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Group
        fields = '__all__'

class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
        extra_kwargs = {
            'teacher': {'required': False},
            'students': {'required': False}
        }



class TeacherSerializer(serializers.ModelSerializer):
    directions = DirectionSerializer(many=True, read_only=True)
    groups = GroupShortSerializer(many=True, read_only=True)
    user = CustomUserSerializer()  # Используем существующий сериализатор пользователя
    
    # Для записи
    direction_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Direction.objects.all(),
        source='directions',
        write_only=True,
        required=False
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        source='groups',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'payment_type', 'payment_amount', 'payment_period',
            'directions', 'groups', 'direction_ids', 'group_ids'
        ]



class TeacherCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    age = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=False)
    telegram = serializers.CharField(write_only=True, required=False)
    
    direction_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Direction.objects.all(),
        source='directions',
        write_only=True,
        required=False
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        source='groups',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Teacher
        fields = [
            'username', 'password', 'first_name', 'last_name', 'age',
            'phone', 'telegram', 'payment_type', 'payment_amount',
            'payment_period', 'direction_ids', 'group_ids'
        ]
    
    def create(self, validated_data):
        user_data = {
            'username': validated_data.pop('username'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'age': validated_data.pop('age'),
            'phone': validated_data.pop('phone', ''),
            'telegram': validated_data.pop('telegram', ''),
            'role': 'Teacher'
        }
        
        directions = validated_data.pop('directions', [])
        groups = validated_data.pop('groups', [])
        
        user = CustomUser.objects.create_user(**user_data)
        teacher = Teacher.objects.create(user=user, **validated_data)
        
        # Установить направления
        teacher.directions.set(directions)

        # Установить группы
        teacher.groups.set(groups)

        # Обновить каждую группу, чтобы добавить преподавателя как teacher
        for group in groups:
            group.teacher = user
            group.save()

        return teacher



class StudentSerializer(serializers.ModelSerializer):
    directions = DirectionSerializer(many=True, read_only=True)
    groups = GroupShortSerializer(many=True, read_only=True)
    user = serializers.SerializerMethodField()
    
    # Для записи
    direction_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Direction.objects.all(),
        source='directions',
        write_only=True,
        required=False
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        source='groups',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Student
        fields = ['id', 'user', 'directions', 'groups', 'direction_ids', 'group_ids']
    
    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'age': obj.user.age,
            'phone': obj.user.phone,
            'telegram': obj.user.telegram
        }






class StudentCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    age = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=False)
    telegram = serializers.CharField(write_only=True, required=False)

    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        source='groups',
        write_only=True,
        required=False
    )
    direction_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Direction.objects.all(),
        source='directions',
        write_only=True,
        required=False
    )

    class Meta:
        model = Student
        fields = [
            'username', 'password', 'first_name', 'last_name', 'age', 'phone', 'telegram',
            'group_ids', 'direction_ids'
        ]

    def create(self, validated_data):
        user_data = {
            'username': validated_data.pop('username'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'age': validated_data.pop('age'),
            'phone': validated_data.pop('phone', ''),
            'telegram': validated_data.pop('telegram', ''),
            'role': 'Student'
        }

        groups = validated_data.pop('groups', [])
        directions = validated_data.pop('directions', [])

        user = CustomUser.objects.create_user(**user_data)
        
        # 👇 validated_data теперь пустой, так что создаём без него
        student = Student.objects.create(user=user)
        
        student.groups.set(groups)
        student.directions.set(directions)

        # Синхронизируем с Group.students (где CustomUser)
        for group in groups:
            group.students.add(user)

        return student







# =====================================================================







# serializers.py
class AttendanceSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), write_only=True)
    course_number = serializers.SerializerMethodField()
    month_number = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'student_id', 'student', 'status', 'course_number', 'month_number', 'lesson']

    def get_course_number(self, obj):
        return obj.lesson.month.course.course_number

    def get_month_number(self, obj):
        return obj.lesson.month.month_number




class PaymentSerializer(serializers.ModelSerializer):
    invoice_id = serializers.PrimaryKeyRelatedField(
        queryset=Invoice.objects.all(),
        source='invoice',
        write_only=True
    )
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    student_name = serializers.CharField(source='invoice.student.get_full_name', read_only=True)
    month_name = serializers.CharField(source='invoice.month.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'invoice_id', 'amount', 'payment_type', 'payment_type_display',
            'date', 'comment', 'student_name', 'month_name'
        ]


# serializers.py
class StudentDetailSerializer(serializers.ModelSerializer):
    attendances = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'age', 'is_active', 
                 'attendances', 'payments']
    
    def get_attendances(self, obj):
            group = self.context.get('group')
            if not group:
                return []
            
            course_ids = group.courses.values_list('id', flat=True)
            
            attendances = Attendance.objects.filter(
                student=obj,
                lesson__month__course_id__in=course_ids
            ).select_related(
                'lesson__month__course'
            )
            
            return AttendanceSerializer(attendances, many=True).data
    

    def get_payments(self, obj):
            try:
                group = self.context.get('group')
                if not group:
                    return []

                # Получаем все курсы группы
                course_ids = group.courses.values_list('id', flat=True)
                
                # Получаем платежи по курсам группы
                payments = Payment.objects.filter(
                    invoice__student=obj,
                    invoice__course_id__in=course_ids
                ).select_related('invoice', 'invoice__student')
                
                return GroupPaymentSerializer(payments, many=True).data
            except Exception:
                return []


class GroupDashboardSerializer(serializers.ModelSerializer):
    direction = DirectionSerializer(read_only=True)
    teacher = CustomUserSerializer(read_only=True)
    courses = CourseWithMonthsSerializer(many=True, read_only=True)
    students = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'group_name', 'direction', 'teacher', 'courses', 'students']
    
    def get_students(self, obj):
        students = obj.students.all()
        serializer = StudentDetailSerializer(
            students,
            many=True,
            context={'group': obj}
        )
        return serializer.data


    


class GroupTableSerializer(serializers.ModelSerializer):
    direction = serializers.CharField(source='direction.name')
    group = serializers.CharField(source='group_name')
    course = serializers.SerializerMethodField()
    lesson = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'direction', 'group', 'course', 'lesson']

    def get_course(self, obj):
        """Определить текущий курс группы"""
        # Если курсов нет — возвращаем 1
        if not obj.courses.exists():
            return 1

        # Логика определения курса — берём максимальный номер курса,
        # по которому уже есть уроки с датой
        last_course_with_lesson = (
            Course.objects.filter(group=obj, months__lessons__date__isnull=False)
            .order_by('-course_number')
            .first()
        )

        if last_course_with_lesson:
            return last_course_with_lesson.course_number

        # Если уроков с датой нет, берём первый курс
        return obj.courses.order_by('course_number').first().course_number

    def get_lesson(self, obj):
        """Получить номер последнего пройденного урока"""
        try:
            course_ids = obj.courses.values_list('id', flat=True)

            last_lesson = Lesson.objects.filter(
                month__course_id__in=course_ids
            ).order_by('-date', '-order').first()

            return last_lesson.order if last_lesson else 0
        except Exception as e:
            print(f"Error getting last lesson: {e}")
            return 0





# serializers.py
class StudentTableSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()

    class Meta:
        model = Student 
        fields = ['id', 'full_name', 'group', 'direction', 'teacher']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or "-"

    def get_group(self, obj):
        groups = obj.groups.all()
        if groups.exists():
            return ", ".join([g.group_name for g in groups])
        return "-"

    def get_direction(self, obj):
        directions = set()
        for group in obj.groups.all():
            if group.direction:
                directions.add(group.direction.name)
        return ", ".join(directions) if directions else "-"

    def get_teacher(self, obj):
        teachers = set()
        for group in obj.groups.all():
            if group.teacher:
                teachers.add(f"{group.teacher.last_name} {group.teacher.first_name}")
        return ", ".join(teachers) if teachers else "-"



# serializers.py
class TeacherTableSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    directions = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'full_name', 'groups', 'directions', 'student_count']

    def get_full_name(self, obj):
        return f"{obj.last_name} {obj.first_name}"

    def get_groups(self, obj):
        try:
            # Получаем объект Teacher через обратное отношение
            teacher = Teacher.objects.get(user=obj)
            groups = teacher.groups.all()
            return ", ".join([g.group_name for g in groups]) if groups.exists() else "-"
        except Teacher.DoesNotExist:
            return "-"

    def get_directions(self, obj):
        try:
            teacher = Teacher.objects.get(user=obj)
            directions = teacher.directions.all()
            return ", ".join([d.name for d in directions]) if directions.exists() else "-"
        except Teacher.DoesNotExist:
            return "-"

    def get_student_count(self, obj):
        try:
            teacher = Teacher.objects.get(user=obj)
            count = 0
            for group in teacher.groups.all():
                count += group.students.count()
            return count
        except Teacher.DoesNotExist:
            return 0
        





# Добавляем к существующим сериализаторам

class InvoiceSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source='course',
        write_only=True
    )
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='Student'),
        source='student',
        write_only=True,
        required=True  # Явно указываем, что поле обязательно
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'student', 'student_id', 'course', 'course_id', 'amount',
            'discount', 'final_amount', 'date_created', 'due_date', 'status',
            'status_display', 'paid_amount', 'balance', 'comment'
        ]
        extra_kwargs = {
            'student_id': {'required': True}  # Дополнительное подтверждение обязательности
        }

    def get_student(self, obj):
        return {
            'id': obj.student.id,
            'full_name': obj.student.get_full_name(),
            'phone': obj.student.phone
        }

    def validate(self, data):
        if 'student' not in data:
            raise serializers.ValidationError("Поле 'student_id' обязательно для заполнения")
        return data





class IncomeSerializer(serializers.ModelSerializer):
    direction_name = serializers.CharField(source='direction.name', read_only=True)
    student_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Income
        fields = [
            'id', 'direction', 'direction_name', 'amount', 'date', 
            'payment_method', 'payment_method_display', 'student', 
            'student_name', 'group', 'group_name', 'comment', 'discount',
            'is_full_payment'
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name() if obj.student else None

class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_display', 'description', 'amount',
            'date', 'teacher', 'teacher_name', 'comment'
        ]

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() if obj.teacher else None

class TeacherPaymentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = TeacherPayment
        fields = [
            'id', 'teacher', 'teacher_name', 'lessons_count', 'rate',
            'payment', 'bonus', 'paid_amount', 'balance', 'date', 'is_paid'
        ]

    def get_balance(self, obj):
        return obj.balance

class FinancialReportSerializer(serializers.ModelSerializer):
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    income_by_type = serializers.SerializerMethodField()
    expenses_by_category = serializers.SerializerMethodField()
    top_courses = serializers.SerializerMethodField()
    
    # Заменяем статические поля на динамические:
    total_income = serializers.SerializerMethodField()
    total_expenses = serializers.SerializerMethodField()
    net_profit = serializers.SerializerMethodField()

    class Meta:
        model = FinancialReport
        fields = [
            'id', 'report_type', 'report_type_display', 'start_date', 'end_date',
            'generated_at', 'total_income', 'total_expenses', 'net_profit',
            'income_by_type', 'expenses_by_category', 'top_courses'
        ]

    def get_total_income(self, obj):
        """Динамически рассчитываем общий доход за период"""
        return Payment.objects.filter(
            date__date__range=[obj.start_date, obj.end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_expenses(self, obj):
        """Динамически рассчитываем общие расходы за период"""
        return Expense.objects.filter(
            date__range=[obj.start_date, obj.end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_net_profit(self, obj):
        """Динамически рассчитываем чистую прибыль"""
        return self.get_total_income(obj) - self.get_total_expenses(obj)

    # Остальные методы (income_by_type, expenses_by_category, top_courses) остаются без изменений
    # ...

    def get_income_by_type(self, obj):
        payments = Payment.objects.filter(
            date__date__range=[obj.start_date, obj.end_date]
        ).values('payment_type').annotate(total=Sum('amount'))
        return {p['payment_type']: float(p['total']) for p in payments}

    def get_expenses_by_category(self, obj):
        expenses = Expense.objects.filter(
            date__range=[obj.start_date, obj.end_date]
        ).values('category').annotate(total=Sum('amount'))
        return {e['category']: float(e['total']) for e in expenses}

    def get_top_courses(self, obj):
        from django.db.models import Sum
        courses = Invoice.objects.filter(
            date_created__date__range=[obj.start_date, obj.end_date]
        ).values('course__group__direction__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]
        
        return {c['course__group__direction__name']: float(c['total']) 
                for c in courses if c['course__group__direction__name']}

# serializers.py
class GroupPaymentSerializer(serializers.ModelSerializer):
    final_amount = serializers.DecimalField(source='invoice.final_amount', max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(source='invoice.paid_amount', max_digits=10, decimal_places=2)
    balance = serializers.DecimalField(source='invoice.balance', max_digits=10, decimal_places=2)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    student_name = serializers.CharField(source='invoice.student.get_full_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'final_amount', 'paid_amount', 'balance',
            'payment_type', 'payment_type_display', 'date', 'comment', 'student_name'
        ]




class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = ['id', 'number', 'capacity']

class ScheduleSerializer(serializers.ModelSerializer):
    classroom = ClassroomSerializer(read_only=True)
    classroom_id = serializers.PrimaryKeyRelatedField(
        queryset=Classroom.objects.all(),
        source='classroom',
        write_only=True
    )
    teacher_name = serializers.CharField(source='get_teacher_name', read_only=True)
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'classroom', 'classroom_id', 'group', 'group_name', 
            'teacher', 'teacher_name', 'start_time', 'end_time', 
            'date', 'note'
        ]
    
    def validate(self, data):
        # Проверка на пересечение времени в одном кабинете
        if Schedule.objects.filter(
            classroom=data['classroom'],
            date=data['date'],
            start_time__lt=data['end_time'],
            end_time__gt=data['start_time']
        ).exists():
            raise serializers.ValidationError("Кабинет уже занят в это время")
        
        # Проверка что преподаватель не ведет другое занятие в это время
        if Schedule.objects.filter(
            teacher=data['teacher'],
            date=data['date'],
            start_time__lt=data['end_time'],
            end_time__gt=data['start_time']
        ).exists():
            raise serializers.ValidationError("Преподаватель уже занят в это время")
        
        return data

class DailyScheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    classrooms = serializers.SerializerMethodField()
    
    def get_classrooms(self, obj):
        date = obj['date']
        classrooms = Classroom.objects.all()
        schedule = Schedule.objects.filter(date=date).select_related('classroom', 'group', 'teacher')
        
        result = []
        for classroom in classrooms:
            classroom_data = ClassroomSerializer(classroom).data
            classroom_data['schedule'] = []
            
            for hour in range(9, 21):  # С 9:00 до 20:00
                time_slot = {
                    'time': f"{hour}:00",
                    'lesson': None
                }
                
                for lesson in schedule:
                    if lesson.classroom == classroom:
                        lesson_start = lesson.start_time.hour
                        lesson_end = lesson.end_time.hour
                        
                        if hour >= lesson_start and hour < lesson_end:
                            time_slot['lesson'] = {
                                'id': lesson.id,
                                'group': lesson.group.group_name,
                                'teacher': lesson.get_teacher_name(),
                                'note': lesson.note
                            }
                            break
                
                classroom_data['schedule'].append(time_slot)
            
            result.append(classroom_data)
        
        return result
    


class ScheduleListSerializer(serializers.ModelSerializer):
    classroom_id = serializers.IntegerField(source='classroom.id')
    time = serializers.SerializerMethodField()
    roomIndex = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    direction = serializers.CharField(source='group.direction.name')
    teacher = serializers.SerializerMethodField()
    group = serializers.CharField(source='group.group_name')
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'classroom_id', 'time', 'roomIndex', 
            'duration', 'direction', 'teacher', 'group',
            'date', 'note'
        ]
    
    def get_time(self, obj):
        return obj.start_time.hour
    
    def get_roomIndex(self, obj):
        # Предполагаем, что номера кабинетов соответствуют индексам
        return obj.classroom.id - 1  # или другая логика для roomIndex
    
    def get_duration(self, obj):
        return (obj.end_time.hour - obj.start_time.hour)
    
    def get_teacher(self, obj):
        return f"{obj.teacher.last_name} {obj.teacher.first_name[0]}."
    


class ActiveStudentsSerializer(serializers.Serializer):
    active_today = serializers.IntegerField()
    new_this_week = serializers.IntegerField()
    left_this_week = serializers.IntegerField()
    avg_age = serializers.DecimalField(max_digits=4, decimal_places=1)
    directions_distribution = serializers.DictField()

class MonthlyIncomeSerializer(serializers.Serializer):
    month = serializers.CharField()
    income = serializers.DecimalField(max_digits=10, decimal_places=0)

class TeacherWorkloadSerializer(serializers.Serializer):
    teacher = serializers.CharField()
    lessons_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    group_income = serializers.DecimalField(max_digits=10, decimal_places=0)

class PopularCoursesSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    course = serializers.CharField()
    students_count = serializers.IntegerField()
    groups_count = serializers.IntegerField()
    income = serializers.DecimalField(max_digits=10, decimal_places=0)




class StudentProfileSerializer(serializers.ModelSerializer):
    teacher = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'first_name', 'last_name', 'username',
            'telegram', 'phone', 'teacher', 'direction',
            'course', 'profile_picture'
        ]
        extra_kwargs = {
            'username': {'read_only': True}
        }

    def get_teacher(self, obj):
        group = obj.student_groups.first()
        return group.teacher.get_full_name() if group and group.teacher else None
    
    def get_direction(self, obj):
        group = obj.student_groups.first()
        return group.direction.name if group and group.direction else None
    
    def get_course(self, obj):
        group = obj.student_groups.first()
        if not group:
            return None
        latest_course = group.courses.order_by('-course_number').first()
        return latest_course.course_number if latest_course else None
    


class StudentAttendanceSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'date', 'subject', 'status', 'status_display',
            'teacher', 'group'
        ]
    
    def get_date(self, obj):
        schedule = Schedule.objects.filter(
            group=obj.lesson.month.course.group,
            date=obj.lesson.date
        ).first()
        return schedule.date.strftime('%d.%m.%Y') if schedule else None
    
    def get_subject(self, obj):
        return obj.lesson.month.course.group.direction.name
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_teacher(self, obj):
        schedule = Schedule.objects.filter(
            group=obj.lesson.month.course.group,
            date=obj.lesson.date
        ).first()
        return schedule.teacher if schedule else None
    
    def get_group(self, obj):
        return obj.lesson.month.course.group.group_name
    

    
class PaymentHistorySerializer(serializers.ModelSerializer):
    date = serializers.DateField(format='%d.%m.%Y')
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    
    class Meta:
        model = Payment
        fields = ['id', 'date', 'amount', 'payment_type', 'comment']




class LeadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_at = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
    updated_at = serializers.DateTimeField(format='%d.%m.%Y %H:%M')
    next_contact_date = serializers.DateTimeField(format='%d.%m.%Y %H:%M', required=False, allow_null=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'phone', 'email', 'course', 'status', 'status_display',
            'source', 'comment', 'created_at', 'updated_at', 'next_contact_date'
        ]

class LeadStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['status', 'comment', 'next_contact_date']



class DashboardStatsSerializer(serializers.Serializer):
    # Новые ученики
    new_students_24h = serializers.IntegerField()
    new_students_week = serializers.IntegerField()
    new_students_month = serializers.IntegerField()
    new_students_year = serializers.IntegerField()
    
    # Последние лиды
    recent_invoices = serializers.ListField(child=serializers.DictField())
    
    # Оплаты
    payments_today = serializers.DictField()
    payments_by_method = serializers.DictField()
    
    # Занятия
    upcoming_classes = serializers.ListField(child=serializers.DictField())
    
    # Посещаемость
    attendance_stats = serializers.DictField(child=serializers.IntegerField())





class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title')
    lesson_number = serializers.IntegerField(source='lesson.order')
    course_number = serializers.SerializerMethodField()
    month_number = serializers.SerializerMethodField()
    month_title = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = HomeworkSubmission
        fields = [
            'id',
            'lesson',
            'lesson_title',
            'lesson_number',
            'course_number',
            'month_number',
            'month_title',
            'student',
            'student_name',
            'group_name',
            'project_links',
            'files',
            'submitted_at',
            'status',
            'score',
            'teacher_comment',
            'feedback'
        ]

    def get_course_number(self, obj):
        return obj.lesson.month.course.course_number if hasattr(obj.lesson, 'month') else None

    def get_month_number(self, obj):
        return obj.lesson.month.month_number if hasattr(obj.lesson, 'month') else None

    def get_month_title(self, obj):
        return obj.lesson.month.title if hasattr(obj.lesson, 'month') else None

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_group_name(self, obj):
        if hasattr(obj.lesson, 'month') and hasattr(obj.lesson.month, 'course'):
            return obj.lesson.month.course.group.group_name
        return None
    


class PaymentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentNotification
        fields = '__all__'