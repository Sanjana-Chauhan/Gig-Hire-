# TEST PLAN

441 automated tests, 20 modules, 97% coverage of `apps/`. Full case list in
[TEST_CASES.md](TEST_CASES.md); interpretations and open questions in
[DECISIONS.md](DECISIONS.md).

---

## 1. Strategy

### What is tested, and at which layer

| Layer | How | Why there |
|---|---|---|
| **API contract** | Every test goes through DRF's `APIClient` — status codes, response bodies, error codes, field names | This is the promise made to a caller. A correct service layer is not the promise. |
| **Business logic** | The same requests, asserting outcomes across records: the gig moved, siblings were turned down, no agreement appeared | Rules 3, 4 and 5 span three models. Checking one record proves nothing. |
| **Data integrity** | Direct model calls in a handful of places — `ProtectedError` on deleting a creator with gigs | Some guarantees must hold for code paths that never touch the API: a management command, the admin, a future job. |
| **Rollback** | Fault injection — `mock.patch("Gig.save", side_effect=RuntimeError)` at the last step of hiring | A transaction never observed to roll back is an assumption. |

### Deliberately out of scope

| Not tested | Reasoning |
|---|---|
| **Screens, clicks, navigation, redirects, toggles** | There is no user interface. The service returns data, not pages. Inventing UI tests would be fabricating coverage. |
| **The framework's data browser and admin pages** | Supplied by Django, not written here. Testing them measures Django. |
| **Authorisation — "only the creator may accept"** | The specification includes no sign-in, so the service cannot know who is asking (Q1). These tests become possible only once identity exists; today they would assert nothing. |
| **Service functions in isolation** | Covered through the API instead. Unit-testing `accept_application` directly would duplicate the coverage while proving less about what a client experiences. |
| **Concurrency** | Cannot be done honestly on SQLite — see the risk section. The one real gap in this suite. |
| **Performance** | No load test. One query-count check exists in the design notes; a real one needs production-shaped data. |

### Two structural decisions

**Factories build records; the API builds states.** `ContractFactory()` would
create an agreement on a still-open gig with an unchanged supplier — a
combination the workflow cannot produce. Tests built on it would pass against a
broken service. So agreements always come from hiring someone. Factories are used
only for preconditions the workflow does not own, and the end-to-end test builds
*everything* through the API as a guard against factory drift.

**Assertions check error `code`, never message text.** `assert_conflict(response,
"workload_cap_reached")` survives a rewording. A suite that fails when copy
improves is a suite people learn to ignore.

---

## 2. Risk assessment

Ranked by **blast radius × how long a bug stays invisible**, not by complexity.

### Tier 1 — silent, and about money

**Rule 4 (three-agreement limit) — highest risk in the specification.**
It is the *only* rule with no database backstop, and that is not an oversight:
"at most three rows matching a condition" cannot be expressed as a `CHECK` or
`UNIQUE` constraint. Every other rule has a second line of defence; this one has
one. A bug corrupts data with nothing to catch it, and **a supplier with four
live agreements looks exactly like one with three until somebody counts.** By
then they have missed deadlines on jobs the platform promised them.

Worse, the correct-looking guard is a lie on this database: `select_for_update()`
is a documented no-op on SQLite, verified by inspecting the SQL — **zero**
`FOR UPDATE` clauses are emitted. Two simultaneous accepts can both read 3 and
both insert.

**Rule 3 (atomic cascade) — largest blast radius.**
Four writes in one operation. A partial failure gives either a gig marked in
progress with no agreement — the supplier works and nobody is contracted to pay
them — or an accepted bid on a still-open gig, which a second creator can accept
again. Partly protected: a database constraint prevents two *active* agreements
on one gig. Covered by fault injection, which is the only way to see the rollback
actually happen.

### Tier 2 — recoverable only with effort

**Rule 7 (delete guard).** The only rule whose failure is *irreversible*. A
cascade would take agreements and reviews with it — the financial record and
someone's reputation, neither rebuildable. Low likelihood (`PROTECT` on the
foreign keys makes it structurally impossible), but recovery cost is infinite,
which is why we also refuse deletion in cases the rule's literal text permits.

**Rule 5 (availability at accept-time).** Hiring an inactive supplier means work
that is never delivered — and the failure is invisible until a deadline passes.
The specific risk is a well-meaning "improvement": moving the check to the apply
endpoint looks like tidying and silently breaks a case the spec explicitly allows.

**Rule 9 (one review per kind).** Reputation is the platform's product. A gap
here lets a supplier stack their own five-star reviews, and unlike money it
cannot be reconciled afterwards.

### Tier 3 — visible or contained

