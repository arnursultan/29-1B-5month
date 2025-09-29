from rest_framework import permissions


class ForbidDeleteShortTitleUnlessStaff(permissions.BasePermission):
    message = "Нельзя удалять заметки с коротким заголовком."

    def has_object_permission(self, request, view, obj):
        if request.method != 'DELETE':
            return True
        title_len = len((obj.title or '').strip())
        if title_len < 5 and not (request.user and request.user.is_staff):
            return False
        return True


class TitleMustBeNonEmptyOnWrite(permissions.BasePermission):
    message = "Заголовок не может быть пустым."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        title = request.data.get('title')
        if title is None:
            return True
        return bool(str(title).strip())
