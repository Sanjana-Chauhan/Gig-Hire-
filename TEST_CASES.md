# GigHire — Test Cases

A complete list of scenarios to verify the GigHire service, written in plain
language so anyone on the team can run them by hand or turn them into automated
tests.

---

## How to read this document

Every test case has an ID, what it checks, the setup it needs, the action to
take, and the **exact** result to expect. If the actual result differs in any
way — a different status number, a different stored value, a different message —
the test has failed.

Status numbers used in this document:

| Number | Meaning in this service |
|---|---|
| 200 | The request worked and returned data |
| 201 | The request worked and created something new |
| 204 | The request worked and there is nothing to return (used by delete) |
| 400 | The request itself was wrong — a missing field, a bad value, a wrong type |
| 404 | The thing named in the address does not exist |
| 405 | That action is not available on that address |
| 409 | The request was well-formed but clashes with the current situation |

**Why some rejections are 400 and others are 409.** A 400 means the request
would never have worked. A 409 means it would have worked earlier, but the
situation has moved on. For example, sending a rate of -5 is always wrong (400),
whereas withdrawing an application is a normal thing to do and only fails
because this particular one was already accepted (409). Both are clean
rejections; neither is an error inside the service.

---

## The exact wording of common messages

Rather than repeating these strings in every case below, cases refer to them by
situation. Any of these appearing with different wording is a failure.

### Amounts (a gig's budget, a supplier's hourly rate, an application's rate)

| Situation | Exact message |
|---|---|
| Zero or negative | "This amount must be greater than zero. The smallest allowed value is 0.01." |
| More than two decimal places | "Amounts may have at most 2 decimal places, for example 45.50." |
| Too large | "This amount is too large. The largest allowed value is 9,999,999,999.99." |
| Not a number at all | "Enter this amount as a number, for example 45.50." |
| Sent with no value | "This field may not be null." |
| Left out when required | "This field is required." |

**All amounts are US dollars.** The platform trades in one currency, so no
request or response carries a currency value — a budget of 500 means $500
everywhere. A rate is the amount agreed **for the whole job**, not per hour; a
supplier's hourly rate on their profile is guide pricing only, and the service
never compares the two.

### Text fields

| Situation | Exact message |
|---|---|
| Empty text where text is required | "This field may not be blank." |
| Sent with no value | "This field may not be null." |
| Longer than allowed | "Ensure this field has no more than N characters." |
| Not text at all (a list, a nested value, true/false) | "Not a valid string." |

### Choices (a gig's status, a supplier's availability, a review's kind)

| Situation | Exact message |
|---|---|
| Not one of the allowed values | "\"<value>\" is not a valid choice." |

---

## What counts as valid text

A text field accepts **anything that is genuinely text**, including text that
contains brackets, quotes or digits. This trips people up, so it is worth being
precise:

| Sent | Accepted? | Stored as |
|---|---|---|
| `"Ada"` | Yes | `Ada` |
| `"['hello']"` — text that happens to contain brackets | **Yes** | `['hello']` |
| `"{\"a\": 1}"` — text that happens to look like a structure | **Yes** | `{"a": 1}` |
| `"123"` — digits written as text | Yes | `123` |
| `123` — an actual number | Yes | `123` |
| `["hello"]` — an actual list | **No, 400** | — |
| `{"a": 1}` — an actual nested structure | **No, 400** | — |
| `true` | **No, 400** | — |

The distinction is between a **string that contains punctuation** and a
**structure**. `"['hello']"` is a perfectly reasonable name for someone to
choose, and refusing it would mean second-guessing what people may call
themselves. A real list is not text at all and cannot become a sensible name.

The one inconsistency: an actual number is converted to text rather than
refused. This is deliberate framework behaviour, because digits legitimately
appear in text fields — a channel called `2000`, a category called `4k`. Nothing
is corrupted; the value stored is the value sent.

---

## What is covered

- Every field on every record: required or optional, allowed values, rejected
  values, values at the edge of what is allowed, wrong types, and empty values.
- Every address the service exposes, and every action available on it.
- Every business rule, including the situations where two rules interact.
- The links between records (a gig belongs to a creator, an application belongs
  to a gig and a supplier, and so on), including what happens when a linked
  record is missing or is removed.
- The complete journey from creating a creator through to both parties leaving
  reviews.
- Filtering and paging, including combinations of filters and pages that do not
  exist.

## What is NOT covered, and why

**There are no screens, buttons, or pages to test.** This project is a service
that other software talks to over the web — it returns data, not web pages.
There is nothing a person clicks. So the following, which would normally be on
a checklist, do not apply here and have deliberately not been invented:

| Not tested | Why not |
|---|---|
| Screen layouts, buttons, menus | The service has no screens. It returns data only. |
| Clicks, navigation, moving between pages | There are no pages to move between. |
| Redirections | The service never sends anyone to a different page. |
| Show/hide behaviour, expanding sections | Nothing is shown or hidden; every response contains the same fields every time. |
| On/off switches and toggles | There are none. The closest equivalent is a supplier's availability setting, which is a stored value with three options, tested under SU and AV below. |
| Sign-in, sign-out, permissions | The specification does not include any sign-in. See the note below. |

**Two things that look like screens but are not part of the deliverable.** The
service ships with a built-in data browser and an administration area, both
provided by the framework we are using rather than written for this project.
They are development conveniences for poking at data by hand. They are not what
the service is for, and testing framework-supplied pages would tell us nothing
about our own work, so they are out of scope.

**A note on who is allowed to do what.** The specification says things like
"the creator accepts an application", but it never describes any way for the
service to know who is making a request. There is no sign-in. As a result,
**anybody can perform any action on anybody's records** — a supplier could
reject a rival's application, or read every rate every other supplier has ever
agreed. This is not a defect in the build; it is a hole in the specification,
and it is recorded as such. It also means no test in this document can check
"only the creator may do this", because the service has no way to tell.

---

## Test data used throughout

Where a test needs records to exist, use these unless the test says otherwise.

| Name | Details |
|---|---|
| Creator A | name "Ada", email "ada@example.com", channel "AdaCodes" |
| Creator B | name "Ben", email "ben@example.com", channel "BenPlays" |
| Supplier X | name "Xena", email "xena@example.com", skills ["editing"], hourly rate $45.00, available |
| Supplier Y | name "Yuri", email "yuri@example.com", skills ["thumbnails"], rate 38.00, available |
| Supplier Z | name "Zoe", email "zoe@example.com", skills ["editing"], rate 50.00, available |
| Gig 1 | Creator A, title "Edit episode 12", budget $500.00 for the job, category "editing", open |

Every test starts from a clean, empty database. No test depends on another test
having run first, and the tests can be run in any order.

---

# 1. Creator

Address: `POST /api/creators/`, `GET /api/creators/{id}/`, `GET /api/creators/`

## 1.1 Creating a creator — accepted

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CR-01 | All three fields supplied | Send name "Ada", email "ada@example.com", channel "AdaCodes" | 201. Response contains an id, the three values as sent, and a created date. |
| CR-02 | Email is stored in lower case | Send email " Ada@Example.COM " (mixed case, spaces at each end) | 201. Stored email is exactly "ada@example.com". Spaces removed, letters lowercased. |
| CR-03 | Longest allowed name | Send a name of exactly 150 characters | 201. The full 150 characters are stored. |
| CR-04 | Longest allowed channel name | Send a channel name of exactly 150 characters | 201. Stored in full. |

## 1.2 Creating a creator — rejected

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CR-05 | Name missing | Send only email and channel | 400. Message names the "name" field and says it is required. |
| CR-06 | Email missing | Send only name and channel | 400. Message names "email" as required. |
| CR-07 | Channel name missing | Send only name and email | 400. Message names "channel_name" as required. |
| CR-08 | Everything missing | Send an empty request | 400. All three fields are listed as required, in one response. |
| CR-09 | Name is empty text | Send name "" | 400. Message says the field may not be blank. |
| CR-10 | Name is only spaces | Send name "   " | 400. Message says the field may not be blank. |
| CR-11 | Name is empty (no value at all) | Send name with no value | 400. Message says the field may not be empty. |
| CR-12 | Email is not an email address | Send email "not-an-email" | 400. Message says a valid email address is required. |
| CR-13 | Email missing the part after @ | Send email "ada@" | 400. Message says a valid email address is required. |
| CR-14 | Email missing the part before @ | Send email "@example.com" | 400. Message says a valid email address is required. |
| CR-15 | Duplicate email, same spelling | Create Creator A, then create another creator with "ada@example.com" | 400. Message names the email field and says a creator with this email already exists. **Not** 409, and never a database error. |
| CR-16 | Duplicate email, different capitals | Create Creator A, then create another with "ADA@Example.com" | 400, same message as CR-15. Because emails are lowercased before checking, these count as the same address. |
| CR-17 | Duplicate email with surrounding spaces | Create Creator A, then create another with " ada@example.com " | 400, same as CR-15. |
| CR-18 | Name too long | Send a name of 151 characters | 400. Message says the name has too many characters. |
| CR-19 | Name is true/false | Send name as true | 400. Message says a valid text value is required. |
| CR-20 | Name is a list | Send name as ["Ada"] | 400. Message says a valid text value is required. |
| CR-21 | Name is a set of nested values | Send name as {"first": "Ada"} | 400. Message says a valid text value is required. |
| CR-22 | Extra unrecognised field | Send the three valid fields plus "nickname": "Adz" | 201. The creator is made and "nickname" is ignored. It does not appear in the response. |

## 1.3 Reading a creator

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CR-23 | Fetch an existing creator | Create Creator A, then fetch it by its id | 200. All stored values are returned, matching what was created. |
| CR-24 | Fetch a creator that does not exist | Fetch id 999999 | 404. Message says no creator matches. |
| CR-25 | Fetch with a non-numeric id | Fetch id "abc" | 404. |
| CR-26 | List creators when none exist | Fetch the creator list on an empty database | 200. Total count is 0 and the list of results is empty. Not an error. |
| CR-27 | List creators, newest first | Create Creator A then Creator B, fetch the list | 200. Count is 2. Creator B appears before Creator A. |

## 1.4 Changing a creator

Changing a name, channel name or email is ordinary account maintenance and is
allowed. Deleting is not — see section 20 for the full picture of what can be
removed.

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CR-28 | Change the name | Create Creator A, send name "Ada Renamed" | 200. Name updated; email and channel unchanged. |
| CR-29 | Change the email | Send email "newada@example.com" | 200. Stored in lower case. |
| CR-30 | Change the channel name | Send channel_name "NewChannel" | 200. |
| CR-31 | Change all three at once | Send all three fields | 200. All three updated. |
| CR-32 | Change one field only | Send only the name | 200. Only the name changes. |
| CR-33 | Change email to an invalid one | Send email "not-an-email" | 400. A valid email address is required. The stored email is unchanged. |
| CR-34 | Change email to one already used | Create Creator B, then set B's email to A's | 400. Message says a creator with this email already exists. B's email is unchanged. |
| CR-35 | Change email, different capitals of an existing one | Set B's email to "ADA@example.com" when A holds "ada@example.com" | 400. Same as CR-34 — emails are compared in lower case. |
| CR-36 | Change a creator that does not exist | Change id 999999 | 404. |
| CR-37 | Creators cannot be deleted | Try to delete Creator A | 405. Message says the delete action is not allowed. The creator still exists. |

## 1.5 A creator can post gigs

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CR-38 | A newly created creator can post a gig | Create Creator A, then create a gig naming that creator | 201. The gig is created and its creator field holds Creator A's id. |

---

# 2. Supplier

Address: `POST /api/suppliers/`, `GET /api/suppliers/{id}/`, `GET /api/suppliers/`,
`PATCH /api/suppliers/{id}/`

