# Submission — School Management System (Zoho CRM + Creator)

**Submitted by:** Hitarth Jangid · jhitarth777@gmail.com
**Assignment:** Zoho Developer — School Management System

---

## Access

| What | Where |
|---|---|
| Zoho CRM implementation | *(share the org: Setup → Users → add `sagar@it-guy.tech` as Administrator)* |
| Zoho Creator Parent Portal | *(Share → add `sagar@it-guy.tech` as Developer; a demo parent login is listed below)* |
| Working CRM Webform | *(paste the published webform URL)* |
| Demo parent login | *(email + temporary password for the customer portal)* |

---

## 1. Data structure and relationships

Twenty-two modules. Three ideas drive the whole model:

**The academic year is an entity, not a text field.** Every year-scoped record points at an
`Academic_Years` record, which is what makes history queryable instead of overwritten.

**`Class_Sections` is the class *instance* for one year** — Grade 5-A in 2026-27 — and it is
what students actually attach to. `Classes` stays a year-independent grade master.

**`Enrollments` is the history spine.** One row per student per academic year, holding the
section, roll number, attendance counters and final result for that year. Promotion never
edits an old row: it closes the current Enrollment and opens a new one. Last year's class,
roll number, attendance percentage and results stay intact forever.

```
Leads ──(confirm admission)──> Students ──1:N──> Enrollments ──N:1──> Class_Sections
                                  │                  │                   ├─> Classes
                                  │                  │                   ├─> Academic_Years
                                  │                  │                   ├─> Teachers (class teacher)
                                  │                  │                   └─> Subject_Allocations ─> Subjects + Teachers
                                  ├──> Attendance      (unique per student per date)
                                  ├──> Marks ──> Exam_Results  (per exam, with class + section rank)
                                  ├──> Student_Fees ──> Fee_Installments ──> Payments
                                  └──> Contacts (Parent)   ← the portal identity
```

Relationships that carry their own data are junction modules, not multi-selects:
`Subject_Allocations` (section × subject × teacher × periods) and `Exam_Schedules`
(exam × section × subject × date × max marks). That is what lets a 25-mark unit test and a
100-mark final coexist without a line of extra code.

Integrity is pushed into the platform wherever the platform can hold it: unique key fields
(`Attendance_Key`, `Marks_Key`, `Enrollment_Key`, `Result_Key`, `Student_ID`) make duplicates
impossible from the UI, the API and imports alike. Deluge is used only where a rule has to
look at other records — holidays, enrolment status, installment balances.

Derived numbers — attendance %, fee outstanding, exam totals and ranks — are stored and
maintained incrementally by workflow functions, not recomputed on read. So the record, the
dashboard and the parent portal always show the same number, and reports stay fast at
5,000 students.

---

## 2. CRM ↔ Creator integration

**CRM owns the data. Creator renders it live. Nothing is duplicated.**

The parent portal is a **pages-first** Creator app. Every screen is a Page whose Deluge
snippet calls a function that reads from CRM over **COQL** at render time. Creator holds
three tiny forms — an identity cache, an access log, and the leave requests it originates.
It holds no students, no marks, no attendance, no fees.

I chose pull over a scheduled sync deliberately. A sync gives you two copies of every mark,
a window in which they disagree, a nightly cost of `O(all records)` to serve a few hundred
page views, and reconciliation code — which is the buggiest part of any project shaped like
this. Pulling the ~30 rows a parent actually opens is cheaper *and* correct by construction:
the portal cannot show a stale fee balance because it has no fee balance of its own.

**Parent ↔ student link.** The key is the parent's **email**, and it is established at
admission time, not by the parent. When a lead converts, CRM creates or reuses a Contact
with that email and points the Student's `Parent` lookup at it. Creator is published as a
Customer Portal, so `zoho.loginuser` is the same string as `Contacts.Email` — no student ID,
roll number or DOB is ever used as a credential, because those are guessable and printed on
every report card.

**Authorisation.** Every data function starts with `portal.assertStudentAccess(studentId)`,
which re-resolves the signed-in parent and checks the requested student against *their own*
children. A student id in a URL is a hint about which child to display, never a grant of
access. Denials are logged. This is the difference between a portal and an IDOR.

**Three channels, tightly scoped:**

1. *Creator → CRM read* — COQL over a read-only connection owned by a dedicated
   integration user. One call per page, columns enumerated.
2. *Creator → CRM write* — `Leave_Requests` create, and nothing else. Its connection holds
   exactly one scope. Failed writes queue in Creator with a bounded retry.
3. *CRM → Creator push* — only two events, because only two can't be discovered by a pull:
   the parent↔student mapping changed (invalidate the identity cache), and a leave request
   was approved or rejected. Both are secret-authenticated.

When a leave is approved, CRM upserts the affected school days as `Approved Leave`
attendance on the unique key — so approval flows through the *same* rollup as normal
marking. One code path, no drift.

---

## 3. Additional feature — Student Early-Warning Engine

**The problem.** A school already holds every signal needed to catch a child slipping —
attendance, marks, fee status — but in three modules nobody joins. Individually each signal
is ignorable: one absence, one bad unit test, one late instalment. Together they are the
profile of a student about to fail the year. Most schools see the pattern at the
parent-teacher meeting, months after an intervention would still have worked.

I picked it over bulk report cards or a transport module for two reasons: it needs **no new
data entry** (every input is already captured for other purposes), and it converts data the
school already owns into **an action with a specific person's name on it** — not another
dashboard.

**What it does.** Nightly, every active student is scored on four weighted signals —
attendance below 75% (40), three or more consecutive absences (25), a 15-point drop between
the last two exams (20), fees overdue past 30 days (15) — and banded. Medium creates a Task
for the class teacher; High adds a parent email; Critical escalates. A separate same-day
"your child was absent today" alert runs after morning marking. All thresholds and weights
live in an `App_Settings` record, so the school retunes the model without a developer.

**Why it is built this way.** This is the only thing in the system that touches every
student every night, so it is where scalability actually bites:

- **No N+1.** The naive version queries attendance, marks and fees per student — 6,000 API
  calls a night at 2,000 students, which exhausts the daily credit budget before it
  finishes. The engine instead runs a fixed number of paged COQL sweeps (200 rows a page)
  and joins them in memory in one pass: ~60 calls instead of ~6,000.
- **It reads pre-aggregated values.** Attendance % is already maintained on the Enrollment
  and exam percentages on `Exam_Results`, so nothing is re-aggregated. The only raw scan is
  a 14-day absence window for streak detection — bounded, not growing with the year.
- **It notifies on band *change*, not on state.** Without that, 80 at-risk students means 80
  identical emails every night and parents mute the sender within a week. This is the most
  important rule in the file.
- **Writes are batched** — upsert, 100 per call, workflow triggers suppressed: ~20 write
  calls, not 2,000.
- **Idempotent and resumable** — unique `Risk_Key`, every loop page-bounded.

---

## Repository contents

```
docs/       01 data model · 02 CRM build guide · 03 Creator guide
            04 integration · 05 reports & dashboards · 06 additional feature
deluge/crm/ 00 utils · 01 student ID · 02 admission conversion · 03 attendance
            04 marks & results · 05 fees & payments · 06 promotion
            07 early-warning engine · 08 Creator sync
deluge/creator/ 01 portal identity & authorisation · 02 portal data · 03 leave write-back
clientscript/   marks entry validation
webform/        admission enquiry webform spec
```
