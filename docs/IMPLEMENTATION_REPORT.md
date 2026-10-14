# Labour Connect — implementation report

Delivered 6 October 2026 as a working Django 5.2/MySQL application with customer, approved-worker and administrator workspaces. The complete electrician case study was exercised in a real Chrome browser, from customer registration to payment, review and updated worker earnings.

## Completed modules

| Module | Implemented behavior |
|---|---|
| Authentication | Customer/worker registration, role redirects, profile/photo editing, logout, password change and token-based reset, account activation and login throttling. |
| Worker verification | Pending registration, approval/rejection with reason and audit history, private document uploads/downloads, approval checks on every protected worker route. |
| Discovery | Approved, active professional profiles; category, keyword, skill, designation, location, experience, rate, rating and availability filters; pagination and optional nearest sorting. |
| Bookings | Direct worker requests; accept/reject, start, complete and eligible customer cancellation; participant-scoped details and histories. |
| Open jobs | Customer posting, available-job browsing, atomic worker assignment, status progression, cancellations and notifications. Concurrent acceptance was tested against MySQL. |
| Payments | One payment per completed service; cash/UPI pending receipt confirmation, paid/failed/refunded states, receipts and paid earnings. Online payment is an explicitly labelled simulation. |
| Reviews | Completed-service eligibility, one review per service, 1–5 ratings, public feedback and database-derived averages. |
| Notifications | Recipient-scoped notifications, unread badges, individual/all read actions through AJAX, and optional email after commit. |
| Complaints | User submission with only their own service references; administrator response/status management and owner notifications. |
| Administration | Custom overview, user activation, worker verification, category management, bookings/jobs/payments/reviews, complaints, announcements by audience and database-driven analytics. |
| Interface | Custom responsive theme, original SVG artwork, local Bootstrap/icons/Chart.js, dashboards, forms, confirmations, loading states, empty/error states, reduced-motion support and mobile navigation. |
| Location | Manual address and browser geolocation without a key; configurable Google Maps and Places (New) integration. |

## Important files

- `config/settings.py`, `config/urls.py`: environment configuration, MySQL, security and routing.
- `accounts/models.py`, `accounts/forms.py`, `accounts/decorators.py`: custom user, registration validation, role and approval enforcement.
- `jobs/services.py`: locked assignment and validated booking/job transitions.
- `payments/services.py` (including `DemoPaymentProvider`), `reviews/services.py`: eligibility, unique records, payment simulation and review rules.
- `workers/search.py`, `workers/storage.py`, `core/validators.py`: professional search, private document storage and upload validation.
- `adminpanel/views.py`, `adminpanel/services.py`, `core/utils.py`: custom administration, moderation and local-month aggregation.
- `templates/`, `static/css/app.css`, `static/js/`, `static/vendor/`: reusable pages, custom theme, interactions and bundled frontend libraries.
- App `migrations/` directories: all required schema migrations.
- `core/management/commands/seed_categories.py`, `seed_demo.py`: idempotent category/demo setup with random passwords.
- `core/tests/`: 57 regression tests.
- `Start-Demo.ps1`, `scripts/demo_server.py`: isolated Windows MySQL/Django launcher.
- `README.md`, `.env.example`, `requirements.txt`, `requirements.lock.txt`: setup, configuration and dependencies.

## Database models

| Model | Purpose |
|---|---|
| `User` | Authentication, role, contact/address, coordinates and photo. Customer details live here. |
| `ServiceCategory` | Discoverable, administratively managed service types. |
| `WorkerProfile` | Professional details, category, skills, rate, availability and verification status. |
| `WorkerDocument` | Private identity/qualification document metadata. |
| `VerificationEvent` | Administrator decision history and reason. |
| `Booking` | Direct customer-to-worker service request and lifecycle. |
| `Job` | Open service request and optional assigned worker. |
| `Payment` | Unique booking/job payment, method, amount and receipt status. |
| `Review` | Unique completed-service rating and feedback. |
| `Notification` | Recipient, type, message, reference and read state. |
| `Complaint` | User support request, optional service, response and resolution status. |
| `Announcement` | Administrator message and role audience. |

