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
    MyHomeworkSubmissionsView, TeacherHomeworkListView, HomeworkReviewView
    )

router = DefaultRouter()


router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'student-table', StudentTableViewSet, basename='student-table')
router.register(r'schedule', ScheduleViewSet, basename='schedule')



urlpatterns = [
    path('', include(router.urls)),
    path('groups/<int:id>/dashboard/', GroupDashboardView.as_view(), name='group-dashboard'),
    path('daily-schedule/', DailyScheduleView.as_view(), name='daily-schedule'),
    path('students/<int:student_id>/profile/', StudentProfileView.as_view(), name='student-profile'),
    path('students/<int:student_id>/attendance/', StudentAttendanceView.as_view(), name='student-attendance'),
    path('my-submissions/', MyHomeworkSubmissionsView.as_view(), name='my-homework-submissions'),
    path('teacher/homework/', TeacherHomeworkListView.as_view(), name='teacher-homework-list'),
    path('teacher/homework/<int:pk>/review/', HomeworkReviewView.as_view(), name='homework-review'),
]