**Which fields must be supplied.** Name, email and hourly rate are required.
Skills and availability may be left out — the specification marks only name,
email and rate as required, so leaving skills out gives an empty list and
leaving availability out gives "available".

## 2.1 Creating a supplier — accepted

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| SU-01 | All fields supplied | name "Xena", email "xena@example.com", skills ["editing"], rate 45.00, availability "available" | 201. All values returned as sent. |
| SU-02 | Skills left out | Send name, email and rate only | 201. Stored skills is an empty list. |
| SU-03 | Availability left out | Send name, email, skills and rate | 201. Stored availability is exactly "available". |
| SU-05 | Availability set to inactive | Send availability "inactive" | 201. Stored as "inactive". |
| SU-06 | Skills are tidied up | Send skills [" Video-Editing ", "video-editing", "THUMBNAILS"] | 201. Stored skills is exactly ["video-editing", "thumbnails"] — spaces trimmed, capitals lowered, the repeat removed, original order kept. |
| SU-07 | Skills order is preserved | Send skills ["writing", "animation", "editing"] | 201. Stored in that exact order, not sorted alphabetically. |
| SU-08 | Empty skills list | Send skills [] | 201. Stored as an empty list. |
| SU-09 | Smallest allowed rate | Send rate 0.01 | 201. Stored as 0.01. |
| SU-10 | Largest sensible rate | Send rate 9999999999.99 | 201. Stored exactly. |
| SU-11 | Rate sent as a number, not text | Send rate 45 (no decimal point) | 201. Stored as 45.00. |
| SU-12 | Most skills allowed | Send 25 different skills | 201. All 25 stored. |
| SU-13 | Longest allowed skill name | Send one skill of exactly 50 characters | 201. Stored in full. |

## 2.2 Creating a supplier — rejected

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| SU-14 | Name missing | Omit name | 400. "name" listed as required. |
| SU-15 | Email missing | Omit email | 400. "email" listed as required. |
| SU-16 | Rate missing | Omit hourly rate | 400. "hourly_rate" listed as required. |
| SU-17 | Everything missing | Send an empty request | 400. name, email and hourly_rate all listed. |
| SU-18 | Rate is zero | Send rate 0 | 400. Message says the value must be at least 0.01. |
| SU-19 | Rate is negative | Send rate -5 | 400. Same message as SU-18. |
| SU-20 | Rate is a tiny fraction | Send rate 0.001 | 400. Message says no more than 2 decimal places are allowed. |
| SU-21 | Rate is text | Send rate "forty five" | 400. Message says a valid number is required. |
| SU-22 | Rate is true/false | Send rate true | 400. Message says a valid number is required. |
| SU-23 | Rate is empty text | Send rate "" | 400. Message says a valid number is required. |
| SU-24 | Rate is empty (no value) | Send rate with no value | 400. Message says the field may not be empty. |
| SU-25 | Rate has too many digits | Send rate 99999999999.99 (13 digits) | 400. Message says there are too many digits. |
| SU-26 | Availability not one of the three | Send availability "on-holiday" | 400. Message says "on-holiday" is not a valid choice. |
| SU-26a | Registering as busy | Send availability "busy" | 400. Message says "busy" is set automatically when a supplier reaches the maximum of 3 live agreements, and to send "available" or "inactive" instead. |
| SU-27 | Availability in wrong case | Send availability "Available" | 400. Not a valid choice — the stored values are lower case. |
| SU-28 | Availability is empty text | Send availability "" | 400. Not a valid choice. |
| SU-29 | Skills sent as plain text | Send skills "editing" | 400. Message says skills must be provided as a list. |
| SU-30 | Skills contain a number | Send skills [123] | 400. Message says each skill must be text. |
| SU-31 | Skills contain empty text | Send skills ["editing", ""] | 400. Message says skills cannot be blank. The empty entry is **rejected**, not quietly dropped. |
| SU-32 | Skills contain only spaces | Send skills ["   "] | 400. Same message as SU-31. |
| SU-33 | Too many skills | Send 26 skills | 400. Message says at most 25 skills are allowed. |
| SU-34 | A skill is too long | Send one skill of 51 characters | 400. Message says each skill may be at most 50 characters. |
| SU-35 | Skills sent as nested values | Send skills {"a": 1} | 400. Message says skills must be provided as a list. |
| SU-36 | Duplicate email, same spelling | Create Supplier X, then another with "xena@example.com" | 400. Message says a supplier with this email already exists. |
| SU-37 | Duplicate email, different capitals | Create Supplier X, then another with "XENA@example.com" | 400, same as SU-36. |
| SU-38 | Email already used by a creator | Create Creator A with "ada@example.com", then a supplier with the same email | 201. Creators and suppliers are separate lists, so the same address may appear once in each. |
| SU-39 | Invalid email format | Send email "xena.example.com" | 400. Message says a valid email address is required. |

## 2.3 Reading suppliers

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| SU-40 | Fetch an existing supplier | Create Supplier X, fetch by id | 200. All values match. |
| SU-41 | Fetch a supplier that does not exist | Fetch id 999999 | 404. |
| SU-42 | List with none present | Fetch the list on an empty database | 200. Count 0, empty list. |
| SU-43 | List several | Create X, Y, Z and fetch the list | 200. Count 3, newest first (Z, Y, X). |

## 2.4 Changing a supplier

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| SU-44 | Change availability to inactive | Create Supplier X, then change availability to "inactive" | 200. Stored availability is "inactive". Everything else unchanged. |
| SU-45 | Change availability to busy | Change an existing supplier's availability to "busy" | 400, same message as SU-26a. "Busy" is worked out by the service from how much work the supplier holds, so setting it by hand would only create a value the next hire overwrites. |
| SU-46 | Change availability to an invalid value | Change availability to "sleeping" | 400. Not a valid choice. The stored value is unchanged. |
| SU-47 | Change the rate | Change rate to 60.00 | 200. Stored as 60.00. |
| SU-48 | Change the rate to zero | Change rate to 0 | 400. Value must be at least 0.01. Stored rate unchanged. |
| SU-49 | Change skills | Change skills to ["Animation"] | 200. Stored as ["animation"] — tidied the same way as when created. |
| SU-50 | Change email to one already in use | Create X and Y, then change Y's email to X's | 400. Message says a supplier with this email already exists. |
| SU-51 | Change only one field | Send only the availability field | 200. Only availability changes; name, email, skills and rate keep their values. |
| SU-52 | Suppliers cannot be deleted | Try to delete Supplier X | 405. Not allowed. The supplier still exists. |
| SU-53 | Changing a supplier that does not exist | Change supplier id 999999 | 404. |

## 2.5 Availability affects hiring, not applying

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| SU-54 | An inactive supplier may still apply | Set Supplier X to inactive, then apply to open Gig 1 | 201. The application is created with status "pending". Availability is **not** checked when applying. |
| SU-55 | A busy supplier may apply | Set Supplier X to busy, then apply | 201, status "pending". |

## 2.6 How "busy" is worked out

"Busy" is not something a supplier chooses. The service sets it when they are
carrying as much work as the platform allows — three live agreements — and clears
it when one finishes. A supplier chooses only between "available" (open to work)
and "inactive" (not taking work).

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| SU-56 | A new supplier is available | Register a supplier | Availability is "available". |
| SU-57 | One live agreement does not make them busy | Hire the supplier once | Availability is still "available". |
| SU-58 | Two live agreements do not make them busy | Hire them twice | Still "available". |
| SU-59 | Three live agreements makes them busy | Hire them three times | Availability is now exactly "busy". |
| SU-60 | Finishing a job makes them available again | With three live agreements, mark one complete | Availability is back to "available". |
| SU-61 | Being hired again makes them busy again | From two live agreements, hire once more | Availability is "busy". |
| SU-62 | A busy supplier cannot be hired | Supplier has three live agreements. Try to hire them for a fourth. | 409, and the message says they already hold 3 live agreements. |
| SU-63 | "Inactive" is never overwritten | Give the supplier three agreements (they become busy), set them to "inactive", then mark one agreement complete | Availability is **still "inactive"**. The service never overrides a supplier's own decision to stop taking work. |
| SU-64 | An inactive supplier stays inactive when hired elsewhere | Set a supplier inactive; they cannot be hired at all | Hiring gives 409. Their availability is unchanged. |
| SU-65 | Availability of other suppliers is untouched | Hire Supplier X three times | Supplier Y's availability is unchanged. |

**Worked example.** Xena registers and is "available". She is hired for episode
12, then a thumbnail set — still "available", holding 2. She is hired for a third
job and becomes "busy". A creator tries to hire her for a fourth: refused, 409.
The thumbnail job is marked complete: she holds 2 again and is "available". She
is hired for a fourth job and is "busy" once more.


---

# 3. Gig — creating

Address: `POST /api/gigs/`

**Which fields must be supplied.** Creator, title, description, budget and
category are all required. Status is **not** accepted when creating — see the
important note under GC-14.

## 3.1 Accepted

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| GC-01 | All required fields | Creator A's id, title "Edit episode 12", description "Cut to 10 minutes", budget 500.00, category "editing" | 201. Values returned as sent, plus an id, a created date, and status "open". |
| GC-02 | Every new gig starts open | Create a gig without mentioning status | 201. Status is exactly "open". |
| GC-03 | Category is tidied up | Send category "  Editing " | 201. Stored category is exactly "editing" — spaces removed, capitals lowered. |
| GC-04 | Smallest allowed budget | Send budget 0.01 | 201. Stored as 0.01. |
| GC-05 | Budget sent without decimals | Send budget 500 | 201. Stored as 500.00. |
| GC-06 | Very long description | Send a description of 10,000 characters | 201. Stored in full; description has no length limit. |
| GC-07 | Longest allowed title | Send a title of exactly 200 characters | 201. Stored in full. |
| GC-08 | Longest allowed category | Send a category of exactly 50 characters | 201. Stored in full. |

## 3.2 Rejected

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| GC-09 | Creator missing | Omit creator | 400. "creator" listed as required. |
| GC-10 | Title missing | Omit title | 400. "title" listed as required. |
| GC-11 | Description missing | Omit description | 400. "description" listed as required. |
| GC-12 | Budget missing | Omit budget | 400. "budget" listed as required. |
| GC-13 | Category missing | Omit category | 400. "category" listed as required. |
| GC-14 | Everything missing | Send an empty request | 400. All five required fields listed together in one response. |
| GC-15 | Creator does not exist | Send creator id 999999 | 400. Message says the id does not match any creator. **400, not 404** — the bad value is inside the request, not in the address. |
| GC-16 | Creator is text | Send creator "abc" | 400. Message says a valid id is required. |
| GC-17 | Creator is empty | Send creator with no value | 400. Message says the field may not be empty. |
| GC-18 | Budget is zero | Send budget 0 | 400. Value must be at least 0.01. |
| GC-19 | Budget is negative | Send budget -100 | 400. Same as GC-18. |
| GC-20 | Budget has too many decimals | Send budget 10.001 | 400. No more than 2 decimal places. |
| GC-21 | Budget is text | Send budget "five hundred" | 400. A valid number is required. |
| GC-22 | Budget is true/false | Send budget true | 400. A valid number is required. |
| GC-23 | Budget is empty text | Send budget "" | 400. A valid number is required. |
| GC-24 | Budget is empty (no value) | Send budget with no value | 400. The field may not be empty. |
| GC-25 | Title is empty text | Send title "" | 400. The field may not be blank. |
| GC-26 | Title is only spaces | Send title "    " | 400. The field may not be blank. |
| GC-27 | Title too long | Send a title of 201 characters | 400. Too many characters. |
| GC-28 | Category too long | Send a category of 51 characters | 400. Too many characters. |
| GC-29 | Description is empty text | Send description "" | 400. The field may not be blank. |
| GC-30 | Title is a list | Send title ["Edit"] | 400. A valid text value is required. |
| GC-31 | Category is a number | Send category 123 | **Currently 201, stored as "123".** See the note below — this is a known gap. |

