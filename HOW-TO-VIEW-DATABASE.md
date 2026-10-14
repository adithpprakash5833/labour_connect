# Run Labour Connect and view its MySQL database

This copy was extracted from your ZIP. Its existing MySQL database was opened successfully, Django reported no system-check issues or pending migrations, and the homepage returned HTTP 200.

The ZIP's Python 3.13 environment could not start here. A working Python 3.12 environment is provided in `.runtime`, with the project's required dependencies. VS Code is configured to use it.

## Start the project

Open this folder in VS Code:

`C:\Users\User\Documents\Codex\2026-10-07\thi\outputs\labour_connect`

Open **Terminal → New Terminal**, then run:

```powershell
.\.runtime\Scripts\python.exe scripts\run_local.py
```

Alternatively run ` .\Start-Local.ps1` if your PowerShell policy permits scripts. This launcher opens the existing data without reseeding it or applying migrations. It starts a separate MySQL instance on port 3307 and Django on port 8000. Keep the terminal open; press Ctrl+C to stop. Run only one launcher against this data folder at a time.

- Website: http://127.0.0.1:8000/
- Read-only database viewer: http://127.0.0.1:8765/
- Existing demo login details: `demo_accounts.txt`.

If a startup error occurs, check `.local/mysql-local.log`. MySQL Server is installed at `C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe`.

## View tables inside VS Code

You already have **Database Client** (`cweijan.vscode-mysql-client2`) installed. No additional extension is needed.

1. Start the project with the command above.
2. Open the **Database** panel in VS Code's left sidebar.
3. Click **+**, choose **MySQL**, and enter:

| Setting | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `3307` |
| Username | `labour_app` |
| Password | Copy the value of `DB_PASSWORD` from this folder's `.env` |
| Database | `labour_connect` |

4. Click **Connect**, expand `labour_connect` → **Tables**, then click a table such as `accounts_user`, `workers_workerprofile`, or `jobs_booking` to see its rows.
5. For SQL queries, open **Open Query** on the connection. The file `View-Database.sql` contains useful read-only queries.

The extension's official instructions are at https://github.com/cweijan/vscode-database-client#connect.

## Existing data verified

| Table | Rows |
|---|---:|
| accounts_user | 19 |
| workers_workerprofile | 14 |
| core_servicecategory | 18 |
| jobs_booking | 51 |
| jobs_job | 9 |
| payments_payment | 41 |
| reviews_review | 40 |

There are 21 tables in total. The saved `database-preview.html` beside this project folder opens without MySQL and reflects the data inspected during setup. It omits password hashes and session secrets. The live viewer refreshes its snapshot on page reload.

The `.ibd` files under `.local/mysql` are MySQL's internal storage files. View their data through a database connection; they are not text files or SQLite databases.