| Rule | Why lower |
|---|---|
| **8** (frozen fields) | A budget changed after hiring is a payment dispute — serious, but someone notices and complains |
| **2** (one live bid) | Backed by a partial unique index, so the database catches an application-layer bug |
| **6** (terminal states) | Mostly confusion rather than damage; a duplicated agreement is blocked by rule 3's constraint |
| **1** (only open gigs) | Worst case is an unwanted bid, closable by rejecting it |
| **10** (validation) | Self-announcing. A 500 or a leaked constraint message is loud, and monitoring catches it in minutes |

**The pattern:** risk tracks *detectability*, not difficulty. Rule 10 is the
easiest to get wrong and the least dangerous, because it fails loudly. Rule 4 is
simple arithmetic and the most dangerous, because it fails in silence.

---

## 3. Manual exploratory charter

Thirty minutes with curl and two terminals. Each line says what to poke and what
would count as a find.

1. **Two accepts at once for a supplier holding three agreements.** Two
   terminals, same instant, different gigs. *Hunting for:* a fourth live
   agreement. This is the one thing the suite cannot check, and the rule with no
   database backstop. Repeat on PostgreSQL, where the row lock is real, to
   confirm it is the database and not the code.

2. **Two accepts at once on the same gig, different bids.** *Hunting for:* two
   agreements on one gig, or two accepted bids. The partial unique index should
   refuse the second — confirm the loser gets a clean 409 and not a 500.

3. **Apply at the instant a gig is hired.** Loop `apply` while accepting in
   another terminal. *Hunting for:* a bid created against a gig that is already
   in progress, which would then be un-acceptable and un-cascaded — a stranded
   record.

4. **Retry a request that timed out.** Send `accept`, kill the client mid-flight,
   send it again. *Hunting for:* two agreements, or a 409 on a request that
   actually succeeded the first time. There are no idempotency keys, so this is
   an unguarded path.

5. **Unicode and direction.** Emoji, right-to-left script, combining accents,
   and a name that is 150 characters of multi-byte text. *Hunting for:* a length
   limit counting bytes instead of characters, and skill tidying that lowercases
   wrongly for non-Latin script.

6. **Numeric edges the JSON layer might mangle.** `5e2`, `+500`, `500.00000`,
   `0.005`, `-0`, `1_000`. *Hunting for:* silent rounding into range, or a value
   accepted by the API and refused by the database.

7. **Duplicate and encoded query parameters.** `?status=open&status=cancelled`,
   `?category=video%20editing`, `?page=1&page=2`. *Hunting for:* which one wins,
   and whether a filter silently ignores half its input.

8. **A very large payload.** A 10 MB description, 1,000 skills, deeply nested
   JSON. *Hunting for:* a 500 or a hung worker where a 400 belongs. Nothing
   limits request size.

9. **Harvest the contract list.** `GET /api/contracts/` with no filter, then walk
   every page. *Hunting for:* how much commercial data one unauthenticated
   request yields. Expect every rate ever agreed — confirming the exposure in Q1
   rather than discovering it in production.

10. **The admin as a back door.** Log in and try to build states the API refuses:
    an agreement on an open gig, a fourth live agreement, a review on an active
    agreement. *Hunting for:* which invariants live only in the API layer. The
    answer tells you what a management command could break.

---

## 4. What I would add next

Ordered by value per hour, not by ambition.

| # | Work | Why now | Rough size |
|---|---|---|---|
| 1 | **CI on every push** — GitHub Actions running `pytest`, failing under 90% coverage | A suite nobody runs automatically decays within weeks. Cheapest possible insurance. | 1 hour |
| 2 | **PostgreSQL in CI, plus a real concurrency test** for rule 4 — threads, `select_for_update` actually locking | Closes the single genuine hole in this suite, on the highest-risk rule. Also proves the lock we already wrote does something. | half a day |
| 3 | **Authentication, then authorisation tests** | Unblocks a whole category of tests that cannot exist today (Q1). Until it lands, every ownership rule in the specification is decorative. | 1–2 days |
| 4 | **OpenAPI schema + contract testing** (`drf-spectacular`, then `schemathesis`) | Generates edge cases from the schema — malformed types, boundary values — that a human would not think to write. Also gives clients a machine-readable contract. | 1 day |
| 5 | **Load test on the accept endpoint** (k6 or Locust) | The one operation holding locks across four writes. Everything else is a read or a single insert. Worth knowing where it degrades before a marketing push finds out. | half a day |
| 6 | **Property-based tests for the state machines** (`hypothesis`) | The transition sweeps enumerate *single* moves. Property testing explores *sequences* — apply, withdraw, reapply, accept, complete — and finds orders nobody wrote down. | 1 day |
| 7 | **Mutation testing** (`mutmut`) | Answers the question coverage cannot: if a rule were broken, would this suite notice? 97% coverage with weak assertions still ships bugs. | half a day, then ongoing |

**If only one:** number 1. Everything else assumes the suite runs.

**Deliberately not first:** more tests. At 441 covering every rule, every
boundary and both full state machines, the next bug is more likely to be in a
gap the current *approach* cannot see — concurrency, authorisation, request
sequences — than in a case the current approach forgot.