## 3.3 Status when creating

Only "open" may be supplied. A gig always starts open; the other three statuses
are reached later — "in_progress" by hiring someone, "completed" and "cancelled"
by an explicit status change on a gig that already exists.

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| GC-32 | Status left out | Send the five required fields, no status | 201. Stored status is "open". |
| GC-33 | Status sent as "open" | Send status "open" | 201. Stored status is "open". |
| GC-34 | Status sent as "in_progress" | Send status "in_progress" | 400. Message says a gig can only be created with status "open", and explains that "in_progress" is reached through the hiring workflow. No gig is created. |
| GC-35 | Status sent as "completed" | Send status "completed" | 400, same style of message naming "completed". No gig is created. |
| GC-36 | Status sent as "cancelled" | Send status "cancelled" | 400, naming "cancelled". No gig is created. |
| GC-37 | Status is not a real status | Send status "nonsense" | 400. Message says "nonsense" is not a valid choice. |
| GC-38 | Status in the wrong case | Send status "OPEN" | 400. Not a valid choice — the stored values are lower case. |
| GC-39 | Status is empty text | Send status "" | 400. Not a valid choice. |
| GC-40 | Status is empty (no value) | Send status with no value | 400. The field may not be empty. |

**Why only "open" is accepted.** If a gig could be created as "in_progress",
there would be a gig marked as being worked on with nobody actually hired and no
agreement attached — and several later rules assume that cannot happen. Refusing
the value, rather than quietly ignoring it, means a caller who sends
"completed" is told their request failed instead of being handed a success
response for a gig that is actually open and still taking applications.

---

