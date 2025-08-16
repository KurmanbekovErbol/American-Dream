from django.contrib import admin
from .models import (
    Direction, Group, Teacher, Student, Course, Months, Lesson,
    HomeworkSubmission, Attendance, Income, Expense, TeacherPayment,
    Invoice, Payment, FinancialReport, Classroom, Schedule, Lead,
    PaymentNotification
)


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_name", "direction", "age_group", "format", "planned_start", "teacher")
    list_filter = ("direction", "format", "planned_start")
    search_fields = ("group_name",)
    filter_horizontal = ("students",)
    autocomplete_fields = ("direction", "teacher")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("user", "payment_type", "payment_amount", "payment_period")
    list_filter = ("payment_type", "payment_period")
    search_fields = ("user__first_name", "user__last_name")
    filter_horizontal = ("groups", "directions")
    autocomplete_fields = ("user",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__first_name", "user__last_name")
    filter_horizontal = ("groups", "directions")
    autocomplete_fields = ("user",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("group", "course_number")
    list_filter = ("group",)
    search_fields = ("group__group_name",)
    autocomplete_fields = ("group",)


@admin.register(Months)
class MonthsAdmin(admin.ModelAdmin):
    list_display = ("course", "month_number", "title")
    list_filter = ("course",)
    search_fields = ("title",)
    autocomplete_fields = ("course",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("month", "title", "order", "date")
    list_filter = ("month", "date")
    search_fields = ("title",)
    autocomplete_fields = ("month",)


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "status", "score", "submitted_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("student__first_name", "student__last_name", "lesson__title")
    autocomplete_fields = ("lesson", "student")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "status")
    list_filter = ("status",)
    search_fields = ("student__first_name", "student__last_name", "lesson__title")
    autocomplete_fields = ("lesson", "student")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("direction", "amount", "date", "payment_method", "student", "group")
    list_filter = ("direction", "payment_method", "date")
    search_fields = ("student__first_name", "student__last_name", "group__group_name")
    autocomplete_fields = ("direction", "student", "group")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "description", "amount", "date", "teacher")
    list_filter = ("category", "date")
    search_fields = ("description", "teacher__first_name", "teacher__last_name")
    autocomplete_fields = ("teacher",)


@admin.register(TeacherPayment)
class TeacherPaymentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "lessons_count", "rate", "payment", "bonus", "paid_amount", "date", "is_paid")
    list_filter = ("is_paid", "date")
    search_fields = ("teacher__first_name", "teacher__last_name")
    autocomplete_fields = ("teacher",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "amount", "discount", "due_date", "status")
    list_filter = ("status", "due_date")
    search_fields = ("student__first_name", "student__last_name", "course__group__group_name")
    autocomplete_fields = ("student", "course")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_type", "date")
    list_filter = ("payment_type", "date")
    search_fields = ("invoice__student__first_name", "invoice__student__last_name")
    autocomplete_fields = ("invoice",)


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ("report_type", "start_date", "end_date", "generated_at")
    list_filter = ("report_type", "generated_at")


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("number", "capacity")
    search_fields = ("number",)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("classroom", "group", "teacher", "date", "start_time", "end_time")
    list_filter = ("date", "classroom", "teacher")
    search_fields = ("group__group_name", "teacher__first_name", "teacher__last_name")
    autocomplete_fields = ("classroom", "group", "teacher")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "course", "status", "source", "created_at")
    list_filter = ("status", "source", "created_at")
    search_fields = ("name", "phone", "course")


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "due_date", "amount", "created_at")
    list_filter = ("due_date", "created_at")
    search_fields = ("recipient_name",)

