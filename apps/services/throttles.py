from rest_framework.throttling import SimpleRateThrottle


class ServiceApplicationIPThrottle(SimpleRateThrottle):
    scope = "service_application_ip"
    rate = "3/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None

        ident = self.get_ident(request)
        if not ident:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def get_rate(self):
        return self.rate
