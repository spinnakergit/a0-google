# Google Suite Plugin Documentation

## Overview

Unified Google integration for Agent Zero — Gmail, Calendar, Drive, Contacts, and Tasks with shared OAuth2 authentication and per-service toggles.

## Contents

- [Quick Start](QUICKSTART.md) — Installation and first-use guide (5-15 minutes)
- [Google Setup Guide](SETUP_GOOGLE.md) — Google Cloud Console project creation, API enablement, and OAuth configuration
- [Development](DEVELOPMENT.md) — Architecture, code patterns, and contributing

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
| `sheets_manage` | Sheets | Create spreadsheets, get metadata, list recent spreadsheets (via Drive) |
| `sheets_values` | Sheets | Read, write, and append cell values over A1-notation ranges |

## Skills (7)

Semantic workflow guides that activate when user intent matches trigger phrases.

| Skill | Category | Description |
|-------|----------|-------------|
| `google-communicate` | Communication | Email composition, drafts, and contact lookup |
| `google-research` | Research | Inbox triage, email search, thread summarization |
| `google-schedule` | Productivity | Calendar viewing, event creation, availability check |
| `google-drive` | Productivity | File search, upload, download, and sharing |
| `google-daily-briefing` | Productivity | Cross-service morning briefing (inbox + calendar + tasks) |
| `google-tasks` | Productivity | Task list management and to-do tracking |
| `google-sheets` | Productivity | Spreadsheet creation and cell read/write/append |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plugins/google/google_config_api` | GET/POST | Read/write config, OAuth flow, credentials upload |
| `/api/plugins/google/google_test` | POST | Test connection and authentication status |

## Auth Model

- **OAuth 2.0 with PKCE** — Single shared credential for all services
- **credentials.json** — OAuth client credentials from Google Cloud Console (Desktop app type)
- **token.json** — Auto-generated refresh/access token, stored with 0o600 permissions
- **Dynamic scopes** — Only enabled services contribute scopes to the OAuth flow
- **Automatic refresh** — Tokens are refreshed transparently when expired
