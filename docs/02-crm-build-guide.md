# CRM Build Guide — order of operations

Build in this order. Each step only depends on steps above it, so nothing has to be
revisited.

---

## Step 0 — Org setup

1. Sign up for **Zoho One trial** → open **CRM** and **Creator**.
2. CRM → Setup → **Company Details**: set the time zone and locale (fee due dates and
   attendance dates are date-only fields, and a mismatched org timezone shifts them).
3. Note your **data centre** (`.in` / `.com` / `.eu`). Every `invokeurl` in
   `deluge/` uses `https://www.zohoapis.in` — search-and-replace if yours differs.

## Step 1 — Connections

Setup → Developer Space → **Connections** → *Zoho OAuth*.

| Name | Where | Scopes |
|---|---|---|
| `crmconn` | CRM | `ZohoCRM.modules.ALL`, `ZohoCRM.coql.READ`, `ZohoCRM.settings.ALL` |
| `creator_conn` | CRM | `ZohoCreator.form.CREATE`, `ZohoCreator.report.UPDATE` |
| `crm_conn` | Creator | `ZohoCRM.coql.READ`, `ZohoCRM.modules.READ` |
| `crm_write_conn` | Creator | `ZohoCRM.modules.leaverequests.CREATE` |

> The two Creator connections are authorised by a **dedicated integration user**, not by
> an admin. `crm_conn` is read-only and `crm_write_conn` can only create Leave Requests.
> That is what makes a bug in the parent portal unable to touch marks or fees.

## Step 2 — Modules

