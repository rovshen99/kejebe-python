from django.core.validators import FileExtensionValidator
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from apps.categories.models import Category
from apps.regions.models import Region, City
from apps.services.validators import validate_file_size
from apps.users.models import User
from core.fields import WebPImageField

from django_summernote.fields import SummernoteTextField

from slugify import slugify


class ServiceQuerySet(models.QuerySet):
    def filter_by_category_ids(self, category_ids):
        if not category_ids:
            return self
        return self.filter(
            Q(category_id__in=category_ids) | Q(additional_categories__id__in=category_ids)
        ).distinct()

    def with_category_match_rank(self, category_id):
        if not category_id:
            return self
        return self.annotate(
            category_match_rank=Case(
                When(category_id=category_id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("category_match_rank", "priority", "-created_at")


class Service(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Vendor"))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_("Category"))
    additional_categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="services_additional",
        verbose_name=_("Additional Categories"),
    )
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("City"))
    avatar = WebPImageField(
        upload_to="services/avatars", verbose_name=_("Avatar"), null=True, default=None, blank=True
    )
    regions = models.ManyToManyField(Region, related_name='services', verbose_name=_("Regions"))
    available_cities = models.ManyToManyField(
        City,
        related_name='services',
        verbose_name=_("Available Cities"),
        blank=True,
    )

    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))

    description_tm = SummernoteTextField(verbose_name=_("Description (TM)"))
    description_ru = SummernoteTextField(verbose_name=_("Description (RU)"))

    price_min = models.FloatField(null=True, blank=True, verbose_name=_("Minimum Price"))
    price_max = models.FloatField(null=True, blank=True, verbose_name=_("Maximum Price"))
    discount_text = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Discount Text"))
    work_experience_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Work Experience (Years)"),
    )

    is_catalog = models.BooleanField(default=False, verbose_name=_("Show in Catalog"))
    show_location = models.BooleanField(default=True, verbose_name=_("Show Location Block"))
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Address"))
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("Latitude"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("Longitude"))
    background = WebPImageField(upload_to="services/backgrounds", verbose_name=_("Background"), null=True)
    is_grid_gallery = models.BooleanField(default=False, verbose_name=_("Display images as grid"))

    is_active = models.BooleanField(default=False, verbose_name=_("Is Active"))
    is_verified = models.BooleanField(default=False, verbose_name=_("Is Verified"))
    is_vip = models.BooleanField(default=False, verbose_name=_("Is VIP"))
    active_until = models.DateTimeField(null=True, blank=True, verbose_name=_("Active Until"))

    tags = models.ManyToManyField("ServiceTag", blank=True, related_name="services", verbose_name=_("Tags"))

    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ('priority', '-created_at')
        indexes = [
            models.Index(fields=["is_active", "priority", "created_at"], name="service_active_order_idx"),
            models.Index(fields=["category", "is_active"], name="service_category_active_idx"),
            models.Index(fields=["city", "is_active"], name="service_city_active_idx"),
        ]

    objects = ServiceQuerySet.as_manager()

    def __str__(self):
        return self.title_tm


class ContactType(models.Model):
    slug = models.SlugField(max_length=50, unique=True, verbose_name=_("Slug"))
    name_tm = models.CharField(max_length=100, verbose_name=_("Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Name (RU)"))
    icon = models.FileField(
        upload_to='contact_type_icons/',
        verbose_name=_("Icon"),
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["svg", "png", "jpg", "jpeg", "webp"])],
        help_text=_("Upload an icon image (SVG/PNG/JPG/WebP recommended)")
    )

    class Meta:
        verbose_name = _("Contact Type")
        verbose_name_plural = _("Contact Types")
        ordering = ['slug']

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_tm)
        super().save(*args, **kwargs)


class ServiceContact(models.Model):
    service = models.ForeignKey(Service, related_name='contacts', on_delete=models.CASCADE, verbose_name=_("Service"))
    type = models.ForeignKey(
        ContactType,
        on_delete=models.CASCADE,
        verbose_name=_("Contact Type"),
        null=True,
        blank=True
    )
    value = models.CharField(max_length=255, verbose_name=_("Contact Value"))

    class Meta:
        verbose_name = _("Service Contact")
        verbose_name_plural = _("Service Contacts")

    def __str__(self):
        return f"{self.type.slug}: {self.value}"


