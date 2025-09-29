from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NoteViewSet,
    NoteListCreateAPIView,
    NoteRetrieveUpdateDestroyAPIView,
    note_list_create_func,
    note_detail_func,
)

router = DefaultRouter()
router.register(r'notes', NoteViewSet, basename='note')

urlpatterns = [
    path('', include(router.urls)),

    path('generic/notes/', NoteListCreateAPIView.as_view(), name='generic-note-list'),
    path('generic/notes/<int:pk>/', NoteRetrieveUpdateDestroyAPIView.as_view(), name='generic-note-detail'),

    path('func/notes/', note_list_create_func, name='func-note-list'),
    path('func/notes/<int:pk>/', note_detail_func, name='func-note-detail'),
]