Create in this sequence (each one's lookups need the previous ones to exist):

```
App_Settings, Sequence_Counters
  → Academic_Years → Classes → Teachers → Subjects
  → Class_Sections → Subject_Allocations
  → Students → Enrollments
  → Holidays → Attendance
  → Examinations → Exam_Schedules → Marks → Exam_Results
  → Fee_Structures → Student_Fees → Fee_Installments → Payments
  → Announcements → Leave_Requests → Student_Risk_Flags
```

Field definitions: `01-data-model.md`.

**Mark these fields Unique** (Edit field → *Do not allow duplicate values*) — they are the
duplicate-prevention layer and several functions depend on them:

`Students.Student_ID` · `Enrollments.Enrollment_Key` · `Attendance.Attendance_Key` ·
`Marks.Marks_Key` · `Exam_Results.Result_Key` · `Class_Sections.Section_Key` ·
`Subject_Allocations.Allocation_Key` · `Student_Risk_Flags.Risk_Key` ·
`Holidays.Holiday_Key` · `Sequence_Counters.Counter_Key` · `App_Settings.Setting_Key` ·
`Contacts.Email` · `Teachers.Employee_ID`

**Formula fields**

| Module | Field | Formula |
|---|---|---|
| Fee_Structures | `Total_Fee` | `Tuition_Fee + Transport_Fee + Lab_Fee + Exam_Fee + Misc_Fee` |
| Student_Fees | `Net_Payable` | `Total_Fee - Concession_Amount` |
| Student_Fees | `Outstanding` | `Total_Fee - Concession_Amount - Amount_Paid` |
| Fee_Installments | `Balance` | `Amount_Due - Amount_Paid` |
| Marks | `Percentage` | `if(Max_Marks > 0, round(Marks_Obtained * 100 / Max_Marks, 2), 0)` |
| Students | `Age` | `(Today() - DOB) / 365` |

## Step 3 — Functions

Deployed from the repo, not pasted by hand. `tools/port_to_standalone.py` turns
`deluge/crm/*.dg` into `tools/functions.json`, and the loader in the browser creates each
function and PUTs its body through the settings API. Re-running it is idempotent.

> **The `school.` prefix in the source is not a namespace.** Zoho CRM function categories
> are a fixed list (Button, Automation, Schedule, Related List, Standalone, Signals); you
> cannot invent one. The port rewrites every `school.x` to `standalone.x`, which is how a
> CRM function is actually addressed.
>
> **`standalone` functions may only return `string`** — the compiler rejects any other
> declared return type — and `standalone` is the only category a function can be called
> from another function. So every helper returns a JSON string and the port rewrites each
> call site to parse it back (`.toJSONList()`, `.toMap()`, `.toLong()`). This is the single
> biggest difference between the design on paper and the code that runs.

Load order does not matter for saving, but it does for validation: the deploy runs two
passes, first registering every signature with an empty body, then writing the real
bodies, so cross-calls resolve.

## Step 3b — The dialect

Five more things CRM Deluge does not accept, all fixed in `tools/fix_crm_deluge*.py`:

| Assumption | Reality |
|---|---|
| `while (cond) { }` | No while loop. |
| `for each index i in 1 to N` | No counted loop either. `for each x in <list>` is all there is, so `school.boundedSeq(n)` materialises the bound. |
| `for each r in resp.get("data").toList()` | The iterable must be a plain variable. Hoist it. |
| `type : method` in `invokeurl` | The HTTP verb must be a literal. |
| `zoho.crm.deleteRecord(...)` | No such task — delete over REST through the connection. |

Also: `sendmail from:` must be `zoho.loginuserid`, and unary minus on a variable
(`-x % 7`) does not parse — write `(x * -1) % 7`.

## Step 4 — Workflow rules

A workflow rule's Function action can only pick a function whose **category is
`automation`**, and an automation function cannot be called from another function. So
`deluge/automation/` holds ten one-line adapters — the entry point for one rule each —
and all the logic stays in the standalone library.

Two things changed once this ran against the real org:

- **The trigger guard lives in the adapter, not in the rule's criteria builder.** "Only
  when `Lead_Status = Admission Confirmed`" is a line of Deluge in git rather than a
  setting buried in a UI. Without it, every lead edit would have created a student.
- **Attendance rollup takes the attendance record id**, not merge fields for the
  enrollment: a merge field on a lookup yields the display name, not the id.

| # | Module | Trigger | Adapter |
|---|---|---|---|
| 1 | Leads | Edit | `wfConfirmAdmission` — guards on `Lead_Status = Admission Confirmed` |
| 2 | Academic_Years | Create or Edit | `wfEnforceSingleCurrentYear` — guards on `Is_Current` |
| 3 | Attendance | Create | `wfAttendanceCreated` — incremental rollup |
| 4 | Attendance | Edit | `wfAttendanceEdited` — full recount |
| 5 | Marks | Create or Edit | `wfValidateMark` |
| 6 | Examinations | Edit | `wfPublishExamResults` — guards on `Results_Published` |
| 7 | Payments | Create | `wfPaymentCreated` — allocate, then receipt |
| 8 | Payments | Edit | `wfPaymentEdited` |
| 9 | Students | Create or Edit | `wfInvalidatePortalCache` |
| 10 | Leave_Requests | Edit | `wfProcessLeaveApproval` — guards on Approved/Rejected |

There is deliberately **no delete rule on Attendance**: a deleted record has nothing left
to read, so the nightly reconciliation is the honest place to correct for it.

Zoho's public API refuses `workflow_rules` outright, so these were created by replaying
the two calls the UI itself makes — `POST /crm/v7/settings/automation/functions` to bind a
function to its argument mapping, then `POST /crm/v8/settings/automation/workflow_rules`.

## Step 5 — Scheduled functions

Schedules need their own category too, so there are four `schedule` adapters.

| Schedule | Time | Adapter | Calls |
|---|---|---|---|
| Attendance reconciliation | daily 01:00 | `schReconcileAttendance` | `reconcileAttendance` |
| Early-warning engine | daily 02:00 | `schEarlyWarning` | `runEarlyWarning` |
| Fee due & overdue sweep | daily 08:00 | `schFeeDueSweep` | `feeDueScheduler` |
| Same-day absence alert | daily 11:00 | `schAbsenceSameDay` | `notifyAbsenceSameDay` |

## Step 6 — Validation rules & Client Script

Three validation rules are live, each stopping the save with an error:

| Module | Field | Criteria | Message |
|---|---|---|---|
| Attendance | `Attendance_Date` | `> ${TODAY}` | Attendance cannot be marked for a future date. |
| Payments | `Amount` | `< 1` | Payment amount must be greater than zero. |
| Marks | `Marks_Obtained` | `> ${Marks.Max_Marks}` | Marks obtained cannot be greater than the maximum marks for this paper. |

Zoho allows one validation rule per primary field, which is why the Marks rule carries the
paper-maximum check rather than a separate non-negative rule; the client script covers the
rest before the round trip.

Client Script: `clientscript/marks_entry_validation.js` on **Marks → Create/Edit**.

## Step 7 — Layout & UX

- **Students** detail page: related lists for Enrollments, Attendance, Marks,
  Exam_Results, Student_Fees, Payments, Leave_Requests, Student_Risk_Flags.
- **Class_Sections** detail page: buttons *Mark Attendance* (widget →
  `school.markSectionAttendance`) and *Enter Marks*.
- **Academic_Years**: button *Promote to Next Year* → `school.promoteStudents`.
- **Examinations**: button *Recompute Results* → `school.publishExamResults`.
- Canvas view on Students showing photo, class, attendance % and fee status as a header
  strip — this is the screen the front office lives in.

## Step 8 — Roles, profiles & sharing

| Profile | Sees |
|---|---|
| Principal / Management | everything, read-write |
| Admission Team | Leads (full), Students (read), Class_Sections (read) |
| Class Teacher | Attendance + Marks for **their own** sections only, Students read-only |
| Accounts | Student_Fees, Fee_Installments, Payments (full); Marks/Attendance hidden |
| Integration User (portal) | read-only on the modules the portal reads; create-only on Leave_Requests |

Data sharing rule on Attendance/Marks: *private*, with a sharing rule granting a teacher
access to records whose `Class_Section.Class_Teacher.CRM_User` is them. A maths teacher
should not be able to edit another section's marks.

## Step 9 — Seed data (order matters)

Academic Year → Classes → Sections → Teachers → Subjects → Subject Allocations →
Fee Structures → Holidays → then run the webform to create the first lead and convert it.
