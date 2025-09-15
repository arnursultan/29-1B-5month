from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Note
from .serializers import NoteSerializer

class NoteListCreateAPIView(APIView):
    def get(self,request):
        search = request.query_params.get("search")
        qs = Note.objects.all()
        if search:
            qs = qs.filter(title__icontains=search)

        serializer = NoteSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self,request):
        serializer = NoteSerializer(data=request.data)
        if serializer.is_valid():
            note = serializer.save()
            return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)
        Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NoteDetailAPIView(APIView):
    def get_object(self,pk):
        return get_object_or_404(Note, pk=pk)

    def get(self,request,pk):
        note = self.get_object(pk)
        serializer = NoteSerializer(note)
        return Response(serializer.data)

    def put(self,request,pk):
        note = self.get_object(pk)
        serializer = NoteSerializer(note, data=request.data)
        if serializer.is_valid():
            note = serializer.save()