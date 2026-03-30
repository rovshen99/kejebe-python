from django.conf import settings
from django.http import HttpResponse


class CorsHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_preflight_request(request):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        return self._apply_cors_headers(request, response)

    @staticmethod
    def _is_api_request(request) -> bool:
        return request.path.startswith("/api/")

    def _is_preflight_request(self, request) -> bool:
        return (
            self._is_api_request(request)
            and request.method == "OPTIONS"
            and bool(request.headers.get("Origin"))
            and bool(request.headers.get("Access-Control-Request-Method"))
        )

    @staticmethod
    def _allowed_origins() -> set[str]:
        return {
            origin.strip().rstrip("/")
            for origin in getattr(settings, "CORS_ALLOWED_ORIGINS", [])
            if origin.strip()
        }

    def _is_allowed_origin(self, origin: str | None) -> bool:
        if not origin:
            return False
        return origin.rstrip("/") in self._allowed_origins()

    @staticmethod
    def _append_vary_header(response, value: str) -> None:
        existing = response.get("Vary")
        if not existing:
            response["Vary"] = value
            return
        vary_values = {item.strip() for item in existing.split(",") if item.strip()}
        if value not in vary_values:
            response["Vary"] = f"{existing}, {value}"

    def _apply_cors_headers(self, request, response):
        if not self._is_api_request(request):
            return response

        origin = request.headers.get("Origin")
        if not self._is_allowed_origin(origin):
            return response

        response["Access-Control-Allow-Origin"] = origin
        self._append_vary_header(response, "Origin")

        if getattr(settings, "CORS_ALLOW_CREDENTIALS", True):
            response["Access-Control-Allow-Credentials"] = "true"

        response["Access-Control-Allow-Methods"] = ", ".join(settings.CORS_ALLOW_METHODS)
        requested_headers = request.headers.get("Access-Control-Request-Headers")
        response["Access-Control-Allow-Headers"] = requested_headers or ", ".join(settings.CORS_ALLOW_HEADERS)
        response["Access-Control-Max-Age"] = str(getattr(settings, "CORS_PREFLIGHT_MAX_AGE", 86400))
        return response
