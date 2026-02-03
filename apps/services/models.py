from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from apps.categories.models import Category
from apps.regions.models import Region, City
from apps.services.validators import validate_file_size
from apps.users.models import User
from core.fields import WebPImageField

from django_summernote.fields import SummernoteTextField

from slugify import slugify


class Service(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Vendor"))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_("Category"))
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("City"))
    avatar = WebPImageField(
        upload_to="services/avatars", verbose_name=_("Avatar"), null=True, default=None, blank=True
    )
    regions = models.ManyToManyField(Region, related_name='services', verbose_name=_("Regions"))
    available_cities = models.ManyToManyField(City, related_name='services', verbose_name=_("Available Cities"))

    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))
    title_en = models.CharField(max_length=255, verbose_name=_("Title (EN)"))

    description_tm = SummernoteTextField(verbose_name=_("Description (TM)"))
    description_ru = SummernoteTextField(verbose_name=_("Description (RU)"))
    description_en = SummernoteTextField(verbose_name=_("Description (EN)"))

    price_min = models.FloatField(null=True, blank=True, verbose_name=_("Minimum Price"))
    price_max = models.FloatField(null=True, blank=True, verbose_name=_("Maximum Price"))
    discount_text = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Discount Text"))

    is_catalog = models.BooleanField(default=False, verbose_name=_("Show in Catalog"))
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

    def __str__(self):
        return self.title_tm


class ContactType(models.Model):
    slug = models.SlugField(max_length=50, unique=True, verbose_name=_("Slug"))
    name_tm = models.CharField(max_length=100, verbose_name=_("Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Name (RU)"))
    name_en = models.CharField(max_length=100, verbose_name=_("Name (EN)"))
    icon = WebPImageField(
        upload_to='contact_type_icons/',
        verbose_name=_("Icon"),
        null=True,
        blank=True,
        help_text=_("Upload an icon image (SVG/PNG recommended)")
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
    aspect_ratio = models.FloatField(null=True, blank=True, verbose_name=_("Aspect Ratio"))

    class Meta:
        verbose_name = _("Service Image")
        verbose_name_plural = _("Service Images")

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
    file = models.FileField(
        upload_to="services/videos/",
        verbose_name=_("Video file"),
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "mov", "webm", "mkv"]), validate_file_size],
        null=True,
    )

    class Meta:
        verbose_name = _("Service Video")
        verbose_name_plural = _("Service Videos")

    def __str__(self):
        return self.file


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
    name_en = models.CharField(max_length=100, verbose_name=_("Tag Name (EN)"))

    class Meta:
        verbose_name = _("Service Tag")
        verbose_name_plural = _("Service Tags")

    def __str__(self):
        return self.name_tm


class Attribute(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="attribute_definitions", verbose_name=_("Category")
    )
    name_tm = models.CharField(max_length=100, verbose_name=_("Attribute Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Attribute Name (RU)"))
    name_en = models.CharField(max_length=100, verbose_name=_("Attribute Name (EN)"))

    slug = models.SlugField(db_index=True, verbose_name=_("Attribute Slug"))
    input_type = models.CharField(
        max_length=20,
        choices=[
            ('text', _('Text')),
            ('number', _('Number')),
            ('boolean', _('Boolean')),
            ('choice', _('Choice')),
        ],
        db_index=True,
        verbose_name=_("Input Type")
    )
    is_required = models.BooleanField(default=False, verbose_name=_("Is Required"))

    class Meta:
        verbose_name = _("Attribute")
        verbose_name_plural = _("Attributes")
        unique_together = ('category', 'slug')

    def __str__(self):
        return f"{self.category.name_tm} → {self.name_tm}"


class AttributeValue(models.Model):
    product = models.ForeignKey(
        'ServiceProduct',
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name=_("Product"),
    )
    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, verbose_name=_("Attribute")
    )

    value_text_tm = models.CharField(max_length=100, verbose_name=_("Text Value (TM)"))
    value_text_ru = models.CharField(max_length=100, verbose_name=_("Text Value (RU)"))
    value_text_en = models.CharField(max_length=100, verbose_name=_("Text Value (EN)"))

    value_number = models.FloatField(null=True, blank=True, verbose_name=_("Number Value"))
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name=_("Boolean Value"))

    class Meta:
        verbose_name = _("Attribute Value")
        verbose_name_plural = _("Attribute Values")
        unique_together = ('product', 'attribute')

    def __str__(self):
        return f"{self.product.title_tm} – {self.attribute.name_tm}"

    @property
    def value(self):
        input_type = self.attribute.input_type

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                return self.value_text_ru
            elif lang == "en":
                return self.value_text_en
            return self.value_text_tm

        elif input_type == 'number':
            return self.value_number
        elif input_type == 'boolean':
            return self.value_boolean
        return None

    @value.setter
    def value(self, val):
        self.value_text_tm = None
        self.value_text_ru = None
        self.value_text_en = None
        self.value_number = None
        self.value_boolean = None

        input_type = self.attribute.input_type

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                self.value_text_ru = str(val)
            elif lang == "en":
                self.value_text_en = str(val)
            else:
                self.value_text_tm = str(val)

        elif input_type == 'number':
            self.value_number = float(val)
        elif input_type == 'boolean':
            self.value_boolean = bool(val)


class ServiceProduct(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='products', verbose_name=_("Service"))

    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))
    title_en = models.CharField(max_length=255, verbose_name=_("Title (EN)"))

    description_tm = models.TextField(null=True, blank=True, verbose_name=_("Description (TM)"))
    description_ru = models.TextField(null=True, blank=True, verbose_name=_("Description (RU)"))
    description_en = models.TextField(null=True, blank=True, verbose_name=_("Description (EN)"))

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

    class Meta:
        verbose_name = _("Service Product Image")
        verbose_name_plural = _("Service Product Images")

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
    city = models.ForeignKey(City, on_delete=models.PROTECT, verbose_name=_("City"))

    phone = models.CharField(max_length=32, verbose_name=_("Phone Number"))
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Service Title"))
    contact_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Contact Name"))
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
