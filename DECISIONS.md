# DECISIONS

Where the specification was silent, ambiguous, or contradicted itself.

**Part 1 is the summary** — every question and interpretation in four tables.
**Part 2 explains the reasoning** behind each one. Nothing was guessed silently.

Where the specification left a genuine choice, we took the reading that matches
how comparable marketplaces behave, applied it consistently, and tested against
it. Only the items in table 1 are left genuinely open.

---

# Part 1 — Summary

## Table 1. Open questions

Six things we could not decide for ourselves. Each needs an answer from whoever
owns the specification.

| # | Question | Why it matters | What we do meanwhile | Detail |
|---|---|---|---|---|
| Q1 | **How does the service know who is asking?** There is no sign-in anywhere in the specification. | Every ownership rule is unenforceable. Anyone can hire, reject, withdraw, complete or review on anyone's behalf. | No ownership checks at all | A-1 |
| Q2 | **How is failed work recorded?** `terminated` is a listed agreement state that no action can reach. | A job that falls through leaves the gig stuck in progress for ever and permanently costs the supplier one of their three slots. | No route exists; the state is unreachable | A-2 |
| Q3 | **Can a terminated agreement be reviewed?** Rule 9 says completed only. | How a job failed is arguably the most useful feedback a marketplace has. | Completed only, as specified | B-9 |
| Q4 | **Should `title` and `description` freeze along with budget and category?** Rule 8 names only two fields. | A creator could rewrite the brief after hiring. | Only budget and category freeze | B-6 |
| Q5 | **Is there an account-closure process?** | Creators and suppliers cannot be removed at all. | Deletion refused; suppliers use `inactive` | D-4 |
| Q6 | **Can a review be corrected or disputed?** | Permanent public ratings with no recourse is a legal exposure. | No edit, no delete, no appeal | D-5 |

## Table 2. Interpretations we applied and test against

Where the specification was open, we took the reading a comparable platform
would use. These are decisions, not questions — the test suite asserts them.

| # | The gap or ambiguity | Our interpretation | Detail |
|---|---|---|---|
| I1 | Rules 2 and 6 look contradictory: reapplying is allowed, yet rejection is terminal | Reapplying creates a **new** application; the old one stays rejected for ever. Uniqueness therefore applies only to *pending* applications | B-1 |
| I2 | Rule 6 does not mention `withdrawn` | Withdrawn is terminal too. **Pending is the only state in which an application can be acted on** | B-2 |
| I3 | Rule 5 blocks only `inactive`, leaving `busy` meaningless | **`busy` means "holding the maximum of 3 live agreements"** — a value the service sets and clears itself. A busy supplier is already blocked by the workload rule, so rule 5 needs no bending | B-3 |
| I4 | No default availability is stated | New suppliers are `available`. Clients may send only `available` or `inactive`; `busy` is service-managed | B-3 |
| I5 | Rule 3 does not say which applications are turned down | Only *pending* ones, and only on *that* gig. Already-finished applications keep their status **and their timestamp** | B-4 |
| I6 | Nothing guards *accepting* on a gig that is not open | Accepting requires an open gig, otherwise a cancelled gig could be revived or a second agreement created | B-5 |
| I7 | Rule 8 defines 2 of 16 possible status changes | Full transition table published; `completed` and `cancelled` are final | B-6 |
| I8 | Does completing an agreement also complete the gig? | No — two explicit steps. Otherwise rule 8's own `in_progress → completed` example would be unreachable | B-7 |
| I9 | What happens to pending applications when a gig is cancelled? | **They are turned down automatically.** Closing a posting declines outstanding proposals; leaving them pending would show live bids for dead work | B-8 |
| I10 | Can a proposal exceed the gig's budget? | Yes. Bidding above budget is a normal negotiating position | B-10 |
| I11 | Is a rate per hour or for the job? | **For the job** (fixed price), matching `budget`. It is the only reading in which the numbers on one gig are comparable | B-11 |
| I12 | No currency is specified | **All amounts are US dollars**, platform-wide. A single-currency market, so no currency field | B-12 |
| I13 | What counts as valid text? | Any genuine text, including text containing brackets, quotes or digits. Only actual lists, structures and true/false are refused | B-13 |
| I14 | Applications when a gig is deleted | Deleted with it. A bid carries no money and no reputation | D-1 |
| I15 | Only creators post gigs | Required in the model, unenforceable without sign-in (Q1) | D-2 |
| I16 | Suppliers can see each other's bids | Left open — normal marketplace behaviour, and often a feature. The write side is the real risk | D-3 |
| I17 | Which failures are 400 and which are 409 | 400 = the request is wrong on its own terms. 409 = the request is fine but the situation moved on | D-6 |
| I18 | The three-agreement limit counts what? | Live **agreements** only. Applications never count, however many | D-7 |

