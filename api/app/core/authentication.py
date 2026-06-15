import json
import uuid

import httpx
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import transaction
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.text import slugify
from rest_framework import authentication, exceptions

from .models import CloudflareAccessIdentity
from .permissions import Groups


class CloudflareAccessCsrfCheck(CsrfViewMiddleware):
    def _reject(self, _request, reason):
        return reason


class CloudflareAccessTokenVerifier:
    def __init__(self, *, team_domain: str, audience: str, jwks_cache_ttl_s: int) -> None:
        self.team_domain = team_domain.rstrip("/")
        self.audience = audience
        self.jwks_cache_ttl_s = jwks_cache_ttl_s
        self.certs_url = f"{self.team_domain}/cdn-cgi/access/certs"
        cache_key_suffix = slugify(self.team_domain) or "default"
        self.cache_key = f"cloudflare-access:jwks:{cache_key_suffix}"

    def verify(self, token: str) -> dict:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed("Invalid Cloudflare Access token header.") from exc

        signing_key = self._get_signing_key(header.get("kid"))

        try:
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                options={"verify_iss": False},
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Cloudflare Access token has expired.") from exc
        except jwt.InvalidAudienceError as exc:
            raise exceptions.AuthenticationFailed(
                "Cloudflare Access token audience did not match the configured audience."
            ) from exc
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed("Invalid Cloudflare Access token.") from exc

        token_issuer = str(claims.get("iss") or "").strip().rstrip("/")
        expected_issuer = self.team_domain.rstrip("/")
        if token_issuer != expected_issuer:
            raise exceptions.AuthenticationFailed(
                "Cloudflare Access token issuer did not match the configured team domain."
            )

        return claims

    def _get_signing_key(self, kid: str | None):
        if not kid:
            raise exceptions.AuthenticationFailed("Cloudflare Access token is missing a key id.")

        key_dicts = self._get_cached_signing_key_dicts()
        if kid not in key_dicts:
            key_dicts = self._fetch_signing_key_dicts(force_refresh=True)

        key_dict = key_dicts.get(kid)
        if key_dict is None:
            raise exceptions.AuthenticationFailed("Unknown Cloudflare Access signing key.")
        return self._build_signing_key(key_dict)

    def _build_signing_key(self, key_dict: dict) -> object:
        try:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_dict))
        except (TypeError, ValueError, jwt.PyJWTError) as exc:
            raise exceptions.AuthenticationFailed(
                "Cloudflare Access signing keys returned an invalid key."
            ) from exc

    def _get_cached_signing_key_dicts(self) -> dict[str, dict]:
        cached_keys = cache.get(self.cache_key)
        if isinstance(cached_keys, dict) and all(
            isinstance(key_dict, dict) for key_dict in cached_keys.values()
        ):
            return cached_keys
        return self._fetch_signing_key_dicts(force_refresh=cached_keys is not None)

    def _fetch_signing_key_dicts(self, *, force_refresh: bool = False) -> dict[str, dict]:
        if force_refresh:
            cache.delete(self.cache_key)

        try:
            response = httpx.get(self.certs_url, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise exceptions.AuthenticationFailed(
                "Unable to fetch Cloudflare Access signing keys."
            ) from exc

        try:
            jwk_set = response.json()
        except ValueError as exc:
            raise exceptions.AuthenticationFailed(
                "Cloudflare Access signing keys returned an invalid response."
            ) from exc

        signing_key_dicts = {}
        for key_dict in jwk_set.get("keys", []):
            kid = key_dict.get("kid")
            if not kid:
                continue
            signing_key_dicts[kid] = key_dict

        if not signing_key_dicts:
            raise exceptions.AuthenticationFailed(
                "Cloudflare Access did not provide any signing keys."
            )

        cache.set(self.cache_key, signing_key_dicts, timeout=self.jwks_cache_ttl_s)
        return signing_key_dicts


def get_cloudflare_access_token_verifier() -> CloudflareAccessTokenVerifier:
    team_domain = getattr(settings, "CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip()
    audience = getattr(settings, "CLOUDFLARE_ACCESS_AUDIENCE", "").strip()

    if not team_domain or not audience:
        raise exceptions.AuthenticationFailed(
            "Cloudflare Access is not configured on the API."
        )

    return CloudflareAccessTokenVerifier(
        team_domain=team_domain,
        audience=audience,
        jwks_cache_ttl_s=getattr(settings, "CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_S", 300),
    )


def _split_full_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return "", ""

    first, _, last = full_name.partition(" ")
    return first.strip(), last.strip()


def _split_cloudflare_name(claims: dict) -> tuple[str, str]:
    first_name = str(claims.get("given_name") or "").strip()
    last_name = str(claims.get("family_name") or "").strip()

    if first_name or last_name:
        return first_name, last_name

    return _split_full_name(str(claims.get("name") or "").strip())


def _fetch_cloudflare_identity_name(team_domain: str, token: str) -> tuple[str, str]:
    """Fall back to Cloudflare's get-identity endpoint for the user's full name.

    The Cf-Access-Jwt-Assertion JWT only carries a minimal claim set (sub,
    email, ...) - it does not include given_name/family_name/name unless the
    IdP is configured to add them as custom claims. get-identity returns the
    full identity payload (including "name") for the same token.
    """
    try:
        response = httpx.get(
            f"{team_domain}/cdn-cgi/access/get-identity",
            headers={"Accept": "application/json"},
            cookies={"CF_Authorization": token},
            timeout=5.0,
        )
        response.raise_for_status()
        identity = response.json()
    except (httpx.HTTPError, ValueError):
        return "", ""

    if not isinstance(identity, dict):
        return "", ""

    return _split_full_name(str(identity.get("name") or "").strip())


def _resolve_cloudflare_identity_name(team_domain: str, token: str, cache_key_subject: str) -> tuple[str, str]:
    cache_key = f"cloudflare-access:identity-name:{slugify(cache_key_subject) or 'unknown'}"
    cached = cache.get(cache_key)
    if isinstance(cached, list) and len(cached) == 2:
        return cached[0], cached[1]

    first_name, last_name = _fetch_cloudflare_identity_name(team_domain, token)
    cache.set(cache_key, [first_name, last_name], timeout=3600)
    return first_name, last_name


def _generate_unique_username(*, subject: str, email: str) -> str:
    user_model = get_user_model()

    if subject:
        normalized_subject = slugify(subject).replace("-", "")
        if normalized_subject:
            username = f"cf-{normalized_subject}"[:150]
            if not user_model.objects.filter(username=username).exists():
                return username

    base_username = slugify(email.partition("@")[0]) or "cf-user"
    username = base_username[:150]
    suffix = 2

    while user_model.objects.filter(username=username).exists():
        suffix_text = f"-{suffix}"
        username = f"{base_username[:150 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    if username:
        return username

    return f"cf-user-{uuid.uuid4().hex[:16]}"


def _sync_user_from_claims(user, *, email: str, first_name: str, last_name: str) -> None:
    changed_fields = []

    if email and user.email != email:
        user.email = email
        changed_fields.append("email")
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        changed_fields.append("first_name")
    if last_name and user.last_name != last_name:
        user.last_name = last_name
        changed_fields.append("last_name")

    if changed_fields:
        user.save(update_fields=changed_fields)


def resolve_cloudflare_user(claims: dict, *, token: str = ""):
    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()

    if not subject and not email:
        raise exceptions.AuthenticationFailed(
            "Cloudflare Access identity must include a subject or email claim."
        )

    first_name, last_name = _split_cloudflare_name(claims)
    if not first_name and not last_name and token:
        team_domain = getattr(settings, "CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip().rstrip("/")
        if team_domain:
            first_name, last_name = _resolve_cloudflare_identity_name(team_domain, token, subject or email)

    user_model = get_user_model()

    with transaction.atomic():
        identity = None
        if subject:
            identity = (
                CloudflareAccessIdentity.objects.select_related("user")
                .filter(subject=subject)
                .first()
            )

        if identity is not None:
            user = identity.user
        else:
            user = None
            if email:
                user = user_model.objects.filter(email__iexact=email).order_by("id").first()

            if user is None:
                user = user_model.objects.create_user(
                    username=_generate_unique_username(subject=subject, email=email),
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=None,
                )
                user.set_unusable_password()
                user.save(update_fields=["password"])

            if subject:
                identity, created = CloudflareAccessIdentity.objects.get_or_create(
                    subject=subject,
                    defaults={
                        "user": user,
                        "email": email,
                    },
                )
                if not created:
                    user = identity.user

        _sync_user_from_claims(user, email=email, first_name=first_name, last_name=last_name)

        if identity is not None and email and identity.email != email:
            identity.email = email
            identity.save(update_fields=["email"])

    return user


class CloudflareAccessAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get("Cf-Access-Jwt-Assertion")
        if not token:
            return None

        claims = get_cloudflare_access_token_verifier().verify(token)
        user = resolve_cloudflare_user(claims, token=token)
        self.enforce_csrf(request)
        return (user, claims)

    def enforce_csrf(self, request) -> None:
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return

        check = CloudflareAccessCsrfCheck(lambda _request: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class DevAutoLoginAuthentication(authentication.BaseAuthentication):
    """Authenticates every request as a fixed local user.

    Only wired up via ``REST_FRAMEWORK`` when ``settings.DEV_AUTO_LOGIN_EMAIL``
    is set, which settings.py restricts to ``DEBUG=True``. Lets the API be
    used locally without a Cloudflare Access session in front of it.
    """

    def authenticate(self, request):
        email = settings.DEV_AUTO_LOGIN_EMAIL
        if not email:
            return None

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={"username": email.partition("@")[0]},
        )
        if created:
            user.is_staff = True
            user.is_superuser = True
            user.set_unusable_password()
            user.save()
            editor_group, _ = Group.objects.get_or_create(name=Groups.EDITOR)
            user.groups.add(editor_group)

        return (user, None)