Relationships and transaction boundaries are described in [ARCHITECTURE.md](ARCHITECTURE.md). Payments/reviews require exactly one booking or job through database constraints. Ratings and earnings are calculated from related records.

## Important URLs

| URL | Purpose |
|---|---|
| `/`, `/services/`, `/workers/`, `/workers/<id>/` | Marketplace, categories, search and professional profiles. |
| `/accounts/register/`, `/accounts/login/` | Registration and login. |
| `/accounts/password/reset/`, `/accounts/password/change/` | Password management. |
| `/customer/dashboard/`, `/customer/jobs/new/`, `/customer/book/<worker-id>/` | Customer workflow. |
| `/worker/dashboard/`, `/worker/jobs/available/`, `/worker/documents/` | Approved worker workflow. |
| `/work/job/<id>/`, `/work/booking/<id>/` | Authorized service details/actions. |
| `/payments/`, `/reviews/`, `/notifications/`, `/complaints/` | Records, feedback and support. |
| `/documents/<id>/download/` | Authenticated private download. |
| `/adminpanel/`, `/adminpanel/verifications/`, `/adminpanel/analytics/` | Custom administrator workspace. |

## Security implemented and tested

Passwords use Django hashing; mutations require CSRF and POST; role and object ownership checks run on the server. Registration cannot create administrators, and profile editing cannot change roles. Pending/rejected workers receive no logged-in session. Existing sessions lose protected access after deactivation or revoked verification. Uploaded images/documents have extension, size and content checks; private documents have no public storage URL. Transactions and database constraints prevent racing job assignments and duplicate/ineligible payments or reviews. Environment secrets and generated credentials are excluded from the source archive.

## Demo accounts and startup

The seed creates `demo_admin`, `demo_customer1`–`demo_customer3`, and `demo_worker1`–`demo_worker13`. Workers 1–10 start approved, 11–12 pending, and 13 rejected. Worker 1 is an approved electrician. Generated random passwords are in the prepared workspace's `demo_accounts.txt`; a fresh installation generates its own credentials. All sample people, reviews, identity documents and payment records are fictional.

The prepared workspace already has its virtual environment and demo database. From the project directory:

```powershell
.\Start-Demo.ps1
```

The terminal prints the URL. To verify startup and stop automatically:

```powershell
.\Start-Demo.ps1 -CheckStartup
```

For a fresh archive, first run `python -m venv .venv` and `.venv\Scripts\python.exe -m pip install -r requirements.lock.txt`. MySQL Server must be installed. The launcher creates its own `.local/mysql/` instance on port 3307. With a separately configured MySQL database, use `python manage.py migrate`, `python manage.py seed_demo`, then `python manage.py runserver`. [README.md](../README.md) includes both complete setup paths.

## Manual configuration and external services

The demo launcher generates `SECRET_KEY` and database credentials. For an existing MySQL server, configure the five `DB_*` values, a unique `SECRET_KEY`, `ALLOWED_HOSTS` and development/HTTPS settings in `.env`.

Supply `GOOGLE_MAPS_API_KEY` for live Google Maps/Places and configure SMTP values for real email delivery. No external key is needed for manual address input, browser geolocation, console password reset or database notifications. The Google adapter is implemented but was not tested against a live billing-enabled Google account. Actual SMTP delivery was not tested; reset and post-commit notification email were tested using Django's in-memory backend. Online payments simulate records and transfer no money.

## Verification result

**57 Django tests passed against MySQL 8.4.9 in 107.710 seconds. 64 real-browser checks passed, with no JavaScript errors or missing static assets.** Six main pages were checked at 1920, 1366, 1024, 768, 430 and 390 pixels. There are 39 actual application screenshots. The Windows launcher passed fresh-database initialization, migrations, seeding, system checks and an HTTP 200 startup probe. See [VERIFICATION.md](VERIFICATION.md) for evidence and coverage.
