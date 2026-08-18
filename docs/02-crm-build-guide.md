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

Setup → Developer Space → **Functions** → *Standalone*. Paste in this order (later files
call earlier ones):

1. `00_utils.dg` — `school.coql`, `coqlPaged`, `bulkInsert`, `bulkUpdate`, `pushBatch`,
   `computeGrade`, `dayDiff`, `currentAcademicYear`, `enforceSingleCurrentYear`
2. `01_student_id_generator.dg`
3. `02_admission_lead_conversion.dg`
4. `03_attendance.dg`
5. `04_marks_and_results.dg`
6. `05_fees_and_payments.dg`
7. `06_year_end_promotion.dg`
8. `07_early_warning_engine.dg`
9. `08_creator_sync.dg`

> Deluge standalone functions are namespaced by the category you create them under. All of
> these live under a category named **`school`**, which is where the `school.` prefix comes
> from. Create the category first, or drop the prefix consistently.

## Step 4 — Workflow rules

| # | Module | Trigger | Action |
|---|---|---|---|
| 1 | Leads | Edit → `Lead_Status = Admission Confirmed` | `school.confirmAdmission(Lead.id)` |
| 2 | Academic_Years | Create/Edit, `Is_Current = true` | `school.enforceSingleCurrentYear(id)` |
| 3 | Attendance | Create | `school.updateAttendanceRollup(Enrollment.id, "", Status, "create")` |
| 4 | Attendance | Edit (`Status` changed) | `school.updateAttendanceRollup(Enrollment.id, oldStatus, Status, "edit")` |
| 5 | Attendance | Delete | `school.updateAttendanceRollup(Enrollment.id, Status, "", "delete")` |
| 6 | Marks | Create / Edit | `school.validateMark(id)` |
| 7 | Examinations | Edit → `Results_Published = true` | `school.publishExamResults(id)` |
| 8 | Payments | Create | `school.allocatePayment(id)` + `school.generateReceipt(id)` |
| 9 | Payments | Edit (`Status` changed) | `school.allocatePayment(id)` |
| 10 | Students | Create / Edit (`Parent`, `Secondary_Parent`, `Status`, `Current_Class_Section`) | `school.invalidatePortalCache(id)` |
| 11 | Leave_Requests | Edit → `Status` in (Approved, Rejected) | `school.processLeaveApproval(id)` |

## Step 5 — Scheduled functions

Setup → Automation → **Schedules**.

| Schedule | Time | Function |
|---|---|---|
| Same-day absence alert | daily 11:00 | `school.notifyAbsenceSameDay` |
| Fee due & overdue sweep | daily 08:00 | `school.feeDueScheduler` |
| Early-warning engine | daily 02:00 | `school.runEarlyWarning` |
| Attendance reconciliation | daily 01:00 | `school.reconcileAttendance` |

## Step 6 — Validation rules & Client Script

Validation rules (declarative, Setup → Customization → Modules → *Validation Rules*):

- `Attendance.Attendance_Date` ≤ TODAY — *"Attendance cannot be marked for a future date."*
- `Payments.Amount` > 0 — *"Payment amount must be greater than zero."*
- `Marks.Marks_Obtained` ≥ 0
- `Leads` : `Rejection_Reason` required when `Lead_Status = Rejected`
- `Class_Sections.Max_Strength` > 0
- `Fee_Structures.No_of_Installments` between 1 and 12

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
