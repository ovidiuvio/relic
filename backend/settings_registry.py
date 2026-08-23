"""Registry of runtime-configurable settings.

This module is the single source of truth for which runtime settings exist,
their types, defaults, and validation bounds. The database stores only
overrides; anything absent there falls back to the default declared here.

Defaults deliberately preserve the behaviour Relic had before the runtime
policy layer existed, so upgrading an instance changes nothing until an
admin opts in. The "hardened" preset is what turns on real restrictions.
"""
from dataclasses import dataclass
from typing import Any, List, Optional

from backend.config import settings


# Setting value types. The frontend picks a widget from these.
TYPE_BOOL = "bool"
TYPE_INT = "int"
TYPE_STR = "str"
TYPE_LIST = "list"


@dataclass(frozen=True)
class SettingDef:
    """Declaration of a single runtime setting."""

    key: str
    section: str
    type: str
    default: Any
    label: str
    help: str
    min: Optional[int] = None
    max: Optional[int] = None
    choices: Optional[List[str]] = None
    # Hint for frontend formatting only ("bytes", "duration", "per_minute", ...).
    unit: Optional[str] = None


# Section display order and labels, used by the admin UI.
SECTIONS = [
    ("features", "Features & Availability"),
    ("uploads", "Uploads"),
    ("quotas", "Per-User Quotas"),
    ("rate_limits", "Rate Limits"),
    ("retention", "Retention"),
    ("content_safety", "Content Safety"),
    ("api", "API"),
]


UNLIMITED_HELP = "0 means unlimited."


