# Google Suite Plugin — Development Guide

## Project Structure

```
a0-google/
├── plugin.yaml              # Plugin manifest (name must be "google")
├── default_config.yaml      # Default settings (service toggles, security, defaults)
├── initialize.py            # Dependency installer (google-auth, google-api-python-client, etc.)
├── install.sh               # Deployment script
├── helpers/
│   ├── __init__.py
│   ├── google_auth.py       # Shared OAuth2: credentials, tokens, scopes, service builders
│   ├── gmail_client.py      # Gmail API wrapper (MIME parsing, message composition)
│   ├── calendar_client.py   # Calendar API wrapper (event CRUD, timezone handling)
│   ├── drive_client.py      # Drive API wrapper (list, search, upload, download, share)
│   ├── contacts_client.py   # People API wrapper (contacts CRUD)
│   ├── tasks_client.py      # Tasks API wrapper (task lists, task CRUD)
│   ├── sanitize.py          # Email content sanitization (tracking pixels, HTML-to-text, validation)
│   └── date_utils.py        # Natural language date parsing with timezone awareness
├── tools/                   # 23 tool implementations
│   ├── gmail_read.py        # Read inbox, specific messages, list labels
│   ├── gmail_send.py        # Compose and send emails with attachments
│   ├── gmail_search.py      # Gmail query-based search with date/sender/label filters
│   ├── gmail_manage.py      # Archive, trash, star, mark read/unread, label management
│   ├── gmail_summarize.py   # LLM-powered email/thread summarization with memory save
│   ├── gmail_draft.py       # Create, list, send, and delete drafts
│   ├── calendar_read.py     # View events by date range or ID
│   ├── calendar_create.py   # Create events with natural language, recurrence
│   ├── calendar_update.py   # Update event properties (duration preservation)
│   ├── calendar_delete.py   # Delete events with notification control
│   ├── calendar_availability.py  # Free/busy check, open slot finder
│   ├── drive_list.py        # List files with folder/mime filtering
│   ├── drive_search.py      # Full-text Drive search
│   ├── drive_upload.py      # Upload with path safety checks
│   ├── drive_download.py    # Download with path traversal protection
│   ├── drive_share.py       # Share via email or link, role-based
│   ├── contacts_list.py     # List contacts with sorting
│   ├── contacts_search.py   # Search contacts by name/email
│   ├── contacts_create.py   # Create contacts with full details
│   ├── tasks_list.py        # List task lists and tasks
│   ├── tasks_manage.py      # Create, update, complete, delete tasks
│   ├── sheets_manage.py     # Create/get/list spreadsheets (list via Drive)
│   └── sheets_values.py     # Read/write/append cell values (A1 notation)
├── prompts/                 # 23 tool prompts + 1 group prompt
│   ├── tool_group.md        # Group context for all Google tools
│   └── agent.system.tool.<name>.md  # Per-tool prompt with JSON examples
├── skills/                  # 6 semantic workflow skills
│   ├── google-communicate/  # Email send/draft with contact lookup
│   ├── google-research/     # Inbox triage, search, summarization
│   ├── google-schedule/     # Calendar view, create, availability
│   ├── google-drive/        # File search, upload, download, share
│   ├── google-daily-briefing/  # Cross-service morning overview
│   └── google-tasks/        # Task list management
├── api/
│   ├── google_config_api.py # Config get/set, OAuth flow, credentials upload
│   └── google_test.py       # Connection test endpoint
├── webui/
│   ├── main.html            # Dashboard (service status cards, connection test)
│   └── config.html          # Settings (auth, service toggles, defaults, security)
├── tests/
│   ├── regression_test.sh   # 47 automated tests across 10 categories
│   ├── HUMAN_TEST_PLAN.md   # 59 manual tests across 9 phases
│   ├── HUMAN_TEST_RESULTS.md
│   └── SECURITY_ASSESSMENT_RESULTS.md
└── docs/
    ├── README.md            # Documentation index
    ├── QUICKSTART.md        # End-user setup guide
    ├── SETUP_GOOGLE.md      # Google Cloud configuration
    └── DEVELOPMENT.md       # This file
```

## Development Setup

1. Start the dev container:
   ```bash
   docker start a0-verify-active
   ```

2. Deploy the plugin:
   ```bash
   docker cp a0-google/. a0-verify-active:/a0/usr/plugins/google/
   docker exec a0-verify-active ln -sf /a0/usr/plugins/google /a0/plugins/google
   docker exec a0-verify-active touch /a0/usr/plugins/google/.toggle-1
   docker exec a0-verify-active supervisorctl restart run_ui
   ```

3. Clear bytecode cache (important after code changes):
   ```bash
   docker exec a0-verify-active find /a0/usr/plugins/google -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
   docker exec a0-verify-active supervisorctl restart run_ui
   ```

4. Run regression tests:
   ```bash
   bash tests/regression_test.sh a0-verify-active 50088
   ```

## Key Patterns

### Tool Pattern

All 23 tools follow this structure:
```python
from helpers.tool import Tool, Response

class GmailFoo(Tool):
    async def execute(self, **kwargs) -> Response:
        # 1. Service toggle guard
        from plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("gmail", self.agent):
            return Response(
                message="Gmail service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        # 2. Parse and validate args
        action = self.args.get("action", "")

        # 3. Get config and authenticate
        config = get_google_config(self.agent)
        service = build_service("gmail", config)

        # 4. Execute action
        self.set_progress("Doing something...")
        result = service.users().messages().list(userId="me").execute()

        # 5. Return formatted result
        return Response(message="Result here", break_loop=False)
```

