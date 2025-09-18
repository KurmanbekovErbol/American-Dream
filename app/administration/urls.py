from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.administration.views import (
    GroupViewSet, TeacherViewSet, StudentViewSet, PopularCoursesPDFView,
    LessonViewSet, AttendanceViewSet, PaymentViewSet, TeacherPaymentsPDFView,
    GroupDashboardView, MonthsViewSet, GroupTableViewSet, StudentTableViewSet,
    TeacherTableViewSet, IncomeViewSet, ExpenseViewSet, TeacherPaymentViewSet, SendReportsView,
    InvoiceViewSet, FinancialReportViewSet, GenerateFinancialReport, IncomePDFView, FinancialReportPDFView,
    CalculateTeacherPayments, ClassroomViewSet, ScheduleViewSet, DailyScheduleView, ExpensePDFView,
    ActiveStudentsAnalytics, MonthlyIncomeAnalytics, TeacherWorkloadAnalytics, PopularCoursesAnalytics,
    StudentProfileView, StudentAttendanceView, StudentPaymentsView, LeadViewSet, AdminDashboardView, 
    HomeworkListView, LessonDetailView, HomeworkSubmissionView, MyHomeworkSubmissionsView, TeacherHomeworkListView,
    HomeworkReviewView, StudentGradesView, PaymentNotificationViewSet, MonthlyIncomePDFView, TeacherWorkloadPDFView,
    TeacherProfileView
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
    path('calculate-teacher-payments/', CalculateTeacherPayments.as_view(), name='calculate-teacher-payments'),
    path('daily-schedule/', DailyScheduleView.as_view(), name='daily-schedule'),
    path('active-students/', ActiveStudentsAnalytics.as_view(), name='active-students'),
    path('monthly-income/', MonthlyIncomeAnalytics.as_view(), name='monthly-income'),
    path('teacher-workload/', TeacherWorkloadAnalytics.as_view(), name='teacher-workload'), 
    path('popular-courses/', PopularCoursesAnalytics.as_view(), name='popular-courses'),
    path('popular-courses-pdf/', PopularCoursesPDFView.as_view(), name='popular-courses-pdf'),
    path('students/<int:student_id>/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('students/<int:student_id>/attendance/', StudentAttendanceView.as_view(), name='student-attendance'),
    path('students/<int:student_id>/payments/', StudentPaymentsView.as_view(), name='student-payments'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('homework/', HomeworkListView.as_view(), name='homework-list'),
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/submit/', HomeworkSubmissionView.as_view(), name='homework-submit'),
    path('my-submissions/', MyHomeworkSubmissionsView.as_view(), name='my-homework-submissions'),
    path('teacher/<int:teacher_id>/profile/', TeacherProfileView.as_view(), name='teacher-profile'),
    path('teacher/homework/', TeacherHomeworkListView.as_view(), name='teacher-homework-list'),
    path('teacher/homework/<int:pk>/review/', HomeworkReviewView.as_view(), name='homework-review'),
    path('groups/<int:group_id>/grades/', StudentGradesView.as_view(), name='student-grades'),
    path('teacher-payments-pdf/', TeacherPaymentsPDFView.as_view(), name='teacher-payments-pdf'),
    path('incomes-pdf/', IncomePDFView.as_view(), name='income-pdf'),
    path('expenses-pdf/', ExpensePDFView.as_view(), name='expense-pdf'),
    path('financial-report-pdf/', FinancialReportPDFView.as_view(), name='financial-report-pdf'),
    path("send-reports/", SendReportsView.as_view(), name="send-reports"),
    path('monthly-income-pdf/', MonthlyIncomePDFView.as_view(), name='monthly-income-pdf'),
    path('teacher-workload-pdf/', TeacherWorkloadPDFView.as_view(), name='teacher-workload-pdf'),

    path('teacher/<int:pk>/', TeacherProfileView.as_view(), name='teacher-profile'),
    path('teacher/me/', TeacherProfileView.as_view(), name='my-profile'),
]