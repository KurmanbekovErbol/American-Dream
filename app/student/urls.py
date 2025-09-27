from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.administration.views import GroupViewSet, GroupDashboardView, ScheduleViewSet
from app.student.views import StudentProgressView

router = DefaultRouter()
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'groups', GroupViewSet, basename='group')


urlpatterns = [
    path('', include(router.urls)),
    path('groups/<int:id>/dashboard/', GroupDashboardView.as_view(), name='group-dashboard'),
    path('progress/<int:pk>/', StudentProgressView.as_view(), name='student-progress'),
]