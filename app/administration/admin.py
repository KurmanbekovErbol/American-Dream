# admin.py
from django.contrib import admin
from .models import (
    Direction, Group, Teacher, Student, Course, Months, Lesson,
    HomeworkSubmission, Attendance, Homework,
    Income, Expense, TeacherPayment,
    Invoice, Payment, PaymentReminder, FinancialReport,
    Classroom, Schedule, Lead
)


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_name", "direction", "format", "planned_start", "teacher")
    list_filter = ("direction", "format", "planned_start")
    search_fields = ("group_name", "direction__name", "teacher__last_name")
    filter_horizontal = ("students",)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("user", "payment_type", "payment_amount", "payment_period")
    list_filter = ("payment_type", "payment_period")
    search_fields = ("user__last_name", "user__first_name")
    filter_horizontal = ("groups", "directions")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__last_name", "user__first_name")
    filter_horizontal = ("groups", "directions")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("group", "course_number")
    list_filter = ("group",)
    search_fields = ("group__group_name",)


@admin.register(Months)
class MonthsAdmin(admin.ModelAdmin):
    list_display = ("course", "month_number", "title")
    list_filter = ("course",)
    ordering = ("month_number",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "month", "order", "date")
    list_filter = ("month",)
    search_fields = ("title",)
    ordering = ("order",)


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "status", "score", "submitted_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("student__last_name", "lesson__title")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "status")
    list_filter = ("status",)
    search_fields = ("student__last_name", "lesson__title")


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "score")
    list_filter = ("score",)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("direction", "amount", "date", "payment_method", "student", "group", "discount", "is_full_payment")
    list_filter = ("direction", "payment_method", "date", "is_full_payment")
    search_fields = ("student__last_name", "group__group_name")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "description", "amount", "date", "teacher")
    list_filter = ("category", "date")
    search_fields = ("teacher__last_name", "description")


@admin.register(TeacherPayment)
class TeacherPaymentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "lessons_count", "rate", "payment", "bonus", "paid_amount", "balance", "is_paid", "date")
    list_filter = ("is_paid", "date")
    search_fields = ("teacher__last_name",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "amount", "discount", "final_amount", "paid_amount", "balance", "status", "due_date")
    list_filter = ("status", "due_date")
    search_fields = ("student__last_name", "course__group__group_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_type", "date")
    list_filter = ("payment_type", "date")
    search_fields = ("invoice__student__last_name",)


@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ("invoice", "reminder_date", "days_before", "sent")
    list_filter = ("sent", "reminder_date")


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
    list_filter = ("classroom", "date", "teacher")
    search_fields = ("group__group_name", "teacher__last_name")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "course", "status", "source", "created_at", "next_contact_date")
    list_filter = ("status", "source", "created_at")
    search_fields = ("name", "phone", "course")