SETTING_DEFS: List[SettingDef] = [
    # ── features ────────────────────────────────────────────────────────
    SettingDef(
        key="maintenance_mode",
        section="features",
        type=TYPE_BOOL,
        default=False,
        label="Maintenance mode",
        help="Return 503 to everyone except admins. Use around destructive operations such as a backup restore.",
    ),
    SettingDef(
        key="maintenance_message",
        section="features",
        type=TYPE_STR,
        default="Relic is temporarily unavailable for maintenance.",
        label="Maintenance message",
        help="Shown to users while maintenance mode is on.",
    ),
    SettingDef(
        key="read_only_mode",
        section="features",
        type=TYPE_BOOL,
        default=False,
        label="Read-only mode",
        help="Reject all writes. Reads continue to work. Admin endpoints are never blocked.",
    ),
    SettingDef(
        key="require_auth_for_writes",
        section="features",
        type=TYPE_BOOL,
        default=False,
        label="Require authentication for writes",
        help="Reject writes without a valid user key. Per-user quotas only bind when this is on.",
    ),
    SettingDef(
        key="allow_anonymous_writes",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow anonymous relic creation",
        help="Allow creating relics with no user key at all.",
    ),
    SettingDef(
        key="allow_registration",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow new user registration",
        help="Turn off to freeze the user list.",
    ),
    SettingDef(
        key="allow_forking",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow forking",
        help="Forking copies stored content server-side and counts against the owner's storage quota.",
    ),
    SettingDef(
        key="allow_comments",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow comments",
        help="Turn off to disable commenting entirely.",
    ),
    SettingDef(
        key="allow_spaces",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow spaces",
        help="Turn off to disable creating and modifying spaces.",
    ),
    SettingDef(
        key="allow_reports",
        section="features",
        type=TYPE_BOOL,
        default=True,
        label="Allow content reports",
        help="Turn off to disable the report queue.",
    ),
    SettingDef(
        key="require_auth_for_reports",
        section="features",
        type=TYPE_BOOL,
        default=False,
        label="Require authentication to report",
        help="Reporting is unauthenticated by default, which makes the admin queue easy to flood.",
    ),

    # ── uploads ─────────────────────────────────────────────────────────
    SettingDef(
        key="max_upload_size_bytes",
        section="uploads",
        type=TYPE_INT,
        default=settings.MAX_UPLOAD_SIZE,
        label="Maximum upload size",
        help="Largest single relic accepted. Must stay below the reverse proxy's client_max_body_size.",
        min=0,
        unit="bytes",
    ),
    SettingDef(
        key="allowed_content_types",
        section="uploads",
        type=TYPE_LIST,
        default=[],
        label="Allowed content types",
        help="Glob patterns such as 'text/*'. Empty means allow everything.",
    ),
    SettingDef(
        key="blocked_content_types",
        section="uploads",
        type=TYPE_LIST,
        default=[],
        label="Blocked content types",
        help="Glob patterns, applied after the allow list. Useful for blocking 'text/html' while allowing 'text/*'.",
    ),
    SettingDef(
        key="max_tag_count",
        section="uploads",
        type=TYPE_INT,
        default=20,
        label="Maximum tags per relic",
        help=UNLIMITED_HELP,
        min=0,
        unit="tags",
    ),
    SettingDef(
        key="max_tag_length",
        section="uploads",
        type=TYPE_INT,
        default=64,
        label="Maximum tag length",
        help=UNLIMITED_HELP,
        min=0,
        unit="characters",
    ),

    # ── quotas ──────────────────────────────────────────────────────────
    SettingDef(
        key="max_relics_per_user",
        section="quotas",
        type=TYPE_INT,
        default=0,
        label="Maximum relics per user",
        help=f"Default for every user; can be overridden per user. {UNLIMITED_HELP}",
        min=0,
        unit="relics",
    ),
    SettingDef(
        key="max_relics_per_user_per_day",
        section="quotas",
        type=TYPE_INT,
        default=0,
        label="Maximum relics per user per day",
        help=f"Rolling 24-hour window. {UNLIMITED_HELP}",
        min=0,
        unit="relics_per_day",
    ),
    SettingDef(
        key="max_storage_bytes_per_user",
        section="quotas",
        type=TYPE_INT,
        default=0,
        label="Maximum storage per user",
        help=f"Total bytes across all of a user's relics, including forks. {UNLIMITED_HELP}",
        min=0,
        unit="bytes",
    ),
    SettingDef(
        key="max_comments_per_user_per_day",
        section="quotas",
        type=TYPE_INT,
        default=0,
        label="Maximum comments per user per day",
        help=f"Rolling 24-hour window. {UNLIMITED_HELP}",
        min=0,
        unit="comments_per_day",
    ),

    # ── rate_limits ─────────────────────────────────────────────────────
    SettingDef(
        key="rate_limit_enabled",
        section="rate_limits",
        type=TYPE_BOOL,
        default=False,
        label="Enable rate limiting",
        help="Limits are keyed by user key, falling back to client IP for anonymous requests.",
    ),
    SettingDef(
        key="rate_limit_requests_per_minute",
        section="rate_limits",
        type=TYPE_INT,
        default=120,
        label="Requests per minute",
        help=f"All requests, reads included. {UNLIMITED_HELP}",
        min=0,
        unit="per_minute",
    ),
    SettingDef(
        key="rate_limit_writes_per_minute",
        section="rate_limits",
        type=TYPE_INT,
        default=30,
        label="Writes per minute",
        help=f"Any non-GET request. {UNLIMITED_HELP}",
        min=0,
        unit="per_minute",
    ),
    SettingDef(
        key="rate_limit_uploads_per_hour",
        section="rate_limits",
        type=TYPE_INT,
        default=0,
        label="Uploads per hour",
        help=f"Relic creations and forks. {UNLIMITED_HELP}",
        min=0,
        unit="per_hour",
    ),

    # ── retention ───────────────────────────────────────────────────────
    SettingDef(
        key="force_expiry",
        section="retention",
        type=TYPE_BOOL,
        default=False,
        label="Force expiry",
        help="Reject relics that never expire. Requires a maximum expiry to be set.",
    ),
    SettingDef(
        key="max_expiry",
        section="retention",
        type=TYPE_STR,
        default="never",
        label="Maximum expiry",
        help="Longer requests are clamped to this. Use forms like 30m, 24h, 7d, 30d, 1y, or 'never'.",
    ),
    SettingDef(
        key="default_expiry",
        section="retention",
        type=TYPE_STR,
        default="never",
        label="Default expiry",
        help="Applied when the client does not specify one.",
    ),

    # ── content_safety ──────────────────────────────────────────────────
    SettingDef(
        key="render_html",
        section="content_safety",
        type=TYPE_BOOL,
        default=True,
        label="Render HTML relics",
        help="Rendering user-supplied HTML executes it on this origin. Turn off on shared or public instances.",
    ),
    SettingDef(
        key="render_svg_inline",
        section="content_safety",
        type=TYPE_BOOL,
        default=True,
        label="Display SVG images",
        help="Controls whether SVGs are displayed in the viewer; they are shown via <img>, which already blocks scripts inside them. The real protection against SVG served as a page is 'Force download of raw content'.",
    ),
    SettingDef(
        key="force_download_raw",
        section="content_safety",
        type=TYPE_BOOL,
        default=False,
        label="Force download of raw content",
        help="Serve non-text raw content as an attachment, so the instance cannot host a working page.",
    ),
    SettingDef(
        key="max_comment_length",
        section="content_safety",
        type=TYPE_INT,
        default=10000,
        label="Maximum comment length",
        help=UNLIMITED_HELP,
        min=0,
        unit="characters",
    ),
    SettingDef(
        key="max_name_length",
        section="content_safety",
        type=TYPE_INT,
        default=255,
        label="Maximum name length",
        help=UNLIMITED_HELP,
        min=0,
        unit="characters",
    ),
    SettingDef(
        key="max_description_length",
        section="content_safety",
        type=TYPE_INT,
        default=2000,
        label="Maximum description length",
        help=UNLIMITED_HELP,
        min=0,
        unit="characters",
    ),

    # ── api ─────────────────────────────────────────────────────────────
    SettingDef(
        key="max_page_limit",
        section="api",
        type=TYPE_INT,
        default=1000,
        label="Maximum page size",
        help="Upper bound on the limit parameter for any paginated endpoint.",
        min=1,
        unit="items",
    ),
    SettingDef(
        key="max_lineage_nodes",
        section="api",
        type=TYPE_INT,
        default=200,
        label="Maximum lineage nodes",
        help="Upper bound on how much of a fork tree one request may walk.",
        min=1,
        unit="nodes",
    ),
]


