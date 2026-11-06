# GovNexus 2.0 — Local Demonstration Guide

GovNexus is a FastAPI + MySQL backend with an HTML/CSS/vanilla JavaScript frontend. It provides citizen service discovery, grounded assistant guidance, profile/preferences, and an authenticated knowledge-management workflow.

## Prerequisites

- Windows PowerShell
- Python 3.11+
- MySQL 8.x with the configured GovNexus database
- The repository virtual environment at `.venv`
- Node.js only for the JavaScript syntax check

Provider credentials are optional for the local UI and deterministic tests. Groq is the primary assistant, Gemini is the fallback, and Prism speech uses the existing voice endpoints. Each provider needs its own credential and network access.

## Environment

Create `.env` from `.env.example` if needed, then set the local MySQL values and a local `JWT_SECRET_KEY`. Keep `SOURCE_ADMIN_API_KEY`, Gemini, Pinecone, and Gnani credentials server-side; never place them in frontend files or browser storage.

The application expects `DEBUG` to be Boolean. If the current PowerShell session contains an older value such as `DEBUG=release`, use the process-local override shown below rather than editing a secret-bearing environment file during a demonstration.

## Start the application

From the repository root, use two PowerShell windows.

Backend:

```powershell
Set-Location A:\schemesathi
$env:DEBUG = "true"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
Set-Location A:\schemesathi\frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open:

- Citizen portal: http://127.0.0.1:5500/
- Citizen sign-in: http://127.0.0.1:5500/pages/login.html
- Admin sign-in: http://127.0.0.1:5500/pages/admin/login.html
- Backend health: http://127.0.0.1:8000/health
- Database health: http://127.0.0.1:8000/health/database
- API documentation: http://127.0.0.1:8000/docs

Verify health before demonstrating. Application startup does not run migrations. Apply reviewed migrations separately with the existing Alembic workflow when required.

## Accounts

No passwords or tokens are stored in this guide. Use an existing local account, or create local accounts through the existing scripts:

```powershell
Set-Location A:\schemesathi
$env:DEBUG = "true"
.\.venv\Scripts\python.exe -m backend.scripts.create_admin
```

Citizen accounts can be created from the citizen sign-in page. Do not use production credentials in a demonstration.

## Demonstration sequence (10–15 minutes)

1. Open the citizen portal and point out the search, category discovery, assistant entry point, and source-aware disclaimer.
2. Open **Explore services**. The current database may show categories but no published services; demonstrate the honest empty catalogue state rather than inventing records.
3. Open the citizen sign-in page. Demonstrate registration validation or sign in with an authorized local account.
4. Open **Profile** and **Preferences**. Change language, accessibility settings, and location fields where master data exists. Save and reload to show persistence.
5. Open **AI assistant**. Ask a general question, show the evidence-unavailable or grounded response state, and explain that unverified facts are not exposed as official guidance.
6. If Gemini credentials are configured, demonstrate a grounded answer and its source references. If not, use the visible text fallback and state the limitation.
7. If Prism credentials and microphone access are configured, demonstrate speech-to-text and text-to-speech. Otherwise use the text composer. Browser speech is not a fallback. Do not claim a live voice call when the credential is missing.
8. Open the admin sign-in page and dashboard. Show live counts from the authenticated API and the zero published-service state if applicable.
9. Open **Sources** and **Ingestion**. Inspect source metadata and existing snapshots. Do not activate unverified sources or start network ingestion during the demonstration.
10. Open **Fact verification**. Inspect the UIDAI evidence quotations, offsets, confidence, and review tasks. Demonstrate the review controls without approving or rejecting facts unless an authorized reviewer explicitly chooses to do so.
11. Open **Service catalogue**. Show draft services, verified-fact linking rules, and publication safeguards. Explain that only verified facts can be linked and published versions are immutable.
12. Finish by signing out of both citizen and admin sessions and confirm protected pages require authentication again.

## Knowledge workflow

The controlled workflow is:

```text
Registered source → selected snapshot → extracted facts → open review task
→ human verification → service-fact link → draft service version
→ publication review → published citizen catalogue
```

Extraction creates `pending_review` facts only. It does not verify, link, publish, or index them.

## Automated checks

Use the project virtual environment:

```powershell
Set-Location A:\schemesathi
$env:DEBUG = "true"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend
$JsFiles = Get-ChildItem .\frontend -Recurse -File -Filter *.js
foreach ($File in $JsFiles) { node --check $File.FullName; if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax failed: $($File.FullName)" } }
git diff --check
```

The test suite uses isolated databases and mocked provider behavior. It does not prove that live Gemini, Pinecone, or Gnani credentials are configured.

## Live integrations and limitations

- The MySQL-backed API and local frontend are demonstrable when the configured database is available.
- The published citizen catalogue is data-dependent. Unpublished or unverified records must remain absent from it.
- Gemini answers require `GEMINI_API_KEY` and a reachable provider.
- Pinecone retrieval requires its configured index credentials; keyword retrieval may still be available.
- Gnani STT/TTS requires configured credentials, network access, and microphone permission.
- Browser automation is not included in the repository. Use manual browser DevTools or provision Playwright for console, network, and responsive checks.
- Interface translations exist for selected strings; missing translations fall back to English. Government facts are not machine-translated by the frontend.
- Password recovery is not implemented in the current API workflow.
- Application records are citizen-recorded tracking notes and are not submissions to government portals.

## Troubleshooting

- **Settings rejects `DEBUG=release`:** run `$env:DEBUG="true"` in the process that starts Uvicorn or tests.
- **PyMuPDF import failure:** use `.venv\Scripts\python.exe`; the project dependency is declared in `requirements.txt`.
- **Database health fails:** confirm MySQL is running and the five `MYSQL_*` values match the local database.
- **CORS error:** serve the frontend at `http://127.0.0.1:5500` or `http://localhost:5500` and use the matching local API host.
- **Empty catalogue:** this is expected until facts are verified, linked to a service version, and published through the admin workflow.
- **Voice unavailable:** use text input and state that Prism is not configured. Do not use browser speech as a substitute.
