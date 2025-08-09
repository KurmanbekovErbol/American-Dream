from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS

class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'Administrator'

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "Manager")

class IsStudent(BasePermission):
    """Разрешить доступ только аутентифицированным пользователям с ролью == 'Ученик'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "Student")

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "Teacher"
    

class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ["Administrator", "Manager"]
        )

class IsAdminOrTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.role == 'Teacher'
        )

class IsAdminOrReadOnlyForOthers(BasePermission):
    """
    Полный доступ для Administrator.
    Чтение для Manager, Teacher, Student.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Полный доступ для администратора
        if user.role == "Administrator":
            return True

        # Доступ только на чтение для остальных указанных ролей
        if user.role in ["Manager", "Teacher", "Student"]:
            return request.method in SAFE_METHODS

        # Остальным запрещено
        return False
    


class IsAdminOrReadOnlyForManagersAndTeachers(BasePermission):
    """
    Полный доступ для Administrator.
    Чтение для Manager и Teacher.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Полный доступ для администратора
        if user.role == "Administrator":
            return True

        # Доступ только на чтение для менеджеров и преподавателей
        if user.role in ["Manager", "Teacher"]:
            return request.method in SAFE_METHODS

        # Остальным запрещено
        return False
    


class IsAdminOrTeacherFullAccessOthersReadOnly(BasePermission):
    """
    Полный доступ для Administrator и Teacher.
    Чтение для Manager и Student.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Полный доступ для администратора и преподавателя
        if user.role in ["Administrator", "Teacher"]:
            return True

        # Доступ только на чтение для менеджеров и студентов
        if user.role in ["Manager", "Student"]:
            return request.method in SAFE_METHODS

        # Остальным запрещено
        return False
    

class IsInAllowedRoles(BasePermission):
    """
    Доступ разрешён всем пользователям с ролями Administrator, Teacher, Manager, Student.
    """

    allowed_roles = {"Administrator", "Teacher", "Manager", "Student"}

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)
    

class IsTeacherFullAccessStudentReadOnly(BasePermission):
    """
    Полный доступ для Teacher.
    Чтение для Student.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Полный доступ для преподавателя
        if user.role == "Teacher":
            return True

        # Чтение для студента
        if user.role == "Student":
            return request.method in SAFE_METHODS

        # Остальным запрещено
        return False