## Table 3. Endpoints and fields we added

The specification cannot be used as written. Everything added is listed so
nothing is smuggled in.

| Addition | Why it was unavoidable |
|---|---|
| `POST /api/creators/` | No gig can be created without a creator, and no creator endpoint is specified |
| `GET /api/creators/{id}/` and `GET /api/creators/` | To read back what was created |
| `PATCH /api/creators/{id}/` | Changing a name, channel or email is ordinary account maintenance |
| `GET /api/suppliers/` | Symmetry; only create and retrieve are specified |
| `PATCH /api/suppliers/{id}/` | Rule 5 requires a supplier to go inactive *between* applying and being hired — unreachable without it |
| `GET /api/contracts/{id}/reviews/` | An endpoint that writes with no way to read back is unusable |
| `created_at` / `updated_at` on every record | Specified for applications only; reconstructing history is worth two columns |

**Deliberately not added,** despite a case for each: authentication, a terminate
action, a currency field, estimated hours, rejection reasons, review editing,
soft deletion, and a link from an agreement back to its application.

## Table 4. Where we are deliberately stricter than the specification

| # | The rule as written | What we do instead | Why | Detail |
|---|---|---|---|---|
| S1 | Rule 7 blocks deleting a gig only while an agreement is **live** | We refuse deletion for **any** agreement history | The literal reading permits destroying the agreement and its reviews, which the same sentence forbids | C-1 |
| S2 | Budget and category "become immutable" | Refused because the field was **sent**, even if the value matches | Simpler and more predictable than a rule that depends on current data | C-2 |
| S3 | — | Creators and suppliers cannot be deleted at all | Everything they own is protected, including other people's statements about them | D-4 |
| S4 | — | `completed` and `cancelled` gigs are final | Reopening would strand the applications rejected on cancellation | B-6 |
| S5 | Gig `status` is a listed field | Only `open` may be supplied when creating | A gig marked in progress with nobody hired breaks several later rules | B-14 |

---

# Part 2 — The reasoning

## Section A — Missing from the specification

### A-1. No authentication or authorisation *(Q1 — highest impact)*

The specification describes actions in terms of who performs them — "a creator
accepts an application", "a supplier withdraws their application" — but never
describes how the service establishes who is asking. There is no sign-in, no
token, no user record.

Every ownership rule is therefore decorative. In this build anyone can:

| Action | Consequence |
|---|---|
| Accept an application on someone else's gig | A stranger commits you to a rate |
| Reject an application | A supplier removes a rival's bid |
| Withdraw an application | Someone withdraws another supplier's bid |
| Complete an agreement | Work is marked delivered by anyone |
| Leave either kind of review | A supplier writes their own five-star review |
| Read every agreement | Every rate ever agreed is public |

We implemented the endpoints as specified without ownership checks, because
inventing an authentication scheme means inventing a user model, a login flow
and a permission model the specification does not describe — a far larger
deviation than reporting the gap.

**Testing impact.** No test can verify "only the creator may do this". Those
tests become possible only once identity exists.

**What production needs.** Token or session authentication; a `User` that both
`Creator` and `Supplier` link to; per-endpoint checks (`accept` requires
`request.user == application.gig.creator`, `withdraw` requires
`request.user == application.supplier`); and querysets scoped to the caller so
listing endpoints cannot leak other people's data.

### A-2. Failed work cannot be recorded *(Q2)*