class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    image = WebPImageField(upload_to="services/images", verbose_name=_("Image"), null=True)
    position = models.PositiveIntegerField(default=100, verbose_name=_("Position"))
    aspect_ratio = models.FloatField(null=True, blank=True, verbose_name=_("Aspect Ratio"))

    class Meta:
        verbose_name = _("Service Image")
        verbose_name_plural = _("Service Images")
        ordering = ("position", "id")

    def __str__(self):
        return self.service.title_tm

    def _calculate_aspect_ratio(self) -> float | None:
        if not self.image:
            return None
        try:
            from PIL import Image
        except Exception:
            return None
        try:
            self.image.open()
            with Image.open(self.image) as img:
                width, height = img.size
        except Exception:
            return None
        if not height:
            return None
        return round(width / height, 3)

    def get_or_set_aspect_ratio(self) -> float | None:
        if self.aspect_ratio:
            return round(self.aspect_ratio, 3)
        ratio = self._calculate_aspect_ratio()
        if ratio is None:
            return None
        self.aspect_ratio = ratio
        if self.pk:
            ServiceImage.objects.filter(pk=self.pk).update(aspect_ratio=ratio)
        return ratio

    def save(self, *args, **kwargs):
        if self.image and not self.aspect_ratio:
            ratio = self._calculate_aspect_ratio()
            if ratio is not None:
                self.aspect_ratio = ratio
        super().save(*args, **kwargs)


