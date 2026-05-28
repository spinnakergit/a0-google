"""Shared Google OAuth2 authentication module.

Provides unified credential management for all Google services
(Gmail, Calendar, Drive, Contacts, Tasks). Single credentials.json
and token.json with dynamically assembled scopes.
"""

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("google_auth")

# ---------------------------------------------------------------------------
# Dep self-heal — works around A0 having no plugin "startup" hook. If the
# container restarts and /opt/venv-a0 lost our deps, the first auth call will
# re-run initialize.py to reinstall them. Cached so it only runs once per
# process; if it fails the subsequent `from google...` import surfaces the
# real error.
# ---------------------------------------------------------------------------
_DEPS_CHECKED = False
_DEPS_LOCK = threading.Lock()
_REQUIRED_MODULES = ("google.auth", "google_auth_oauthlib", "googleapiclient")


def _ensure_deps() -> None:
    """If any required Google module is missing, re-run initialize.py once."""
    global _DEPS_CHECKED
    if _DEPS_CHECKED:
        return
    with _DEPS_LOCK:
        if _DEPS_CHECKED:
            return
        try:
            missing = []
            for mod in _REQUIRED_MODULES:
                try:
                    __import__(mod)
                except ImportError:
                    missing.append(mod)
            if missing:
                init_script = Path(__file__).parent.parent / "initialize.py"
                msg = f"[google-plugin] Missing deps {missing}; re-running {init_script}"
                logger.warning(msg)
                if init_script.exists():
                    subprocess.run(
                        [sys.executable, str(init_script)],
                        check=False, timeout=180,
                    )
        finally:
            # Only attempt the heal once per process even if it failed.
            _DEPS_CHECKED = True

# ---------------------------------------------------------------------------
# Scope registry — maps service names to their required OAuth scopes
# ---------------------------------------------------------------------------
SERVICE_SCOPES = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
    ],
    "contacts": [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/contacts",
    ],
    "tasks": [
        "https://www.googleapis.com/auth/tasks",
    ],
}

# Service name → (API name, API version)
SERVICE_API = {
    "gmail": ("gmail", "v1"),
    "calendar": ("calendar", "v3"),
    "drive": ("drive", "v3"),
    "contacts": ("people", "v1"),
    "tasks": ("tasks", "v1"),
}

# Default enabled services
DEFAULT_ENABLED = {"gmail", "calendar", "drive"}


class GoogleAuthError(Exception):
    """Raised when OAuth2 authentication fails."""
    pass


class GoogleAPIError(Exception):
    """Raised when a Google API call fails."""
    def __init__(self, error: str, status: int = 0):
        self.status = status
        super().__init__(error)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_google_config(agent=None) -> dict:
    """Load plugin configuration through the A0 framework."""
    try:
        from helpers import plugins
        config = plugins.get_plugin_config("google", agent=agent) or {}
    except Exception:
        config = {}
    return config


def get_enabled_services(config: dict) -> set:
    """Return the set of enabled service names."""
    services = config.get("services", {})
    if not services:
        return DEFAULT_ENABLED.copy()
    return {
        name for name, svc in services.items()
        if svc.get("enabled", name in DEFAULT_ENABLED)
    }


def is_service_enabled(service_name: str, agent=None) -> bool:
    """Check if a Google service is enabled in plugin config."""
    config = get_google_config(agent)
    return service_name in get_enabled_services(config)


def get_scopes(config: dict) -> list:
    """Assemble OAuth scopes from enabled services."""
    enabled = get_enabled_services(config)
    scopes = []
    for service in enabled:
        for scope in SERVICE_SCOPES.get(service, []):
            if scope not in scopes:
                scopes.append(scope)
    return scopes


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

def _data_dir(config: dict) -> Path:
    """Resolve the data directory for credential storage."""
    candidates = [
        Path(__file__).parent.parent / "data",
        Path("/a0/usr/plugins/google/data"),
        Path("/a0/plugins/google/data"),
        Path("/git/agent-zero/usr/plugins/google/data"),
    ]
    for p in candidates:
        if p.exists():
            logger.debug("Using data dir: %s", p)
            return p
    # Create the first candidate
    logger.info("No existing data dir found, creating: %s", candidates[0])
    candidates[0].mkdir(parents=True, exist_ok=True)
    os.chmod(str(candidates[0]), 0o700)
    return candidates[0]


def _credentials_path(config: dict) -> Path:
    """Locate credentials.json."""
    explicit = config.get("auth", {}).get("credentials_path", "")
    if explicit and Path(explicit).exists():
        return Path(explicit)
    data = _data_dir(config)
    return data / "credentials.json"


def _token_path(config: dict) -> Path:
    """Locate token.json."""
    return _data_dir(config) / "token.json"


# ---------------------------------------------------------------------------
# OAuth2 Authentication
# ---------------------------------------------------------------------------

