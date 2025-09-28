from rest_framework import serializers
from .models import User
from apps.regions.models import City
from apps.regions.serializers import CitySerializer, RegionSerializer


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    city = CitySerializer(read_only=True)

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
        fields = ['uuid', 'name', 'surname', 'email', 'phone', 'role', 'city', 'avatar', 'created_at']


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
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), allow_null=True, required=False)

    class Meta:
        model = User
        fields = ['name', 'surname', 'email', 'role', 'avatar', 'city']