`terminated` is a valid agreement status, and rule 4 counts it explicitly
("non-completed, **non-terminated**"). But the only action on an agreement is
`POST /api/contracts/{id}/complete/`. Nothing can set an agreement to
terminated.

This is more than a spare value, because the gig lifecycle closes the loop:

```
A gig is "in progress" only while a live agreement exists
        ↓
Leaving "in progress" requires completing or cancelling the gig
        ↓
Both require that no live agreement remains
        ↓
The only way to clear a live agreement is to mark it COMPLETE
        ↓
So the only exit from "in progress" is to declare the work successfully done
```

**Worked example.** Ada hires Xena to edit episode 12 for $420. Xena goes quiet
and never delivers.

| Ada tries | Result |
|---|---|
| Cancel the gig | Refused — there is a live agreement |
| End the agreement | No such action exists |
| Delete the gig and repost | Refused — it has an agreement |
| Mark the agreement complete | Works, but records that Xena delivered — and would let her be reviewed as though she had |

Ada is stuck; the gig stays in progress for ever. Worse, Xena's abandoned job
counts as live indefinitely, permanently occupying one of her three slots — and
under our interpretation of `busy` (I3) she is marked busy for ever too.

We added no terminate action, because it would mean inventing its rules: who may
call it, whether anything is owed, whether the agreement can then be reviewed.

**Testing impact.** Cases involving terminated agreements set the state directly
in the database, since no sequence of API calls can produce it.

### A-3. No individual agreement endpoint

`GET /api/contracts/{id}/` does not exist (404). The specification asks only for
the list and the two actions. An agreement is reached through the list, or as the
response to accepting. Left as specified.

---

## Section B — Ambiguities and how we read them

### B-1. Rules 2 and 6 look contradictory *(I1)*

Rule 2 allows reapplying after withdrawal or rejection. Rule 6 makes those
states terminal. They agree once you notice that reapplying creates a **new
record** rather than reviving the old one.

This had to be settled before any code, because it decides a database-level rule:

| Possible rule | Result |
|---|---|
| One application per supplier per gig | Breaks rule 2 — a rejected supplier could never reapply |
| No rule at all | Breaks rule 2's other half — two live bids at once |
| **One *pending* application per supplier per gig** | **Both rules hold** |

A supplier may accumulate any number of finished applications on one gig, and at
most one live one.

### B-2. Rule 6 does not mention "withdrawn" *(I2)*

Withdrawn is terminal too. Withdrawing twice is meaningless, and re-accepting
something a supplier has pulled out of would be worse. So **pending is the only
state in which an application can be acted on** — the code asks "is this
pending?" rather than keeping a list of finished states, which stays correct if a
state is ever added.

### B-3. `busy` means "at the agreement cap" *(I3, I4)*

**The problem.** Rule 5 blocks only `inactive` suppliers from being hired. Read
literally, `busy` changes nothing at all — a label no rule reads, while the
three-agreement cap does the job people would expect it to do.

**Our interpretation**, taken from how marketplaces normally present
availability: **a supplier is busy exactly when they are carrying as much work as
the platform allows** — three live agreements.

**Why this resolves rule 5 rather than contradicting it.** If busy means "at the
cap", a busy supplier is *already* blocked by the workload rule. Rule 5 stays
exactly as written, `busy` becomes meaningful, and the two agree without either
being bent.

| Event | Availability becomes |
|---|---|
| Registers | `available` (no default is specified) |
| Hired, now holding fewer than 3 | unchanged, `available` |
| Hired, now holding 3 | **`busy`** |
| Finishes a job, now holding fewer than 3 | **`available`** |
| Chooses `inactive` | `inactive`, and **never** overwritten by the service |

**Clients may send only `available` or `inactive`.** `busy` is derived, so setting
it by hand would create a value the next hire overwrites; sending it returns 400
explaining that the service maintains it.

**`inactive` is never overwritten**, because it is the supplier's own decision to
stop taking work. Someone who steps away while holding three jobs is still
inactive when one finishes.

### B-4. Rule 3 does not say which applications are turned down *(I5)*

