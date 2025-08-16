from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.administration.views import (
    GroupViewSet, TeacherViewSet, StudentViewSet, 
    LessonViewSet, AttendanceViewSet, PaymentViewSet, 
    GroupDashboardView, MonthsViewSet, GroupTableViewSet, StudentTableViewSet,
    TeacherTableViewSet, IncomeViewSet, ExpenseViewSet, TeacherPaymentViewSet, 
    InvoiceViewSet, FinancialReportViewSet, GenerateFinancialReport, 
    CalculateTeacherPayments, ClassroomViewSet, ScheduleViewSet, DailyScheduleView,
    ActiveStudentsAnalytics, MonthlyIncomeAnalytics, TeacherWorkloadAnalytics, PopularCoursesAnalytics,
    StudentProfileView, StudentAttendanceView, StudentPaymentsView, LeadViewSet, AdminDashboardView, 
    HomeworkListView, LessonDetailView, HomeworkSubmissionView, MyHomeworkSubmissionsView, TeacherHomeworkListView,
    HomeworkReviewView, StudentGradesView, PaymentNotificationViewSet
    )

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'teachers-add', TeacherViewSet, basename='teacher_add')
router.register(r'students-add', StudentViewSet, basename='student_add')

router.register(r'lessons-add', LessonViewSet, basename='lesson-add')
router.register(r'attendances', AttendanceViewSet, basename='attendance')

router.register(r'months', MonthsViewSet, basename='month')
router.register(r'group-table', GroupTableViewSet, basename='group_table')
router.register(r'student-table', StudentTableViewSet, basename='student-table')
router.register(r'teacher-table', TeacherTableViewSet, basename='teacher-table')

router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'notifications', PaymentNotificationViewSet, basename='notifications')
router.register(r'payments', PaymentViewSet, basename='payment')
# router.register(r'payment-reminders', PaymentReminderViewSet, basename='payment-reminder')
router.register(r'financial-reports', FinancialReportViewSet, basename='financial-report')
router.register(r'incomes', IncomeViewSet, basename='income')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'teacher-payments', TeacherPaymentViewSet, basename='teacher-payment')

router.register(r'classrooms', ClassroomViewSet, basename='classroom')
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'leads', LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
    path('groups/<int:id>/dashboard/', GroupDashboardView.as_view(), name='group-dashboard'),
    path('generate-report/', GenerateFinancialReport.as_view(), name='generate-report'),
    # path('send-reminders/', SendPaymentReminders.as_view(), name='send-reminders'),
    path('calculate-teacher-payments/', CalculateTeacherPayments.as_view(), name='calculate-teacher-payments'),
    path('daily-schedule/', DailyScheduleView.as_view(), name='daily-schedule'),
    path('active-students/', ActiveStudentsAnalytics.as_view(), name='active-students'),
    path('monthly-income/', MonthlyIncomeAnalytics.as_view(), name='monthly-income'),
    path('teacher-workload/', TeacherWorkloadAnalytics.as_view(), name='teacher-workload'),
    path('popular-courses/', PopularCoursesAnalytics.as_view(), name='popular-courses'),
    path('students/<int:student_id>/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('students/<int:student_id>/attendance/', StudentAttendanceView.as_view(), name='student-attendance'),
    path('students/<int:student_id>/payments/', StudentPaymentsView.as_view(), name='student-payments'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('homework/', HomeworkListView.as_view(), name='homework-list'),
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/submit/', HomeworkSubmissionView.as_view(), name='homework-submit'),
    path('my-submissions/', MyHomeworkSubmissionsView.as_view(), name='my-homework-submissions'),
    path('teacher/homework/', TeacherHomeworkListView.as_view(), name='teacher-homework-list'),
    path('teacher/homework/<int:pk>/review/', HomeworkReviewView.as_view(), name='homework-review'),
    path('groups/<int:group_id>/grades/', StudentGradesView.as_view(), name='student-grades'),
]