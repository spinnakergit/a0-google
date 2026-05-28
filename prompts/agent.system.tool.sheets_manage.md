## sheets_manage

Manage Google Spreadsheets at the file level: create new spreadsheets, fetch metadata for an existing one, or list spreadsheets in the user's Drive.

**Arguments:**
- **action** (string, required): One of `create`, `get`, or `list`.
  - `create` — Create a new spreadsheet.
  - `get` — Retrieve metadata (title, tabs, URL) for a specific spreadsheet.
  - `list` — List spreadsheets in the user's Drive (requires the Drive service to be enabled).
- **title** (string, optional): Spreadsheet title. Required when `action` is `create`.
- **sheet_titles** (array or string, optional): Tab names to create inside the new spreadsheet. Accepts a JSON array (`["Q1","Q2"]`) or a comma-separated string. Used only with `create`.
- **spreadsheet_id** (string, optional): The spreadsheet ID. Required when `action` is `get`.
- **limit** (integer, optional): Maximum spreadsheets to return for `list`. Defaults to 25, max 100.

**Examples:**

Create a new spreadsheet with two tabs:
~~~json
{
  "action": "create",
  "title": "2026 Budget",
  "sheet_titles": ["Income", "Expenses"]
}
~~~

Get metadata (find tab names and URL):
~~~json
{
  "action": "get",
  "spreadsheet_id": "1AbCDeFgHiJkLmNoPqRsTuVwXyZ1234567890_ExAmPlE"
}
~~~

List the 10 most recently modified spreadsheets:
~~~json
{
  "action": "list",
  "limit": 10
}
~~~
