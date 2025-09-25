from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings

from .models import Note
from .serializers import NoteSerializer, NoteListSerializer

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["created_at"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return NoteListSerializer
        return NoteSerializer

    def get_queryset(self):

        qs = super().get_queryset()
        user_lookup = self.kwargs.get("user_pk") or self.kwargs.get("user_id")
        if user_lookup and hasattr(Note, "author"):
            qs = qs.filter(author_id=user_lookup)
        return qs

    def perform_create(self, serializer):
        request = self.request
        if hasattr(Note, "author") and getattr(request, "user", None) and request.user.is_authenticated:
            serializer.save(author=request.user)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title_len = len((instance.title or "").strip())
        if title_len < 5 and not request.user.is_staff:
            return Response(
                {"detail": "Нельзя удалять заметки с коротким заголовком."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def recent(self, request):

        qs = self.get_queryset().order_by("-created_at")[:5]
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @method_decorator(cache_page(getattr(settings, "CACHE_TTL", 0)))
    def list(self, request, *args, **kwargs):
        lite = request.query_params.get("lite") in {"1", "true", "yes"}
        if lite:
            self.serializer_class = NoteListSerializer
        else:
            self.serializer_class = None
        return super().list(request, *args, **kwargs)



class NoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = Note.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        lite = self.request.query_params.get("lite") in {"1", "true", "yes"}
        return NoteListSerializer if lite else NoteSerializer

    @method_decorator(cache_page(getattr(settings, "CACHE_TTL", 0)))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]