def get_credentials(config: dict):
    """Load or refresh OAuth2 credentials.

    Returns a google.oauth2.credentials.Credentials object or raises GoogleAuthError.
    """
    _ensure_deps()
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_file = _token_path(config)
    scopes = get_scopes(config)
    logger.info("Loading credentials from %s (requesting %d scopes)", token_file, len(scopes))

    creds = None
    if not token_file.exists():
        raise GoogleAuthError(
            f"token.json not found at {token_file}. "
            "Place a google-auth-format token file there, or complete OAuth via plugin settings."
        )

    try:
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    except Exception as e:
        raise GoogleAuthError(
            f"Failed to load {token_file}: {type(e).__name__}: {e}. "
            "Expected google-auth format with keys: token, refresh_token, token_uri, "
            "client_id, client_secret, scopes."
        )

    # Scope mismatch: token covers fewer scopes than the plugin is asking for.
    token_scopes = set(creds.scopes or [])
    missing = [s for s in scopes if s not in token_scopes]
    if missing:
        logger.warning(
            "Token scopes %s do not cover requested scopes; missing: %s",
            sorted(token_scopes), missing,
        )

    if creds.expired and creds.refresh_token:
        logger.info("Token expired (expiry=%s); refreshing", getattr(creds, "expiry", None))
        try:
            creds.refresh(Request())
            _save_token(creds, config)
            logger.info("Token refresh succeeded")
        except Exception as e:
            raise GoogleAuthError(
                f"Token refresh failed: {type(e).__name__}: {e}. "
                "The refresh_token may be revoked/expired, or client_id/client_secret "
                "in token.json may not match the OAuth client that issued the token."
            )

    if not creds.valid:
        reason = []
        if creds.expired:
            reason.append("expired")
        if not creds.refresh_token:
            reason.append("no refresh_token")
        if missing:
            reason.append(f"missing scopes: {missing}")
        raise GoogleAuthError(
            f"Credentials loaded but not valid ({', '.join(reason) or 'unknown'}). "
            "Re-authorize or provide a token with full required scopes."
        )

    return creds


def _save_token(creds, config: dict):
    """Persist token.json with restrictive permissions."""
    token_file = _token_path(config)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = token_file.with_suffix(".tmp")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(creds.to_json())
        os.replace(str(tmp), str(token_file))
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        with open(str(token_file), "w") as f:
            f.write(creds.to_json())
        try:
            os.chmod(str(token_file), 0o600)
        except OSError:
            pass


def _pkce_path(config: dict) -> Path:
    """Temp file to persist PKCE code_verifier between auth URL and token exchange."""
    return _data_dir(config) / ".pkce_verifier"


def generate_auth_url(config: dict) -> str:
    """Generate the OAuth2 authorization URL for the user to visit."""
    _ensure_deps()
    from google_auth_oauthlib.flow import Flow

    creds_file = _credentials_path(config)
    if not creds_file.exists():
        raise GoogleAuthError(
            "credentials.json not found. Upload it via plugin settings or "
            f"place it in {creds_file.parent}/"
        )

    scopes = get_scopes(config)
    flow = Flow.from_client_secrets_file(
        str(creds_file),
        scopes=scopes,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # Persist PKCE code_verifier so exchange_auth_code() can use it
    code_verifier = getattr(flow, "code_verifier", None)
    if code_verifier:
        pkce_file = _pkce_path(config)
        try:
            fd = os.open(str(pkce_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(code_verifier)
        except Exception:
            pkce_file.write_text(code_verifier)

    return auth_url


def exchange_auth_code(config: dict, code: str):
    """Exchange an authorization code for credentials and save the token."""
    _ensure_deps()
    from google_auth_oauthlib.flow import Flow

    creds_file = _credentials_path(config)
    if not creds_file.exists():
        raise GoogleAuthError("credentials.json not found.")

    scopes = get_scopes(config)
    flow = Flow.from_client_secrets_file(
        str(creds_file),
        scopes=scopes,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )

    # Restore PKCE code_verifier from generate_auth_url()
    pkce_file = _pkce_path(config)
    if pkce_file.exists():
        try:
            flow.code_verifier = pkce_file.read_text().strip()
        except Exception:
            pass
        finally:
            try:
                pkce_file.unlink(missing_ok=True)
            except Exception:
                pass

    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_token(creds, config)
    return creds


def is_authenticated(config: dict) -> tuple[bool, str]:
    """Check if valid credentials exist. Returns (authenticated, email_or_error)."""
    try:
        creds = get_credentials(config)
        # Probe via whichever enabled service supports a cheap identity call.
        enabled = get_enabled_services(config)
        probe = "gmail" if "gmail" in enabled else next(iter(enabled), None)
        if probe == "gmail":
            service = build_service("gmail", config, creds=creds)
            profile = service.users().getProfile(userId="me").execute()
            return True, profile.get("emailAddress", "unknown")
        if probe == "calendar":
            service = build_service("calendar", config, creds=creds)
            cal = service.calendars().get(calendarId="primary").execute()
            return True, cal.get("id", "unknown")
        # Fallback: creds load + refresh succeeded, but no cheap identity probe available.
        return True, "authenticated (no identity probe for enabled services)"
    except GoogleAuthError as e:
        logger.warning("Authentication check failed: %s", e)
        return False, str(e)
    except Exception as e:
        logger.exception("Unexpected error during auth check")
        return False, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Service builders
# ---------------------------------------------------------------------------

def build_service(service_name: str, config: dict, creds=None):
    """Build a Google API service object for the given service."""
    _ensure_deps()
    from googleapiclient.discovery import build

    if creds is None:
        creds = get_credentials(config)

    api_name, api_version = SERVICE_API.get(service_name, (service_name, "v1"))
    return build(api_name, api_version, credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Secure File I/O
# ---------------------------------------------------------------------------

def secure_write_json(path, data, indent: int = 2):
    """Write JSON to a file with restrictive permissions (0o600) and atomic rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=indent)
        os.replace(str(tmp_path), str(path))
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        with open(path, "w") as f:
            json.dump(data, f, indent=indent)
        try:
            os.chmod(str(path), 0o600)
        except OSError:
            pass
