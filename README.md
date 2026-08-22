# GigHire

A hiring service where creators post work and suppliers apply for it, built with
Django and Django REST Framework against a written specification.

| | |
|---|---|
| **Tests** | 441 passing, 20 modules |
| **Coverage** | 97% of `apps/` |
| **Runtime** | ~9 seconds |
| **Database** | SQLite (no setup required) |

## Documents

| File | What it is for |
|---|---|
| [DECISIONS.md](DECISIONS.md) | Every ambiguity in the specification, how it was read, and the six questions still open. **Read the four tables at the top first.** |
| [TEST_CASES.md](TEST_CASES.md) | 525 scenarios in plain language, with exact expected results |
| [TEST_PLAN.md](TEST_PLAN.md) | Strategy, risk ranking of the ten rules, exploratory charter, what to build next |

---

## Setup

Requires Python 3.10 or newer.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS or Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API is then at **http://127.0.0.1:8000/api/**.

No configuration is needed. Every setting has a working default; copy
`.env.example` to `.env` only if you want to override something.

## Running the tests

```bash
pytest
```

That runs everything and prints a coverage report — both are configured in
`pyproject.toml`, so there are no flags to remember.

```
441 passed in 9.08s
TOTAL      636     17     72      3    97%
```

### Useful variations

```bash
pytest -x                     # stop at the first failure
pytest --lf                   # re-run only what failed last time
pytest -q --no-cov            # fastest feedback loop
pytest tests/test_reviews.py  # one module
pytest -k "cascade or busy"   # anything matching a word
```

### Selecting tests by what they prove

```bash
pytest -m rule            # 220 tests — the ten specification rules
pytest -m interpretation  #  55 tests — decisions made where the spec was silent
pytest -m smoke           #   1 test  — the whole journey, end to end
```

That split matters for review: `-m rule` asks *"does this match the
specification"*, `-m interpretation` asks *"does this match what we decided and
wrote down"*. Nobody has to take an interpretation on trust as though it were a
requirement.

### Coverage in a browser

```bash
pytest --cov-report=html
start htmlcov/index.html      # or open htmlcov/index.html
```

### Current coverage

| Area | Coverage |
|---|---|
| `apps/hiring/services.py` — the hiring workflow | 97% |
| `apps/gigs/transitions.py` — the gig lifecycle | 98% |
| `apps/hiring/views.py`, `apps/gigs/views.py` | 100% |
| Serializers, filters, validators, enums | 100% |
| **Total** | **97%** |

### What the remaining 3% is

Worth being precise about, because a coverage number on its own says nothing:

| Uncovered | Lines | Why it is uncovered |
|---|---|---|
| `__str__` methods on the models | 6 | Display helpers used by the admin, not the API. Testing them would assert a string format nothing depends on. |
| `IntegrityError` fallbacks in `services.py` | 4 | The branches catching two simultaneous requests that both passed the same check. Unreachable without real concurrency. |
| The exception handler's last-resort branches | 6 | The paths translating a database error or a model-level validation error into a clean response. |

The middle row is left uncovered deliberately rather than faked: a test that mocks
its way into a race-condition branch proves the mock works, not the code. Closing
that gap properly needs PostgreSQL and threads, which is item 2 in
[TEST_PLAN.md](TEST_PLAN.md).

**The third row is good news.** Those branches exist to catch a database
constraint firing or a model validator rejecting something -- cases that should be
impossible if the request-validation layer is doing its job. That they never
execute across 441 tests is evidence the layer above them works. They stay as a
safety net, and they log loudly if they ever run.

---

## The API

All amounts are US dollars. A rate is the amount agreed **for the job**, not per
hour (see B-11 in DECISIONS.md).