class ServiceVideo(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    position = models.PositiveIntegerField(default=100, verbose_name=_("Position"))
    file = models.FileField(
        upload_to="services/videos/",
        verbose_name=_("Video file"),
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "mov", "webm", "mkv"]), validate_file_size],
        null=True,
    )
    preview = WebPImageField(
        upload_to="services/videos/previews",
        verbose_name=_("Preview image"),
        null=True,
        blank=True,
    )
    hls_playlist = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("HLS playlist path"),
    )
    hls_ready = models.BooleanField(default=False, verbose_name=_("HLS ready"))
    hls_error = models.TextField(blank=True, default="", verbose_name=_("HLS error"))
    hls_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("HLS updated at"))


    class Meta:
        verbose_name = _("Service Video")
        verbose_name_plural = _("Service Videos")
        ordering = ("position", "id")

    def __str__(self):
        if self.file:
            return self.file.name
        return ""

    def get_hls_url(self):
        if not self.hls_ready or not self.hls_playlist:
            return None
        try:
            return default_storage.url(self.hls_playlist)
        except Exception:
            return None


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"), related_name="reviews")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"), related_name="reviews")
    rating = models.PositiveSmallIntegerField(verbose_name=_("Rating"))
    comment = models.TextField(verbose_name=_("Comment"))
    is_approved = models.BooleanField(default=True, verbose_name=_("Approved"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.user} – {self.rating}★"


class ReviewReport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RESOLVED = "resolved", _("Resolved")

    class Source(models.TextChoices):
        APP = "app", _("App")

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("Review"),
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="review_reports",
        verbose_name=_("Reporter"),
    )
    reason = models.TextField(blank=True, default="", verbose_name=_("Reason"))
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.APP,
        verbose_name=_("Source"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Review Report")
        verbose_name_plural = _("Review Reports")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("review", "reporter"),
                name="unique_review_reporter_pair",
            )
        ]

    def __str__(self):
        return f"review={self.review_id}, reporter={self.reporter_id}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name=_("Service"),
        related_name="favorites",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        'ServiceProduct',
        on_delete=models.CASCADE,
        verbose_name=_("Product"),
        related_name="favorites",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Favorite")
        verbose_name_plural = _("Favorites")
        constraints = [
            models.CheckConstraint(
                name="favorite_exactly_one_target",
                check=(
                    (models.Q(service__isnull=False) & models.Q(product__isnull=True))
                    | (models.Q(service__isnull=True) & models.Q(product__isnull=False))
                ),
            ),
            models.UniqueConstraint(
                fields=["user", "service"],
                name="unique_user_service_favorite",
                condition=models.Q(service__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_favorite",
                condition=models.Q(product__isnull=False),
            ),
        ]

    def __str__(self):
        target = self.service or self.product
        return f"{self.user} ♥ {target}"


class ServiceTag(models.Model):
    name_tm = models.CharField(max_length=100, verbose_name=_("Tag Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Tag Name (RU)"))

    class Meta:
        verbose_name = _("Service Tag")
        verbose_name_plural = _("Service Tags")

    def __str__(self):
        return self.name_tm


class Attribute(models.Model):
    name_tm = models.CharField(max_length=100, verbose_name=_("Attribute Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Attribute Name (RU)"))
    icon = models.FileField(
        upload_to="service_attributes/icons/",
        verbose_name=_("Icon"),
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["svg", "png", "jpg", "jpeg", "webp"])],
        help_text=_("Upload an icon image (SVG/PNG/JPG/WebP recommended)"),
    )

    slug = models.SlugField(db_index=True, verbose_name=_("Attribute Slug"))
    input_type = models.CharField(
        max_length=20,
        choices=[
            ('text', _('Text')),
            ('number', _('Number')),
            ('boolean', _('Boolean')),
            ('choice', _('Choice')),
            ('multiselect', _('Multi Select')),
        ],
        db_index=True,
        verbose_name=_("Input Type")
    )
    unit_tm = models.CharField(max_length=32, blank=True, default="", verbose_name=_("Unit (TM)"))
    unit_ru = models.CharField(max_length=32, blank=True, default="", verbose_name=_("Unit (RU)"))
    placeholder_tm = models.CharField(max_length=150, blank=True, default="", verbose_name=_("Placeholder (TM)"))
    placeholder_ru = models.CharField(max_length=150, blank=True, default="", verbose_name=_("Placeholder (RU)"))
    help_text_tm = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Help Text (TM)"))
    help_text_ru = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Help Text (RU)"))
    min_value = models.FloatField(null=True, blank=True, verbose_name=_("Min Value"))
    max_value = models.FloatField(null=True, blank=True, verbose_name=_("Max Value"))
    step = models.FloatField(null=True, blank=True, verbose_name=_("Step"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_required = models.BooleanField(default=False, verbose_name=_("Is Required"))

    class Meta:
        verbose_name = _("Attribute")
        verbose_name_plural = _("Attributes")
        ordering = ("name_tm", "id")

    def __str__(self):
        return self.name_tm

    @property
    def supports_options(self):
        return self.input_type in {"choice", "multiselect"}


class AttributeOption(models.Model):
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("Attribute"),
    )
    value = models.SlugField(max_length=100, verbose_name=_("Value"))
    label_tm = models.CharField(max_length=100, verbose_name=_("Label (TM)"))
    label_ru = models.CharField(max_length=100, verbose_name=_("Label (RU)"))
    sort_order = models.PositiveIntegerField(default=100, verbose_name=_("Sort Order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        verbose_name = _("Attribute Option")
        verbose_name_plural = _("Attribute Options")
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(fields=("attribute", "value"), name="uniq_attribute_option_value"),
        ]

    def __str__(self):
        return f"{self.attribute.name_tm} → {self.label_tm}"


class CategoryAttribute(models.Model):
    class Scope(models.TextChoices):
        SERVICE = "service", _("Service")
        PRODUCT = "product", _("Product")

    class FilterType(models.TextChoices):
        AUTO = "auto", _("Auto")
        CHECKBOX = "checkbox", _("Checkbox")
        SELECT = "select", _("Select")
        MULTISELECT = "multiselect", _("Multi Select")
        RANGE = "range", _("Range")

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="category_attributes",
        verbose_name=_("Category"),
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name="category_links",
        verbose_name=_("Attribute"),
    )
    scope = models.CharField(max_length=16, choices=Scope.choices, verbose_name=_("Scope"))
    is_required = models.BooleanField(default=False, verbose_name=_("Is Required"))
    is_filterable = models.BooleanField(default=False, verbose_name=_("Is Filterable"))
    is_highlighted = models.BooleanField(default=False, verbose_name=_("Is Highlighted"))
    section_tm = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Section (TM)"))
    section_ru = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Section (RU)"))
    show_in_filters = models.BooleanField(default=False, verbose_name=_("Show in Filters"))
    show_in_card = models.BooleanField(default=False, verbose_name=_("Show in Card"))
    show_in_detail = models.BooleanField(default=True, verbose_name=_("Show in Detail"))
    filter_type = models.CharField(
        max_length=20,
        choices=FilterType.choices,
        default=FilterType.AUTO,
        verbose_name=_("Filter Type"),
    )
    filter_order = models.PositiveIntegerField(default=100, verbose_name=_("Filter Order"))
    sort_order = models.PositiveIntegerField(default=100, verbose_name=_("Sort Order"))

    class Meta:
        verbose_name = _("Category Attribute")
        verbose_name_plural = _("Category Attributes")
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("category", "attribute", "scope"),
                name="uniq_category_attribute_scope",
            ),
        ]

    def __str__(self):
        return f"{self.category.name_tm} → {self.attribute.name_tm} ({self.scope})"


class BaseAttributeValue(models.Model):
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        verbose_name=_("Attribute"),
    )
    option = models.ForeignKey(
        AttributeOption,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Option"),
    )
    value_text_tm = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Text Value (TM)"))
    value_text_ru = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Text Value (RU)"))
    value_number = models.FloatField(null=True, blank=True, verbose_name=_("Number Value"))
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name=_("Boolean Value"))

    class Meta:
        abstract = True

    @property
    def value(self):
        input_type = self.attribute.input_type

        if input_type in {"choice", "multiselect"} and self.option_id:
            lang = translation.get_language()
            if lang == "ru":
                return self.option.label_ru
            return self.option.label_tm

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                return self.value_text_ru
            return self.value_text_tm

        if input_type == 'number':
            return self.value_number
        if input_type == 'boolean':
            return self.value_boolean
        return None

    @value.setter
    def value(self, val):
        self.option = None
        self.value_text_tm = None
        self.value_text_ru = None
        self.value_number = None
        self.value_boolean = None

        input_type = self.attribute.input_type

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                self.value_text_ru = str(val)
            else:
                self.value_text_tm = str(val)

        elif input_type == 'number':
            self.value_number = float(val)
        elif input_type == 'boolean':
            self.value_boolean = bool(val)


