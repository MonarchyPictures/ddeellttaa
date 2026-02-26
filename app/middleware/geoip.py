import logging
import os
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

logger = logging.getLogger("delta9.geoip")

class KenyaLockingMiddleware:
    def __init__(self, app):
        self.app = app
        self.enabled = os.getenv("KENYA_LOCKING_ENABLED", "true").lower() == "true"
        self.strict_mode = os.getenv("KENYA_LOCKING_STRICT", "false").lower() == "true"
        self.allowed_countries = ["KE", "KENYA"]
        # Whitelist local dev
        self.whitelist_ips = ["127.0.0.1", "localhost", "::1"]

    async def __call__(self, scope, receive, send):
        # Skip WebSocket and other non-HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.enabled:
            await self.app(scope, receive, send)
            return

        # Extract client IP
        client_ip = scope.get("client", [""])[0]
        
        # 1. Allow Localhost
        if client_ip in self.whitelist_ips:
            await self.app(scope, receive, send)
            return

        # 2. Check Cloudflare/Proxy Headers (Fastest)
        headers = Headers(scope=scope)
        country = headers.get("CF-IPCountry") or \
                  headers.get("X-Country-Code") or \
                  headers.get("X-AppEngine-Country")

        if country:
            if country.upper() not in self.allowed_countries:
                msg = f"Access Denied: Request from {country} (IP: {client_ip}) blocked by Kenya Locking."
                logger.warning(msg)
                if self.strict_mode:
                    response = JSONResponse(status_code=403, content={"detail": msg})
                    await response(scope, receive, send)
                    return
            else:
                # Valid Kenya Request
                pass
        else:
            # 3. No Country Header? (e.g. Direct access or local dev simulating external)
            logger.debug(f"GeoIP: No country header found for IP {client_ip}. Allowing (Soft Fail).")

        await self.app(scope, receive, send)