# 4. Gig — reading

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| GR-01 | Fetch an existing gig | Create Gig 1, fetch by id | 200. All values match, including status "open". |
| GR-02 | Fetch a gig that does not exist | Fetch id 999999 | 404. Message says no gig matches. |
| GR-03 | Fetch a gig after it is deleted | Create a gig, delete it, fetch it | 404. |
| GR-04 | An in-progress gig can be read | Hire someone on Gig 1, then fetch it | 200. Status is "in_progress". |
| GR-05 | A completed gig can be read | Take Gig 1 through to completed, then fetch it | 200. Status is "completed". |
| GR-06 | A cancelled gig can be read | Cancel Gig 1, then fetch it | 200. Status is "cancelled". |
| GR-07 | The creator is shown as an id | Fetch any gig | 200. The creator field holds a plain number (the creator's id), not a nested block of creator details. |

---

# 5. Gig — updating

Address: `PATCH /api/gigs/{id}/`

## 5.1 While the gig is open, everything except status can change

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| GU-01 | Change the budget | Gig 1 is open. Send budget 1000 | 200. Stored budget is 1000.00. |
| GU-02 | Change the category | Send category "design" | 200. Stored as "design". |
| GU-03 | Category is tidied on update too | Send category "  Design " | 200. Stored as exactly "design". |
| GU-04 | Change the title | Send title "Edit episode 13" | 200. Title updated; nothing else changes. |
| GU-05 | Change the description | Send a new description | 200. Description updated. |
| GU-06 | Change several fields at once | Send title, budget and category together | 200. All three updated to the sent values. |
| GU-07 | Budget still cannot be zero | Send budget 0 | 400. Value must be at least 0.01. The old budget is unchanged. |
| GU-08 | Budget still cannot be negative | Send budget -1 | 400. Old budget unchanged. |
| GU-09 | Budget still cannot be text | Send budget "lots" | 400. A valid number is required. |
| GU-10 | Cancel an open gig | Send status "cancelled" | 200. Status is "cancelled". Any pending applications on it are turned down at the same time — see section 5.6. |
| GU-11 | Change the owning creator | Create Creator B, send creator = Creator B's id | 200. The gig now belongs to Creator B. Nothing in the specification forbids this. |
| GU-12 | Update a gig that does not exist | Update id 999999 | 404. |

## 5.2 Once the gig is no longer open, budget and category are frozen

Set up each row by taking the gig into the stated status first.

| ID | Gig status | Field sent | Exact expected result |
|---|---|---|---|
| GU-13 | in_progress | budget 999 | 409. Message says budget cannot be changed once a gig leaves the open state, and names the current status. Stored budget unchanged. |
| GU-14 | in_progress | category "design" | 409, same style of message. Stored category unchanged. |
| GU-15 | completed | budget 999 | 409. Unchanged. |
| GU-16 | completed | category "design" | 409. Unchanged. |
| GU-17 | cancelled | budget 999 | 409. Unchanged. |
| GU-18 | cancelled | category "design" | 409. Unchanged. |
| GU-19 | in_progress | budget and category together | 409. Message names **both** fields. Neither is changed. |
| GU-20 | in_progress | budget sent with the value it already has (500.00) | 409. The field is refused because it was **sent**, not because the value differs. |
| GU-21 | in_progress | title "corrected typo" | 200. Title is updated. Only budget and category are frozen; the specification names only those two. |
| GU-22 | in_progress | description "clearer brief" | 200. Description updated. |
| GU-23 | completed | title "new title" | 200. Title updated. |

**On GU-20.** Refusing a field that was sent, even when the value matches, is a
deliberate choice: "you may not send this field now" is a simpler and more
predictable rule than "you may send it as long as the value happens to match".
The permissive version would give two callers different answers for identical
requests depending on data they may not have fresh.

## 5.3 Status changes — the complete set

There are four statuses, so there are sixteen possible moves. All sixteen are
listed. Set the gig to the starting status, then send the target status.

| ID | From | To | Exact expected result |
|---|---|---|---|
| GU-24 | open | open | 200. No change. Sending the status a gig already has is not an error. |
| GU-25 | open | in_progress | 409. Message says a gig cannot move from open to in_progress. A gig only becomes in progress when someone is hired. |
| GU-26 | open | completed | 409. Nothing was ever agreed, so there is no work to have finished. |
| GU-27 | open | cancelled | 200. Status becomes "cancelled", and every pending application on the gig becomes "rejected" — see section 5.6. |
| GU-28 | in_progress | open | 409. A hire cannot be undone this way. |
| GU-29 | in_progress | in_progress | 200. No change. |
| GU-30 | in_progress | completed | 200 **only if** the agreement on that gig has already been marked complete. Otherwise 409 — see GU-36. |
| GU-31 | in_progress | cancelled | 200 **only if** there is no live agreement. Otherwise 409 — see GU-37. |
| GU-32 | completed | open | 409. Completed is final. |
| GU-33 | completed | in_progress | 409. |
| GU-34 | completed | completed | 200. No change. |
| GU-35 | completed | cancelled | 409. |
| GU-36 | cancelled | open | 409. Cancelled is final. A creator who changes their mind posts a new gig. |
| GU-37 | cancelled | in_progress | 409. |
| GU-38 | cancelled | completed | 409. |
| GU-39 | cancelled | cancelled | 200. No change. |

## 5.4 Status changes blocked by a live agreement

| ID | What is checked | Setup | Action | Exact expected result |
|---|---|---|---|---|
| GU-40 | Cannot finish a gig while the agreement is live | Hire Supplier X on Gig 1. The agreement is active. | Send status "completed" | 409. Message says the gig has a live agreement and it must be completed first. Gig stays "in_progress". |
| GU-41 | Cannot cancel a gig while the agreement is live | Same setup | Send status "cancelled" | 409, same message. Gig stays "in_progress". |
| GU-42 | Can finish the gig once the agreement is complete | Hire Supplier X, then mark the agreement complete | Send status "completed" | 200. Gig status is "completed". |
| GU-43 | Invalid status value | Gig 1 is open | Send status "finished" | 400. Message says "finished" is not a valid choice. |
| GU-44 | Status is empty text | Send status "" | 400. Not a valid choice. |

## 5.5 Cannot cancel a gig that is being worked on — a gap in the specification

| ID | What is checked | Steps | Result today |
|---|---|---|---|
| GU-45 | Abandoning work that has gone wrong | Hire Supplier X on Gig 1. The supplier then disappears and never delivers. Try to cancel the gig. | **409 every time.** There is no way to cancel it. |

**Why.** Cancelling requires that no live agreement exists. A gig is in progress
precisely because it has a live agreement. The only way to clear a live agreement
is to mark it **complete** — and the specification provides no way to end an
agreement that failed. So the only exit from "in progress" is to declare the
work successfully finished.

This is not a build error. The specification lists "terminated" as a valid
agreement state but gives no action that produces it. The result is that failed
work cannot be recorded as failed, and the supplier's slot is never freed.
This is a question for whoever owns the specification.

## 5.6 Cancelling a gig turns down its outstanding bids

When a gig is cancelled, the bids still waiting on it are turned down. Leaving
them waiting would be worse than untidy: they can never be accepted, so they
would sit in listings as live bids for work that no longer exists, and every
supplier would wait for an answer that could not come.

Bids that were already finished are left exactly as they were.

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| GU-46 | Pending bids are turned down | Gig 1 open with two pending applications. Cancel the gig. | 200. The gig is "cancelled" and **both applications are "rejected"**. |
| GU-47 | Already-rejected bids are untouched | Gig 1 with one rejected and one pending application. Cancel the gig. | The already-rejected one keeps its status **and its "last changed" date**. The pending one becomes "rejected". |
| GU-48 | Withdrawn bids stay withdrawn | Gig 1 with one withdrawn and one pending application. Cancel the gig. | The withdrawn one is **still "withdrawn"** with its original "last changed" date. It is not turned into "rejected". |
| GU-49 | Mixed states | Gig 1 with A rejected, B withdrawn, C pending, D pending. Cancel the gig. | A stays "rejected", B stays "withdrawn", C and D both become "rejected". |
| GU-50 | A gig with no bids | Gig 1 with no applications. Cancel it. | 200. No error. |
| GU-51 | Both changes happen together | After GU-46 | There is never a moment where the gig is cancelled but a bid is still pending, or a bid is rejected but the gig is still open. |
| GU-52 | Cancelling does not create or remove bids | After GU-49 | Still exactly four applications on that gig. Only statuses changed. |
| GU-53 | No agreement is created | After GU-46 | No agreement exists for that gig. |
| GU-54 | Cancelling twice | Cancel a cancelled gig | 200, no change. No applications are re-stamped, because none are pending. |


---

# 6. Gig — deleting

Address: `DELETE /api/gigs/{id}/`

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| GD-01 | Delete a gig nobody has applied to | Gig 1, open, no applications | 204. Nothing is returned. Fetching the gig afterwards gives 404. |
| GD-02 | Delete a gig with applications but no agreement | Gig 1 with two pending applications | 204. The gig is gone. Both applications are gone too — an application only means something in the context of its gig. |
| GD-03 | Delete a gig with a live agreement | Hire Supplier X on Gig 1 | 409. Message says the gig has a live agreement and cannot be deleted. |
| GD-04 | Nothing is lost when the delete is refused | Same as GD-03, then check every record | The gig still exists, the agreement still exists, and its status is still "active". |
| GD-05 | Delete a gig whose agreement is finished | Hire Supplier X, mark the agreement complete | 409. Message says the gig has agreement history and deleting it would destroy the agreement and any reviews attached to it. |
| GD-06 | Reviews survive a refused delete | Hire Supplier X, complete the agreement, leave both reviews, then try to delete the gig | 409. Afterwards: the gig exists, the agreement exists, and **both reviews still exist**. |
| GD-07 | Delete a cancelled gig | Cancel Gig 1 (no agreement ever made), then delete it | 204. |
| GD-08 | Delete a gig that does not exist | Delete id 999999 | 404. |
| GD-09 | Delete the same gig twice | Delete Gig 1, then delete it again | First 204, second 404. |

**A note on GD-05.** The specification only forbids deleting a gig with a
**live** agreement. Read strictly, a gig whose agreement is finished could be
deleted — and that would take the agreement and its reviews with it, destroying
the record of paid work and someone's reputation. Since the specification also
says a delete "must not remove the agreement or its reviews", the strict reading
contradicts its own intent. This build therefore refuses both cases, and says
so with two different messages so the caller knows which situation they are in.

---

# 7. Gig — filtering and paging

Address: `GET /api/gigs/`

**Setup for this section.** Create six gigs under Creator A:

| Gig | Category | Status |
|---|---|---|
| G1 | editing | open |
| G2 | editing | open |
| G3 | design | open |
| G4 | editing | cancelled |
| G5 | design | cancelled |
| G6 | writing | open |

## 7.1 Filtering

| ID | Request | Exact expected result |
|---|---|---|
| GF-01 | No filter | 200. Count 6. All six returned. |
| GF-02 | `?status=open` | 200. Count 4 — G1, G2, G3, G6. |
| GF-03 | `?status=cancelled` | 200. Count 2 — G4, G5. |
| GF-04 | `?status=in_progress` | 200. Count 0, empty list. A valid filter that matches nothing is a success, not an error. |
| GF-05 | `?category=editing` | 200. Count 3 — G1, G2, G4. |
| GF-06 | `?category=design` | 200. Count 2 — G3, G5. |
| GF-07 | `?category=writing` | 200. Count 1 — G6. |
| GF-08 | `?category=photography` | 200. Count 0, empty list. |
| GF-09 | `?category=EDITING` | 200. Count 3, same as GF-05. Capitals do not matter because categories are stored in lower case and the filter is lowered to match. |
| GF-10 | `?category=  editing  ` (spaces around it) | 200. Count 3, same as GF-05. |
| GF-11 | Both filters: `?status=open&category=editing` | 200. Count 2 — G1, G2. Both conditions must be true. |
| GF-12 | Both filters: `?status=cancelled&category=design` | 200. Count 1 — G5. |
| GF-13 | Both filters, no overlap: `?status=cancelled&category=writing` | 200. Count 0. G6 is writing but open; G4 and G5 are cancelled but not writing. |
| GF-14 | Both filters, one impossible: `?status=completed&category=editing` | 200. Count 0. |
| GF-15 | Invalid status: `?status=nonsense` | 400. Message says "nonsense" is not a valid choice and lists the valid ones. **Not** an empty list — the caller has made a mistake and needs to know. |
| GF-16 | Invalid status with a valid category: `?status=nonsense&category=editing` | 400. The bad filter is reported even though the other one is fine. |
| GF-17 | Empty status: `?status=` | 200. Count 6. An empty filter is treated as no filter. |
| GF-18 | Empty category: `?category=` | 200. Count 6. |
| GF-19 | Unknown filter name: `?colour=red` | 200. Count 6. Unrecognised filters are ignored. |

**Why GF-08 and GF-15 differ.** "photography" is a perfectly valid category
that no gig happens to use — the honest answer is "no matches". "nonsense" is
not a status at all, so the honest answer is "your request is wrong". Returning
an empty list for both would hide the caller's mistake.

## 7.2 Paging

Twenty items are returned per page unless the request asks for a different size.
The most that can be asked for is 100.

| ID | Setup | Request | Exact expected result |
|---|---|---|---|
| GF-20 | 6 gigs | No paging options | 200. Count 6. All 6 in the results. A link to the next page is empty. |
| GF-21 | 6 gigs | `?page_size=2` | 200. Count 6 (the total, not the page size). 2 results. A link to page 2 is present. |
| GF-22 | 6 gigs | `?page_size=2&page=2` | 200. Count 6. 2 results — the third and fourth gigs. Links to both page 1 and page 3 are present. |
| GF-23 | 6 gigs | `?page_size=2&page=3` | 200. Count 6. 2 results — the last two. The link to a next page is empty. |
| GF-24 | 6 gigs | `?page_size=2&page=4` | 404. Message says the page is not valid. There is no page 4. |
| GF-25 | 6 gigs | `?page=2` (default size 20) | 404. All 6 fit on page 1, so page 2 does not exist. |
| GF-26 | 6 gigs | `?page=0` | 404. Page numbers start at 1. |
| GF-27 | 6 gigs | `?page=-1` | 404. |
| GF-28 | 6 gigs | `?page=abc` | 404. |
| GF-29 | 6 gigs | `?page_size=100` | 200. Count 6, all 6 returned. |
| GF-30 | 6 gigs | `?page_size=99999` | 200. Count 6, all 6 returned. The request is capped at 100 rather than rejected. |
| GF-31 | 6 gigs | `?page_size=0` | 200. Falls back to the default size of 20; all 6 returned. |
| GF-32 | 6 gigs | `?page_size=abc` | 200. Falls back to the default size; all 6 returned. |
| GF-33 | 0 gigs | No options | 200. Count 0, empty list, no next or previous link. |
| GF-34 | 6 gigs | `?status=open&page_size=2` | 200. Count 4 (matching gigs only, not all 6). 2 results. |
| GF-35 | 6 gigs | `?status=open&page_size=2&page=2` | 200. Count 4. 2 results — the third and fourth open gigs. |
| GF-36 | 6 gigs | `?status=open&page_size=2&page=3` | 404. Only 4 gigs match, so there are only 2 pages. |
| GF-37 | 6 gigs | Compare page 1 and page 2 contents | No gig appears on both pages, and together the pages contain every matching gig exactly once. |
| GF-38 | 6 gigs | Fetch page 1 twice | Identical results both times. Ordering is stable — newest first, and ties broken by id — so paging never shuffles. |

---

# 8. Applying to a gig

Address: `POST /api/gigs/{id}/apply/`
Request body: `supplier_id` and `proposed_rate`.

## 8.1 Accepted

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AP-01 | A supplier applies to an open gig | Gig 1 open, Supplier X available | 201. Response contains an id, the gig id, the supplier id, the rate as sent, and status "pending". |
| AP-02 | Two different suppliers apply to the same gig | Gig 1 open | Both get 201. Two separate applications exist, both "pending". |
| AP-03 | One supplier applies to two different gigs | Gigs 1 and 2 open | Both get 201. The limit is one live application per gig, not per supplier. |
| AP-04 | Smallest allowed rate | Send rate 0.01 | 201. Stored as 0.01. |
| AP-05 | Rate higher than the gig's budget | Gig 1 budget is 500.00. Send rate 99999.00 | 201. This is allowed. Nothing in the specification says a proposal must fit the budget. |
| AP-06 | Rate exactly equal to the budget | Send rate 500.00 | 201. |
| AP-07 | An inactive supplier applies | Set Supplier X inactive first | 201, status "pending". Availability is only checked at hiring time. |
| AP-08 | A busy supplier applies | Set Supplier X busy first | 201, status "pending". |

## 8.2 Rejected — the gig is not open

| ID | Gig status | Exact expected result |
|---|---|---|
| AP-09 | in_progress | 409. Message says applications are only accepted while a gig is open, and names the current status. No application is created. |
| AP-10 | completed | 409, same message with "completed". |
| AP-11 | cancelled | 409, same message with "cancelled". |

## 8.3 Rejected — one live application per supplier per gig

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| AP-12 | Applying twice while the first is live | Supplier X applies to Gig 1 (201), then applies again | 409. Message says this supplier already has a pending application for this gig. Only one application exists afterwards. |
| AP-13 | The second attempt changes nothing | Same as AP-12 | The first application still has its original rate. The second rate is not stored anywhere. |

## 8.4 Accepted — applying again after finishing

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| AP-14 | Apply again after withdrawing | Supplier X applies, withdraws, applies again | 201. A **new** application is created with status "pending". |
| AP-15 | Apply again after being rejected | Supplier X applies, the creator rejects it, Supplier X applies again | 201. A new pending application is created. |
| AP-16 | The earlier application is untouched | After AP-14 | Two applications exist for this supplier and gig: the first still "withdrawn", the second "pending". The first is **not** overwritten or reused. |
| AP-17 | The history builds up | Apply, withdraw, apply, get rejected, apply again | Three applications exist: "withdrawn", "rejected", "pending". |
| AP-18 | Cannot apply again after being hired | Supplier X applies and is hired | The gig is now in progress, so a further application gives 409 "gig is not open". |

## 8.5 Rejected — bad request contents

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| AP-19 | Supplier id missing | Send only the rate | 400. "supplier_id" listed as required. |
| AP-20 | Rate missing | Send only the supplier id | 400. "proposed_rate" listed as required. |
| AP-21 | Empty request | Send nothing | 400. Both fields listed as required. |
| AP-22 | Wrong field name | Send "supplier" instead of "supplier_id" | 400. "supplier_id" listed as required. The specification names the field "supplier_id". |
| AP-23 | Supplier does not exist | Send supplier_id 999999 | 400. Message says the id does not match any supplier. |
| AP-24 | Supplier id is text | Send supplier_id "abc" | 400. A valid id is required. |
| AP-25 | Supplier id is empty | Send supplier_id with no value | 400. The field may not be empty. |
| AP-26 | Rate is zero | Send rate 0 | 400. Value must be at least 0.01. |
| AP-27 | Rate is negative | Send rate -5 | 400. Same as AP-26. |
| AP-28 | Rate has too many decimals | Send rate 0.001 | 400. No more than 2 decimal places. |
| AP-29 | Rate is text | Send rate "fifty" | 400. A valid number is required. |
| AP-30 | Rate is true/false | Send rate true | 400. A valid number is required. |
| AP-31 | Rate is empty | Send rate with no value | 400. The field may not be empty. |
| AP-32 | Gig does not exist | Apply to gig id 999999 | 404. Message says no gig matches. **404 here, because the missing thing is named in the address.** |
| AP-33 | Gig was deleted | Create Gig 1, delete it, then apply to it | 404. |
| AP-34 | Order of checks | Apply to a **cancelled** gig with a rate of -5 | 400 for the rate. The contents of the request are checked before the situation, so the caller hears about the clearly-wrong value first. |

## 8.6 Listing a gig's applications

Address: `GET /api/gigs/{id}/applications/`

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AL-01 | List applications | Gig 1 with 3 applications | 200. Count 3. Each entry shows its id, gig, supplier, rate and status. |
| AL-02 | Gig with no applications | Gig 1, nobody applied | 200. Count 0, empty list. |
| AL-03 | Gig does not exist | List applications for gig 999999 | 404. **Not** an empty list — an empty list would tell someone with a typo in the address that the gig simply has no applicants. |
| AL-04 | Only that gig's applications | Gigs 1 and 2 each with 2 applications | Listing Gig 1 returns exactly its own 2. Gig 2's do not appear. |
| AL-05 | Mixed statuses all appear | Gig 1 with one pending, one withdrawn, one rejected | 200. Count 3. All three appear regardless of status. |
| AL-06 | Newest first | Create three applications in order | The most recently created appears first. |
| AL-07 | Paging works | Gig 1 with 3 applications, ask for page size 2 | 200. Count 3, 2 results, link to page 2 present. |
| AL-08 | Page beyond the last | Same, ask for page 3 | 404. Page is not valid. |

---

# 9. Withdrawing and rejecting an application

Addresses: `POST /api/applications/{id}/withdraw/`, `POST /api/applications/{id}/reject/`

**The rule.** An application can only be acted on while it is "pending". Once it
is accepted, rejected or withdrawn it is finished, and any further action on it
must be refused with a clear message — never quietly accepted, and never an
error inside the service.

## 9.1 The complete picture

Four possible starting states, three possible actions. All twelve combinations
are listed. Set the application to the starting status, then perform the action.

| ID | Starting status | Action | Exact expected result |
|---|---|---|---|
| AW-01 | pending | withdraw | 200. Status becomes "withdrawn". |
| AW-02 | pending | reject | 200. Status becomes "rejected". |
| AW-03 | pending | accept | 201. An agreement is created (covered in section 10). |
| AW-04 | accepted | withdraw | 409. Message says the application is accepted and can no longer be changed. Status stays "accepted". |
| AW-05 | accepted | reject | 409, same message. Status stays "accepted". |
| AW-06 | accepted | accept | 409, same message. Status stays "accepted". **No second agreement is created.** |
| AW-07 | rejected | withdraw | 409. Message says the application is rejected and can no longer be changed. |
| AW-08 | rejected | reject | 409, same message. |
| AW-09 | rejected | accept | 409, same message. |
| AW-10 | withdrawn | withdraw | 409. Message says the application is withdrawn and can no longer be changed. |
| AW-11 | withdrawn | reject | 409, same message. |
| AW-12 | withdrawn | accept | 409, same message. |

**Every one of the nine refusals must be a 409 with a readable message.** None
may return 200 with no change, and none may produce an error inside the service.

## 9.2 Repeating an action

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| AW-13 | Withdraw twice | Withdraw a pending application (200), then withdraw again | Second attempt is 409. It is **not** a silent success. |
| AW-14 | Reject twice | Reject a pending application (200), then reject again | Second attempt is 409. |
| AW-15 | Withdraw then reject | Withdraw (200), then reject | 409. |
| AW-16 | Reject then withdraw | Reject (200), then withdraw | 409. |

**Why a repeated action is refused rather than accepted.** Rejecting an
already-rejected application arguably reaches the desired state, so returning
200 might seem harmless. It is not. If the application had in fact been
**accepted**, a 200 on "reject" would tell the creator they had cancelled a hire
that is actually still live. Reporting success for something that did not happen
is worse than an error, because the caller's understanding of the situation
silently stops matching reality.

## 9.3 Nothing else is affected

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AW-17 | Rejecting one application leaves the others alone | Gig 1 with three pending applications. Reject the first. | The first is "rejected". The other two are still "pending". |
| AW-18 | Rejecting creates no agreement | Same as AW-17 | No agreement exists for that gig. |
| AW-19 | Rejecting does not change the gig | Same as AW-17 | The gig status is still "open". |
| AW-20 | Withdrawing does not change the gig | Gig 1 with one pending application. Withdraw it. | The gig status is still "open". |
| AW-21 | Withdrawing leaves the others alone | Gig 1 with three pending. Withdraw the first. | Other two still "pending". |

## 9.4 Which gig statuses allow these actions

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AW-22 | Reject on a cancelled gig | A pending application on a gig that was cancelled without going through the cancel action (set directly, so the automatic turn-down did not run) | 200. Status becomes "rejected". Rejecting never depends on the gig's status. |
| AW-23 | Reject on a completed gig | A pending application on a completed gig | 200. Rejected. |
| AW-24 | Reject on an in-progress gig | A pending application on an in-progress gig | 200. Rejected. |
| AW-25 | Withdraw on a cancelled gig | Same setup as AW-22 | 200. Withdrawn. |

**Why these are allowed.** Closing out a bid must never depend on the state of
the gig. Cancelling through the normal action already turns pending bids down
(section 5.6), but a gig can reach a non-open state by other routes, and a bid
left waiting with no way to resolve it would sit in listings for ever. Tidying up
is always allowed.

## 9.5 Bad requests

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| AW-26 | Withdraw an application that does not exist | Withdraw id 999999 | 404. Message says no application matches. |
| AW-27 | Reject an application that does not exist | Reject id 999999 | 404. |
| AW-28 | Non-numeric id | Withdraw id "abc" | 404. |
| AW-29 | A request body is not needed | Withdraw a pending application sending nothing | 200. These actions need no request body; the address identifies everything. |
| AW-30 | An unexpected body is ignored | Withdraw sending {"reason": "changed my mind"} | 200. The extra value is ignored. |
| AW-31 | Wrong method | Send a GET to the withdraw address | 405. Message says GET is not allowed. |

---

# 10. Accepting an application — the most important workflow

Address: `POST /api/applications/{id}/accept/`

Four things must all be true before an application can be accepted:

1. The application is still "pending".
2. The gig is still "open".
3. The supplier is not "inactive".
4. The supplier does not already hold 3 live agreements.

## 10.1 What a successful acceptance does

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AA-01 | Acceptance succeeds | Gig 1 open, one pending application from Supplier X at 420.00 | 201. The response is the new agreement, containing an id, the gig id, the supplier id, agreed rate 420.00, and status "active". |
| AA-02 | The application becomes accepted | After AA-01 | The application status is exactly "accepted". |
| AA-03 | The gig moves to in progress | After AA-01 | The gig status is exactly "in_progress". |
| AA-04 | An agreement is created | After AA-01 | Exactly one agreement exists for that gig. |
| AA-05 | The agreed rate copies the proposed rate | Application proposed 420.00 | The agreement's agreed rate is exactly 420.00. **Worked example:** Supplier X lists an hourly rate of $45.00 on their profile and proposes **$420.00 for the whole job** against a budget of $500.00. The agreement records $420.00 — not the $45.00 hourly figure, and not the $500.00 budget. |
| AA-06 | The agreed rate does not follow later changes | After AA-01, change Supplier X's hourly rate to 900.00 | The agreement's agreed rate is still 420.00. What was agreed cannot be changed afterwards by editing a profile. |
| AA-07 | The agreement links the right supplier | Gig 1 has applications from X, Y and Z. Accept Y's. | The agreement's supplier is Y, not X or Z. |
| AA-08 | The agreement links the right gig | Two gigs each with applications. Accept one. | The agreement's gig is the one that application belonged to. |
| AA-09 | A busy supplier can be hired | Set Supplier X to "busy", then accept | 201. The agreement is created. Only "inactive" blocks hiring — the specification names only that one value. |

## 10.2 Other pending applications are turned down automatically

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AA-10 | Three pending, accept one | Gig 1 with pending applications A (Supplier X), B (Supplier Y), C (Supplier Z). Accept B. | 201. Then: A is "rejected", B is "accepted", C is "rejected". The gig is "in_progress". One agreement exists, for Supplier Y. |
| AA-11 | Only one pending | Gig 1 with a single pending application. Accept it. | 201. That application is "accepted". Nothing else to turn down. |
| AA-12 | Five pending, accept one | Gig 1 with five pending applications. Accept the third. | 201. The third is "accepted"; the other four are all "rejected". |
| AA-13 | Applications on other gigs are untouched | Supplier X has pending applications on Gig 1 and Gig 2. Accept the one on Gig 1. | The Gig 2 application is still "pending". Turning down competitors applies only to the gig being filled. |
| AA-14 | Other suppliers keep their other chances | Supplier Y has pending applications on Gig 1 and Gig 2. Accept Supplier X on Gig 1. | Supplier Y's Gig 1 application is "rejected"; their Gig 2 application is still "pending". |

## 10.3 Already-finished applications are left exactly as they were

This is the mixed case: a gig can hold applications in several states at once.

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| AA-15 | Mixed states before accepting | Gig 1 with: A "rejected", B "withdrawn", C "pending", D "pending". Accept C. | 201. Then: **A is still "rejected", B is still "withdrawn"**, C is "accepted", D is "rejected". |
| AA-16 | Finished applications are not re-stamped | Same as AA-15 | A's and B's "last changed" timestamps are exactly the same as before the acceptance. They were not touched at all — not even re-saved with the same value. |
| AA-17 | Withdrawn stays withdrawn | Same as AA-15 | B's status is "withdrawn". It is **not** changed to "rejected". |

## 10.4 The four conditions — refusals

| ID | Condition broken | Setup | Exact expected result |
|---|---|---|---|
| AA-18 | Application already accepted | Accept once, then accept again | 409. Message says the application is accepted and can no longer be changed. **Still only one agreement exists.** |
| AA-19 | Application already rejected | Reject it, then accept it | 409. No agreement is created. |
| AA-20 | Application already withdrawn | Withdraw it, then accept it | 409. No agreement is created. |
| AA-21 | Gig is cancelled | A pending application on a cancelled gig | 409. Message says applications can only be accepted while a gig is open, and names "cancelled". The gig stays "cancelled". |
| AA-22 | Gig is completed | A pending application on a completed gig | 409, naming "completed". |
| AA-23 | Gig is already in progress | A pending application on an in-progress gig | 409, naming "in_progress". No second agreement is created. |
| AA-24 | Application does not exist | Accept id 999999 | 404. |
| AA-25 | Wrong method | Send a GET to the accept address | 405. |

## 10.5 Availability is checked at the moment of hiring

This is the deliberate edge case in the specification.

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| AV-01 | Available when applying, inactive when hired | 1. Supplier X is "available". 2. X applies to Gig 1 — 201. 3. X is changed to "inactive". 4. The creator accepts. | Step 4 gives **409**. Message says the supplier is inactive and cannot be given new work. |
| AV-02 | Nothing is left behind after that refusal | After AV-01 | The application is **still "pending"** (not accepted, not rejected). The gig is **still "open"**. **No agreement exists.** |
| AV-03 | It works once availability is restored | After AV-01, set Supplier X back to "available", then accept again | 201. The agreement is created, the application becomes "accepted", the gig becomes "in_progress". |
| AV-04 | Inactive from the start | Supplier X is "inactive", applies (201), then the creator accepts | 409. Applying was allowed; hiring is not. |
| AV-05 | Busy does not block hiring | Supplier X is "busy", applies, then is accepted | 201. Only "inactive" blocks hiring. |
| AV-06 | Hiring does not change availability | Supplier X is "available" and is hired | Supplier X's availability is **still "available"** afterwards. Nothing in the specification says hiring makes someone busy, so it does not. |
| AV-07 | Only the hired supplier's availability matters | Gig 1 has pending applications from X (available) and Y (inactive). Accept X's. | 201. Y being inactive does not block X from being hired. Y's application becomes "rejected" as normal. |

---

# 11. The three-agreement limit

**The rule.** A supplier may hold at most **3 live agreements** at once. "Live"
means the agreement is active — neither completed nor terminated.

**How the count is worked out.** Count only the supplier's agreements whose
status is "active". Completed and terminated ones are ignored entirely.

**Worked example.** Supplier X has four agreements:

| Agreement | Status | Counts towards the limit? |
|---|---|---|
| 1 | active | Yes |
| 2 | active | Yes |
| 3 | completed | No |
| 4 | terminated | No |

Live count = **2**. The limit is 3, so 2 is under the limit and Supplier X can
be hired for one more job. After that fifth hire the live count is 3, and any
further hire is refused.

## 11.1 Counting up to and past the limit

Set up a separate open gig with a pending application from Supplier X for each
step.

| ID | What is checked | Live agreements before | Action | Exact expected result |
|---|---|---|---|---|
| CP-01 | First hire | 0 | Accept | 201. Live count becomes 1. |
| CP-02 | Second hire | 1 | Accept | 201. Live count becomes 2. |
| CP-03 | Third hire — the limit itself | 2 | Accept | **201.** Live count becomes 3. Three is allowed; the rule is "no more than 3". |
| CP-04 | Fourth hire — over the limit | 3 | Accept | **409.** Message says the supplier already holds 3 live agreements and the maximum is 3. |
| CP-05 | Nothing is left behind | After CP-04 | Check everything | The application is still "pending". The gig is still "open". No fourth agreement exists. Live count is still exactly 3. |
| CP-06 | Fifth attempt also refused | After CP-04, try a different gig | 409. The limit does not drift. |

## 11.2 Finishing work frees a slot

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| CP-07 | Completing an agreement allows one more hire | Supplier X has 3 live agreements. Mark one complete. Then accept a fourth application. | The acceptance gives **201**. Live count is 3 again (two old plus one new), and one completed agreement sits alongside. |
| CP-08 | The completed one still exists | After CP-07 | The completed agreement is still there with status "completed". It was not deleted, only discounted. |
| CP-09 | Completed agreements never count | Supplier X has 3 completed agreements and 0 live ones. Accept an application. | 201. Three completed agreements do not block anything. |
| CP-10 | Terminated agreements never count | Supplier X has 3 terminated agreements and 0 live ones. Accept an application. | 201. |
| CP-11 | Mixed states, worked example | Supplier X has 2 active, 1 completed, 1 terminated. Accept an application. | 201, because the live count is 2. Afterwards the live count is 3. |
| CP-12 | Mixed states at the limit | Supplier X has 3 active, 5 completed, 2 terminated. Accept an application. | 409. Only the 3 active ones matter. |

**Note on terminated agreements.** There is no action in the specification that
turns an agreement into "terminated", so for CP-10 and CP-11 the state has to be
set directly in the database. This is a gap in the specification, not in the
build — see the note at GU-45.

## 11.3 The limit is per supplier, not shared

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| CP-13 | One supplier at the limit does not block another | Supplier X has 3 live agreements. Supplier Y has none. Accept an application from Y. | 201. Y is unaffected by X's workload. |
| CP-14 | Two suppliers can each hold 3 | X and Y each get hired three times | All six acceptances give 201. Each supplier has 3 live agreements. |
| CP-15 | The limit counts across different creators | X has 3 live agreements, all from Creator A's gigs. Creator B tries to hire X. | 409. The limit is about the supplier's total workload, not per creator. |

---

# 12. Everything must succeed together, or nothing at all

Accepting an application does four things: the application becomes accepted, the
competing applications become rejected, the gig moves to in progress, and an
agreement is created. **These are one single operation.** If any part fails, none
of them may remain.

| ID | What is checked | How to test it | Exact expected result |
|---|---|---|---|
| CA-01 | A failure part-way through undoes everything | Set up Gig 1 with three pending applications. Make the very last step (updating the gig) fail on purpose. Then accept one application. | Afterwards: the gig is still "open", **all three applications are still "pending"**, and **no agreement exists**. Not one of the four changes survives. |
| CA-02 | No half-finished state is ever visible | After CA-01 | The combination "application accepted but gig still open" never exists. Neither does "application accepted, gig in progress, but no agreement". Neither does "agreement created but competitors still pending". |
| CA-03 | The service still works afterwards | After CA-01, remove the forced failure and accept again | 201. The forced failure left nothing broken behind. |
| CA-04 | A refusal writes nothing at all | Try to accept an inactive supplier's application (see AV-01) | Nothing anywhere has changed: application pending, gig open, no agreement, competing applications still pending. |
| CA-05 | A refusal on the limit writes nothing | Try to accept a fourth agreement (see CP-04) | Nothing has changed. |
| CA-06 | Counts are consistent afterwards | After any successful acceptance on a gig with several applicants | The number of applications for that gig is unchanged — none were added or removed. Only their statuses changed. |

---

# 13. Agreements — listing and completing

## 13.1 Listing

Address: `GET /api/contracts/`

**Setup.** Creator A posts two gigs; Creator B posts one. Supplier X is hired on
Creator A's first gig and on Creator B's gig. Supplier Y is hired on Creator A's
second gig. That gives three agreements.

| ID | Request | Exact expected result |
|---|---|---|
| CL-01 | No filter | 200. Count 3. All three returned. |
| CL-02 | `?supplier_id=` Supplier X's id | 200. Count 2 — only X's agreements. |
| CL-03 | `?supplier_id=` Supplier Y's id | 200. Count 1. |
| CL-04 | `?creator_id=` Creator A's id | 200. Count 2 — the agreements on A's two gigs. |
| CL-05 | `?creator_id=` Creator B's id | 200. Count 1. |
| CL-06 | Both filters, matching | `?supplier_id=X&creator_id=A` | 200. Count 1 — the single agreement that is both X's and on A's gig. |
| CL-07 | Both filters, no overlap | `?supplier_id=Y&creator_id=B` | 200. Count 0, empty list. Y was never hired by B. |
| CL-08 | A supplier with no agreements | `?supplier_id=` Supplier Z's id | 200. Count 0, empty list. Not an error. |
| CL-09 | A supplier that does not exist | `?supplier_id=999999` | 200. Count 0, empty list. A number that matches nothing is a valid question with the answer "none". |
| CL-10 | A creator that does not exist | `?creator_id=999999` | 200. Count 0, empty list. |
| CL-11 | Supplier filter is not a number | `?supplier_id=abc` | 400. Message says a number is required. **Not** an empty list — the caller has made a mistake. |
| CL-12 | Creator filter is not a number | `?creator_id=abc` | 400. |
| CL-13 | Empty filter value | `?supplier_id=` | 200. Count 3. An empty filter is treated as no filter. |
| CL-14 | Completed agreements still appear | Complete one agreement, then list with no filter | 200. Count 3. Completing does not hide it. |
| CL-15 | Paging | Ask for page size 2 | 200. Count 3, 2 results, link to page 2. |
| CL-16 | Page beyond the last | Page size 2, page 3 | 404. |
| CL-17 | Filter combined with paging | `?supplier_id=X&page_size=1` | 200. Count 2 (X's total), 1 result. |
| CL-18 | Newest first | Three agreements created in order | The most recent appears first. |

**A note worth recording.** With no filter, this address returns **every
agreement on the platform**, including the rate agreed on each one. Because the
specification includes no sign-in, anyone can read it. That means every
supplier's pricing history is public to anyone who asks. This is a consequence of
the missing sign-in, not a choice, and it should be raised with whoever owns the
specification.

## 13.2 Completing an agreement

Address: `POST /api/contracts/{id}/complete/`

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| CC-01 | Complete a live agreement | Hire Supplier X on Gig 1 | 200. The agreement's status becomes exactly "completed". |
| CC-02 | Complete it twice | Complete it (200), then complete again | 409. Message says the agreement is completed and can no longer be completed. Status stays "completed". |
| CC-03 | Complete a terminated agreement | Set the agreement's status to "terminated" directly, then complete it | 409. Message says the agreement is terminated and can no longer be completed. |
| CC-04 | The gig is not changed | After CC-01 | The gig status is **still "in_progress"**. Completing the agreement does not automatically finish the gig. |
| CC-05 | The gig can then be finished | After CC-01, set the gig status to "completed" | 200. The gig becomes "completed". Two deliberate steps: the work is declared done, then the creator signs the gig off. |
| CC-06 | The order cannot be reversed | Hire Supplier X, then immediately try to set the gig to "completed" without completing the agreement | 409. The gig cannot be finished while its agreement is live. |
| CC-07 | Agreement does not exist | Complete id 999999 | 404. |
| CC-08 | Wrong method | Send a GET to the complete address | 405. |
| CC-09 | No body needed | Complete sending nothing | 200. |
| CC-10 | The frees-a-slot effect | See CP-07 | Completing reduces the supplier's live count by one. |

**Why completing the agreement does not finish the gig.** The specification
lists "in progress to completed" as a permitted status change on the gig. If
completing the agreement finished the gig automatically, that permitted change
could never be used. Keeping them separate also lets a creator sign off
separately from the supplier declaring the work delivered.

## 13.3 Agreements cannot be created or edited directly

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| CC-11 | No way to create an agreement by hand | Send a create request to `/api/contracts/` | 405. Message says the action is not allowed. Agreements only come from accepting an application. |
| CC-12 | No way to edit an agreement | Try to change an agreement's agreed rate at `/api/contracts/{id}/` | 404. That address does not exist at all, so there is nothing to edit. |
| CC-13 | No way to delete an agreement | Try to delete `/api/contracts/{id}/` | 404, for the same reason. |
| CC-14 | Agreements are not individually readable | Fetch `/api/contracts/{id}/` | 404. The specification only asks for the list. Individual agreements are reached through the list, or as the response to accepting. |

---

# 14. Reviews

Address: `POST /api/contracts/{id}/reviews/` and `GET /api/contracts/{id}/reviews/`

**The rules.** A review can only be left on a **completed** agreement. There are
exactly two kinds of review, and each kind may be left only once per agreement.
The rating must be a whole number from 1 to 5.

The two kinds:

| Value | Meaning |
|---|---|
| `creator_on_supplier` | The creator rates the supplier |
| `supplier_on_creator` | The supplier rates the creator |

## 14.1 Which agreements can be reviewed

| ID | Agreement status | Exact expected result |
|---|---|---|
| RV-01 | completed | 201. The review is created. |
| RV-02 | active | 409. Message says reviews can only be left on completed agreements, and names "active". No review is created. |
| RV-03 | terminated | 409, naming "terminated". No review is created. |

**On RV-03.** A terminated agreement can never be reviewed. That follows the
specification exactly, but it is worth flagging: how a job went wrong is often
the most useful thing a marketplace could record, and this rule makes it
impossible.

## 14.2 One review of each kind

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| RV-04 | The creator reviews the supplier | Completed agreement. Send kind "creator_on_supplier", rating 5 | 201. |
| RV-05 | The supplier then reviews the creator | After RV-04, send kind "supplier_on_creator", rating 4 | 201. Both reviews now exist on the same agreement. |
| RV-06 | The creator tries to review twice | After RV-04, send "creator_on_supplier" again with rating 1 | 409. Message says a creator_on_supplier review already exists for this agreement. Only the first review exists; its rating is still 5. |
| RV-07 | The supplier tries to review twice | After RV-05, send "supplier_on_creator" again | 409, with the matching message. |
| RV-08 | Both kinds, both refused on repeat | Leave both reviews, then try each kind again | Both further attempts give 409. Exactly two reviews exist. |
| RV-09 | Reviews on different agreements do not clash | Two completed agreements. Leave a "creator_on_supplier" review on each. | Both give 201. The limit is one per kind **per agreement**. |

## 14.3 Rating values

Use a completed agreement, and remove any existing review of that kind before
each row so the rating is the only thing being tested.

| ID | Rating sent | Exact expected result |
|---|---|---|
| RV-10 | 1 | 201. Stored as 1. The lowest allowed value. |
| RV-11 | 2 | 201. |
| RV-12 | 3 | 201. |
| RV-13 | 4 | 201. |
| RV-14 | 5 | 201. Stored as 5. The highest allowed value. |
| RV-15 | 0 | 400. Message says the value must be at least 1. |
| RV-16 | 6 | 400. Message says the value must be at most 5. |
| RV-17 | -1 | 400. Must be at least 1. |
| RV-18 | 10 | 400. Must be at most 5. |
| RV-19 | 3.5 | 400. Message says a whole number is required. A half-star is not allowed. |
| RV-20 | 4.0 | **201. Stored as 4.** A number with nothing after the decimal point counts as a whole number. |
| RV-21 | "abc" | 400. A whole number is required. |
| RV-22 | "3" (a number written as text) | 201. Stored as 3. Text that reads as a whole number is accepted. |
| RV-23 | "4.0" (as text) | 201. Stored as 4, same as RV-20. |
| RV-24 | "  4  " (spaces around it) | 201. Stored as 4. Surrounding spaces are ignored. |
| RV-25 | true | 400. A whole number is required. True is not treated as 1. |
| RV-26 | empty (no value) | 400. The field may not be empty. |
| RV-27 | omitted entirely | 400. "rating" listed as required. |
| RV-28 | 999999999999 | 400. Must be at most 5. The upper limit is checked, not just the type. |

**On RV-20 and RV-23.** `4.0` and `"4.0"` are accepted and stored as 4, while
`3.5` is refused. The rule being applied is "must represent a whole number",
not "must be typed as a whole number". This is worth knowing rather than
guessing: a test expecting `4.0` to be refused would fail against correct
behaviour.

## 14.4 The kind of review

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| RV-29 | Kind omitted | Send only a rating | 400. "reviewer_type" listed as required. |
| RV-30 | Kind not one of the two | Send "creator_on_creator" | 400. Message says it is not a valid choice. |
| RV-31 | Kind in the wrong case | Send "Creator_On_Supplier" | 400. Not a valid choice — the stored values are lower case. |
| RV-32 | Kind is empty text | Send "" | 400. Not a valid choice. |
| RV-33 | Kind is a number | Send 1 | 400. Not a valid choice. |

## 14.5 The comment

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| RV-34 | Comment supplied | Send a comment "Fast and clean." | 201. Stored exactly as sent. |
| RV-35 | Comment omitted | Send only kind and rating | 201. Stored comment is empty text. There is only ever one way to say "no comment". |
| RV-36 | Comment is empty text | Send comment "" | 201. Stored as empty text. |
| RV-37 | Comment is empty (no value) | Send comment with no value | 400. Message says the field may not be empty. Use empty text or leave it out instead. |
| RV-38 | Comment is a number | Send comment 123 | 201. Stored as the text "123". |
| RV-39 | Comment is a list | Send comment ["a"] | 400. Message says a valid text value is required. |
| RV-40 | Very long comment | Send a comment of 10,000 characters | 201. Stored in full; there is no length limit on comments. |
| RV-41 | Comment with line breaks and symbols | Send a multi-line comment containing quotes and emoji | 201. Stored exactly as sent, unchanged. |

## 14.6 Reading reviews

| ID | What is checked | Setup | Exact expected result |
|---|---|---|---|
| RV-42 | List an agreement's reviews | Completed agreement with both reviews | 200. Count 2. Each entry shows its id, agreement, kind, rating, comment and created date. |
| RV-43 | Agreement with no reviews | Completed agreement, none left yet | 200. Count 0, empty list. |
| RV-44 | Only that agreement's reviews | Two agreements, each with one review | Listing the first returns exactly its own one review. |
| RV-45 | Agreement does not exist | List reviews for id 999999 | 404. **Not** an empty list. |
| RV-46 | Reviews on an active agreement | An active agreement | 200. Count 0. Reading is allowed even though writing is not. |

## 14.7 Bad addresses

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| RV-47 | Review an agreement that does not exist | Send a review to agreement 999999 | 404. |
| RV-48 | The agreement cannot be set in the request | Send a review to agreement 1 with an extra field naming agreement 2 | 201, and the review belongs to **agreement 1**. The address decides which agreement; the extra value is ignored. |
| RV-49 | Wrong method | Send a delete to the reviews address | 405. |

---

# 15. Links between records, and empty values

Every record points at others. These tests check that those links are enforced,
and that a missing or removed record behaves sensibly.

## 15.1 Links must point at something real

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| RE-01 | Gig must name a real creator | Create a gig with creator id 999999 | 400. The id does not match any creator. No gig is created. |
| RE-02 | Application must name a real supplier | Apply with supplier id 999999 | 400. No application is created. |
| RE-03 | Application must name a real gig | Apply to gig id 999999 | 404. |
| RE-04 | Review must name a real agreement | Review agreement id 999999 | 404. |
| RE-05 | Completing must name a real agreement | Complete agreement id 999999 | 404. |
| RE-06 | Accepting must name a real application | Accept application id 999999 | 404. |

**Why some are 400 and others 404.** When the missing thing is named **inside**
the request, the request is wrong, so it is 400. When it is named **in the
address**, the thing being asked for does not exist, so it is 404.

## 15.2 Removing a record that others depend on

| ID | What is checked | Steps | Exact expected result |
|---|---|---|---|
| RE-07 | A creator with gigs cannot be removed | Creator A has Gig 1. Try to remove Creator A directly. | Refused. The creator and the gig both remain. Removing a creator must never quietly wipe out their gigs. |
| RE-08 | A supplier with applications cannot be removed | Supplier X has applied to Gig 1. Try to remove Supplier X directly. | Refused. Both remain. |
| RE-09 | A supplier with agreements cannot be removed | Supplier X holds an agreement. Try to remove Supplier X. | Refused. |
| RE-10 | Deleting a gig removes its applications | Gig 1 has 3 applications, no agreement. Delete the gig. | 204. The gig and all 3 applications are gone. An application means nothing without its gig. |
| RE-11 | Deleting a gig cannot remove an agreement | Gig 1 has an agreement. Delete the gig. | 409. Gig, agreement and any reviews all remain. |
| RE-12 | An agreement cannot lose its gig | Confirm after RE-11 | The agreement still points at a gig that exists. There are never agreements pointing at nothing. |
| RE-13 | A review cannot lose its agreement | Complete an agreement, leave a review, then try to delete the gig | 409. The review still points at an agreement that exists. |

## 15.3 Empty values

For each field, send it with no value at all and confirm the result.

| ID | Record and field | Exact expected result |
|---|---|---|
| RE-14 | Creator name empty | 400. May not be empty. |
| RE-15 | Creator email empty | 400. May not be empty. |
| RE-16 | Creator channel name empty | 400. May not be empty. |
| RE-17 | Supplier name empty | 400. May not be empty. |
| RE-18 | Supplier email empty | 400. May not be empty. |
| RE-19 | Supplier rate empty | 400. May not be empty. |
| RE-20 | Supplier skills empty | 400. May not be empty. Send an empty list instead. |
| RE-21 | Supplier availability empty | 400. Not a valid choice. |
| RE-22 | Gig creator empty | 400. May not be empty. |
| RE-23 | Gig title empty | 400. May not be empty. |
| RE-24 | Gig description empty | 400. May not be empty. |
| RE-25 | Gig budget empty | 400. May not be empty. |
| RE-26 | Gig category empty | 400. May not be empty. |
| RE-27 | Application supplier id empty | 400. May not be empty. |
| RE-28 | Application rate empty | 400. May not be empty. |
| RE-29 | Review kind empty | 400. Not a valid choice. |
| RE-30 | Review rating empty | 400. May not be empty. |
| RE-31 | Review comment empty | 400. May not be empty. Send empty text or leave it out. |

## 15.4 Values that are always set by the service, never by the caller

| ID | What is checked | Action | Exact expected result |
|---|---|---|---|
| RE-32 | A gig's id cannot be chosen | Create a gig sending id 999 | 201. The gig gets the next id in sequence; 999 is ignored. |
| RE-33 | Created and changed dates cannot be set | Create a gig sending a created date of last year | 201. The stored created date is now, not the value sent. |
| RE-34 | An application's status cannot be chosen | Apply sending status "accepted" | 201. The stored status is "pending". |
| RE-35 | An agreement's status cannot be chosen | Not possible — agreements cannot be created directly | See CC-11. |
| RE-36 | A changed date updates on change | Note a gig's changed date, wait, then change its title | The changed date is later than before. The created date is unchanged. |
| RE-37 | Turned-down applications get a new changed date | Note a pending application's changed date, then accept a competitor | The turned-down application's changed date is later than before, because its status really did change. |
| RE-38 | Already-finished applications keep their old date | Note a rejected application's changed date, then accept a competitor | The date is **unchanged**. It was not touched. |

---

# 16. The complete journey

One test, run from an empty database, covering the whole flow end to end.

| ID | Step | Action | Exact expected result |
|---|---|---|---|
| E2E-01 | 1 | Create Creator A | 201. Note the id. |
| | 2 | Create Supplier X | 201. Note the id. |
| | 3 | Create Supplier Y | 201. Note the id. |
| | 4 | Create Gig 1 under Creator A, budget 500.00, category "editing" | 201. Status "open". |
| | 5 | Supplier X applies at 420.00 | 201. Status "pending". |
| | 6 | Supplier Y applies at 390.00 | 201. Status "pending". |
| | 7 | Try to review the not-yet-existing agreement | Not possible — there is no agreement id yet. |
| | 8 | Creator accepts Supplier X's application | 201. An agreement is returned with agreed rate 420.00 and status "active". |
| | 9 | Check Supplier X's application | Status is "accepted". |
| | 10 | Check Supplier Y's application | Status is "rejected" — turned down automatically. |
| | 11 | Check the gig | Status is "in_progress". |
| | 12 | Check the agreed rate | Exactly 420.00 — the amount Supplier X proposed for the job. Not their $45.00 hourly profile rate, and not the $500.00 budget. |
| | 13 | Try to leave a review now | 409. The agreement is still active. |
| | 14 | Try to change the gig's budget | 409. Frozen once the gig left open. |
| | 15 | Try to delete the gig | 409. It has a live agreement. |
| | 16 | List agreements filtered by Supplier X | 200, count 1. |
| | 17 | List agreements filtered by Creator A | 200, count 1. |
| | 18 | Mark the agreement complete | 200. Status "completed". |
| | 19 | Check the gig again | Still "in_progress" — completing the agreement does not finish the gig. |
| | 20 | Set the gig to "completed" | 200. Status "completed". |
| | 21 | Creator reviews the supplier, rating 5 | 201. |
| | 22 | Supplier reviews the creator, rating 4 | 201. |
| | 23 | Creator tries to review again | 409. Only one review of each kind. |
| | 24 | List the agreement's reviews | 200, count 2. |
| | 25 | Try to delete the gig again | 409. It has agreement history; the agreement and both reviews must survive. |
| | 26 | Check Supplier X's availability after being hired | Still "available" — one live agreement, well under the limit of three. |
| | 27 | Confirm the final state | Gig "completed". Supplier X's application "accepted". Supplier Y's application "rejected". Agreement "completed", agreed rate $420.00. Two reviews exist. Supplier X holds 0 live agreements and is "available", so they are free to be hired again. |

---

# 17. Error behaviour across the whole service

| ID | What is checked | How to test | Exact expected result |
|---|---|---|---|
| EF-01 | Nothing ever produces an internal error | Run every negative test in this document | No request anywhere returns a 500. Every rejection is a 400, 404, 405 or 409. |
| EF-02 | Database rules never leak to the caller | Trigger every duplicate and out-of-range case | No response ever contains raw database wording such as "UNIQUE constraint failed" or "IntegrityError". |
| EF-03 | Rejections explain themselves | Check each 400 and 409 message | Every message says what was wrong in readable words. None is blank or generic. |
| EF-04 | Field errors name the field | Send a bad budget | The response identifies "budget" as the field at fault, so a caller knows what to fix. |
| EF-05 | Several problems reported together | Send a gig with no title **and** a budget of -5 | 400. Both problems appear in one response, rather than only the first. |
| EF-06 | Situation errors carry a short code | Trigger each 409 | Each response contains a short unchanging code, for example "gig_not_open" or "workload_cap_reached", alongside the readable message. |
| EF-07 | Codes stay the same across releases | Compare codes to the list below | The code for each situation is stable, so automated checks can rely on it rather than on wording. |
| EF-08 | Unknown addresses | Request `/api/nonsense/` | 404. |
| EF-09 | Wrong method on a known address | Send a delete to `/api/gigs/` | 405. Message says the method is not allowed. |
| EF-10 | Badly formed request body | Send text that is not valid data at all | 400. Message says the body could not be read. |

## The short codes used for situation errors

| Code | When it appears |
|---|---|
| `gig_not_open` | Applying to, or hiring on, a gig that is not open |
| `duplicate_pending_application` | A supplier already has a live application on that gig |
| `application_not_pending` | Accepting, rejecting or withdrawing something already finished |
| `supplier_not_hireable` | The supplier is inactive at the moment of hiring |
| `workload_cap_reached` | The supplier already holds 3 live agreements |
| `invalid_status_transition` | A gig status change that is not permitted |
| `gig_fields_immutable` | Changing budget or category after the gig left open |
| `gig_has_active_contract` | Deleting or closing a gig with a live agreement |
| `gig_has_contract_history` | Deleting a gig that has agreement history |
| `contract_not_active` | Completing an agreement that is already finished |
| `contract_not_completed` | Reviewing an agreement that is not completed |
| `duplicate_review` | A review of that kind already exists |

---

# 18. Checklist coverage

Every item from the supplied business-rules checklist, and the tests that cover it.

| # | Checklist item | Covered by | Status |
|---|---|---|---|
| 1 | Creator fields, unique email, rejections | CR-01 to CR-30 | Covered. See note (a) on data types. |
| 2 | Supplier fields, availability values, rate > 0, unique email | SU-01 to SU-65 | Covered. `busy` is worked out by the service — see note (d) |
| 2 | Availability affects hiring, not applying | SU-54, SU-55, AP-07, AV-01 to AV-07 | Covered |
| 3 | Gig fields, budget > 0, valid statuses | GC-01 to GC-31 | Covered |
| 3 | Invalid status on create rejected | GC-32 to GC-40 | Covered |
| 4 | Open gig: applications, updates, delete | AP-01, GU-01, GD-01 | Covered |
| 4 | In-progress gig: no applications, budget/category frozen, status may change | AP-09, GU-13, GU-14, GU-30 | Covered |
| 4 | Completed gig: no applications, frozen, readable | AP-10, GU-15, GU-16, GR-05 | Covered |
| 4 | Cancelled gig: no applications, frozen, readable | AP-11, GU-17, GU-18, GR-06 | Covered |
| 5 | Filter by category and status, combined | GF-01 to GF-14 | Covered |
| 5 | No matches gives an empty set, not an error | GF-04, GF-08, GF-13 | Covered |
| 5 | Paging: first, last, beyond last | GF-20 to GF-38 | Covered |
| 5 | Invalid filter values handled cleanly | GF-15, GF-16 | Covered |
| 6 | Budget change allowed while open | GU-01 | Covered |
| 6 | Budget frozen in all three later states | GU-13, GU-15, GU-17 | Covered |
| 6 | Category frozen in all three later states | GU-14, GU-16, GU-18 | Covered |
| 6 | Permitted status changes | GU-24 to GU-44 | Covered — all 16 combinations |
| 7 | Delete allowed with no live agreement | GD-01, GD-02, GD-07 | Covered |
| 7 | Delete refused with a live agreement | GD-03, GD-04 | Covered |
| 7 | Agreement and reviews survive | GD-04, GD-05, GD-06, RE-11, RE-13 | Covered |
| 8 | Applying with supplier_id and rate | AP-01 to AP-08, AP-19 to AP-34 | Covered |
| 9 | Cannot apply to a non-open gig | AP-09, AP-10, AP-11 | Covered. Returns 409 — see note (c). |
| 10 | No second live application | AP-12, AP-13 | Covered |
| 11 | May apply again after rejection | AP-15, AP-16, AP-17 | Covered |
| 12 | May apply again after withdrawal | AP-14, AP-16, AP-17 | Covered |
| 13 | Four application statuses, finished is final | AW-01 to AW-16 | Covered — all 12 combinations |
| 14 | Withdraw only while pending | AW-01, AW-04, AW-07, AW-10, AW-13 | Covered |
| 15 | Reject only while pending | AW-02, AW-05, AW-08, AW-11, AW-14 | Covered |
| 16 | Four conditions before hiring | AA-18 to AA-23, AV-01, CP-04 | Covered |
| 17 | What hiring does, in full | AA-01 to AA-14 | Covered |
| 18 | Hiring is all-or-nothing | CA-01 to CA-06 | Covered |
| 19 | Only pending competitors are turned down | AA-15, AA-16, AA-17, RE-38 | Covered |
| 20 | Live means not completed and not terminated | CP-09, CP-10, CP-11 | Covered |
| 21 | Fourth live agreement refused | CP-03, CP-04, CP-05 | Covered |
| 22 | Finished agreements do not count | CP-07 to CP-12 | Covered. Terminated needs direct database setup — see note (d). |
| 23 | Availability checked when hiring | AV-01, AV-04 | Covered |
| 24 | A refused hire leaves nothing behind | AV-02, CA-04 | Covered |
| 25 | Cannot hire on an already-accepted application | AA-18, AW-06 | Covered |
| 26 | Cannot hire on a rejected application | AA-19, AW-09 | Covered |
| 27 | Cannot hire on a withdrawn application | AA-20, AW-12 | Covered |
| 28 | Agreement created automatically, rate copied | AA-01, AA-04, AA-05, AA-06, CC-11 | Covered |
| 29 | Agreement statuses, starts active | AA-01, CC-01, CC-03 | Covered |
| 30 | Completing an agreement, frees a slot | CC-01, CC-10, CP-07 | Covered |
| 31 | Completing twice, or completing a terminated one | CC-02, CC-03 | Covered |
| 32 | Listing agreements by supplier and creator | CL-01 to CL-18 | Covered |
| 33 | Reviews only on completed agreements | RV-01, RV-02, RV-03 | Covered |
| 34 | Two kinds of review | RV-04, RV-05, RV-30 | Covered |
| 35 | Rating between 1 and 5 | RV-10 to RV-28 | Covered |
| 36 | One review of each kind per agreement | RV-06 to RV-09 | Covered |
| 37 | Review examples, valid and invalid | RV-04 to RV-09 | Covered |
| 38 | Email unique for creators and suppliers | CR-15 to CR-17, SU-36, SU-37, SU-38 | Covered |
| 39 | Numeric limits, never a database error | SU-18 to SU-25, GC-18 to GC-24, AP-26 to AP-31, RV-15 to RV-28, EF-01, EF-02 | Covered |
| 40 | The complete journey | E2E-01 | Covered |
| 41 | The 21 priority negative scenarios | All listed above | Covered |
| 42 | The state machines | GU-24 to GU-39, AW-01 to AW-12, CC-01 to CC-03, RV-01 to RV-09 | Covered |

## Notes on the items that are not a clean pass

**(a) Whole numbers are accepted where text is expected.** Sending a name or
category as `123` is accepted and stored as the text `"123"`. True/false values,
real lists and real nested values are all correctly refused, and text that merely
*looks* like a list — `"['hello']"` — is correctly accepted, because it is text.
So the rule "wrong types are refused" holds for every type except numbers, which
are converted. This is the framework's standard behaviour and exists because
digits legitimately appear in text fields. Nothing is corrupted. See the "What
counts as valid text" table near the top.

**(b) Applying to a non-open gig returns 409, not 400.** The checklist says 400
for this one case, while allowing "400 / 409" elsewhere. Both are clean refusals
and the original specification permits either. 409 is used consistently for "the
request is fine but the situation moved on"; the tests assert 409.

**(c) Terminated agreements cannot be produced through the service.** The
specification lists "terminated" as a valid state but provides no action that
reaches it. Cases CP-10, CP-11, CC-03, RV-03 and WL-03/WL-05 therefore set the
state directly in the database. The tests are valid, but they exercise a state
real users cannot reach. This is question Q2 in DECISIONS.md.

**(d) "Busy" is worked out by the service, not sent by the caller.** The
specification lists `busy` as an availability value but gives it no meaning —
rule 5 blocks only `inactive`, so as written `busy` affects nothing. We read it as
"holding the maximum of three live agreements", which is how marketplaces
normally present availability, and the service maintains it. A caller sending
`busy` gets 400. This is an interpretation (I3 in DECISIONS.md), not a
specification requirement, and cases SU-56 to SU-65 test it.

**(e) Cancelling a gig turns down its pending bids.** The specification does not
say what happens to them. We turn them down, matching how closing a job posting
behaves elsewhere. Interpretation I9; cases GU-46 to GU-54.

---

# 19. Totals

| Area | Cases |
|---|---|
| Creator | 38 |
| Supplier, including availability | 65 |
| Gig — create and read | 47 |
| Gig — update, transitions, cancel cascade | 54 |
| Gig — delete | 9 |
| Gig — filter and page | 38 |
| Applying and listing applications | 42 |
| Withdraw and reject | 31 |
| Hiring, and availability at hiring | 32 |
| The three-agreement limit | 21 |
| All-or-nothing hiring | 6 |
| Agreements — list and complete | 32 |
| Reviews | 49 |
| Links and empty values | 38 |
| What can be changed or removed | 12 |
| Complete journey | 1 |
| Error behaviour | 10 |
| **Total** | **525** |

Roughly one in four is a straightforward success case; the rest are refusals,
edge values, and combinations. That balance is deliberate — the successes prove
the service works, and the refusals prove it cannot be made to do the wrong
thing.

---

# 20. What can be changed or removed — the full picture

Because the service has no sign-in, **anyone** can perform any action. So this
table is about what is *possible at all*, not about who is permitted.

| Record | Can be changed? | Can be deleted? |
|---|---|---|
| Creator | Yes — name, email, channel name | **No**, 405 |
| Supplier | Yes — name, email, skills, rate, availability | **No**, 405. Retire by setting availability to "inactive" |
| Gig — open | Yes, every field | **Yes**, 204 |
| Gig — in progress | Status only, and only once no live agreement remains | **No**, 409 |
| Gig — completed | Title and description only | **No**, 409 |
| Gig — cancelled | Title and description only | **Yes**, if no agreement was ever made |
| Application | No direct edits — only accept, reject, withdraw | Only by deleting its gig |
| Agreement | No — that address does not exist (404) | No, 404 |
| Review | No | No |

| ID | What is checked | Exact expected result |
|---|---|---|
| PD-01 | Delete an open gig | 204 |
| PD-02 | Delete an in-progress gig | 409 `gig_has_active_contract`. **Never possible** — being in progress means a live agreement exists, which is exactly what rule 7 protects |
| PD-03 | Delete a completed gig | 409 `gig_has_contract_history`. **Never possible** — reaching completed requires having had an agreement |
| PD-04 | Delete a cancelled gig that never had an agreement | 204 |
| PD-05 | Delete a creator | 405 |
| PD-06 | Delete a supplier | 405 |
| PD-07 | Delete an agreement | 404 — no such address |
| PD-08 | Delete a review | 405 |
| PD-09 | Delete an application directly | 404 — no such address |
| PD-10 | Change an agreement's agreed rate | 404 — no such address |
| PD-11 | Change an application's status directly | 404 — no such address. Status changes only through accept, reject and withdraw |
| PD-12 | Change a review's rating | 405 |

---

# 21. The three-agreement limit counts agreements, not applications

Applying is free. Only being hired consumes capacity.

| ID | Supplier holds | Live count | Can be hired again? |
|---|---|---|---|
| WL-01 | 11 pending applications, 0 agreements | 0 | **Yes**, 201 |
| WL-02 | 2 active agreements plus 8 pending applications | 2 | **Yes**, 201 |
| WL-03 | 2 active, 1 completed, 1 terminated | 2 | **Yes**, 201 |
| WL-04 | 3 active | 3 | **No**, 409 |
| WL-05 | 3 active, 5 completed, 2 terminated | 3 | **No**, 409 |
| WL-06 | 3 active plus 11 pending applications | 3 | **No**, 409 — and the pending applications remain pending, untouched |

**Worked example for WL-06.** A supplier bids on 14 gigs and is hired for 3 of
them. Live count is 3, so the fourth hire is refused. The remaining 11 bids stay
pending — they are not rejected, not cancelled, and do not count. Bidding widely
is exactly what a marketplace wants suppliers to do, so it costs them nothing.