### Service Toggle Guard

Every tool **must** check if its service is enabled as the first thing in `execute()`:
```python
from plugins.google.helpers.google_auth import is_service_enabled
if not is_service_enabled("<service_name>", self.agent):
    return Response(message="<Service> service is disabled...", break_loop=False)
```

Service names: `gmail`, `calendar`, `drive`, `contacts`, `tasks`.

### Config Access

```python
from plugins.google.helpers.google_auth import get_google_config, build_service

config = get_google_config(self.agent)          # Get plugin config dict
service = build_service("gmail", config)         # Build authenticated API service
```

Under the hood, `get_google_config()` calls `plugins.get_plugin_config("google", agent=agent)`.

### API Handler Pattern

```python
from helpers.api import ApiHandler, Request, Response

class GoogleFooApi(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return True  # MANDATORY — never return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Handle request
        return {"ok": True}
```

### WebUI Pattern

```javascript
// CSRF-aware fetch
const fetchApi = globalThis.fetchApi || fetch;

// Use data-gg= attributes for scoped element selection
const el = (name) => document.querySelector(`[data-gg="${name}"]`);
const statusEl = el('connection-status');
statusEl.textContent = 'Connected';
```

### Security Patterns

- **Email sanitization**: All email body content goes through `sanitize_body()` before display
- **Recipient allow-list**: `validate_recipients(to, allowed=allowed_list)` in send/draft tools
- **Path validation**: Drive download restricted to safe dirs; upload blocked from sensitive dirs
- **Atomic writes**: `secure_write_json()` uses `os.open(0o600)` + `os.replace()` for token/config
- **CSRF**: Every API handler returns `requires_csrf() -> True`
- **Content limits**: `MAX_EMAIL_BODY=50000`, `MAX_SUBJECT=500`, `MAX_BULK_CHARS=200000`

## Skills

Skills are Markdown-based workflow guides stored in `skills/<name>/SKILL.md`. They are **not Python code** — they teach the agent how to chain tools together for multi-step tasks.

### Skill Structure
```
skills/google-<name>/
└── SKILL.md          # YAML frontmatter + workflow markdown
```

### SKILL.md Frontmatter
```yaml
---
name: "google-<name>"
description: "What this skill does"
version: "1.0.0"
author: "AgentZero Google Suite Plugin"
license: "MIT"
tags: ["google", "relevant", "tags"]
triggers:
  - "natural language phrase that activates this skill"
  - "another trigger phrase"
allowed_tools:
  - tool_name_1
  - tool_name_2
metadata:
  complexity: "basic"        # basic, intermediate, advanced
  category: "communication"  # communication, research, productivity, administration
---
```

### How Skills Work
- **Triggers** are natural language phrases — when a user's message matches, the framework injects the SKILL.md into the agent's context
- **allowed_tools** tells the agent which tools are relevant for this workflow
- The body contains step-by-step instructions with JSON tool call examples
- Skills are installed to `$A0_ROOT/usr/skills/` (shared across all plugins)

### Adding a New Skill

1. Create `skills/google-<name>/SKILL.md` with frontmatter and workflow
2. Add 4-8 trigger phrases that cover common ways users would request this
3. List the tools the skill uses in `allowed_tools`
4. Write step-by-step workflow with JSON examples for each tool call
5. Add tips section with edge cases and best practices
6. Update `docs/README.md` and root `README.md` skill tables

## Adding a New Tool

1. Create `tools/<service>_<name>.py` with a `Tool` subclass
2. Add service toggle guard as the first check in `execute()`
3. Create `prompts/agent.system.tool.<service>_<name>.md` with JSON examples
4. Import sanitization helpers for any external content
5. Add tests to `tests/regression_test.sh`
6. Update `docs/README.md` and root `README.md` tool tables
7. Run the full regression suite to verify

## Adding a New Google Service

1. Add scope definitions to `SERVICE_SCOPES` in `google_auth.py`
2. Add API mapping to `SERVICE_API` in `google_auth.py`
3. Create `helpers/<service>_client.py` with API wrapper class
4. Create tool files in `tools/`
5. Create prompt files in `prompts/`
6. Add service toggle to `default_config.yaml`
7. Add WebUI tab in `config.html` (optional)
8. Update all documentation

## Testing

### Regression Tests (47 tests)

```bash
bash tests/regression_test.sh <container> <port>
```

Tests cover: container basics, required files, Python imports, CSRF enforcement, config API, tool registration, WebUI files, prompt files, service clients, and security checks.

### Human Verification (59 tests)

See `tests/HUMAN_TEST_PLAN.md` for the 9-phase manual test plan covering WebUI, OAuth, all 5 services, service toggles, and security edge cases.

### Important: Clear __pycache__

After deploying code changes to the container, always clear Python bytecode cache:
```bash
docker exec <container> find /a0/usr/plugins/google -name "__pycache__" -type d -exec rm -rf {} +
docker exec <container> supervisorctl restart run_ui
```

Stale `.pyc` files can cause Python to load old code despite updated `.py` files.
