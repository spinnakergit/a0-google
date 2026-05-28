---
name: "google-sheets"
description: "Work with Google Sheets: create spreadsheets, read and write cell ranges, append rows."
version: "1.0.0"
author: "AgentZero Google Suite Plugin"
license: "MIT"
tags: ["google", "sheets", "spreadsheets", "productivity"]
triggers:
  - "google sheets"
  - "create spreadsheet"
  - "new spreadsheet"
  - "read spreadsheet"
  - "write to sheet"
  - "append to sheet"
  - "update spreadsheet"
  - "list spreadsheets"
allowed_tools:
  - sheets_manage
  - sheets_values
metadata:
  complexity: "basic"
  category: "productivity"
---

# Google Sheets Skill

Create spreadsheets, look up existing ones, and read/write/append cell ranges. Use this when the user mentions sheets, spreadsheets, tabular data, or wants to record rows of data.

## Two-tool model

- **`sheets_manage`** — file-level: `create`, `get` (metadata for a spreadsheet incl. tab names), `list` (recent spreadsheets via Drive).
- **`sheets_values`** — cell-level: `read`, `write`, `append` using A1 notation like `Sheet1!A1:C10`.

You almost always need a `spreadsheet_id` for value operations. Get it from a previous `create`, a `list`, or directly from the user (it's the long ID in the spreadsheet URL).

## Workflow

### Find an existing spreadsheet
```json
{"tool": "sheets_manage", "args": {"action": "list", "limit": 10}}
```

### Inspect a spreadsheet (get tab names + URL)
```json
{"tool": "sheets_manage", "args": {"action": "get", "spreadsheet_id": "1AbC...xYz"}}
```

### Create a new spreadsheet
```json
{"tool": "sheets_manage", "args": {"action": "create", "title": "2026 Budget", "sheet_titles": ["Income", "Expenses"]}}
```

### Read a range
```json
{"tool": "sheets_values", "args": {"action": "read", "spreadsheet_id": "1AbC...xYz", "range": "Income!A1:D20"}}
```

### Write a range (overwrites)
```json
{
  "tool": "sheets_values",
  "args": {
    "action": "write",
    "spreadsheet_id": "1AbC...xYz",
    "range": "Income!A1",
    "values": [["Source", "Amount"], ["Salary", 5000], ["Freelance", 1200]]
  }
}
```

### Append a row
```json
{
  "tool": "sheets_values",
  "args": {
    "action": "append",
    "spreadsheet_id": "1AbC...xYz",
    "range": "Income!A:B",
    "values": [["Dividend", 240]]
  }
}
```

## Tips

- The Sheets service is disabled by default — enable it in plugin settings and re-authorize.
- `range` uses A1 notation. Examples: `Sheet1!A1:C10`, `Sheet1!A:C` (whole columns), or `Sheet1` (the entire tab).
- `write` overwrites cells starting at the top-left of `range`. To add new rows without overwriting, use `append`.
- `value_input` defaults to `USER_ENTERED` (Sheets parses dates/formulas like the UI does). Use `RAW` to store strings literally.
- `list` requires the Drive service to also be enabled — the Sheets API itself has no list endpoint.
- If the user asks to "download" a spreadsheet as a file, use `drive_download` with the spreadsheet ID (Google Sheets export as PDF).
