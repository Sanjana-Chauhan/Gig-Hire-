# GigHire

A hiring service where creators post work and suppliers apply for it, built with
Django and Django REST Framework against a written specification.

| | |
|---|---|
| **Tests** | 441 passing, 0 skipped, 20 modules |
| **Coverage** | 97% of `apps/` (636 statements, 17 uncovered) |
| **Runtime** | ~15 seconds, no setup |
| **Database** | SQLite, created and destroyed per test run |
| **Endpoints** | 15 from the specification, 7 added out of necessity |

### Where to start

| If you want to… | Read |
|---|---|
| See the requirements traced to code and tests | [§2 below](#2-what-the-specification-asked-for) |
| Run the suite | [§4 below](#4-running-the-tests) |
| Understand a failure | [§5 below](#5-analysing-the-results) |
| Know what a file does | [§7 below](#7-what-each-file-is-for) |
| See where the spec was ambiguous | [DECISIONS.md](DECISIONS.md) — the four tables at the top |
| See the test strategy and risk ranking | [TEST_PLAN.md](TEST_PLAN.md) |
| Read the scenarios in plain language | [TEST_CASES.md](TEST_CASES.md) |

---

## 1. Contents

1. [Contents](#1-contents)
2. [What the specification asked for](#2-what-the-specification-asked-for)
3. [Setup](#3-setup)
4. [Running the tests](#4-running-the-tests)
5. [Analysing the results](#5-analysing-the-results)
6. [Coverage, in detail](#6-coverage-in-detail)
7. [What each file is for](#7-what-each-file-is-for)
8. [Trying the API by hand](#8-trying-the-api-by-hand)
9. [How the code is arranged](#9-how-the-code-is-arranged)
10. [Known gaps](#10-known-gaps)

---

## 2. What the specification asked for

Three things: six models, fifteen endpoints, ten business rules. Each is traced
to the code that implements it and the tests that prove it.

### 2.1 The six models

Every model also carries `created_at` and `updated_at`. The specification asks
for them on applications only; having them everywhere costs two columns and
makes history reconstructable.

| Model | Fields | Represents |
|---|---|---|
| **Creator** | `name`, `email` (unique), `channel_name` | Someone who posts work |
| **Supplier** | `name`, `email` (unique), `skills` (list of text), `hourly_rate`, `availability_status` | Someone who does work |
| **Gig** | `creator` →, `title`, `description`, `budget`, `category`, `status` | A job posting |
| **Application** | `gig` →, `supplier` →, `proposed_rate`, `status` | A bid on a posting |
| **Contract** | `gig` →, `supplier` →, `agreed_rate`, `status` | An agreement to do the work |
| **Review** | `contract` →, `reviewer_type`, `rating` (1–5), `comment` | Feedback after the work |

The allowed values for every choice field:

| Field | Values |
|---|---|
| `Supplier.availability_status` | `available` · `busy` · `inactive` — `busy` is set by the service, never by a client ([I3, I4](DECISIONS.md)) |
| `Gig.status` | `open` · `in_progress` · `completed` · `cancelled` — only `open` may be supplied on create ([S5](DECISIONS.md)) |
| `Application.status` | `pending` · `accepted` · `rejected` · `withdrawn` |
| `Contract.status` | `active` · `completed` · `terminated` — `terminated` is unreachable ([Q2](DECISIONS.md)) |
| `Review.reviewer_type` | `creator_on_supplier` · `supplier_on_creator` |

`agreed_rate` is **copied** from the application's `proposed_rate` rather than
read through the relation. A financial record must not change because someone
edited a row it points at.

All amounts are US dollars, and a rate is the amount agreed **for the job**, not
per hour ([I11, I12](DECISIONS.md)).

### 2.2 The endpoints

**Specified** — all fifteen are implemented:

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/gigs/` | `status` may be omitted or sent as `open`; anything else is refused |
| `GET` | `/api/gigs/` | Paginated. Filters: `category`, `status` |
| `GET` | `/api/gigs/{id}/` | |
| `PATCH` | `/api/gigs/{id}/` | `budget` and `category` freeze once the gig leaves `open` |
| `DELETE` | `/api/gigs/{id}/` | Refused once any agreement exists |
| `POST` | `/api/suppliers/` | |
| `GET` | `/api/suppliers/{id}/` | |
| `POST` | `/api/gigs/{id}/apply/` | Body: `supplier_id`, `proposed_rate` |
| `GET` | `/api/gigs/{id}/applications/` | |
| `POST` | `/api/applications/{id}/accept/` | **201** with the new agreement |
| `POST` | `/api/applications/{id}/reject/` | **200** with the updated application |
| `POST` | `/api/applications/{id}/withdraw/` | **200** with the updated application |
| `GET` | `/api/contracts/` | Filters: `supplier_id`, `creator_id`, both optional |
| `POST` | `/api/contracts/{id}/complete/` | **200** with the updated agreement |
| `POST` | `/api/contracts/{id}/reviews/` | **201** with the new review |

**Added**, because the specification cannot be used as written. Every addition is
listed so nothing is smuggled in:

| Method | Path | Why it was unavoidable |
|---|---|---|
| `POST` | `/api/creators/` | Every gig needs a creator and no creator endpoint is specified |
| `GET` | `/api/creators/`, `/api/creators/{id}/` | To read back what was created |
| `PATCH` | `/api/creators/{id}/` | Changing a name or email is ordinary account maintenance |
| `GET` | `/api/suppliers/` | Symmetry with creators; only create and retrieve are specified |
| `PATCH` | `/api/suppliers/{id}/` | Rule 5 requires a supplier to go inactive *between* applying and being hired — unreachable without it |
| `GET` | `/api/contracts/{id}/reviews/` | An endpoint that writes with no way to read back is unusable |

`PUT` also works wherever `PATCH` does; it comes with DRF's `ModelViewSet` and
rejecting it would surprise clients for no benefit. There is deliberately **no**
`DELETE` on creators or suppliers ([S3, Q5](DECISIONS.md)) and no individual
`/api/contracts/{id}/` detail route, which the specification never asks for.

### 2.3 The ten business rules

This is the requirements traceability matrix: every rule, the code that enforces
it, and how many tests assert it. Run any row with `pytest -m rule` and find the
identifier in the test source.

| # | The rule | Enforced in | Tests |
|---|---|---|---|
| **1** | Only `open` gigs accept applications | `hiring/services.py` → `_assert_gig_accepts_hiring` | 3 |
| **2** | One live application per supplier per gig; reapplying allowed after the first is finished | Partial unique index in `hiring/models.py`, plus a check in `apply_to_gig` | 4 |
| **3** | Accepting creates the agreement, moves the gig to `in_progress`, and turns down competing pending bids — **all or nothing** | `hiring/services.py` → `accept_application` | 23 |
| **4** | A supplier holds at most **3** live agreements | `hiring/services.py` → `_assert_under_workload_cap` | 15 |
| **5** | An `inactive` supplier cannot be hired, checked when accepting — not when applying | `hiring/services.py` → `_assert_supplier_is_hireable` | 8 |
| **6** | `accepted`, `rejected` and `withdrawn` applications are terminal | `hiring/services.py` → `_assert_application_is_pending` | 38 |
| **7** | A gig with an agreement cannot be deleted, and deletion must not cascade to agreements or reviews | `gigs/transitions.py` → `assert_gig_deletable`, plus `PROTECT` on the FKs | 8 |
| **8** | Once a gig leaves `open`, `budget` and `category` freeze; only listed status transitions are allowed | `gigs/transitions.py` → `ALLOWED_TRANSITIONS`, `assert_transition_allowed`, `assert_fields_mutable` | 30 |
| **9** | One review per agreement per reviewer kind, on `completed` agreements only, rating 1–5 | `hiring/services.py` → `create_review`, plus a unique constraint and a `CHECK` | 44 |
| **10** | Input validation: required fields, positive amounts, valid choices, well-formed email | Serializers in each app, `common/fields.py`, `common/exceptions.py` | 60 |

The column sums to 233 across 220 distinct tests — a test that covers two rules
at once is counted under both.

**Rule 4 has no database backstop, and that is not an oversight.** "At most three
rows matching a condition" cannot be written as a `CHECK` or `UNIQUE`
constraint. Every other rule has a second line of defence in the schema; this one
is enforced in application code alone, which is why it is ranked the highest risk
in [TEST_PLAN.md](TEST_PLAN.md) and carries a fault-injection test proving a
refusal writes nothing at all.

---

## 3. Setup

Requires Python 3.10 or newer. No database server, no environment file, no
seeding.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS or Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API is then at **http://127.0.0.1:8000/api/**, browsable in a browser.

Every setting has a working default. Copy `.env.example` to `.env` only to
override one — nothing is required to run or test the project.

---

## 4. Running the tests

### The one command

```bash
pytest
```

Nothing else. Verbosity, the failure summary, traceback style and coverage are
all set in `pyproject.toml`, so there are no flags to remember and no way for two
people to get different results from the same code.

### What the output looks like

Every test names itself and its outcome, one line each:

```
tests/test_applications_apply.py::test_a_supplier_can_apply_to_an_open_gig PASSED [  0%]
tests/test_applications_apply.py::test_two_suppliers_can_bid_on_the_same_gig PASSED [  0%]
tests/test_applications_apply.py::test_a_gig_that_is_not_open_accepts_no_bids[in_progress] PASSED [  1%]
tests/test_applications_apply.py::test_a_gig_that_is_not_open_accepts_no_bids[completed] PASSED [  1%]
tests/test_applications_apply.py::test_a_gig_that_is_not_open_accepts_no_bids[cancelled] PASSED [  2%]
...
TOTAL                            636     17     72      3    97%
============================ 441 passed in 15.47s =============================
```

The text in square brackets is the variation being tested — the same test run
against `in_progress`, `completed` and `cancelled` gigs. Each counts separately,
so a failure tells you *which* case broke, not just that the test broke.

### Every command worth knowing

**Narrowing what runs:**

| Command | What it does |
|---|---|
| `pytest tests/test_reviews.py` | One module |
| `pytest tests/test_reviews.py::test_a_review_can_be_left_on_a_completed_agreement` | One test (all its variations) |
| `pytest -k "cascade or busy"` | Any test whose name matches |
| `pytest -x` | Stop at the first failure |
| `pytest --lf` | Re-run only what failed last time |
| `pytest --ff` | Failures first, then everything else |

**Changing the output:**

| Command | What it does |
|---|---|
| `pytest -q` | Back to compact dots — verbosity is cumulative, so `-q` cancels the configured `-v` |
| `pytest --tb=no -ra` | Failure *names* only, no tracebacks — the fastest way to see the shape of a breakage |
| `pytest --tb=long` | Full traceback when a short one is not enough |
| `pytest -vv` | Do not truncate long assertion values |
| `pytest --no-cov` | Skip coverage; roughly twice as fast |
| `pytest --collect-only` | List what *would* run without running it |
| `pytest --durations=10` | The ten slowest tests |

**Selecting by what a test proves.** Every test carries at least one
traceability marker — this is checked, not assumed:

| Command | Tests | Asks |
|---|---|---|
| `pytest -m rule` | 220 | Does this match the **specification**? |
| `pytest -m interpretation` | 55 | Does this match what **we decided** where the spec was silent? |
| `pytest -m case` | 435 | Does this match a numbered scenario in `TEST_CASES.md`? |
| `pytest -m smoke` | 1 | Does the whole journey work end to end? |

That first split is the one that matters for review. A reviewer can run
`-m rule` and check the result against the specification without having to take
any of our interpretations on trust — and can run `-m interpretation` to see
exactly which behaviours are ours rather than the document's.

### Coverage in a browser

```bash
pytest --cov-report=html
start htmlcov/index.html      # or open htmlcov/index.html
```

Coverage output is gitignored, because a committed report goes stale silently and
then lies with authority.

---

## 5. Analysing the results

### 5.1 When everything passes

Read the last two lines. `441 passed` with a `TOTAL` line means the suite ran
clean; anything else — `failed`, `error`, `skipped`, `xfailed` — appears there.

**Nothing in this suite is skipped or expected-to-fail.** There are no
`@pytest.mark.skip`, `skipif` or `xfail` markers anywhere, no `except: pass`,
and no vacuous assertions. Behind the 441 tests are **571 checks** — 234 direct
`assert` statements plus 337 calls to the helpers in `tests/assertions.py`, each
of which asserts one to three things. If a number other than 441 appears,
something changed.

### 5.2 When something fails

Work through it in this order.

**Step 1 — read the summary at the bottom first.** `-ra` prints every
non-passing outcome in one block, so nothing scrolls past unnoticed:

```
=========================== short test summary info ===========================
FAILED tests/test_hiring_workload_cap.py::test_a_fourth_live_agreement_is_refused_and_nothing_is_written
FAILED tests/test_hiring_workload_cap.py::test_the_limit_does_not_drift_across_repeated_attempts
FAILED tests/test_hiring_workload_cap.py::test_only_live_agreements_are_counted[three-live-at-the-limit]
FAILED tests/test_hiring_workload_cap.py::test_the_limit_counts_work_from_every_creator
========================= 4 failed, 9 passed in 1.87s =========================
```

**The shape tells you more than any single failure.** Four failures all in
`workload_cap` means one rule broke, not four unrelated things. Failures
scattered across unrelated modules usually mean a shared fixture or a serializer
everything depends on.

**Step 2 — read the failure block.** `--tb=short` gives the assertion and the
value that was actually produced:

```
_______ test_a_fourth_live_agreement_is_refused_and_nothing_is_written ________
tests\test_hiring_workload_cap.py:57: in test_a_fourth_live_agreement_is_refused_and_nothing_is_written
    detail = assert_conflict(response, "workload_cap_reached")
tests\assertions.py:56: in assert_conflict
    assert response.status_code == status.HTTP_409_CONFLICT, (
E   AssertionError: expected 409 Conflict with code 'workload_cap_reached',
    got 201: {'id': 4, 'gig': 1, 'supplier': 1, 'agreed_rate': '420.00',
              'status': 'active', ...}
```

Three things are readable without opening a file:

- **The name says what should have happened** — a fourth live agreement is
  refused and nothing is written.
- **The message says what happened instead** — a 201, and the agreement that
  should not exist is printed in full.
- **The helper is named for the rule** — `assert_conflict(..., "workload_cap_reached")`,
  not `assert response.status_code == 409`.

This is why the helpers in `tests/assertions.py` exist. A bare assertion would
have said `assert 201 == 409`, which tells you a number is wrong but not which
rule you broke.

**Step 3 — isolate it.**

```bash
pytest tests/test_hiring_workload_cap.py::test_a_fourth_live_agreement_is_refused_and_nothing_is_written -vv --no-cov
```

**Step 4 — find out which requirement it belongs to.** Markers are applied in
two places. The rule sits at the top of the module, because every test in the
file is about that rule:

```python
# tests/test_hiring_workload_cap.py
pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-04")]
```

The scenario id sits on the individual test:

```python
@pytest.mark.case("CP-04,CP-05")
def test_a_fourth_live_agreement_is_refused_and_nothing_is_written(...):
```

Then follow whichever you have:

| Marker | Look it up in |
|---|---|
| `rule("BR-04")` | The table in [§2.3](#23-the-ten-business-rules) — a specification requirement |
| `case("CP-04")` | [TEST_CASES.md](TEST_CASES.md) — the scenario in plain language with its exact expected result |
| `interpretation("I3")` | [DECISIONS.md](DECISIONS.md) table 2 — our reading of something the spec left open |

Each module's docstring also states its coverage in words: *"Covers cases CP-01
to CP-15 and WL-01 to WL-06 in TEST_CASES.md, and business rule 4."*

A failing `rule` test means the code no longer matches the specification. A
failing `interpretation` test means it no longer matches a decision we made and
wrote down — which may be the right change to make, but it must be a decision,
not a side effect.

**Step 5 — decide which side is wrong.** The test is a suspect too. Five of the
bugs found while building this suite were in the *tests*: a fixture reusing a
supplier who already had a bid, setup that hit the three-agreement cap before the
test began, a factory returning a model where a response body was expected. Ask
"is the expectation right?" before changing the code it is checking.

### 5.3 Proving the suite can actually fail

441 passing tests mean nothing unless the tests would fail on a real bug.
Coverage cannot answer that — a line can execute under a test that asserts
nothing about it. The check is to break the code deliberately and see who
notices:

| Break | Result |
|---|---|
| Delete the cap guard in `accept_application` | **6 failed** across `test_hiring_workload_cap.py`, `test_hiring_atomicity.py`, `test_supplier_availability.py` |
| Drop `updated_at=timezone.now()` from the cascade update | **1 failed** — `test_relations.py::test_a_bid_turned_down_by_the_cascade_gets_a_new_changed_date` |
| Make the cascade touch every bid, not only pending ones | **2 failed** in `test_hiring_cascade.py` |

The second is the one worth dwelling on. Django's `auto_now` does not fire on a
bulk `queryset.update()`, so fifty applications would change status while
claiming they had never been modified. Exactly one test catches it — which is
why that test exists.

Three breaks is a spot check, not a proof. The systematic version is **mutation
testing**: `mutmut` alters every operator, boundary and return value in turn and
reports which mutations no test noticed. That is item 7 in
[TEST_PLAN.md](TEST_PLAN.md).

### 5.4 What the suite structurally cannot catch

**Concurrency.** Two simultaneous accepts for a supplier holding two agreements
could both pass the cap check and produce a fourth. The `select_for_update()`
that would prevent it is a documented **no-op on SQLite** — verified by
inspecting the emitted SQL, which contains zero `FOR UPDATE` clauses.

No test here goes red for that. Closing it needs PostgreSQL and threads, which
is item 2 in [TEST_PLAN.md](TEST_PLAN.md) and the first entry in its exploratory
charter. It is named rather than papered over: a test that mocks its way into a
race-condition branch proves the mock works, not the code.

---

## 6. Coverage, in detail

97% of `apps/` — 636 statements, 17 uncovered, 72 branches, 3 partial.

| Area | Coverage |
|---|---|
| Views — `accounts`, `gigs`, `hiring` | 100% |
| Serializers, filters, validators, enums, fields | 100% |
| `gigs/transitions.py` — the gig lifecycle | 98% |
| `hiring/services.py` — the hiring workflow | 97% |
| `hiring/models.py` | 95% |
| `accounts/models.py` | 93% |
| `common/exceptions.py` | 76% |
| **Total** | **97%** |

### Every uncovered line, and why

A coverage percentage says nothing on its own, so here is all seventeen:

| Uncovered | Statements | Why |
|---|---|---|
| `__str__` on all six models | 6 | Display helpers for the admin. A test would assert a string format nothing depends on. |
| `IntegrityError` fallbacks in `services.py` (duplicate application, duplicate review) | 4 | The branch that catches two simultaneous requests both passing the same check. Unreachable without real concurrency (§5.4). |
| `IntegrityError` branch in the exception handler | 3 | Translates a database constraint into a clean 409 and an ERROR log. |
| Django `ValidationError` branch in the handler | 1 | Translates a model-level validation error into a 400. |
| `_flatten_django_validation_error` | 3 | Only called by the branch above. |

**The last two rows are good news, not a gap.** Those branches exist to catch a
database constraint firing or a model validator rejecting something — cases that
should be *impossible* if the request-validation layer above them is doing its
job. That they never execute across 441 tests is evidence the layer above works.
They stay as a safety net and log loudly if they ever run.

### The three partial branches

| Where | What |
|---|---|
| `common/exceptions.py` ×2 | The `if isinstance(...)` guards for the two never-taken handler branches above |
| `gigs/transitions.py` → `74->exit` | **Unreachable by construction.** Line 74 asks whether the target status is `completed` or `cancelled`; the false path is dead because `ALLOWED_TRANSITIONS` only ever permits those two as targets. It would come alive the moment a third target is added — which is the point of leaving the guard in. |

### What coverage does not tell you

That last item is the illustration. Coverage measures which lines *ran*, not
whether anything *checked the result*. A suite of 441 tests with no assertions
would report the same 97%. The evidence that these tests assert something useful
is §5.3, not this section.

---

## 7. What each file is for

### Top level

| File | Purpose |
|---|---|
| `manage.py` | Django's command-line entry point |
| `pyproject.toml` | pytest and coverage configuration — one place for how the suite runs |
| `requirements.txt` | Dependencies, pinned |
| `README.md` | This file |
| `DECISIONS.md` | Every ambiguity in the specification: 6 open questions, 18 interpretations, additions, 5 places we are deliberately stricter |
| `TEST_PLAN.md` | Strategy, risk ranking of the ten rules, manual exploratory charter, prioritised next steps |
| `TEST_CASES.md` | 525 scenarios in plain language with exact expected results |

### `config/` — configuration and routing

| File | Purpose |
|---|---|
| `settings/base.py` | Everything shared, read from the environment via `django-environ` |
| `settings/dev.py` | Local development: `DEBUG` on |
| `settings/test.py` | Test runs: `DEBUG` **off**, so tests assert production-shaped error responses rather than the debug versions |
| `urls.py` | Root map: `/admin/` and `/api/` |
| `api_urls.py` | Merges each app's router into one registry so `/api/` lists every collection |
| `wsgi.py`, `asgi.py` | Server entry points |

### `apps/common/` — shared building blocks

Depends on nothing. Everything here exists because two or more apps needed it.

| File | Purpose |
|---|---|
| `models.py` | `TimeStampedModel` — the `created_at`/`updated_at` base every model inherits |
| `fields.py` | `PositiveMoneyField` — one definition of what a monetary amount is: precision, scale, and "must be positive" |
| `serializers.py` | `BaseModelSerializer`, which maps model fields to the right serializer fields automatically, plus `NormalizedEmailField` and `MoneyField` |
| `exceptions.py` | `DomainError`, `InvalidRequest` (400), `ConflictError` (409), and the single handler that turns them into HTTP responses |
| `constants.py` | Money precision, the platform currency, the three-agreement cap |
| `constraints.py` | `positive_value_constraint` — the database `CHECK` that backs `PositiveMoneyField` |
| `pagination.py` | `DefaultPagination`, with page size read from settings so tests can shrink it |
| `text.py` | `canonicalize_tag` — shared by supplier skills and gig categories so both normalise identically |

`serializers.py` is worth knowing about: declaring a serializer field explicitly
makes DRF **silently drop** the validators it would have inferred from the model.
That caused a real bug here — duplicate emails returning 409 instead of 400 —
and the field mapping in this file is the fix.

### `apps/accounts/` — the two kinds of people

| File | Purpose |
|---|---|
| `models.py` | `Creator`, `Supplier` |
| `enums.py` | `AvailabilityStatus` |
| `validators.py` | `validate_skill_list`, `normalize_skills` — a skills list must be a list of non-blank text |
| `serializers.py` | Request validation, including refusing `busy` as a client-supplied value |
| `views.py` | `CreatorViewSet`, `SupplierViewSet` — create, retrieve, list, update. No delete, deliberately |
| `urls.py` | Router registrations |
| `constants.py` | Name and channel-name length limits |
| `admin.py` | Admin registration, for setting up awkward states by hand |

### `apps/gigs/` — the job posting and its lifecycle

| File | Purpose |
|---|---|
| `models.py` | `Gig`, plus `is_open` / `has_active_contract` / `has_contract_history` — questions phrased the way the business asks them |
| `enums.py` | `GigStatus` |
| `transitions.py` | **The gig lifecycle.** `ALLOWED_TRANSITIONS` as a readable table, plus `assert_transition_allowed`, `assert_fields_mutable`, `assert_gig_deletable` |
| `filters.py` | `GigFilterSet` — `status` is a choice filter, so a bad value is a 400 rather than an empty page |
| `serializers.py` | `GigSerializer` (create: only `open`), `GigUpdateSerializer` (update: transitions allowed) |
| `views.py` | `GigViewSet`. `perform_update` wraps the cancel cascade in a transaction; `perform_destroy` applies the delete guard |

`transitions.py` is a table rather than scattered `if` statements on purpose: the
set of legal moves is the single most important thing to be able to *read* about
a state machine, and a table can be checked against the specification by someone
who does not read Python.

### `apps/hiring/` — bids, agreements, reviews

| File | Purpose |
|---|---|
| `models.py` | `Application`, `Contract`, `Review`, their querysets, and the database constraints: a partial unique index on *pending* applications, one active agreement per gig, one review per kind, a `CHECK` on rating 1–5 |
| `enums.py` | `ApplicationStatus`, `ContractStatus`, `ReviewerType` |
| `services.py` | **Every business rule that spans more than one model.** `apply_to_gig`, `accept_application`, `reject_application`, `withdraw_application`, `complete_contract`, `create_review`, plus one named guard per rule |
| `filters.py` | `ContractFilterSet` — `supplier_id` and `creator_id`, the latter traversing `gig__creator_id` |
| `serializers.py` | Request and response shapes for the action endpoints |
| `views.py` | The seven action endpoints. Each parses a request, calls one service, returns a response |

`services.py` is where to look first for anything about hiring. Rules 3, 4 and 5
each span three models and need a transaction, which is more than a serializer
should know about. Every guard is a separate named function — `_assert_application_is_pending`,
`_assert_under_workload_cap` — so `accept_application` reads as a list of rules
rather than a wall of conditionals.

The partial unique index in `models.py` is how the apparent contradiction between
rules 2 and 6 is resolved: uniqueness applies only to *pending* applications, so
reapplying after a rejection is allowed while the rejection stays on the record
for ever ([I1](DECISIONS.md)).

### `tests/` — the suite

Four support files, then twenty test modules.

| File | Purpose |
|---|---|
| `conftest.py` | Fixtures. Record fixtures (`creator`, `supplier`, `open_gig`) and workflow fixtures that build *states* through the API — `hire`, `busy_supplier`, `give_live_agreements`, `completed_agreement`, `gig_with_three_bids` |
| `factories.py` | `factory_boy` factories for building records directly |
| `endpoints.py` | Every address in one place, written as **literal paths** rather than `reverse()` |
| `assertions.py` | `assert_created`, `assert_ok`, `assert_field_error`, `assert_conflict`, `assert_not_found`, `assert_method_not_allowed`, `assert_page`, `ids_in` |

Two deliberate choices there:

**Factories build records; the API builds valid states.** A factory can create a
`Contract` row that no sequence of requests could ever produce. Fixtures like
`busy_supplier` go through `POST /apply/` and `POST /accept/` instead, so the
state under test is one a real client could actually reach.

**Paths are literal, not `reverse()`.** These are the addresses the
specification promises to callers. Writing them out means a renamed route breaks
a test — which is correct, because it would break every client too. `reverse()`
would follow the rename silently and hide the fact that a published contract had
changed.

| Module | Tests | Covers |
|---|---|---|
| `test_suppliers.py` | 52 | Registering, reading, updating; every field validated |
| `test_gigs_transitions.py` | 46 | Rule 8 — all sixteen from/to combinations, and frozen fields |
| `test_reviews.py` | 44 | Rule 9 — one per kind, completed only, rating boundaries |
| `test_creators.py` | 44 | Creating, reading, updating; validation and null checks |
| `test_gigs_create.py` | 42 | Posting a gig; only `open` accepted |
| `test_applications_terminal_states.py` | 37 | Rule 6 — every state × action combination |
| `test_gigs_filtering.py` | 35 | `category` and `status` filters, mixed, and paging |
| `test_applications_apply.py` | 29 | Rules 1 and 2 — applying, and one live bid per gig |
| `test_contracts.py` | 20 | Listing and completing agreements |
| `test_supplier_availability.py` | 13 | What `busy` means and who sets it |
| `test_hiring_workload_cap.py` | 13 | Rule 4 — the three-agreement limit |
| `test_relations.py` | 12 | Foreign keys, cascades, and timestamps |
| `test_error_contract.py` | 11 | Error shape: stable `code`, no leaked database wording, no 500s |
| `test_hiring_accept.py` | 10 | Rule 3 — the happy path of hiring |
| `test_hiring_cascade.py` | 8 | Rule 3 — competing bids turned down, finished ones untouched |
| `test_gigs_delete.py` | 7 | Rule 7 — what can and cannot be deleted |
| `test_gigs_cancel_cascade.py` | 7 | Cancelling a gig turns down its outstanding bids |
| `test_hiring_availability.py` | 5 | Rule 5 — inactive at accept time |
| `test_hiring_atomicity.py` | 5 | Rule 3 — a refused hire writes **nothing**, proven by fault injection |
| `test_end_to_end.py` | 1 | The whole journey: post, bid, hire, finish, review |

`test_hiring_atomicity.py` is the transaction-consistency requirement. It forces
a failure part-way through `accept_application` with `mock.patch(...,
side_effect=RuntimeError)` and then asserts that the agreement, the gig's status
and every competing bid are all unchanged. Without fault injection you can only
test that the happy path works — not that the rollback does.

---

## 8. Trying the API by hand

The service ships with DRF's browsable API, so
**http://127.0.0.1:8000/api/** is clickable. The action endpoints (`apply`,
`accept`, `reject`, `withdraw`, `complete`) accept only `POST`, so there is no
page to browse for those — use curl or Postman.

```bash
# a creator, a supplier, and a gig
curl -sX POST localhost:8000/api/creators/ -H 'Content-Type: application/json' \
  -d '{"name":"Ada","email":"ada@example.com","channel_name":"AdaCodes"}'

curl -sX POST localhost:8000/api/suppliers/ -H 'Content-Type: application/json' \
  -d '{"name":"Xena","email":"xena@example.com","skills":["editing"],"hourly_rate":"45.00"}'

curl -sX POST localhost:8000/api/gigs/ -H 'Content-Type: application/json' \
  -d '{"creator":1,"title":"Edit episode 12","description":"Cut to ten minutes.","budget":"500.00","category":"editing"}'

# bid, hire, finish, review
curl -sX POST localhost:8000/api/gigs/1/apply/ -H 'Content-Type: application/json' \
  -d '{"supplier_id":1,"proposed_rate":"420.00"}'
curl -sX POST localhost:8000/api/applications/1/accept/
curl -sX POST localhost:8000/api/contracts/1/complete/
curl -sX PATCH localhost:8000/api/gigs/1/ -H 'Content-Type: application/json' \
  -d '{"status":"completed"}'
curl -sX POST localhost:8000/api/contracts/1/reviews/ -H 'Content-Type: application/json' \
  -d '{"reviewer_type":"creator_on_supplier","rating":5,"comment":"Fast and clean."}'
```

Note the two separate steps at the end: completing the *agreement* does not
complete the *gig* ([I8](DECISIONS.md)). The specification names
`in_progress → completed` as an allowed gig transition, so auto-completing it
here would make the spec's own example unreachable.

For setting up awkward states — flipping a supplier to `inactive` mid-workflow,
or seeing what a cascade did to sibling rows — the admin is faster:

```bash
DJANGO_SUPERUSER_PASSWORD=devpass python manage.py createsuperuser \
  --noinput --username admin --email admin@example.com
```

Then **http://127.0.0.1:8000/admin/**.

---

## 9. How the code is arranged

```
config/settings/{base,dev,test}.py   configuration, read from the environment
apps/common/     shared pieces: money fields, domain errors, pagination
apps/accounts/   Creator, Supplier
apps/gigs/       Gig, and the status transition table
apps/hiring/     Application, Contract, Review, and services.py
tests/           the automated suite
```

Dependencies point one way only — `hiring → gigs → accounts → common` — so any
app can be understood without reading the ones above it. This was not free:
keeping it acyclic meant moving the three-agreement constant into `common` and
giving `Gig` a `has_active_contract` property that reaches *down* the reverse
relation rather than importing from `hiring`.

A request travels: **route → view → serializer → service → model → database.**
Each layer has one job, and the reason for that split is defence in depth — the
serializer protects the user from a bad request, the service protects the rules,
the database protects the truth. Rule 2 has all three: a check in the service for
a good message, and a partial unique index that makes the rule true even if the
service is wrong.

Refusals are raised as domain errors and translated to HTTP in exactly one place
(`apps/common/exceptions.py`), so the status-code mapping cannot drift between
endpoints. Every refusal carries a short stable `code` alongside its message:

```json
{"detail": "This application is accepted and can no longer be modified.",
 "code": "application_not_pending"}
```

Tests assert on `code`, never on the prose. Message wording should be free to
improve; a test that pins the text fails the moment someone rewords it, and a
suite that produces false failures is one people learn to ignore.

**400 means the request is wrong on its own terms** — a rate of `-5` would never
have worked. **409 means the request is fine but the situation has moved on** —
applying to a gig that has since been filled. A client must react differently to
each: fix the input, or refresh and reconsider. So they are kept apart
([I17](DECISIONS.md)).

---

## 10. Known gaps

Six questions are still open, listed in full in table 1 of
[DECISIONS.md](DECISIONS.md). The two that matter most:

- **There is no sign-in.** The specification describes actions in terms of who
  performs them but never says how the service identifies a caller. So anyone can
  hire, reject, withdraw or review on anyone's behalf, and the unfiltered
  agreement list exposes every rate ever agreed. Every ownership rule in the
  document is currently decorative.

- **Work that fails cannot be recorded as failed.** `terminated` is a listed
  agreement state that no endpoint can reach. A supplier who takes a job and
  disappears leaves the gig stuck in progress for ever and permanently occupies
  one of their three slots.

Neither is a build error. Both are gaps in the specification, reported rather
than silently patched — and neither was invented an endpoint to work around,
because implementing a feature the specification never asked for is a worse
failure than reporting the gap.

The one genuine gap in the *test suite*, as opposed to the specification, is
concurrency (§5.4).

### What I would do next

The top five of the seven items in [TEST_PLAN.md](TEST_PLAN.md), numbered as
they are there. Full reasoning in that document.

| # | Next | Why | Effort |
|---|---|---|---|
| 1 | **CI on every push** — GitHub Actions running `pytest`, failing under 90% coverage | A suite nobody runs automatically decays within weeks. Cheapest possible insurance. | 1 hour |
| 2 | **PostgreSQL in CI plus a real concurrency test for rule 4** — threads, and `select_for_update` actually locking | Closes the single genuine hole in this suite, on the highest-risk rule (§5.4) | half a day |
| 3 | **Authentication, then authorisation tests** | Unblocks a whole category of tests that cannot exist today ([Q1](DECISIONS.md)). Until it lands, every ownership rule in the specification is decorative. | 1–2 days |
| 4 | **OpenAPI schema and contract testing** — `drf-spectacular`, then `schemathesis` | Generates edge cases from the schema that a human would not think to write, and gives clients a machine-readable contract | 1 day |
| 7 | **Mutation testing** — `mutmut` | Turns the three-break spot check in §5.3 into a systematic answer for the whole suite | half a day |

Items 5 and 6 — a load test on the accept endpoint, and property-based testing of
the state machines with `hypothesis` — are in `TEST_PLAN.md` too.

Items 3 and 4 are the two I would most like to have had time for: without
authentication a third of the specification's rules cannot be enforced at all,
only described.
