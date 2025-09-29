from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from .models import Note
from .serializers import NoteSerializer, NoteListSerializer
from .permissions import (
    ForbidDeleteShortTitleUnlessStaff,
    TitleMustBeNonEmptyOnWrite,
)


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ForbidDeleteShortTitleUnlessStaff,
        TitleMustBeNonEmptyOnWrite,
    ]

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
    permission_classes = [IsAuthenticatedOrReadOnly, TitleMustBeNonEmptyOnWrite]
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
    permission_classes = [IsAuthenticatedOrReadOnly, ForbidDeleteShortTitleUnlessStaff, TitleMustBeNonEmptyOnWrite]


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly, TitleMustBeNonEmptyOnWrite])
def note_list_create_func(request):
    if request.method == "GET":
        qs = Note.objects.all().order_by("-created_at")
        lite = request.query_params.get("lite") in {"1", "true", "yes"}
        ser = (NoteListSerializer(qs, many=True) if lite else NoteSerializer(qs, many=True))
        return Response(ser.data)

    ser = NoteSerializer(data=request.data, context={'request': request})
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly, ForbidDeleteShortTitleUnlessStaff, TitleMustBeNonEmptyOnWrite])
def note_detail_func(request, pk: int):
    note = get_object_or_404(Note, pk=pk)

    if request.method == "GET":
        return Response(NoteSerializer(note).data)

    if request.method in ("PUT", "PATCH"):
        partial = request.method == "PATCH"
        ser = NoteSerializer(note, data=request.data, partial=partial, context={'request': request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    note.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
