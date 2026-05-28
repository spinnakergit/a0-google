## sheets_values

Read, write, or append cell values in a Google spreadsheet using A1-notation ranges.

**Arguments:**
- **action** (string, required): One of `read`, `write`, or `append`.
  - `read` — Read all values in a range.
  - `write` — Overwrite cells in a range starting at the top-left of `range`.
  - `append` — Append rows after the last data row in the given range/table.
- **spreadsheet_id** (string, required): The spreadsheet ID (from `sheets_manage` list/get/create).
- **range** (string, required): A1 notation, e.g. `Sheet1!A1:C10`, `Sheet1!A:C`, or just `Sheet1`. For `append`, the range is used to identify the table to append to.
- **values** (array or string, required for `write` and `append`): A 2D array of rows. Each row is an array of cell values. Accepts a JSON-encoded string as a fallback. A flat 1D array is treated as a single row.
- **value_input** (string, optional): `USER_ENTERED` (default — parses dates, formulas, numbers) or `RAW` (stores as literal strings).

**Examples:**

Read the first 10 rows:
~~~json
{
  "action": "read",
  "spreadsheet_id": "1AbC...xYz",
  "range": "Sheet1!A1:D10"
}
~~~

Write a header row and two data rows:
~~~json
{
  "action": "write",
  "spreadsheet_id": "1AbC...xYz",
  "range": "Sheet1!A1",
  "values": [
    ["Name", "Email", "Joined"],
    ["Alice", "alice@example.com", "2026-01-15"],
    ["Bob", "bob@example.com", "2026-02-03"]
  ]
}
~~~

Append a single new row to the end of a table:
~~~json
{
  "action": "append",
  "spreadsheet_id": "1AbC...xYz",
  "range": "Sheet1!A:C",
  "values": [["Carol", "carol@example.com", "2026-05-25"]]
}
~~~

Write a formula literally (no evaluation):
~~~json
{
  "action": "write",
  "spreadsheet_id": "1AbC...xYz",
  "range": "Sheet1!A1",
  "values": [["=SUM(B:B)"]],
  "value_input": "RAW"
}
~~~