SETTINGS_BY_KEY = {d.key: d for d in SETTING_DEFS}

# Per-user quota overrides. Maps the User column to the global setting it
# overrides, so resolution and validation stay in one place.
QUOTA_OVERRIDE_COLUMNS = {
    "quota_max_relics": "max_relics_per_user",
    "quota_max_relics_per_day": "max_relics_per_user_per_day",
    "quota_max_storage_bytes": "max_storage_bytes_per_user",
}


DEFAULTS = {d.key: d.default for d in SETTING_DEFS}


class SettingError(ValueError):
    """Raised when a setting value fails validation."""


def coerce_and_validate(key: str, value: Any) -> Any:
    """Coerce a raw value to the declared type for `key` and range-check it.

    Raises SettingError with a user-facing message on any problem, so callers
    can turn it straight into a 400.
    """
    definition = SETTINGS_BY_KEY.get(key)
    if definition is None:
        raise SettingError(f"Unknown setting: {key}")

    if definition.type == TYPE_BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise SettingError(f"{key} must be a boolean")

    if definition.type == TYPE_INT:
        # bool is an int subclass; reject it explicitly so True doesn't become 1.
        if isinstance(value, bool):
            raise SettingError(f"{key} must be an integer")
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            raise SettingError(f"{key} must be an integer")
        if definition.min is not None and coerced < definition.min:
            raise SettingError(f"{key} must be at least {definition.min}")
        if definition.max is not None and coerced > definition.max:
            raise SettingError(f"{key} must be at most {definition.max}")
        return coerced

    if definition.type == TYPE_STR:
        if not isinstance(value, str):
            raise SettingError(f"{key} must be a string")
        if definition.choices and value not in definition.choices:
            raise SettingError(f"{key} must be one of: {', '.join(definition.choices)}")
        return value

    if definition.type == TYPE_LIST:
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            raise SettingError(f"{key} must be a list")
        items = [str(item).strip() for item in value if str(item).strip()]
        return items

    raise SettingError(f"Setting {key} has an unsupported type")


# Curated bundles an admin can apply in one action.
#
# "default" is expressed as an empty override set rather than a list of values,
# so it always means "whatever the registry currently declares" and can never
# drift out of sync with DEFAULTS.
PRESETS = {
    "default": {},
    "hardened": {
        # Identity and write access
        "require_auth_for_writes": True,
        "allow_anonymous_writes": False,
        "require_auth_for_reports": True,
        # Resource ceilings
        "max_upload_size_bytes": 5 * 1024 * 1024,
        "max_relics_per_user": 50,
        "max_relics_per_user_per_day": 25,
        "max_storage_bytes_per_user": 100 * 1024 * 1024,
        "max_comments_per_user_per_day": 50,
        # Throttling
        "rate_limit_enabled": True,
        "rate_limit_requests_per_minute": 60,
        "rate_limit_writes_per_minute": 10,
        "rate_limit_uploads_per_hour": 30,
        # Content self-cleans
        "force_expiry": True,
        "max_expiry": "24h",
        "default_expiry": "24h",
        # Never execute user content on this origin
        "render_html": False,
        "render_svg_inline": False,
        "force_download_raw": True,
        # Bound query cost
        "max_page_limit": 100,
        "max_lineage_nodes": 50,
    },
}


def schema_for_api() -> List[dict]:
    """Return the registry grouped by section, for the admin UI to render widgets from."""
    by_section = {key: [] for key, _ in SECTIONS}
    for definition in SETTING_DEFS:
        by_section[definition.section].append({
            "key": definition.key,
            "type": definition.type,
            "default": definition.default,
            "label": definition.label,
            "help": definition.help,
            "min": definition.min,
            "max": definition.max,
            "choices": definition.choices,
            "unit": definition.unit,
        })
    return [
        {"section": key, "label": label, "settings": by_section[key]}
        for key, label in SECTIONS
    ]
