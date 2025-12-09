from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from .models import User
from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer
from apps.devices.models import Device


@extend_schema(
    request=RegisterSerializer,
    responses={201: UserSerializer},
    tags=["Auth"],
    summary="Register a new user",
    description="Creates a new user with the provided role and details."
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    responses={200: UserSerializer},
    tags=["Auth"],
    summary="Get current user",
    description="Returns information about the authenticated user (requires token)."
)
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)


@extend_schema(
    request=UserUpdateSerializer,
    responses={200: UserSerializer},
    tags=["Auth"],
    summary="Update current user's profile",
    description="Allows the authenticated user to update name, surname, email, role, and avatar."
)
class MeUpdateView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        instance.refresh_from_db()
        output = UserSerializer(instance, context={"request": request})
        return Response(output.data)


@extend_schema(
    tags=["Auth"],
    summary="Logout",
    description="Clears device binding from the current user for the provided device_id. Tokens are not blacklisted."
)
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.query_params.get("device_id")
        )
        if not device_id:
            return Response({"detail": "device_id is required"}, status=400)

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return Response(status=204)

        if device.user_id == request.user.id:
            device.user = None
            device.save(update_fields=["user", "updated_at"])

        return Response(status=204)
