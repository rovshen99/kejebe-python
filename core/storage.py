from urllib.parse import urlparse, urlunparse

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class PublicMinioStorage(S3Boto3Storage):
    def get_object_parameters(self, name):
        params = super().get_object_parameters(name)
        if name and (name.startswith("category/thumbs/") or name.startswith("home/variants/")):
            params = {
                **params,
                "CacheControl": "public, max-age=31536000, immutable",
                "ContentType": "image/webp",
            }
        return params

    def url(self, name, parameters=None, expire=None):
        url = super().url(name, parameters=parameters, expire=expire)
        public_base = getattr(settings, "MINIO_PUBLIC_BASE_URL", "")
        if not public_base:
            return url
        parsed_public = urlparse(public_base)
        if not parsed_public.netloc:
            return url
        parsed_url = urlparse(url)
        scheme = parsed_public.scheme or parsed_url.scheme
        return urlunparse(
            (
                scheme,
                parsed_public.netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment,
            )
        )