class ServiceAttributeValue(BaseAttributeValue):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="service_attribute_values",
        verbose_name=_("Service"),
    )

    class Meta:
        verbose_name = _("Service Attribute Value")
        verbose_name_plural = _("Service Attribute Values")
        constraints = [
            models.UniqueConstraint(
                fields=("service", "attribute"),
                condition=Q(option__isnull=True),
                name="uniq_service_attr_without_option",
            ),
            models.UniqueConstraint(
                fields=("service", "attribute", "option"),
                condition=Q(option__isnull=False),
                name="uniq_service_attr_with_option",
            ),
        ]

    def __str__(self):
        return f"{self.service.title_tm} – {self.attribute.name_tm}"


class ProductAttributeValue(BaseAttributeValue):
    product = models.ForeignKey(
        'ServiceProduct',
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name=_("Product"),
    )

    class Meta:
        verbose_name = _("Product Attribute Value")
        verbose_name_plural = _("Product Attribute Values")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "attribute"),
                condition=Q(option__isnull=True),
                name="uniq_product_attr_without_option",
            ),
            models.UniqueConstraint(
                fields=("product", "attribute", "option"),
                condition=Q(option__isnull=False),
                name="uniq_product_attr_with_option",
            ),
        ]

    def __str__(self):
        return f"{self.product.title_tm} – {self.attribute.name_tm}"


class ServiceProduct(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='products', verbose_name=_("Service"))

    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))

    description_tm = models.TextField(null=True, blank=True, verbose_name=_("Description (TM)"))
    description_ru = models.TextField(null=True, blank=True, verbose_name=_("Description (RU)"))

    price = models.FloatField(null=True, blank=True, verbose_name=_("Price"))
    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service Product")
        verbose_name_plural = _("Service Products")
        ordering = ['priority', '-created_at']

    def __str__(self):
        return self.title_tm


class ServiceProductImage(models.Model):
    product = models.ForeignKey(
        ServiceProduct,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Product")
    )
    image = WebPImageField(upload_to="services/product_images", verbose_name=_("Image"))
    position = models.PositiveIntegerField(default=100, verbose_name=_("Position"))

    class Meta:
        verbose_name = _("Service Product Image")
        verbose_name_plural = _("Service Product Images")
        ordering = ("position", "id")

    def __str__(self):
        return self.image.url if self.image else str(self.pk)


class ServiceApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category")
    )
    category_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Category Name"))
    city = models.ForeignKey(City, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_("City"))
    city_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("City Name"))

    phone = models.CharField(max_length=32, verbose_name=_("Phone Number"))
    email = models.EmailField(max_length=254, null=True, blank=True, verbose_name=_("Email"))
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Service Title"))
    contact_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Contact Name"))
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Address"))
    price_from = models.FloatField(null=True, blank=True, verbose_name=_("Price From"))
    work_experience_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Work Experience (Years)"),
    )
    description = models.TextField(verbose_name=_("Service Description"))

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name=_("Status"))
    admin_note = models.TextField(null=True, blank=True, verbose_name=_("Admin Note"))
    processed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="processed_applications",
        verbose_name=_("Processed By")
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Processed At"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Service Application")
        verbose_name_plural = _("Service Applications")
        ordering = ("-created_at",)

    def __str__(self):
        parts = [self.title or "Service Application", self.phone]
        return " – ".join([p for p in parts if p])


class ServiceApplicationLink(models.Model):
    application = models.ForeignKey(
        ServiceApplication,
        on_delete=models.CASCADE,
        related_name="links",
        verbose_name=_("Application"),
    )
    url = models.URLField(max_length=500, verbose_name=_("URL"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Service Application Link")
        verbose_name_plural = _("Service Application Links")
        ordering = ("created_at",)

    def __str__(self):
        return self.url


class ServiceApplicationImage(models.Model):
    application = models.ForeignKey(
        ServiceApplication,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_("Application"),
    )
    image = WebPImageField(upload_to="service_applications/images", verbose_name=_("Image"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Service Application Image")
        verbose_name_plural = _("Service Application Images")
        ordering = ('created_at',)

    def __str__(self):
        return self.image.url if self.image else str(self.pk)
