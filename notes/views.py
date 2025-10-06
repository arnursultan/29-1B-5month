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

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes

from .models import Note
from .serializers import NoteSerializer, NoteListSerializer
from .permissions import (
    ForbidDeleteShortTitleUnlessStaff,
    TitleMustBeNonEmptyOnWrite,
)


@extend_schema_view(
    list=extend_schema(
        tags=["Notes"],
        summary="Список заметок",
        description=(
            "Возвращает список заметок. Поддерживает пагинацию, поиск, сортировку.\n\n"
            "**lite** — если включен, возвращает укороченный сериализатор."
        ),
        parameters=[
            OpenApiParameter(
                name="lite",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Облегчённый список: "1", "true", "yes".',
                examples=[
                    OpenApiExample("LiteOn", value="1"),
                    OpenApiExample("LiteOff", value="0"),
                ],
            ),
            OpenApiParameter(name="search", location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                             description='Поиск по "title" и "body"'),
            OpenApiParameter(name="ordering", location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                             description='Поля сортировки: "created_at", "title". Пример: "-created_at"'),
            OpenApiParameter(name="created_at", location=OpenApiParameter.QUERY, type=OpenApiTypes.DATETIME,
                             description='Фильтр по точной дате/времени (пример: 2025-01-01T12:00:00Z)'),
        ],
        responses={200: OpenApiResponse(response=NoteListSerializer, description="OK (или NoteSerializer, если lite=0)")},
    ),
    create=extend_schema(
        tags=["Notes"],
        summary="Создать заметку",
        request=NoteSerializer,
        responses={201: NoteSerializer},
        examples=[
            OpenApiExample(
                "Создание заметки",
                value={"title": "Моя заметка", "body": "Текст..."},
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Notes"],
        summary="Получить заметку",
        responses={200: NoteSerializer},
    ),
    update=extend_schema(
        tags=["Notes"],
        summary="Обновить заметку (PUT)",
        request=NoteSerializer,
        responses={200: NoteSerializer},
    ),
    partial_update=extend_schema(
        tags=["Notes"],
        summary="Частично обновить заметку (PATCH)",
        request=NoteSerializer,
        responses={200: NoteSerializer},
    ),
    destroy=extend_schema(
        tags=["Notes"],
        summary="Удалить заметку",
        responses={204: OpenApiResponse(description="Удалено")},
    ),
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

    @extend_schema(
        tags=["Notes"],
        summary="Последние 5 заметок",
        description="Возвращает 5 последних заметок по дате создания.",
        responses={200: NoteListSerializer(many=True)},
    )
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


@extend_schema_view(
    get=extend_schema(
        tags=["Notes"],
        summary="Список заметок (CBV)",
        parameters=[
            OpenApiParameter(name="lite", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY,
                             description='Облегчённый список: "1", "true", "yes"'),
            OpenApiParameter(name="search", location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                             description='Поиск по "title" и "body"'),
            OpenApiParameter(name="ordering", location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                             description='Сортировка по "created_at" или "title"'),
        ],
        responses={200: NoteListSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Notes"],
        summary="Создать заметку (CBV)",
        request=NoteSerializer,
        responses={201: NoteSerializer},
    ),
)
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


@extend_schema_view(
    get=extend_schema(tags=["Notes"], summary="Получить заметку (CBV)", responses={200: NoteSerializer}),
    put=extend_schema(tags=["Notes"], summary="Обновить заметку (PUT, CBV)", request=NoteSerializer, responses={200: NoteSerializer}),
    patch=extend_schema(tags=["Notes"], summary="Частично обновить заметку (PATCH, CBV)", request=NoteSerializer, responses={200: NoteSerializer}),
    delete=extend_schema(tags=["Notes"], summary="Удалить заметку (CBV)", responses={204: OpenApiResponse(description="Удалено")}),
)
class NoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, ForbidDeleteShortTitleUnlessStaff, TitleMustBeNonEmptyOnWrite]


@extend_schema(
    tags=["Notes (FBV)"],
    methods=["GET"],
    summary="Список заметок (FBV)",
    parameters=[
        OpenApiParameter(name="lite", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY,
                         description='Облегчённый список: "1", "true", "yes"'),
    ],
    responses={200: NoteListSerializer(many=True)},
)
@extend_schema(
    tags=["Notes (FBV)"],
    methods=["POST"],
    summary="Создать заметку (FBV)",
    request=NoteSerializer,
    responses={201: NoteSerializer},
    examples=[OpenApiExample("Создание", value={"title": "Новая", "body": "Текст"}, request_only=True)],
)
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


@extend_schema(
    tags=["Notes (FBV)"],
    methods=["GET"],
    summary="Получить заметку (FBV)",
    responses={200: NoteSerializer},
)
@extend_schema(
    tags=["Notes (FBV)"],
    methods=["PUT"],
    summary="Обновить заметку (PUT, FBV)",
    request=NoteSerializer,
    responses={200: NoteSerializer},
)
@extend_schema(
    tags=["Notes (FBV)"],
    methods=["PATCH"],
    summary="Частично обновить заметку (PATCH, FBV)",
    request=NoteSerializer,
    responses={200: NoteSerializer},
)
@extend_schema(
    tags=["Notes (FBV)"],
    methods=["DELETE"],
    summary="Удалить заметку (FBV)",
    responses={204: OpenApiResponse(description="Удалено")},
)
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