Both halves of our reading matter:

- **Only that gig's.** The hired supplier may have live applications on other
  gigs; those are untouched, because they are still legitimately in the running.
- **Only pending ones.** Applications already rejected or withdrawn keep their
  status **and their timestamp**. They are not re-saved, because nothing about
  them changed, so "when was this rejected?" stays answerable.

### B-5. Nothing guards *accepting* on a gig that is not open *(I6)*

Rule 1 stops a supplier *applying* to a gig that is not open. No rule stops a
creator *accepting* on one. Without a guard, accepting on a cancelled gig would
revive it as in progress, and a second acceptance on an in-progress gig would
create a second agreement. Accepting therefore requires an open gig.

### B-6. Rule 8 defines 2 of 16 possible status changes *(I7, S4)*

| From \ To | open | in_progress | completed | cancelled |
|---|---|---|---|---|
| **open** | no change | no | no | **yes** (spec example) |
| **in_progress** | no | no change | **yes** (spec example), if no live agreement | **yes**, if no live agreement |
| **completed** | no | no | no change | no |
| **cancelled** | no | no | no | no change |

- **open to in_progress** belongs to hiring, which also creates the agreement.
  Allowing it here produces a gig marked as worked on with nobody hired.
- **open to completed**: nothing was agreed, so there is no work to have finished.
- **in_progress to open**: a hire cannot be undone by editing a field.
- **completed and cancelled are final.** Reopening a cancelled gig would strand
  the applications turned down when it was cancelled (I9). A creator who changes
  their mind posts a new gig, which keeps history honest.
- **Sending the status a gig already has** changes nothing and is accepted;
  refusing it would break callers that safely resend a request.

**Q4 stays open:** rule 8 freezes `budget` and `category` but not `title` or
`description`. We read that literally — fixing a typo in a brief harms nobody —
but it may have been an oversight.

### B-7. Completing an agreement does not complete the gig *(I8)*

Our first reading was the opposite, and it was wrong. Rule 8 names
`in_progress` to `completed` as an allowed change **on the gig**; if completing
the agreement did it automatically, that named transition could never be used.

So finishing a job is two steps: complete the agreement (the work is declared
delivered), then set the gig to completed (the creator signs it off). The gig
transition is refused while a live agreement remains, so the order cannot be
reversed.

### B-8. Cancelling a gig turns down its outstanding bids *(I9)*

The specification never says what happens to pending applications when a gig is
cancelled. Our interpretation: **they are rejected automatically**, in the same
transaction as the cancellation.

Closing a job posting declines the proposals outstanding on it, which is how
marketplaces normally behave. The alternative is worse than untidy: those
applications can never be accepted (I6), so they would sit in listings as live
bids for work that no longer exists, and every supplier would wait for an answer
that could not come.

Already-finished applications are untouched, timestamps included (I5).

### B-9. A terminated agreement cannot be reviewed *(Q3)*

Rule 9 allows reviews only on completed agreements, so a terminated one can never
be reviewed. Implemented as specified, and flagged: how a job went wrong is often
the most useful signal a marketplace has. Currently moot anyway, since nothing
can produce a terminated agreement (A-2).

### B-10. A proposal may exceed the gig's budget *(I10)*

No rule connects `proposed_rate` to `budget`. Bidding above budget is a normal
negotiating position — the creator sees the number and decides — so it is
allowed. It is also a spam vector, which a production system would rate-limit
rather than forbid.

### B-11. A rate is the amount for the job, not per hour *(I11)*

`Supplier.hourly_rate` is explicitly per hour. `Gig.budget` reads as a total.
`Application.proposed_rate` — and therefore `Contract.agreed_rate`, which copies
it — is never defined as either.

This matters: if a proposal were hourly, comparing it to a total budget would be
meaningless, and an agreement would record **no total value for the job at all**.

We read `proposed_rate` and `agreed_rate` as **the amount agreed for the job**,
matching `budget`. It is the only reading in which the numbers on one gig are
comparable, and fixed-price work is the simpler of the two models a marketplace
offers. A supplier's `hourly_rate` therefore stands as guide pricing on their
profile, not a figure the workflow compares anything against.

