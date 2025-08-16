from rest_framework import serializers
from app.administration.models import Attendance, HomeworkSubmission

from app.users.models import CustomUser

class StudentAttendanceSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title')
    lesson_date = serializers.DateTimeField(source='lesson.date')
    month_number = serializers.IntegerField(source='lesson.month.month_number')
    course_number = serializers.IntegerField(source='lesson.month.course.course_number')

    class Meta:
        model = Attendance
        fields = ['id', 'status', 'lesson_title', 'lesson_date', 'month_number', 'course_number']

class StudentHomeworkSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title')
    lesson_date = serializers.DateTimeField(source='lesson.date')
    month_number = serializers.IntegerField(source='lesson.month.month_number')
    course_number = serializers.IntegerField(source='lesson.month.course.course_number')

    class Meta:
        model = HomeworkSubmission
        fields = ['id', 'score', 'lesson_title', 'lesson_date', 'month_number', 'course_number']

class StudentProgressSerializer(serializers.ModelSerializer):
    attendances = serializers.SerializerMethodField()
    homeworks = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'attendances', 'homeworks']
    
    def get_attendances(self, obj):
        student = self.context.get('student', obj)
        return StudentAttendanceSerializer(
            Attendance.objects.filter(student=student).select_related(
                'lesson', 'lesson__month', 'lesson__month__course'
            ).order_by('lesson__date'),
            many=True
        ).data
    
    def get_homeworks(self, obj):
        student = self.context.get('student', obj)
        return StudentHomeworkSerializer(
            HomeworkSubmission.objects.filter(student=student).select_related(
                'lesson', 'lesson__month', 'lesson__month__course'
            ).order_by('lesson__date'),
            many=True
        ).data
    

