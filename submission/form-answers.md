# Google Form answers — IT GUY practical assignment

---

## Data Structure & Relationships

The system is 23 CRM modules. The spine is a three-level split that keeps history
queryable instead of overwritten:

**Masters (year-independent).** `Classes` is the grade master (Grade 1–10, with a
numeric `Level` used for sorting and promotion). `Subjects`, `Teachers` and
`Academic_Years` sit alongside it. An academic year is an *entity*, not a text field —
that is what makes "what was this student's attendance in 2025-26" answerable.

**Class_Sections — the class instance for one year.** `2026-27 / Grade 5 / A` is a
record, keyed by `Section_Key` = `<Year_Code>-<Level>-<Section>`, which is unique, so
the same section cannot be created twice for one year. It points at an Academic Year, a
Class and a class teacher.

**Enrollments — the history spine.** One row per student per academic year, linking
`Students` → `Class_Sections`, keyed uniquely by `<Student_ID>-<Year_Code>`. This is the
single most important design decision in the schema: **promotion opens a new Enrollment
row, it never edits an old one.** Last year's class, roll number, attendance percentage
and result stay intact and reportable forever. Everything year-scoped — attendance,
marks, results, fees — hangs off the student and the enrollment rather than off the
student alone.

Around that spine:

- **Admissions:** `Leads` (the enquiry, with the student's details as custom fields) →
  converts to `Contacts` (the parent) + `Students` + the first `Enrollment`. The student
  keeps a `Source_Lead` lookup, so every admission has an audit trail back to the enquiry.
- **Attendance:** `Attendance` → Student, Enrollment, Class_Section. Duplicates are
  impossible because `Attendance_Key` = `<Student_ID>-<date>` is a unique field — enforced
  by the CRM engine itself, so it holds against the UI, the API, imports and concurrent
  bulk marking alike.
- **Examinations:** `Examinations` → `Exam_Schedules` (exam × section × subject, carrying
  that paper's max and passing marks) → `Marks` → `Exam_Results` (one ranked report-card
  row per student per exam).
- **Fees:** `Fee_Structures` (price list per year per class) → `Student_Fees` (one per
  student per year) → `Fee_Installments` → `Payments`.
- **Junctions instead of multi-selects.** `Subject_Allocations` (year × section × subject
  × teacher × periods per week) is what answers "which teachers and subjects are
  associated with this student": Student → Enrollment → Class_Section →
  Subject_Allocations → Subject + Teacher. A multi-select field cannot carry periods per
  week or a term, so it would have been the wrong shape.

Integrity is declarative wherever the platform can enforce it — unique keys on
`Attendance_Key`, `Marks_Key`, `Enrollment_Key`, `Section_Key`, `Student_ID`, plus
validation rules stopping future-dated attendance, non-positive payments, and marks above
the paper maximum. Deluge is used only where a rule has to look at *other* records.

---

## CRM–Creator Integration

**The integration is a read-through, not a sync.** Creator stores no master data.

Every parent-facing screen is a Creator Page whose Deluge calls a function that reads
**live from CRM over COQL** through a connection named `crmconn`. There is no sync job,
no duplicated student/attendance/marks/fee data, and therefore no window in which the two
systems disagree. The portal cannot show stale marks because it has no marks of its own to
go stale.

Creator holds only three things that are genuinely its own: an identity cache
(`Parent_Portal_User`, 30-minute TTL), an append-only access log, and the leave requests
parents originate.

**Identity.** The parent↔student link is the parent's email, set at admission. Creator
authenticates the parent, `zoho.loginuser` is matched against `Contacts.Email` in CRM, and
the children are resolved from there. Every data function then re-checks the requested
student through `portal.assertStudentAccess()` — the URL parameter is a *hint about which
child to show, never a grant of access*. Without that check the portal would be an IDOR.

**Writes go the other way.** A leave request is created in Creator, then pushed into the
CRM `Leave_Requests` module. When a teacher approves or rejects it in CRM, a workflow
fires `processLeaveApproval`, which calls back into Creator over a `creator_conn`
connection with a shared secret, updates the Creator record, and — on approval — writes
the corresponding `Approved Leave` attendance rows in CRM. `Sync_Status` and a retry path
exist because a cross-application write can fail.

**Cache invalidation is pushed, not polled.** Any change in CRM to a student's parent
link, status or section fires `invalidatePortalCache`, which clears that parent's cached
identity in Creator immediately rather than waiting out the TTL.

The whole CRM side is deployed from version-controlled files through Zoho's settings API,
not clicked into a settings screen — so the org can be rebuilt from the repository.

---

## Additional Feature Implemented

**A nightly early-warning engine that finds students who are quietly slipping, and tells
the right adult before it becomes a crisis.**

Every night it scores each active student on four signals, weighted from a config record
so the school can retune it without a code change:

1. Attendance below the year's threshold
2. Consecutive-absence streaks (a three-day streak is a different problem from the same
   number of scattered absences)
3. A drop in exam percentage between the two most recent published exams
4. Fee installments significantly overdue

The score maps to a band — Low / Medium / High / Critical — written to a
`Student_Risk_Flags` record with the reasons in plain language, so the flag explains
itself rather than just showing a number.

**What makes it usable rather than noisy is that it acts only on a band *change*, and only
upward.** A student who was High yesterday and is High today generates nothing. That is
the difference between a system teachers keep using and one they mute in a fortnight. On
an upward change it creates a task for the class teacher (due in 1 day for Critical, 3 for
High) and emails the parent for High and Critical.

**On scalability**, which was the other thing to get right: the engine reads through paged
COQL that selects only the columns it needs and filters on related-module fields in a
single call, rather than pulling full records per student. For a 90-student demo the
difference is invisible; at a few thousand students it is roughly 60 API calls instead of
6,000, and it stays inside the daily API credit budget. The attendance, fee and result
figures it reads are pre-aggregated by workflow functions as records are written, so the
nightly pass never recomputes a year of attendance from scratch.
