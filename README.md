# GovNexus 2.0

GovNexus is a citizen assistance platform for discovering government services and asking questions grounded in reviewed evidence. The frontend is HTML/CSS/Vanilla JavaScript; the backend is FastAPI, SQLAlchemy and Alembic.

## Requirements

- Windows PowerShell
- Python 3.11 or newer
- MySQL 8.x, with a local database and credentials
- Node.js for the optional JavaScript syntax check
- Provider credentials only for live Groq, Gemini, Pinecone, or Prism voice functionality

## Python environment and configuration

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

If PowerShell blocks activation, allow it for the current shell only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Set `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, and `MYSQL_DATABASE` to match your local MySQL setup. Set `JWT_SECRET_KEY` to a new random value; generate one locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit `.env` or paste secrets into source files, browser storage, or support logs. `.env.example` contains variable names and safe placeholders only. `SOURCE_ADMIN_API_KEY` is a server-side credential; do not put it in frontend code. Leave provider credentials blank unless you explicitly intend to perform live provider tests.

### Environment variables

| Variables | Purpose |
|---|---|
| `APP_NAME`, `APP_VERSION`, `DEBUG`, `API_V1_PREFIX` | Application metadata and local debug mode |
| `MYSQL_*` | MySQL connection settings; all five values are used by the SQLAlchemy engine |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT signing and citizen token lifetime; admin tokens currently expire after eight hours |
| `SOURCE_ADMIN_API_KEY` | Server-side authentication for source registration and ingestion endpoints |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL`, `GROQ_TIMEOUT_SECONDS` | Primary assistant. Default model `openai/gpt-oss-20b` is a Groq production model. The server checks that ID against Groq's model list before calling it. |
| `GEMINI_*` | Fallback generation when Groq is unavailable, plus embeddings |
| `PINECONE_*`, `RAG_*` | Optional Pinecone index connection and retrieval thresholds |
| `GNANI_*` | Optional Prism speech-to-text and text-to-speech. The existing Vachana Prisma endpoints and model IDs are preserved. Browser speech is not used as a fallback. |
| `REDIS_URL` | Redis connection setting for queue-worker deployments |

## MySQL database

Create the database if it does not already exist. This does not drop or reset existing data:

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS schemesathi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Use the database name and an account with the required schema privileges in `.env`. Verify that MySQL is running and that the configured account can connect before continuing.

## Inspect and apply migrations manually

The migration history is linear and currently ends at `d73e6a10c24b`. Inspect the current database revision and the full history:

```powershell
python -m alembic current
python -m alembic history --verbose
python -m alembic heads
```

Render the SQL for review without applying it:

```powershell
python -m alembic upgrade head --sql | Out-File -Encoding utf8 .\migration-review.sql
Get-Content .\migration-review.sql
```

Before applying, make and verify a database backup. The command prompts for the MySQL password:

```powershell
$DbUser = Read-Host "MySQL backup user"
$DbName = Read-Host "MySQL database name"
mysqldump --single-transaction --routines --triggers -u $DbUser -p --result-file=.\schemesathi-before-migrations.sql $DbName
Get-Item .\schemesathi-before-migrations.sql | Select-Object Name, Length, LastWriteTime
```

Only after reviewing the SQL and confirming the backup is usable, apply migrations explicitly:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Application startup does not apply migrations. Do not run `downgrade` against a database containing data without a reviewed recovery plan: `b91c83b4c9da` drops duplicate-candidate data and `sources.content_changed_at`; `c84a1fe29d72` drops citizen application/history tables and the citizen token-version column; `d73e6a10c24b` drops the admin token-version column.

## Optional reference data and administrator

The migration creates schema, not catalogue content. To insert/update the repository's built-in languages and categories:

```powershell
python -m backend.scripts.seed_reference_data
```

This script activates and updates the built-in languages but leaves other language records unchanged. Review it before using it on a database with custom language configuration. An optional initial catalogue script creates unpublished service records; it does not create verified facts or publish services:

```powershell
python -m backend.scripts.seed_initial_catalogue
```

Populate the English labels for India's 28 states and 8 Union Territories, and enable the 22 Eighth Schedule languages:

```powershell
python -m backend.scripts.seed_indian_locations
```

The location seed is idempotent and only inserts or updates top-level master-data rows. These scripts add reference data, not government schemes, verified facts, or translations.

Create an administrator interactively; the script prompts for identity, role, and password and does not print the password:

```powershell
python -m backend.scripts.create_admin
```

Only administrators with appropriate access to the configured backend should run administration scripts.

## Controlled official-source ingestion

The batch importer accepts JSON or CSV manifests of HTTPS `.gov.in` and `.nic.in` URLs (maximum 100 entries and 1 MB). Each entry requires `url` and `publisher_name`; optional fields are `source_type` (`government_portal` or `official_website`), `language_code`, and a top-level `jurisdiction_code` such as `IN-MH`. It validates public URL safety and registered language/location codes. It does not fetch pages. Newly registered records remain inactive and unverified.

First validate a manifest without changing the database:

```powershell
python -m backend.scripts.import_official_source_manifest --manifest .\official-sources.json
```

After reviewing every URL and confirming that its domain and document are official and appropriate, explicitly register the entries:

```powershell
python -m backend.scripts.import_official_source_manifest --manifest .\official-sources.json --apply
```

An authorized operator must then review each source's authority and activate it through the existing source-administration API. Never expose `SOURCE_ADMIN_API_KEY` in browser code or page storage. Fetch only individually selected, active, manually reviewed source UUIDs; this command requires explicit network-fetch confirmation:

