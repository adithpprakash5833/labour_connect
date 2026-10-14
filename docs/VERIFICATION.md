# Recorded verification — 6 October 2026

## Environment

- Windows, Python 3.12, Django 5.2.18, mysqlclient 2.3.0, MySQL Server 8.4.9.
- MySQL was used for migrations, regression tests, real concurrent transactions and browser workflows. No SQLite fallback was used.
- Playwright controlled installed Google Chrome in headless mode.
- Local frontend dependencies: Bootstrap 5.3.8, Bootstrap Icons 1.13.1, Chart.js 4.5.1.

## Django regression suite

```text
python manage.py test core.tests --noinput
Ran 57 tests in 107.710s
OK
System check identified no issues (0 silenced).
```

The disposable MySQL test database was created and destroyed successfully. No tests were skipped. The concurrent-acceptance test used two threads and independent database connections with a barrier: one worker won the locked assignment, the other received the already-assigned error, and the database retained one assignment.

Coverage includes registration and validation, administrator-role protection, pending/rejected-worker login and direct URL gates, approval/rejection, revoked sessions, CSRF and POST logout, password reset/change, post-commit email, login throttling, full-name/category/filter/distance search, upload validation and document privacy, categories and activation, announcements, template compilation and page rendering, ownership checks, bookings/jobs and invalid transitions, cancellations, inactive-category assignment protection, payment eligibility/uniqueness/confirmation/refund/earnings, review eligibility/range/uniqueness/average, notification ownership, complaint responses and correct local-month chart aggregation without MySQL named timezone tables.

The raw final output is in [tests-output.txt](tests-output.txt).

## Browser verification

**64 checks passed; zero collected JavaScript errors or missing static assets.** The full checklist is in [browser-results.json](browser-results.json).

Six main screens were exercised at every required width:

| Screen | 1920 | 1366 | 1024 | 768 | 430 | 390 |
|---|---|---|---|---|---|---|
| Homepage | Pass | Pass | Pass | Pass | Pass | Pass |
| Find workers | Pass | Pass | Pass | Pass | Pass | Pass |
| Registration | Pass | Pass | Pass | Pass | Pass | Pass |
| Customer dashboard | Pass | Pass | Pass | Pass | Pass | Pass |
| Worker dashboard | Pass | Pass | Pass | Pass | Pass | Pass |
| Administrator dashboard | Pass | Pass | Pass | Pass | Pass | Pass |

Page-width overflow checks passed at all sizes. Tables use intentional internal horizontal scrolling on small screens. Mobile navigation and dashboard sidebar opening were checked. Screenshot inspection confirmed layout and content, and images were loaded before capture.

The real browser completed customer registration and geolocation, electrician search and profile viewing, requested booking, worker acceptance/start/completion, labelled demo payment, customer review, updated paid earnings and administrator transaction inspection. It also completed an open job, customer cash recording and worker receipt confirmation, complaint submission and administrator resolution visible to the owner, AJAX mark-all-read, and blocked pending-worker login followed by administrator approval and successful login. A customer was denied a worker's private identity document.

There are **39 screenshots** under `screenshots/`: the 36 screen/width combinations above plus a payment receipt, verification page and mobile professional profile. Representative images:

- [Homepage, desktop](screenshots/home-1366.png)
- [Homepage, mobile](screenshots/home-390.png)
- [Customer dashboard, mobile](screenshots/customer-dashboard-390.png)
- [Worker dashboard](screenshots/worker-dashboard-1366.png)
- [Administrator dashboard](screenshots/admin-dashboard-1366.png)
- [Payment receipt](screenshots/payment-receipt-1366.png)

Screenshots show a fictional demo database after some workflows were exercised; a fresh seed may have different totals and dates.

## Build and startup checks

- All shipped migrations applied successfully to a fresh MySQL database.
- `python manage.py check --database default`: no issues.
- `python manage.py makemigrations --check --dry-run`: no model changes detected.
- `python manage.py collectstatic --noinput`: local static assets collected successfully.
- Python compilation and Ruff checks for syntax, imports and unused names passed (`E4,E7,E9,F,I`). JavaScript syntax checks passed.
- `Start-Demo.ps1 -CheckStartup`: isolated fresh MySQL initialization, migration, seed, system check and homepage HTTP 200 passed. Both spawned servers were stopped at completion.

## Verification limits

Live Google Maps/Places needs the user's restricted key and billing-enabled project; the live Google service was not called. Manual address fallback and browser geolocation were tested. Actual SMTP delivery needs the user's provider configuration; token reset and post-commit email behavior were tested using Django's in-memory email backend. Online payment is a tested academic simulator, not a real gateway. This delivery was verified as a local development/demo application; a public production deployment was not performed.
