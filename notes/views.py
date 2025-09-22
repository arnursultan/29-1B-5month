from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from .models import Note
from .serializers import NoteSerializer, NoteListSerializer
from django.conf import settings

class NoteListCreateAPIView(APIView):

    @method_decorator(cache_page(settings.CACHE_TTL))
    def get(self, request):
        search = request.query_params.get("search")
        lite = request.query_params.get("lite") in {"1", "true", "yes"}

        qs = Note.objects.all()
        if search:
            qs = qs.filter(title__icontains=search)
        if lite:
            qs = qs.only("id", "title", "created_at")

        serializer_class = NoteListSerializer if lite else NoteSerializer
        serializer = serializer_class(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = NoteSerializer(data=request.data)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NoteDetailAPIView(APIView):
    def get_object(self, pk):
        return get_object_or_404(Note, pk=pk)

    def get(self, request, pk):
        note = self.get_object(pk)
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        note = self.get_object(pk)
        serializer = NoteSerializer(note, data=request.data)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        note = self.get_object(pk)
        serializer = NoteSerializer(note, data=request.data, partial=True)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        note = self.get_object(pk)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
@cache_page(settings.CACHE_TTL)
def note_list_create(request):
    if request.method == "GET":
        search = request.query_params.get("search")
        lite = request.query_params.get("lite") in {"1", "true", "yes"}

        qs = Note.objects.all()
        if search:
            qs = qs.filter(title__icontains=search)
        if lite:
            qs = qs.only("id", "title", "created_at")
            serializer_class = NoteListSerializer if lite else NoteListSerializer
            serializer = serializer_class(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = NoteSerializer(data=request.data)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk)

    if request.method == "GET":
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "PUT":
        serializer = NoteSerializer(note, data=request.data)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PATCH":
        serializer = NoteSerializer(note, data=request.data, partial=True)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

