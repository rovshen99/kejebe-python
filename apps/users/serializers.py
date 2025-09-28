from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        avatar_field = getattr(obj, 'avatar', None)
        if not avatar_field:
            return None
        try:
            url = avatar_field.url
        except Exception:
            return None

        request = self.context.get('request') if hasattr(self, 'context') else None
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = User
        fields = ['uuid', 'name', 'surname', 'email', 'phone', 'role', 'avatar', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("phone", "password", "name", "surname", "email", "role")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'surname', 'email', 'role', 'avatar']
