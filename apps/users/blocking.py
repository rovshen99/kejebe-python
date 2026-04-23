from __future__ import annotations

import uuid

from apps.users.models import User, UserBlock


def resolve_user_by_identifier(identifier: str) -> User:
    value = (identifier or "").strip()
    if not value:
        raise User.DoesNotExist

    try:
        parsed_uuid = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise User.DoesNotExist

    return User.objects.get(uuid=parsed_uuid)


def get_blocked_user_ids(user) -> list[int]:
    if not user or not getattr(user, "is_authenticated", False):
        return []

    cache_attr = "_cached_blocked_user_ids"
    cached = getattr(user, cache_attr, None)
    if cached is not None:
        return cached

    blocked_ids = list(
        UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    )
    setattr(user, cache_attr, blocked_ids)
    return blocked_ids
