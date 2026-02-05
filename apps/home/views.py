from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Prefetch, Q, Value, Case, When, IntegerField, Subquery
from django.db.models.functions import Round
from django.utils import timezone, translation
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from apps.banners.models import Banner
from apps.categories.models import Category
from apps.home.models import HomeBlock, HomeBlockSourceMode, HomeBlockType, HomePageConfig
from apps.home.serializers import (
    BannerSerializer,
    CategoryLightSerializer,
    HomeBlockSerializer,
    StoriesRowItemSerializer,
)
from apps.regions.models import City, Region
from apps.regions.serializers import CitySerializer
from apps.services.serializers import ServiceCarouselSerializer, ServiceListSerializer
from apps.services.models import Favorite, Service, ServiceImage
from apps.stories.models import ServiceStory
from core.utils import get_lang_code, localized_value


class HomeViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        lang = self._resolve_language(request)
        city = self._resolve_city(request)
        region = self._resolve_region(request)
        if city and city.region and not region:
            region = city.region

        config_qs = (
            HomePageConfig.objects.filter(is_active=True)
            .filter(Q(locale=lang) | Q(locale__isnull=True) | Q(locale=""))
        )
        if city:
            config_qs = config_qs.filter(Q(city=city) | Q(city__isnull=True))
        else:
            config_qs = config_qs.filter(Q(city__isnull=True))

        if region:
            config_qs = config_qs.filter(Q(region=region) | Q(region__isnull=True))
        else:
            config_qs = config_qs.filter(Q(region__isnull=True))

        city_match = (
            Case(
                When(city=city, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
            if city
            else Value(0, output_field=IntegerField())
        )
        region_match = (
            Case(
                When(region=region, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
            if region
            else Value(0, output_field=IntegerField())
        )
        config_qs = config_qs.annotate(
            locale_match=Case(
                When(locale=lang, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            city_match=city_match,
            region_match=region_match,
            city_isnull=Case(
                When(city__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            region_isnull=Case(
                When(region__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by(
            "-locale_match",
            "-city_match",
            "-region_match",
            "city_isnull",
            "region_isnull",
            "-priority",
        )
        config = config_qs.first()

        city_payload = CitySerializer(city).data if city else None
        if not config:
            return Response({"version": 0, "city": city_payload, "blocks": []})

        blocks_payload: List[Dict[str, Any]] = []
        blocks = (
            config.blocks.filter(is_active=True)
            .order_by("position", "id")
            .prefetch_related("manual_items__content_object")
        )
        for block in blocks:
            items, view_all = self._build_block(block, city, region, request)
            block_limit = block.limit
            if block.type == HomeBlockType.CATEGORY_STRIP:
                block_limit = self._resolve_category_strip_limit(block)
            block_payload = {
                "id": f"blk_{block.id}",
                "type": block.type,
                "title": localized_value(block, "title", lang=lang) or None,
                "limit": block_limit,
                "style": block.style or {},
                "items": items,
                "view_all": view_all,
            }
            serialized_block = HomeBlockSerializer(block_payload).data
            blocks_payload.append(serialized_block)

        return Response(
            {
                "version": config.id,
                "city": city_payload,
                "blocks": blocks_payload,
            }
        )

    @staticmethod
    def _resolve_language(request) -> str:
        return get_lang_code(request)

    @staticmethod
    def _should_filter_by_location(block: HomeBlock, request) -> bool:
        style = block.style or {}
        if "location_filter" in style:
            val = style.get("location_filter")
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("1", "true", "yes", "y", "on")

        raw = request.query_params.get("location_filter")
        if raw is None:
            return False
        return str(raw).lower() in ("1", "true", "yes", "y", "on")

    @staticmethod
    def _manual_objects(block: HomeBlock, model_cls):
        objs = [
            item.content_object
            for item in block.manual_items.all()
            if isinstance(item.content_object, model_cls)
        ]
        return objs[: block.limit] if block.limit else objs

    @staticmethod
    def _param_list(params: Dict[str, Any], *keys: str) -> List[int]:
        raw = None
        for key in keys:
            if key in params:
                raw = params.get(key)
                break
        if raw is None:
            return []

        if isinstance(raw, str):
            raw = [part.strip() for part in raw.split(",") if part.strip()]
        elif isinstance(raw, (int, float)):
            raw = [raw]
        elif isinstance(raw, (list, tuple)):
            raw = list(raw)
        else:
            return []

        cleaned = []
        for val in raw:
            try:
                cleaned.append(int(val))
            except (TypeError, ValueError):
                continue
        return cleaned

    @staticmethod
    def _resolve_city(request) -> Optional[City]:
        city_id = request.query_params.get("city_id")
        if not city_id:
            device = getattr(request, "device", None)
            if device and device.city_id:
                return device.city
            user = getattr(request, "user", None)
            if user and getattr(user, "is_authenticated", False) and getattr(user, "city_id", None):
                return user.city
            return None
        try:
            return City.objects.select_related("region").get(id=city_id)
        except City.DoesNotExist:
            return None

    @staticmethod
    def _resolve_region(request) -> Optional[Region]:
        region_id = request.query_params.get("region_id")
        if region_id:
            try:
                return Region.objects.get(id=region_id)
            except Region.DoesNotExist:
                return None

        device = getattr(request, "device", None)
        if device and device.region_id:
            return device.region
        if device and device.city_id:
            return device.city.region

        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False) and getattr(user, "city_id", None):
            return user.city.region
        return None

    def _build_block(
        self, block: HomeBlock, city: Optional[City], region: Optional[Region], request
    ) -> Tuple[List[Any], Optional[Dict[str, Any]]]:
        if block.type == HomeBlockType.STORIES_ROW:
            return self._build_stories_row(block, city, region, request), None
        if block.type == HomeBlockType.BANNER_CAROUSEL:
            return self._build_banner_carousel(block, city, region, request), None
        if block.type == HomeBlockType.CATEGORY_STRIP:
            items, total_count, display_limit = self._build_category_strip(block, request)
            style = block.style or {}
            if "view_all" in style:
                view_all = style.get("view_all")
            elif total_count <= display_limit:
                view_all = None
            else:
                view_all = self._default_category_view_all()
            return items, self._ensure_view_all_label(view_all)
        if block.type in (HomeBlockType.SERVICE_CAROUSEL, HomeBlockType.SERVICE_LIST):
            return self._build_service_block(block, city, region, request)
        return [], None

    @staticmethod
    def _build_stories_row(
        block: HomeBlock, city: Optional[City], region: Optional[Region], request
    ) -> List[Dict[str, Any]]:
        lang = get_lang_code(request)
        now = timezone.now()
        stories_qs = (
            ServiceStory.objects.filter(
                Q(is_active=True),
                Q(starts_at__isnull=True) | Q(starts_at__lte=now),
                Q(ends_at__isnull=True) | Q(ends_at__gte=now),
            )
            .select_related("service", "service__city__region")
            .prefetch_related("service__available_cities")
            .order_by("service_id", "priority", "-starts_at", "-created_at")
        )

        items_map: Dict[int, Dict[str, Any]] = {}
        order_counter = 0
        for story in stories_qs:
            service = story.service
            if not service or not service.is_active:
                continue
            is_owner = bool(
                getattr(request, "user", None)
                and getattr(request.user, "is_authenticated", False)
                and service.vendor_id == getattr(request.user, "id", None)
            )
            city_match = False
            if region and not city:
                if service.city and service.city.region_id == region.id:
                    region_match = True
                else:
                    region_match = any(c.region_id == region.id for c in service.available_cities.all())
                if not region_match:
                    continue
            if city:
                if service.city_id == city.id:
                    city_match = True
                else:
                    city_match = any(c.id == city.id for c in service.available_cities.all())
            data = items_map.get(service.id)
            if data is None:
                order_counter += 1
                data = {
                    "id": story.id,
                    "service_id": service.id,
                    "title": localized_value(service, "title", lang=lang) or "",
                    "avatar_url": service.avatar.url if service.avatar else None,
                    "story_cover_url": story.image.url if story.image else None,
                    "has_unseen": True,
                    "stories_count": 0,
                    "is_owner": is_owner,
                    "city_match": city_match,
                    "order": order_counter,
                    "open": {"type": "story", "service_id": service.id},
                }
            else:
                data["city_match"] = data.get("city_match", False) or city_match
                data["is_owner"] = data.get("is_owner", False) or is_owner
            data["stories_count"] += 1
            if not data.get("story_cover_url") and story.image:
                data["story_cover_url"] = story.image.url
            items_map[service.id] = data

        items = list(items_map.values())
        items.sort(
            key=lambda x: (
                not x.get("is_owner", False),
                not x.get("city_match", False),
                x.get("order", 0),
            )
        )
        for item in items:
            item.pop("city_match", None)
            item.pop("order", None)
        if block.limit:
            items = items[: block.limit]
        return StoriesRowItemSerializer(items, many=True).data

    def _build_banner_carousel(
        self, block: HomeBlock, city: Optional[City], region: Optional[Region], request
    ) -> List[Dict[str, Any]]:
        lang = get_lang_code(request)
        banners: Iterable[Banner]
        apply_location_filter = self._should_filter_by_location(block, request)
        if block.source_mode == HomeBlockSourceMode.MANUAL:
            banners = self._manual_objects(block, Banner)
        else:
            banners_qs = Banner.objects.active_now().prefetch_related("cities", "regions")
            if apply_location_filter:
                if city:
                    banners_qs = banners_qs.filter(Q(cities=city) | Q(cities__isnull=True)).filter(
                        Q(regions=city.region) | Q(regions__isnull=True)
                    )
                elif region:
                    banners_qs = banners_qs.filter(Q(cities__region=region) | Q(cities__isnull=True)).filter(
                        Q(regions=region) | Q(regions__isnull=True)
                    )

            params = block.query_params or {}
            city_ids = self._param_list(params, "city_ids", "cities")
            region_ids = self._param_list(params, "region_ids", "regions")
            if city_ids:
                banners_qs = banners_qs.filter(cities__id__in=city_ids)
            if region_ids:
                banners_qs = banners_qs.filter(regions__id__in=region_ids)
            banners_qs = banners_qs.order_by("priority", "-created_at").distinct()
            banners = banners_qs if not block.limit else banners_qs[: block.limit]

        serializer = BannerSerializer(banners, many=True, context={"lang": lang, "request": request})
        return serializer.data

    @staticmethod
    def _parse_positive_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _default_view_all_label() -> Dict[str, str]:
        return {
            "ru": "Показать все",
            "tm": "Hemmesini gör",
        }

    @classmethod
    def _ensure_view_all_label(cls, view_all: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if view_all is None or not isinstance(view_all, dict):
            return view_all
        if "label" in view_all:
            return view_all
        updated = dict(view_all)
        updated["label"] = cls._default_view_all_label()
        return updated

    @classmethod
    def _default_category_view_all(cls) -> Dict[str, Any]:
        return {
            "type": "navigate",
            "screen": "AllCategories",
            "params": {},
            "label": cls._default_view_all_label(),
        }

    def _resolve_category_strip_limit(self, block: HomeBlock) -> int:
        block_limit = self._parse_positive_int(block.limit)
        default_limit = HomeBlock._meta.get_field("limit").default
        if block_limit is not None and block_limit != default_limit:
            return block_limit
        return 6

    def _build_category_strip(self, block: HomeBlock, request) -> Tuple[List[Dict[str, Any]], int, int]:
        lang = get_lang_code(request)
        display_limit = self._resolve_category_strip_limit(block)
        categories: Iterable[Category]
        if block.source_mode == HomeBlockSourceMode.MANUAL:
            all_categories = [
                item.content_object
                for item in block.manual_items.all()
                if isinstance(item.content_object, Category)
            ]
            total_count = len(all_categories)
            categories = all_categories[:display_limit]
        else:
            params = block.query_params or {}
            qs = Category.objects.filter(parent__isnull=True)
            category_ids = self._param_list(params, "category_ids", "categories")
            if category_ids:
                qs = qs.filter(id__in=category_ids)
            qs = qs.order_by("priority", "id")
            total_count = qs.count()
            categories = qs[:display_limit]

        serializer = CategoryLightSerializer(categories, many=True, context={"lang": lang, "request": request})
        return serializer.data, total_count, display_limit

    def _build_service_block(
        self, block: HomeBlock, city: Optional[City], region: Optional[Region], request
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        catalog_only = block.source_mode != HomeBlockSourceMode.MANUAL
        include_images = block.type == HomeBlockType.SERVICE_CAROUSEL
        include_tags = block.type == HomeBlockType.SERVICE_CAROUSEL
        services_qs = self._base_service_queryset(
            request.user,
            catalog_only=catalog_only,
            include_images=include_images,
            include_tags=include_tags,
        )
        manual_order: Optional[List[int]] = None
        pinned_ids: Optional[List[int]] = None
        apply_location_filter = self._should_filter_by_location(block, request)
        needs_distinct = False
        manual_items = None
        if block.source_mode in (HomeBlockSourceMode.MANUAL, HomeBlockSourceMode.PINNED_QUERY):
            manual_items = list(block.manual_items.all())

        if block.source_mode == HomeBlockSourceMode.MANUAL:
            manual_order = [
                item.object_id
                for item in manual_items or []
                if isinstance(item.content_object, Service)
            ]
            services_qs = services_qs.filter(id__in=manual_order)
        else:
            params = block.query_params or {}
            if block.source_mode == HomeBlockSourceMode.PINNED_QUERY:
                pinned_ids = [
                    item.object_id
                    for item in manual_items or []
                    if isinstance(item.content_object, Service)
                ]

            category_ids = self._param_list(params, "category_ids", "categories")
            tag_ids = self._param_list(params, "tag_ids", "tags")
            city_ids = self._param_list(params, "city_ids", "cities")
            region_ids = self._param_list(params, "region_ids", "regions")

            if category_ids:
                services_qs = services_qs.filter(category_id__in=category_ids)
            if tag_ids:
                services_qs = services_qs.filter(tags__id__in=tag_ids)
                needs_distinct = True
            if city_ids:
                services_qs = services_qs.filter(Q(city_id__in=city_ids) | Q(available_cities__id__in=city_ids))
                needs_distinct = True
            if region_ids:
                services_qs = services_qs.filter(
                    Q(city__region_id__in=region_ids) | Q(available_cities__region_id__in=region_ids)
                )
                needs_distinct = True

            order = params.get("ordering")
            if order:
                services_qs = services_qs.order_by(order)

        if apply_location_filter:
            if city:
                services_qs = services_qs.filter(Q(city=city) | Q(available_cities=city))
                needs_distinct = True
            elif region:
                services_qs = services_qs.filter(Q(city__region=region) | Q(available_cities__region=region))
                needs_distinct = True

        if needs_distinct:
            services_qs = services_qs.distinct()

        services: List[Service]
        if manual_order is not None:
            services_map = {service.id: service for service in services_qs}
            services = [services_map[sid] for sid in manual_order if sid in services_map]
            if block.limit:
                services = services[: block.limit]
        elif pinned_ids is not None:
            pinned_qs = services_qs.filter(id__in=pinned_ids)
            pinned_map = {s.id: s for s in pinned_qs}
            services = [pinned_map[sid] for sid in pinned_ids if sid in pinned_map]
            if block.limit:
                remaining = block.limit - len(services)
                if remaining > 0:
                    query_qs = services_qs.exclude(id__in=pinned_ids)[:remaining]
                    services.extend(list(query_qs))
            else:
                query_qs = services_qs.exclude(id__in=pinned_ids)
                services.extend(list(query_qs))
        else:
            services = list(services_qs[: block.limit])

        serializer_cls = (
            ServiceCarouselSerializer
            if block.type == HomeBlockType.SERVICE_CAROUSEL
            else ServiceListSerializer
        )
        serializer = serializer_cls(services, many=True, context={"request": request})
        view_all = self._build_view_all_for_service_block(
            block, city, region, apply_location_filter=apply_location_filter
        )

        return serializer.data, self._ensure_view_all_label(view_all)

    @staticmethod
    def _build_view_all_for_service_block(
        block: HomeBlock,
        city: Optional[City],
        region: Optional[Region],
        apply_location_filter: bool = False,
    ) -> Optional[Dict[str, Any]]:
        style = block.style or {}
        if "view_all" in style:
            return style.get("view_all")

        params = deepcopy(block.query_params) if block.query_params else {}
        if apply_location_filter and city:
            params.setdefault("city_ids", [city.id])
        elif apply_location_filter and region:
            params.setdefault("region_ids", [region.id])
        if not params:
            return None
        return {"type": "search", "params": params}

    @staticmethod
    def _base_service_queryset(
        user,
        catalog_only: bool = True,
        include_images: bool = False,
        include_tags: bool = True,
    ):
        prefetches = ["tags"] if include_tags else []
        if include_images:
            prefetches.append(
                Prefetch(
                    "serviceimage_set",
                    queryset=ServiceImage.objects.order_by("id"),
                    to_attr="prefetched_images",
                )
            )
        qs = (
            Service.objects.filter(is_active=True)
            .select_related("category", "city__region")
            .prefetch_related(*prefetches)
            .annotate(
                rating=Round(Avg("reviews__rating", filter=Q(reviews__is_approved=True)), 2),
                reviews_count=Count("reviews", filter=Q(reviews__is_approved=True)),
                cover_image_path=Subquery(
                    ServiceImage.objects.filter(service_id=OuterRef("pk"))
                    .order_by("id")
                    .values("image")[:1]
                ),
            )
            .defer("description_tm", "description_ru")
            .order_by("priority", "-created_at")
        )
        # if catalog_only:
        #     qs = qs.filter(is_catalog=True)
        if user and getattr(user, "is_authenticated", False):
            qs = qs.annotate(
                is_favorite=Exists(
                    Favorite.objects.filter(user=user, service_id=OuterRef("pk"))
                )
            )
        else:
            qs = qs.annotate(is_favorite=Value(False, output_field=BooleanField()))
        return qs
