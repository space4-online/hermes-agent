"""
Aliyun OSS client wrapper.

Resolves credentials from the Hermes vault by profile name, exposes a
small API that the CLI dispatches to. Keeps oss2 import lazy so `info`
and `--help` work even when the SDK is not installed.
"""

from __future__ import annotations

import mimetypes
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from _vault_reader import get as vault_get


class OssConfigError(RuntimeError):
    pass


@dataclass
class OssProfile:
    name: str
    endpoint: str
    bucket: str
    access_key_id: str
    access_key_secret: str
    prefix: str = ""
    public_default: bool = False

    def public_summary(self) -> dict:
        """Profile metadata safe for prompt / log output (no secrets)."""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "public_default": self.public_default,
        }


def load_profile(name: str) -> OssProfile:
    """Pull all 5 vault keys for the given profile name. Case-insensitive."""
    profile = name.upper()
    needed = {
        "endpoint":      f"OSS_{profile}_ENDPOINT",
        "bucket":        f"OSS_{profile}_BUCKET",
        "ak":            f"OSS_{profile}_AK",
        "sk":            f"OSS_{profile}_SK",
    }
    optional = {
        "prefix":        f"OSS_{profile}_PREFIX",
        "public":        f"OSS_{profile}_PUBLIC",
    }
    resolved: dict[str, Optional[str]] = {k: vault_get(v) for k, v in needed.items()}
    missing = [needed[k] for k, v in resolved.items() if not v]
    if missing:
        raise OssConfigError(
            f"vault entries not found: {', '.join(missing)}. "
            f"Run 'hermes vault add <NAME>' for each, or set them as env vars."
        )

    prefix = vault_get(optional["prefix"]) or ""
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    public_raw = (vault_get(optional["public"]) or "").strip().lower()
    public_default = public_raw in ("1", "true", "yes", "on")

    assert resolved["endpoint"] and resolved["bucket"]
    assert resolved["ak"] and resolved["sk"]
    return OssProfile(
        name=name.lower(),
        endpoint=resolved["endpoint"],
        bucket=resolved["bucket"],
        access_key_id=resolved["ak"],
        access_key_secret=resolved["sk"],
        prefix=prefix,
        public_default=public_default,
    )


def _import_oss2():
    try:
        import oss2  # type: ignore[import-not-found]
        return oss2
    except ImportError as e:
        # The CLI runs `_bootstrap.ensure_dependencies()` at startup, so
        # reaching here means bootstrap was disabled (HERMES_OSS_NO_BOOTSTRAP=1)
        # or could not write to the cache dir.
        raise OssConfigError(
            "oss2 not installed and bootstrap could not load it. "
            "Unset HERMES_OSS_NO_BOOTSTRAP, or run "
            "'pip install oss2' inside the hermes runtime. (" + str(e) + ")"
        )


def _bucket(profile: OssProfile):
    oss2 = _import_oss2()
    auth = oss2.Auth(profile.access_key_id, profile.access_key_secret)
    endpoint = profile.endpoint
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "https://" + endpoint
    return oss2.Bucket(auth, endpoint, profile.bucket)


def _normalize_endpoint_host(endpoint: str) -> str:
    """Strip scheme; the public URL form is always https://<bucket>.<host>/<key>."""
    return endpoint.replace("https://", "").replace("http://", "").rstrip("/")


def public_url(profile: OssProfile, key: str) -> str:
    host = _normalize_endpoint_host(profile.endpoint)
    return f"https://{profile.bucket}.{host}/{key}"


def default_key(profile: OssProfile, local_path: Path) -> str:
    """Auto-generate object key when the caller didn't supply one."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short = uuid.uuid4().hex[:8]
    return f"{profile.prefix}{today}/{short}-{local_path.name}"


def upload_file(
    profile: OssProfile,
    local_path: Path,
    key: Optional[str] = None,
    public: Optional[bool] = None,
    expires_seconds: int = 86400,
) -> dict:
    if not local_path.exists():
        raise FileNotFoundError(f"local file not found: {local_path}")
    if not local_path.is_file():
        raise ValueError(f"not a regular file: {local_path}")

    object_key = key or default_key(profile, local_path)
    use_public = profile.public_default if public is None else public

    bucket = _bucket(profile)
    headers = {}
    mime, _ = mimetypes.guess_type(local_path.name)
    if mime:
        headers["Content-Type"] = mime
    res = bucket.put_object_from_file(object_key, str(local_path), headers=headers)

    if use_public:
        url = public_url(profile, object_key)
        expires_in = 0
    else:
        url = bucket.sign_url("GET", object_key, expires_seconds, slash_safe=True)
        expires_in = expires_seconds

    return {
        "ok": True,
        "url": url,
        "key": object_key,
        "size": local_path.stat().st_size,
        "etag": (res.etag or "").strip('"'),
        "content_type": mime or "application/octet-stream",
        "public": use_public,
        "expires_in": expires_in,
        "profile": profile.name,
        "bucket": profile.bucket,
    }


def share(profile: OssProfile, key: str, expires_seconds: int = 86400) -> dict:
    bucket = _bucket(profile)
    if not bucket.object_exists(key):
        raise FileNotFoundError(f"object not found: {key}")
    url = bucket.sign_url("GET", key, expires_seconds, slash_safe=True)
    return {
        "ok": True,
        "url": url,
        "key": key,
        "expires_in": expires_seconds,
        "public": False,
        "profile": profile.name,
        "bucket": profile.bucket,
    }


def list_objects(
    profile: OssProfile,
    prefix: Optional[str] = None,
    limit: int = 100,
) -> dict:
    oss2 = _import_oss2()
    bucket = _bucket(profile)
    eff_prefix = prefix if prefix is not None else profile.prefix
    items = []
    for obj in oss2.ObjectIteratorV2(bucket, prefix=eff_prefix or ""):
        items.append({
            "key": obj.key,
            "size": obj.size,
            "last_modified": datetime.fromtimestamp(
                obj.last_modified, tz=timezone.utc
            ).isoformat(),
            "etag": (obj.etag or "").strip('"'),
        })
        if len(items) >= limit:
            break
    return {
        "ok": True,
        "objects": items,
        "count": len(items),
        "prefix": eff_prefix,
        "profile": profile.name,
        "bucket": profile.bucket,
    }


def delete(profile: OssProfile, key: str) -> dict:
    bucket = _bucket(profile)
    bucket.delete_object(key)
    return {
        "ok": True,
        "key": key,
        "profile": profile.name,
        "bucket": profile.bucket,
    }
