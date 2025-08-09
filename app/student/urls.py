from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.administration.views import GroupViewSet, GroupDashboardView, ScheduleViewSet, HomeworkListView, LessonDetailView, HomeworkSubmissionView 
from app.student.views import StudentProgressView

router = DefaultRouter()
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'groups', GroupViewSet, basename='group')


urlpatterns = [
    path('', include(router.urls)),
    path('groups/<int:id>/dashboard/', GroupDashboardView.as_view(), name='group-dashboard'),
    path('progress/<int:pk>/', StudentProgressView.as_view(), name='student-progress'),
    path('homework/', HomeworkListView.as_view(), name='homework-list'),
    path('lesson/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lesson/<int:lesson_id>/submit/', HomeworkSubmissionView.as_view(), name='homework-submit'),
]