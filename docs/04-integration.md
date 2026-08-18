# CRM ↔ Creator Integration

## The one-line version

**CRM owns the data; Creator renders it live over COQL; nothing is duplicated; only two
events are ever pushed from CRM to Creator.**

---

## Why pull, not sync

The obvious build is a nightly (or 15-minute) sync that copies Students, Attendance, Marks
and Fees into Creator forms. It is also the wrong one for this system:

| | Sync-based | Pull-based (chosen) |
|---|---|---|
| Copies of a mark | 2 | 1 |
| Staleness window | up to one sync interval | none |
| Failure mode | silent divergence — the portal shows a fee as unpaid after the parent paid | an API error, visible and retryable |
| Cost as school grows | O(all records) every cycle, forever | O(what a parent actually opens) |
| Reconciliation code | needed, and it is the buggiest part of any such project | none |

A parent portal is a **low-traffic, read-heavy** surface: a few hundred page views a day
against a database of hundreds of thousands of rows. Copying the whole database every night
to serve that is backwards. Pulling only the ~30 rows a parent actually looks at is both
cheaper and correct by construction.

The trade-off is a live dependency on CRM availability, and per-page API latency. Both are
handled: the identity resolution (the only per-page overhead that isn't the data itself) is
cached for 30 minutes, and every page is a single COQL call selecting only displayed
columns.

---

## The three channels

### 1. Creator → CRM, read (the main channel)

`portal.coql()` → `POST /crm/v5/coql` over connection **`crm_conn`**.

- Read-only OAuth scopes, authorised by a dedicated integration user whose CRM profile has
  no write permission on any school module.
- One call per page. Columns are enumerated, never `select *`.
- Related-module fields are traversed in the query itself
  (`Current_Class_Section.Class_Teacher.Name`), so a profile page is one round trip rather
  than four.

### 2. Creator → CRM, write (narrow)

`POST /crm/v5/Leave_Requests` over **`crm_write_conn`** — scope
`ZohoCRM.modules.leaverequests.CREATE` and nothing else. A parent can create a leave
request. That is the entire write surface of the portal. Failed writes are queued in
Creator with a bounded retry (5 attempts, then "contact the office"), so a network blip
never silently loses a parent's request.

### 3. CRM → Creator, push (two events only)

Over **`creator_conn`**, to Creator functions published for REST access:

| Event | CRM trigger | Creator function | Why a pull can't do it |
|---|---|---|---|
| Parent↔student mapping changed | Workflow on Students (`Parent`, `Secondary_Parent`, `Status`, `Current_Class_Section`) | `invalidateParentCache(email)` | Creator can't know its cache went stale |
| Leave approved / rejected | Workflow on Leave_Requests | `updateLeaveStatus(crmRecordId, status, secret)` | The parent needs to see the outcome without polling |

Both calls carry a shared secret held in `App_Config` / `App_Settings`, so the published
Creator endpoint cannot be driven by anyone who merely knows its URL.

---

## The end-to-end flow

```
 Public website
      │  webform (reCAPTCHA)
      ▼
  CRM Leads ──── follow-up workflow, tasks, campus visit, assessment
      │
      │  Lead_Status = "Admission Confirmed"
      ▼
  school.confirmAdmission()
      ├─ Contact (parent)  ← email becomes the portal identity
      ├─ Student           ← Student_ID from the sequence generator
      ├─ Enrollment        ← least-loaded section of the target class
      └─ Student_Fee + Fee_Installments  ← from the class fee structure
      │
      ▼
  Day-to-day CRM operations
      ├─ Attendance  → incremental rollup onto Enrollment
      ├─ Marks       → validation → Exam_Results with ranks on publish
      └─ Payments    → FIFO allocation → fee summary + receipt email
      │
      │  COQL, live, authorised per student
      ▼
  Creator Parent Portal
      └─ Leave request ──write──► CRM Leave_Requests
                                     │ approved
                                     ▼
                          Attendance upserted as "Approved Leave"
                          → the same rollup → attendance % updated
```

---

## Handling change safely ("changes to important information are handled appropriately")

| Change | What happens | Why it's safe |
|---|---|---|
| Attendance corrected | Row updated in place (unique key), rollup adjusts by delta | No duplicate row; percentage stays consistent |
| Mark corrected after publish | `validateMark` re-grades the row; *Recompute Results* re-ranks the exam via upsert | `Result_Key` means recompute updates, never duplicates |
| Cheque bounces | Payment `Status` → Bounced → `recomputeFeeSummary` re-derives everything from successful payments only | Balances can't drift, because they are never incrementally patched |
| Guardian email changed | Portal cache invalidated for both old and new email | Old guardian loses access immediately |
| Student changes section mid-year | Enrollment repointed, section strengths adjusted | Attendance and marks stay attached to the Enrollment, so history follows the child |
| Student leaves | `Status = Transferred Out`, Enrollment closed | Portal resolution excludes them; all history retained |
| New academic year | `promoteStudents` opens new Enrollments | **Nothing from the old year is edited** |

---

## Failure and idempotency

Every entry point is safe to run twice:

| Function | Guard |
|---|---|
| `confirmAdmission` | Checks for an existing Student with that `Source_Lead`; rolls back partial creates on any error |
| `markSectionAttendance` | Reads the day's rows first; unique `Attendance_Key` as the backstop |
| `publishExamResults` | Upsert on `Result_Key` |
| `promoteStudents` | Unique `Enrollment_Key` |
| `recomputeFeeSummary` | Fully derived from payment rows — running it 100 times gives the same answer |
| `runEarlyWarning` | Upsert on `Risk_Key`; notifies only on an upward band change |
| `notifyAbsenceSameDay` | `Parent_Notified` stamp |
| Leave write-back | Bounded retry, then a clear message to the parent |