**Production would need more:** an explicit contract type (fixed price or
hourly), and for hourly work an estimated number of hours, without which an
agreement has no financial value.

### B-12. All amounts are US dollars *(I12)*

No currency is specified. With more than one that is dangerous: a budget of 500
and a proposal of 450 look like agreement whether they mean dollars or rupees,
and nothing in the service would notice.

Our interpretation: **the platform trades in a single currency, US dollars.**
Recorded as `PLATFORM_CURRENCY` in `apps/common/constants.py` rather than left
implicit, so introducing a second currency is a visible change with an obvious
starting point.

We added no currency **field**, because that raises questions the specification
cannot answer: is currency a property of the creator, the gig, or the platform?
May a supplier bid in a different currency? Who bears conversion?

**Production would** put a currency code on the gig and store amounts as whole
numbers of the smallest unit (cents) to avoid rounding errors entirely.

### B-13. What counts as valid text *(I13)*

Anything genuinely text is accepted, including text containing brackets, quotes
or digits. `"['hello']"` is a valid name — a string that happens to contain
punctuation — and refusing it would mean second-guessing what people call
themselves. What is refused is a value that is **not text**: a real list
`["hello"]`, a real structure `{"a": 1}`, or `true`.

One inconsistency, deliberately left: a number sent where text is expected is
converted rather than refused, so `123` becomes `"123"`. This is standard
framework behaviour and exists because digits legitimately appear in text fields
— a channel called `2000`, a category called `4k`. Nothing is corrupted; the
value stored is the value sent.

### B-14. Only `open` may be supplied when creating a gig *(S5)*

Sending any other status returns 400. `in_progress` is reached only by hiring
someone, which also creates the agreement; `completed` and `cancelled` only by an
explicit change on an existing gig.

The field is *accepted and refused* rather than ignored. Making it read-only also
protected the workflow, but read-only fields are dropped silently — so a caller
sending `status: "completed"` got a success response for a gig that was actually
open and still taking applications. The safe outcome without the honest one.

---

## Section C — Where we are stricter than the specification

### C-1. Deleting a gig with a *finished* agreement is also refused *(S1)*

Rule 7: "A Gig cannot be deleted while it has an active contract attached
(400/409, and must not cascade-delete the contract or its reviews)."

Read strictly, only a **live** agreement blocks deletion — so a gig whose
agreement has been completed is deletable. But deleting it would take the
agreement and its reviews with it: the record of paid work, and someone's
reputation. The same sentence forbids exactly that. The literal permission
contradicts the rule's own stated intent.

We refuse both, with different messages so the caller knows which case they are
in:

| Situation | Response |
|---|---|
| Live agreement | 409 `gig_has_active_contract` |
| Finished agreement | 409 `gig_has_contract_history` |

Applications still disappear with the gig (I14), because a bid carries no money
and no reputation.

**Production should not face this choice at all:** never delete, mark deleted.

### C-2. A frozen field is refused because it was *sent* *(S2)*

Sending `budget: 500.00` to an in-progress gig whose budget is already 500.00 is
refused, even though nothing would change.

"You may not send this field now" is simpler and more predictable than "you may
send it if the value happens to match". The permissive version makes the answer
depend on data the caller may not have fresh, gives two callers different answers
for identical requests, and drags in whether `500`, `500.00` and `500.000` are
the same value.

---

## Section D — Decisions on matters never mentioned

### D-1. Applications are deleted with their gig *(I14)*

An application is a bid for one specific piece of work — no money, no reputation,
and no meaning without its gig. Protecting them instead would make
`DELETE /api/gigs/{id}/` unusable, since any gig that ever received a bid would
be undeletable, contradicting the specification exposing the endpoint at all.

### D-2. Only creators post gigs — but nothing enforces it *(I15)*

Every gig requires a creator and one cannot be created without naming an existing
one. But with no sign-in (Q1), **anyone can post a gig naming any creator**,
including a supplier posting in a creator's name. We require the link, refuse an
id that does not exist, and record the ownership rule as unenforceable until
identity exists.