### Specified endpoints

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/gigs/` | `status` may be omitted or sent as `open`; nothing else |
| `GET` | `/api/gigs/` | Paginated. Filter by `category`, `status` |
| `GET` `PATCH` `DELETE` | `/api/gigs/{id}/` | Delete is refused once an agreement exists |
| `POST` `GET` | `/api/suppliers/`, `/api/suppliers/{id}/` | |
| `POST` | `/api/gigs/{id}/apply/` | Body: `supplier_id`, `proposed_rate` |
| `GET` | `/api/gigs/{id}/applications/` | |
| `POST` | `/api/applications/{id}/accept/` | Returns **201** with the new agreement |
| `POST` | `/api/applications/{id}/reject/` · `/withdraw/` | Return **200** with the updated application |
| `GET` | `/api/contracts/?supplier_id=&creator_id=` | Both filters optional |
| `POST` | `/api/contracts/{id}/complete/` | |
| `POST` | `/api/contracts/{id}/reviews/` | |

### Added, because the specification cannot be used without them

| Method | Path | Why |
|---|---|---|
| `POST` `GET` `PATCH` | `/api/creators/`, `/api/creators/{id}/` | Every gig needs a creator and the specification lists no way to make one |
| `GET` | `/api/suppliers/` | Symmetry with creators |
| `PATCH` | `/api/suppliers/{id}/` | Rule 5 requires a supplier to go inactive *between* applying and being hired — unreachable otherwise |
| `GET` | `/api/contracts/{id}/reviews/` | An endpoint that writes with no way to read back is unusable |

Full list and reasoning in table 3 of [DECISIONS.md](DECISIONS.md).

### Trying it by hand

The service ships with Django REST Framework's browsable API, so
**http://127.0.0.1:8000/api/** is clickable in a browser. Note that the action
endpoints (`apply`, `accept`, `reject`, `withdraw`, `complete`) accept only
`POST`, so there is no page to browse to — use curl or Postman for those.

```bash
# a creator, a supplier, and a gig
curl -sX POST localhost:8000/api/creators/ -H 'Content-Type: application/json' \
  -d '{"name":"Ada","email":"ada@example.com","channel_name":"AdaCodes"}'

curl -sX POST localhost:8000/api/suppliers/ -H 'Content-Type: application/json' \
  -d '{"name":"Xena","email":"xena@example.com","skills":["editing"],"hourly_rate":"45.00"}'

curl -sX POST localhost:8000/api/gigs/ -H 'Content-Type: application/json' \
  -d '{"creator":1,"title":"Edit episode 12","description":"Cut to ten minutes.","budget":"500.00","category":"editing"}'

# hire, finish, review
curl -sX POST localhost:8000/api/gigs/1/apply/ -H 'Content-Type: application/json' \
  -d '{"supplier_id":1,"proposed_rate":"420.00"}'
curl -sX POST localhost:8000/api/applications/1/accept/
curl -sX POST localhost:8000/api/contracts/1/complete/
curl -sX PATCH localhost:8000/api/gigs/1/ -H 'Content-Type: application/json' \
  -d '{"status":"completed"}'
curl -sX POST localhost:8000/api/contracts/1/reviews/ -H 'Content-Type: application/json' \
  -d '{"reviewer_type":"creator_on_supplier","rating":5,"comment":"Fast and clean."}'
```

For setting up awkward states by hand — flipping a supplier to `inactive`
mid-workflow, or seeing what a cascade did to sibling rows — the Django admin is
faster:

```bash
DJANGO_SUPERUSER_PASSWORD=devpass python manage.py createsuperuser \
  --noinput --username admin --email admin@example.com
```

Then **http://127.0.0.1:8000/admin/**.

---

## How the code is arranged

```
config/settings/{base,dev,test}.py   configuration, read from the environment
apps/common/     shared pieces: money fields, domain errors, pagination
apps/accounts/   Creator, Supplier
apps/gigs/       Gig, and the status transition table
apps/hiring/     Application, Contract, Review, and services.py
tests/           the automated suite
```

Dependencies point one way only — `hiring → gigs → accounts → common` — so any
app can be understood without reading the ones above it.

Business rules live in `apps/hiring/services.py` and
`apps/gigs/transitions.py`, not in views or serializers. Rules 3, 4 and 5 each
span three models and need a transaction, which is more than a serializer should
know about. Views parse a request, call one service, and return a response.

Refusals are raised as domain errors and translated to HTTP in exactly one place
(`apps/common/exceptions.py`), so the status-code mapping cannot drift between
endpoints. Every refusal carries a short stable `code` alongside its message:

```json
{"detail": "This application is accepted and can no longer be modified.",
 "code": "application_not_pending"}
```

**400 means the request is wrong on its own terms** — a rate of -5 would never
have worked. **409 means the request is fine but the situation has moved on** —
applying to a gig that has since been filled. A client needs to react
differently to each, so they are kept apart.

---

## Known gaps

Six questions remain open, listed in full in table 1 of
[DECISIONS.md](DECISIONS.md). The two that matter most:

- **There is no sign-in.** The specification describes actions in terms of who
  performs them but never says how the service identifies a caller. As a result
  anyone can hire, reject, withdraw or review on anyone's behalf, and the
  unfiltered agreement list exposes every rate ever agreed.

- **Work that fails cannot be recorded as failed.** `terminated` is a listed
  agreement state that no endpoint can reach. A supplier who takes a job and
  disappears leaves the gig stuck in progress for ever and permanently occupies
  one of their three slots.

Neither is a build error. Both are gaps in the specification, reported rather
than silently patched.