```powershell
python -m backend.scripts.ingest_selected_sources --source-id <SOURCE_UUID> --confirm-network-fetch
```

Review the resulting snapshots before running `python -m backend.scripts.extract_source_facts`. Extraction creates pending-review facts only; it does not verify facts, link them to a service version, publish a service, or index evidence. Administrators must review and verify facts, link them to the appropriate service version, publish through the existing workflow, and explicitly run indexing. Do not treat extraction as approval or publication.

## Start the backend

In a PowerShell window at the repository root with the virtual environment active:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/health/database`. Interactive API documentation is at `http://127.0.0.1:8000/docs`; the OpenAPI JSON is at `http://127.0.0.1:8000/openapi.json`.

## Start the frontend

In a second PowerShell window:

```powershell
Set-Location .\frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open `http://127.0.0.1:5500/`. Use the same host spelling for the frontend and API (`127.0.0.1` with `127.0.0.1`, or `localhost` with `localhost`); the backend CORS allowlist is limited to those hosts on port 5500. Keep `DEBUG=true` only for local development. Production requires HTTPS and secure cookies.

## Automated checks

From the repository root:

```powershell
python -m pytest -q
python -m compileall -q backend
$JsFiles = Get-ChildItem .\frontend -Recurse -File -Filter *.js
foreach ($File in $JsFiles) { node --check $File.FullName; if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax failed: $($File.FullName)" } }
git diff --check
```

The test suite uses mocked provider responses; it must not make live paid Gemini, Pinecone, or Gnani requests. No test implies that a live provider is configured or available.

## Manual testing checklist

Use a local development database and non-production credentials.

1. **Database:** Confirm MySQL is running; inspect `.env` locally; run the read-only migration inspection commands above. Back up the database, then apply `python -m alembic upgrade head` manually and confirm `python -m alembic current` reports `d73e6a10c24b (head)`.
2. **Backend and frontend:** Start both servers using the commands above. Check `/health`, `/health/database`, `/docs`, and the frontend home page.
3. **Citizen registration and login:** Register using an active language, sign out, then log in. In browser DevTools, confirm the citizen session cookie is HttpOnly and there is no JWT in local/session storage. Check invalid credentials and session expiry.
4. **Dashboard, profile and preferences:** Confirm account data loads; update the display name and language; save notification and device-local accessibility preferences; reload and verify persistence.
5. **Catalogue and service details:** Search and paginate published catalogue entries. Open details, check that unavailable information is identified as unavailable, and verify that only published services/evidence are shown. An empty catalogue is expected until appropriate services have been reviewed and published.
6. **Saved services and tracking:** Save and remove a published service. Add and edit an application tracking record. Confirm the interface labels it citizen-recorded and does not suggest government submission or live portal status.
7. **Chat and conversation history (no voice-provider credentials required):** Ask an intentionally unsupported question to verify the evidence-unavailable response without requiring Gemini. If eligible evidence is found but Gemini is not configured, a grounded answer request returns an unavailable error instead. Inspect citations; sign in, start a conversation, reload, and open it from history. Do not interpret a response without evidence as official guidance.
8. **Admin sign-in and dashboard:** Create an admin with the interactive script, sign in at `/pages/admin/login.html`, check dashboard metrics, then sign out. Verify that a copied pre-logout JWT, if inspected for this security test, no longer authorizes admin endpoints.
9. **Service and fact workflow:** In the admin service page, create a draft service/version, add a translation, link only a verified fact, and publish only when the backend allows it. Review facts with a reasoned decision; exercise explicit indexing only with valid backend index configuration. Do not approve facts merely to complete the test.
10. **Source workflow:** Seed locations/languages if needed, dry-run an official source manifest, and inspect its entries before applying. Source authority review/activation remains an authorized server-side action; ingestion fetches only selected, reviewed records after the explicit confirmation flag. Check each extracted fact remains pending until human verification. Do not enter the source key into DevTools or page storage.
11. **Voice (requires live Gnani credentials and may incur provider charges):** Only if explicitly authorized and configured, test microphone transcription and speech synthesis in a secure context/localhost. Confirm transcription follows the grounded chat path and audio/provider errors are surfaced. Automated tests are mocked and do not perform these calls.
12. **Logout:** Sign out separately from citizen and admin pages. Confirm protected routes require authentication again and that prior sessions are rejected.

## Current limitations

- No application startup migration is performed; database backup and migration application are operator-controlled.
- No scheme records were imported as part of this work. The current catalogue remains empty until an operator collects official sources, verifies their facts, links them to service versions, and publishes them.
- Navigation and general UI copy are not fully translated. AI language selection is available, but a response is not a human-verified translation unless explicitly reviewed; missing translated service content falls back to available source-language material.
- Gnani voice support is limited to provider-supported languages; browser read-aloud is a local fallback and is not a verified translation.
- Source manifests capture URL, publisher, source type, language, and jurisdiction. The current ingestion model does not fully track source document publication dates or explicit document versions.
- Password recovery is not available in the current frontend workflow.
- Catalogue contents and translations depend on reviewed, published backend data. Seeded service records are unpublished.
- Gemini, Pinecone, and Gnani live behavior requires configured credentials and is not established by the automated test suite.
- Admin logout revokes all outstanding admin JWTs for that administrator by incrementing a token version; citizen logout likewise invalidates that citizen's existing tokens.
- The frontend makes requests to the configured local API URL by default; configure the existing `schemesathi-api-base` meta setting if your authorized local API runs elsewhere.
