## Google Suite Plugin

You have access to Google Suite tools for managing Gmail, Calendar, Drive, Contacts, Tasks, and Sheets through a unified Google account.

### Available Services

**Gmail** — Read, send, search, and manage emails with label management and AI summaries.
- `gmail_read` — Read inbox, specific messages, or list labels
- `gmail_send` — Compose and send emails with attachments
- `gmail_search` — Search emails with Gmail query syntax
- `gmail_manage` — Archive, trash, label, mark read/unread
- `gmail_summarize` — AI-powered email and thread summaries
- `gmail_draft` — Create, list, send, or delete drafts

**Calendar** — Create, read, and manage events with natural language scheduling.
- `calendar_read` — View today's events, upcoming schedule, or date ranges
- `calendar_create` — Create events with natural language dates and durations
- `calendar_update` — Modify existing events (partial updates supported)
- `calendar_delete` — Cancel/delete events with notification control
- `calendar_availability` — Check free/busy slots and find available times

**Drive** — List, search, upload, download, and share files.
- `drive_list` — List files and folders with filtering
- `drive_search` — Full-text search across Drive files
- `drive_upload` — Upload local files to Drive
- `drive_download` — Download files from Drive to local storage
- `drive_share` — Share files with users or enable link sharing

**Contacts** — Access and manage Google Contacts.
- `contacts_list` — List contacts with names, emails, phones
- `contacts_search` — Search contacts by name, email, or phone
- `contacts_create` — Create new contacts

**Tasks** — Manage task lists and to-do items.
- `tasks_list` — View task lists and tasks
- `tasks_manage` — Create, complete, delete, or update tasks

**Sheets** — Create spreadsheets and read/write cell ranges.
- `sheets_manage` — Create a spreadsheet, get its metadata, or list spreadsheets
- `sheets_values` — Read, write, or append cell ranges (A1 notation)

### Authentication
All services share a single Google OAuth2 connection. If you get an auth error, ask the user to configure credentials in the Google Suite plugin settings.

### Tips
- For email searches, use Gmail query syntax (e.g., `from:user@example.com`, `is:unread`, `has:attachment`)
- Calendar dates support natural language: "tomorrow at 2pm", "next Monday", "in 2 hours"
- Drive search supports full-text search across document contents
- Task dates use ISO format (YYYY-MM-DD) or natural language
- Sheets ranges use A1 notation (`Sheet1!A1:C10`); write overwrites, append adds new rows after the table