### D-3. Suppliers can see each other's bids *(I16)*

`GET /api/gigs/{id}/applications/` returns every application on a gig, competing
rates included. Left open: seeing what others bid is normal in a marketplace and
often a deliberate feature, because it helps suppliers price sensibly.

**The real risk is the write side**, not the read: a supplier should be able to
change only their own application, a creator only their own gigs. That is
unenforceable without identity (Q1).

### D-4. Creators and suppliers cannot be deleted *(S3, Q5)*

Everything they own is protected: a creator's gigs; a supplier's applications,
agreements and reviews. A delete would either fail at the database or silently
destroy a large amount of history — **including records that belong to other
people**. A supplier's reviews are the creators' statements about them.

The recognised way to leave a marketplace is to stop appearing in it, not to
erase what you did. For suppliers that mechanism already exists: `inactive`.

### D-5. Reviews cannot be edited or removed *(Q6)*

One review of each kind per agreement, permanent once written. A rating given in
error cannot be corrected and there is no dispute process — which for a real
platform is a genuine problem, not just a missing feature.

### D-6. When 400 and when 409 *(I17)*

The specification writes "400/409" interchangeably. We distinguish them:

- **400** — the request is wrong *on its own terms*; it would never have worked.
  A rate of -5, a missing field, a status that does not exist.
- **409** — the request is well-formed and *would have worked at another moment*.
  Applying to a gig that has since been filled; withdrawing an application
  already accepted.

An application built on this service needs to react differently: 400 means
"correct your form", 409 means "your form was fine, refresh — things changed".
Collapsing both into 400 would show a supplier "your application is invalid"
beside a perfectly filled-in form when the only problem was timing.

### D-7. The cap counts agreements, never applications *(I18)*

Only agreements with status `active` count. Applications never do, however many.

| Supplier holds | Live count | Can be hired? |
|---|---|---|
| 11 pending applications, 0 agreements | 0 | Yes |
| 2 active agreements | 2 | Yes |
| 2 active, 1 completed, 1 terminated | 2 | Yes |
| 3 active | 3 | No, 409 |
| 3 active, 5 completed, 2 terminated | 3 | No, 409 |

Rule 4 says "active (non-completed, non-terminated) **contracts**", and an
application is not a contract. Counting applications would also punish suppliers
for bidding widely, which is exactly what a marketplace wants them to do.

### D-8. What can be changed or removed

"Who" cannot be answered without identity (Q1), so this is what is possible at
all.

| Record | Changeable | Deletable |
|---|---|---|
| Creator | name, email, channel name | **No** (405) |
| Supplier | name, email, skills, rate; availability as `available`/`inactive` only | **No** (405) — retire via `inactive` |
| Gig — open | every field | **Yes** (204) |
| Gig — in progress | status only, once no live agreement remains | **No** (409) |
| Gig — completed | title and description only | **No** (409) |
| Gig — cancelled | title and description only | **Yes**, if never contracted |
| Application | no direct edits — accept, reject, withdraw only | only with its gig |
| Agreement | no (404 — no such address) | no (404) |
| Review | no | no |

**An in-progress gig can never be deleted**, because being in progress means a
live agreement exists — precisely what rule 7 protects. **A completed gig can
never be deleted either**, because reaching completed requires having had an
agreement (C-1). Only open and cancelled gigs are deletable, a cancelled one only
if it never reached an agreement.

### D-9. Error messages about amounts

The framework's defaults describe the storage format — "Ensure that there are no
more than 12 digits in total" — which tells a caller nothing useful. Replaced
throughout with wording about the amount:

| Situation | Message |
|---|---|
| Zero or negative | "This amount must be greater than zero. The smallest allowed value is 0.01." |
| Too many decimals | "Amounts may have at most 2 decimal places, for example 45.50." |
| Too large | "This amount is too large. The largest allowed value is 9,999,999,999.99." |
| Not a number | "Enter this amount as a number, for example 45.50." |

Applied to a gig's budget, a supplier's hourly rate and an application's proposed
rate at once, so the three cannot drift apart.
