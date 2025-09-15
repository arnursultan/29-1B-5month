from rest_framework import serializers
from .models import Note

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "body", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Длина заголовка должна составлять не менее 3 символов.")
        qs = Note.objects.filter(title__iexact=value)
        instance = getattr(self, "instance", None)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Заметка с таким названием уже существует.")
        return value

    def validate(self, attrs):
        title = attrs.get("title") or getattr(self.instance, "title", None)
        body = attrs.get("body") or getattr(self.instance, "body", "")
        if title and body and title.strip() == body.strip():
            raise serializers.ValidationError({"non_field_errors": ["Заголовок и основная часть не должны быть идентичными."]})
        return attrs


class NoteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "created_at"]
        read_only_fields = fields