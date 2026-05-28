# Google Suite Plugin for Agent Zero

Unified Google integration — Gmail, Calendar, Drive, Contacts, Tasks, and Sheets with shared OAuth2 authentication.

## Features

- **Gmail** — Read, send, search, reply, manage emails with AI-powered summaries and tracking pixel removal
- **Google Calendar** — Create, read, update, delete events with natural language scheduling and recurrence
- **Google Drive** — List, search, upload, download, and share files with link sharing
- **Google Contacts** — List, search, and create contacts via the People API
- **Google Tasks** — Manage task lists, create, complete, and delete to-do items
- **Google Sheets** — Create spreadsheets, list them via Drive, read and write cell ranges, append rows
- **Service toggles** — Enable or disable individual services without re-authentication
- **Recipient allow-list** — Restrict email sending to approved addresses
- **Content sanitization** — Tracking pixel removal, HTML-to-text, body truncation

## Quick Start

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the required APIs:
   - **Gmail API**
   - **Google Calendar API**
   - **Google Drive API**
   - **People API** (for Contacts)
   - **Tasks API**
   - **Google Sheets API**
4. Go to **APIs & Services > Credentials**
5. Click **Create Credentials > OAuth 2.0 Client ID**
6. Application type: **Desktop app**
7. Download the `credentials.json` file

### 2. Configure the Plugin

1. Open Agent Zero WebUI > **Settings > External Services > Google Suite**
2. In the **Auth** tab, paste the contents of `credentials.json`
3. Click **Authorize** — you'll be redirected to Google's consent screen
4. Grant the requested permissions and copy the authorization code
5. Paste the authorization code back into the plugin
6. Verify the connection shows "Authenticated" with your email address

### 3. Try It

- "Read my latest emails"
- "What's on my calendar today?"
- "List my recent Drive files"
- "Find my contact named Alice"
- "Add a task: Buy groceries, due tomorrow"
- "Schedule a meeting called 'Team Sync' tomorrow at 2pm for 1 hour"
- "Send an email to bob@example.com with subject 'Hello' and body 'Hi Bob'"

## Required APIs and OAuth Scopes

| Service | API | OAuth Scopes |
|---------|-----|-------------|
| Gmail | Gmail API | `gmail.readonly`, `gmail.send`, `gmail.modify` |
| Calendar | Google Calendar API | `calendar`, `calendar.events` |
| Drive | Google Drive API | `drive.file`, `drive.readonly` |
| Contacts | People API | `contacts.readonly`, `contacts` |
| Tasks | Tasks API | `tasks` |
| Sheets | Google Sheets API | `spreadsheets` |

Only scopes for **enabled** services are requested during the OAuth flow.

## Tools (23)

| Tool | Service | Description |
|------|---------|-------------|
| `gmail_read` | Gmail | Read inbox, specific messages, and list labels |
| `gmail_send` | Gmail | Compose and send emails with optional attachments |
| `gmail_search` | Gmail | Search with Gmail query syntax (from, to, date, labels) |
| `gmail_manage` | Gmail | Archive, trash, star, mark read/unread, add/remove labels |
| `gmail_summarize` | Gmail | AI-powered email and thread summarization with memory save |
| `gmail_draft` | Gmail | Create, list, send, and delete drafts |
| `calendar_read` | Calendar | View events for a date range or specific event |
| `calendar_create` | Calendar | Create events with natural language dates, duration, and recurrence |
| `calendar_update` | Calendar | Update event title, time, description, location, attendees |
| `calendar_delete` | Calendar | Delete events with optional attendee notification |
| `calendar_availability` | Calendar | Check free/busy status and find open time slots |
| `drive_list` | Drive | List files and folders with filtering and sorting |
| `drive_search` | Drive | Full-text search across Drive files |
| `drive_upload` | Drive | Upload local files to Drive with folder and description |
| `drive_download` | Drive | Download files (Google Docs auto-exported as PDF) |
| `drive_share` | Drive | Share files via email or link sharing with role control |
| `contacts_list` | Contacts | List contacts sorted by name or last modified |
| `contacts_search` | Contacts | Search contacts by name or email |
| `contacts_create` | Contacts | Create new contacts with name, email, phone, organization |
| `tasks_list` | Tasks | List task lists and tasks with filtering |
| `tasks_manage` | Tasks | Create, update, complete, and delete tasks |
| `sheets_manage` | Sheets | Create, get metadata for, or list spreadsheets |
| `sheets_values` | Sheets | Read, write, or append cell ranges (A1 notation) |

