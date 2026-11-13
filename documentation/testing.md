# Django test suite

This suite targets `Scilly-guy/carshare` main (`19c5fbd` as the starting point).
It uses Django's built-in runner, `SimpleTestCase`, `TestCase` and
`TransactionTestCase`. No pytest dependency is required. Production settings and
behaviour are unchanged, and local debug payment/email features are not included.

## Running locally

Use Python 3.12, the locked Poetry dependencies, the customised crispy-tailwind
package (`make setup-crispy-tailwind`), and PostgreSQL. The application database
user must be able to create a separate test database and install `btree_gist`.
The existing migrations install that extension. The PostgreSQL superuser in the
CI service has the necessary privileges. Do not run with production credentials.

```sh
poetry install --no-root
make setup-crispy-tailwind
make test
```

Equivalent command:

```sh
poetry run python manage.py test --settings=carshare.test_settings
```

The standard Django settings environment variables configure PostgreSQL:
`POSTGRES_HOST`, `POSTGRES_PORT` (local default 5433), `POSTGRES_DB`,
`POSTGRES_USER` and `POSTGRES_PASSWORD`. Django creates and destroys its own
`test_...` database; it does not load sample data into the application database.
SQLite is not a substitute for PostgreSQL range constraints and locking.

Run selected tests or retain the test database between local runs:

```sh
make test TEST_ARGS="bookings billing --keepdb --verbosity 2"
```

Test settings use fast password hashing, an in-memory email outbox and eager
Celery execution. The runner rejects unexpected Requests HTTP and SMTP calls;
Stripe responses are patched at the SDK boundary. A Redis/RabbitMQ broker,
Stripe account, SMS gateway or mail server is not needed. This guard is specific
to those transports, not a general network sandbox. Always use the documented
test settings to enable it. No real card, identity document or customer data is
used. Builders create driver subclasses through the ORM, preserving polymorphic
content types. Time-sensitive tests freeze Django's clock, with dates chosen
explicitly rather than relative to the execution date.

## What is covered

| Area | Assertions |
| --- | --- |
| Pricing | Independent GBP examples, hourly rounding, daily caps, tariff cutoff, booking-ID and special-account exceptions, operator exemption. |
| Billing | Account validity, setup/callback ownership, ordinary/monthly invoice selection, exact pence/customer/currency, zero-cost bookings, provider failures and repeat completed runs. |
| Reservations | Persisted times and turnaround buffer, real overlap constraint, exact buffer boundary, cancellation release, minimum duration, past-start/end-horizon rejection, allowed and foreign-account confirmation. |
| Concurrency | Two separate PostgreSQL connections attempt the same interval; only one row commits. A loser can receive an exclusion violation or PostgreSQL deadlock abort. This is a database-invariant test, not a claim that HTTP endpoints provide deadlock retries. |
| Vehicle state | Web unlock/late lock/task progression, consistent booking-box association, preserved first start, rejected user access, normal RFID unlock/lock and unrelated-card rejection. |
| Permissions | Direct requests to every current backoffice route as anonymous, ordinary, staff-only and superuser-only users; operator read access; booking and payment ownership; confirmation CSRF. |
| Users/drivers | Booking versus driving permissions, member privileges, verified mobile promotion, wrong codes, profile expiry, licence/annual approval bounds and missing review evidence. |
| Media | Real protected URL routes, owner and privileged access, denial for unrelated/anonymous users, internal redirect target and device authentication for firmware. This does not validate a deployed Nginx configuration. |
| Hardware | Authentication failures, telemetry attribution and retention boundary; no physical hardware is contacted. |
| Public pages | Exact redirect targets without fetching external sites. |

The builders in `test_support/factories.py` make only the necessary records;
there is no autouse fixture forcing pure pricing tests to create database rows.
Subtests exercise boundary/role matrices; the runner's test count therefore
understates the number of individual scenarios.

## Explicit known gaps

Two tests use `unittest.expectedFailure` to document existing main-branch defects:

- Disabled RFID cards are not rejected by the card-touch handler.
- Retrying billing after invoice creation succeeds but item creation fails can
  create a second invoice instead of resuming the first.

These assertions express the desired behaviour. They must not be weakened to
endorse the defect. An unexpected success fails the suite, prompting removal of
the marker when production code is fixed. Review expected-failure output on every
release. The test-suite branch does not fix these production defects.

Remaining work includes complete signup/recovery and document-upload journeys,
malformed device payloads, safe HTTP methods for existing GET mutations, broader
concurrent edit/access/billing races, Stripe failure reconciliation, invoice tax
semantics, browser accessibility/layout and deployment checks. Existing monthly
billing uses a naive cutoff; timezone semantics still need dedicated tests and a
production fix. This is a substantial initial suite, not proof that the whole
application is safe or a replacement for physical vehicle integration testing.

## CI and maintenance

`.github/workflows/tests.yml` installs the existing lock file and template
dependency, checks Black and migration drift, then runs the suite against a
PostgreSQL 14 service on every pull request and pushes to main. It does not build
or publish an image. The workflow itself must be confirmed on GitHub; running
locally does not execute GitHub Actions.

Add a failing regression when changing business behaviour, then verify the
relevant successful, unauthorised, boundary and failure/retry cases. Keep pure
rules fast, integration checks real, and external services mocked. Track critical
workflow coverage rather than aiming for a line-coverage percentage alone.
