from rest_framework import generics, viewsets, permissions
from app.users.models import CustomUser
from app.student.serializers import StudentProgressSerializer
from app.users.permissions import IsStudent
# from app.student.models import Homework
from rest_framework.response import Response


class StudentProgressView(generics.RetrieveAPIView):
    permission_classes = [IsStudent]
    serializer_class = StudentProgressSerializer
    queryset = CustomUser.objects.filter(role='Student')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['student'] = self.get_object()
        return context
    