from django.db import transaction
from rest_framework import serializers
from .models import Note

class NoteSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=200, trim_whitespace=True)

    class Meta:
        model = Note
        fields = ["id", "title", "body", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Длина заголовка должна быть не меньше 3 символов.")

        qs = Note.objects.filter(title__iexact=value)
        instance = getattr(self, "instance", None)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Заметка с таким названием уже существует.")
        return value

    def validate(self, attrs):
        title = attrs.get("title") if "title" in attrs else (getattr(self.instance, "title", None) if self.instance else None)
        body = attrs.get("body") if "body" in attrs else (getattr(self.instance, "body", "") if self.instance else "")
        if title and body and title.strip() == body.strip():
            raise serializers.ValidationError("Заголовок и основная часть не должны быть идентичными.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):

        request = self.context.get("request")
        if request is not None and hasattr(validated_data, "__setitem__"):
            user = getattr(request, "user", None)
            if user and user.is_authenticated and hasattr(Note, "author"):
                validated_data["author"] = user
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class NoteListSerializer(serializers.ModelSerializer):

    excerpt = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Note
        fields = ["id", "title", "excerpt", "created_at"]
        read_only_fields = fields

    def get_excerpt(self, obj):
        if not obj.body:
            return ""
        text = obj.body.strip()
        if len(text) <= 100:
            return text
        cut = text[:100].rsplit(" ", 1)[0]
        return cut + "…"