## Configuration

### Service Toggles

Each Google service can be independently enabled or disabled in the plugin config:

| Service | Default | Notes |
|---------|---------|-------|
| Gmail | Enabled | Core email functionality |
| Calendar | Enabled | Scheduling and events |
| Drive | Enabled | File management |
| Contacts | Disabled | Enable in config to use |
| Tasks | Disabled | Enable in config to use |
| Sheets | Disabled | Enable in config to use. `list` requires Drive enabled too. |

Disabling a service hides its tools from the agent. Re-enabling requires no re-authentication unless new OAuth scopes are needed.

### Security Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `allowed_recipients` | `[]` (all) | Restrict email sending to listed addresses |
| `allowed_calendars` | `[]` (all) | Restrict calendar access to listed calendar IDs |
| `max_attachment_size_mb` | 25 | Maximum email attachment size |
| `max_attendees` | 50 | Maximum attendees per calendar event |
| `sanitize_content` | true | Enable email content sanitization |

### Calendar Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `timezone` | `America/New_York` | Default timezone for events |
| `calendar_id` | `primary` | Default calendar |
| `default_duration_minutes` | 60 | Default event duration |

**Important:** The agent uses relative time expressions (e.g., "tomorrow at 2pm") based on the configured timezone. Make sure your Google Calendar account timezone matches the plugin timezone setting.

## Skills (7)

Skills are semantic workflow guides that teach the agent how to chain tools together for common tasks. They are loaded automatically when your request matches their trigger phrases.

| Skill | Triggers | Description |
|-------|----------|-------------|
| `google-communicate` | "send email", "draft email", "compose email" | Email composition with contact lookup |
| `google-research` | "check my inbox", "search emails", "summarize emails" | Inbox triage, search, and summarization |
| `google-schedule` | "schedule a meeting", "check calendar", "find free time" | Calendar view, create events, check availability |
| `google-drive` | "upload to drive", "find file", "share document" | File search, upload, download, and sharing |
| `google-daily-briefing` | "morning briefing", "what's my day", "catch me up" | Cross-service overview (inbox + calendar + tasks) |
| `google-tasks` | "show my tasks", "add a task", "complete task" | Task list management and to-do tracking |
| `google-sheets` | "create spreadsheet", "read spreadsheet", "append to sheet" | Spreadsheet create/list/get + cell read/write/append |

## Architecture

```
a0-google/
├── plugin.yaml              # Plugin manifest
├── initialize.py            # Dependency installer
├── default_config.yaml      # Default configuration
├── helpers/
│   ├── google_auth.py       # Shared OAuth2 (credentials, tokens, scopes)
│   ├── gmail_client.py      # Gmail API wrapper
│   ├── calendar_client.py   # Calendar API wrapper
│   ├── drive_client.py      # Drive API wrapper
│   ├── contacts_client.py   # People API wrapper
│   ├── tasks_client.py      # Tasks API wrapper
│   ├── sheets_client.py     # Sheets API wrapper
│   ├── sanitize.py          # Email content sanitization
│   └── date_utils.py        # Natural language date parsing
├── tools/                   # 23 tool files
├── skills/                  # 7 semantic workflow skills
├── api/                     # Config and test API handlers
├── webui/                   # Dashboard and config UI
├── prompts/                 # Tool prompt definitions
└── tests/                   # Regression tests and test plans
```

## License

MIT
