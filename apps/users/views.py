from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from rest_framework import status

from .blocking import resolve_user_by_identifier
from .models import User, UserBlock, UserModerationEvent
from .serializers import (
    BlockedUserListItemSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
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
    summary="Deactivate current user",
    description=(
        "Soft deletes the authenticated user's account by anonymizing personal data, "
        "revoking the phone number, and setting is_active to false."
    ),
    responses={204: None},
)
class DeactivateMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.deleted_at:
            return Response(status=204)

        user.soft_delete()

        Device.objects.filter(user=user).update(user=None, updated_at=timezone.now())
        return Response(status=204)


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


@extend_schema(
    tags=["Users"],
    summary="Block or unblock user",
    parameters=[
        OpenApiParameter(
            name="user_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Target user identifier (numeric id or UUID).",
        )
    ],
)
class UserBlockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id: str):
        try:
            target_user = resolve_user_by_identifier(user_id)
        except User.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.id == request.user.id:
            return Response(
                {"detail": "You cannot block yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block_obj, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked=target_user,
        )
        if created:
            UserModerationEvent.objects.create(
                actor=request.user,
                target=target_user,
                action=UserModerationEvent.Action.BLOCK,
                source=UserModerationEvent.Source.APP,
            )

        return Response(
            {
                "blocked_user_id": str(target_user.uuid),
                "is_blocked": True,
                "created_at": block_obj.created_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, user_id: str):
        try:
            target_user = resolve_user_by_identifier(user_id)
        except User.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.id == request.user.id:
            return Response(
                {"detail": "You cannot unblock yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = UserBlock.objects.filter(
            blocker=request.user,
            blocked=target_user,
        ).delete()

        if deleted_count:
            UserModerationEvent.objects.create(
                actor=request.user,
                target=target_user,
                action=UserModerationEvent.Action.UNBLOCK,
                source=UserModerationEvent.Source.APP,
            )

        return Response(
            {
                "blocked_user_id": str(target_user.uuid),
                "is_blocked": False,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Users"],
    summary="List blocked users",
    responses={200: BlockedUserListItemSerializer(many=True)},
)
class BlockedUsersListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = (
            UserBlock.objects.filter(blocker=request.user)
            .select_related("blocked")
            .order_by("-created_at")
        )
        serializer = BlockedUserListItemSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)
