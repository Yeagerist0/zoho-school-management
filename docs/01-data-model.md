# Data Model — Zoho CRM

## Design principles

1. **CRM is the single system of record.** Creator stores no master data — only portal
   identity and portal-originated requests. Nothing about a student, mark, or payment
   is written twice.
2. **Junction modules instead of multi-selects** wherever a relationship carries its own
   data (a teacher teaching a subject to a section has periods, a term, a workload — that
   cannot live in a multi-select field).
3. **The academic year is an entity, not a text field.** Every year-scoped record points
   at an Academic Year record, which is what makes history queryable instead of
   overwritten.
4. **Derived numbers are stored, not computed on read.** Attendance %, fee outstanding and
   exam totals are maintained incrementally by workflow functions. A parent portal that
   recomputes a year of attendance on every page load does not scale past a few hundred
   students.

---

## Modules

### Standard modules (reused)

| Module | Used as | Key custom fields |
|---|---|---|
| **Leads** | Admission Enquiry | `Student_First_Name`, `Student_Last_Name`, `Student_DOB`, `Gender`, `Applying_For_Class` (lookup → Classes), `Target_Academic_Year` (lookup), `Previous_School`, `Enquiry_Source`, `Application_No` (auto-number, unique), `Assessment_Score`, `Rejection_Reason` |
| **Contacts** | Parent / Guardian | `Relationship` (Father/Mother/Guardian), `Occupation`, `Portal_Enabled` (checkbox), `Alternate_Mobile`. Email is unique — it is the portal login key. |

Leads keeps the native `Lead Status` picklist, re-valued to the admission funnel:
`New → Contacted → Campus Visit Scheduled → Application Submitted → Assessment Done →
Admission Offered → Admission Confirmed → Rejected → Dropped`.

### Custom modules

**1. Academic_Years**
`Name` (2026-27) · `Year_Code` (2627, unique) · `Start_Date` · `End_Date` ·
`Is_Current` (checkbox, kept singleton by Deluge) · `Total_Working_Days` (number)

**2. Classes** — the grade master, year-independent
`Class_Name` (Grade 1) · `Level` (integer 1..12, used for sorting and promotion) ·
`Stream` (picklist, senior grades only)

**3. Class_Sections** — the *class instance for one year*. This is what students attach to.
`Name` (auto: `2026-27 / Grade 5 / A`) · `Academic_Year` (lookup) · `Class` (lookup) ·
`Section` (picklist A–F) · `Class_Teacher` (lookup → Teachers) · `Room_No` ·
`Max_Strength` · `Current_Strength` (maintained) · `Is_Active`
Unique key field `Section_Key` = `<Year_Code>-<Level>-<Section>` prevents duplicates.

**4. Teachers**
`Employee_ID` (unique) · `Name` · `Email` (unique) · `Mobile` · `Date_of_Joining` ·
`Qualification` · `Department` · `Status` (Active / On Leave / Resigned) ·
`CRM_User` (lookup → Users, so a teacher who is also a CRM user can be scoped by data
sharing rules to only their own sections)

**5. Subjects**
`Subject_Code` (unique) · `Subject_Name` · `Applicable_Class` (lookup → Classes) ·
`Default_Max_Marks` · `Is_Elective` · `Has_Practical`

**6. Subject_Allocations** — junction: who teaches what, where
`Academic_Year` · `Class_Section` (lookup) · `Subject` (lookup) · `Teacher` (lookup) ·
`Periods_Per_Week`
Unique key `Allocation_Key` = `<Section_Key>-<Subject_Code>`.

> This one junction answers *"which teachers and subjects are associated with a student"*:
> Student → Enrollment → Class_Section → Subject_Allocations → Subject + Teacher.

**7. Students**
`Student_ID` (unique, system-generated `STU-2627-00042`) · `Student_Name` · `DOB` ·
`Gender` · `Blood_Group` · `Photo` (image) · `Admission_Date` ·
`Parent` (lookup → Contacts) · `Secondary_Parent` (lookup → Contacts) ·
`Current_Enrollment` (lookup → Enrollments) ·
`Current_Class_Section` (lookup — denormalised so class-wise reports need no join) ·
`Status` (Active / Alumni / Transferred Out / Suspended) ·
`Source_Lead` (lookup → Leads — full admission audit trail) ·
`Address`, `City`, `Pincode` · `Transport_Opted` · `Medical_Notes`

**8. Enrollments** — the history spine. One row per student per academic year.
`Name` (auto) · `Student` (lookup) · `Academic_Year` (lookup) · `Class_Section` (lookup) ·
`Roll_No` · `Enrollment_Date` · `Status` (Active / Promoted / Detained / Left) ·
`Days_Marked` · `Days_Present` · `Attendance_Percent` ·
`Final_Percentage` · `Final_Result` (Pass / Fail / Pending)
Unique key `Enrollment_Key` = `<Student_ID>-<Year_Code>` — a student cannot be enrolled
twice in the same year.

> Moving a student to a new class or a new year **never edits an old row**; it closes the
> current Enrollment and opens a new one. Last year's class, roll number, attendance and
> result stay intact and reportable forever.

**9. Attendance**
`Student` · `Enrollment` · `Class_Section` · `Attendance_Date` · `Status`
(Present / Absent / Late / Half Day / Approved Leave) · `Marked_By` (lookup → Teachers) ·
`Remarks` · `Attendance_Key` (**unique**: `<Student_ID>-<yyyy-MM-dd>`)

The unique field is the duplicate guard — enforced by the CRM engine itself, so it holds
against the UI, the API, imports and concurrent bulk marking alike.

**10. Holidays** — `Holiday_Date` · `Name` · `Type` (Holiday / Weekly Off / Vacation /
Exam Break) · `Academic_Year` · unique key `Holiday_Key`. Drives attendance validation and
working-day counts.

**11. Examinations**
`Exam_Name` · `Academic_Year` · `Exam_Type` (Unit Test 1/2, Mid Term, Pre-Final, Final) ·
`Start_Date` · `End_Date` · `Weightage_Percent` · `Results_Published` (checkbox — the gate
that makes marks visible to parents)

**12. Exam_Schedules** — junction: Exam × Class_Section × Subject
`Examination` · `Class_Section` · `Subject` · `Exam_Date` · `Max_Marks` · `Passing_Marks`
Unique key `Schedule_Key`. Mark entry validates against *this* record's max marks, so a
different paper ceiling per class needs no code change.

**13. Marks**
`Student` · `Examination` · `Subject` · `Exam_Schedule` (lookup) · `Marks_Obtained` ·
`Max_Marks` · `Is_Absent` · `Percentage` (formula) · `Grade` · `Result` (Pass/Fail) ·
`Entered_By`
Unique key `Marks_Key` = `<Student_ID>-<Exam id>-<Subject_Code>`.

**14. Exam_Results** — one report-card row per student per exam
`Student` · `Examination` · `Enrollment` · `Total_Obtained` · `Total_Max` · `Percentage` ·
`Overall_Grade` · `Subjects_Failed` · `Result` · `Class_Rank` · `Section_Rank`
Computed in one batch pass when results are published.

**15. Fee_Structures** — the price list, per year per class
`Academic_Year` · `Class` · `Tuition_Fee` · `Transport_Fee` · `Lab_Fee` · `Exam_Fee` ·
`Misc_Fee` · `Total_Fee` (formula) · `No_of_Installments` ·
`Installment_Plan` (multi-line JSON: `[{"no":1,"percent":40,"due_offset_days":10}, ...]`)

**16. Student_Fees** — one per student per year
`Student` · `Academic_Year` · `Fee_Structure` · `Total_Fee` · `Concession_Amount` ·
`Concession_Reason` · `Net_Payable` (formula) · `Amount_Paid` (maintained) ·
`Outstanding` (formula `Net_Payable - Amount_Paid`) ·
`Status` (Not Started / Partially Paid / Paid / Overdue) · `Next_Due_Date` · `Next_Due_Amount`

**17. Fee_Installments**
`Student_Fee` · `Installment_No` · `Due_Date` · `Amount_Due` · `Amount_Paid` ·
`Balance` (formula) · `Status` (Pending / Partially Paid / Paid / Overdue)

**18. Payments**
`Receipt_No` (auto-number, unique) · `Student` · `Student_Fee` · `Payment_Date` · `Amount` ·
`Mode` (Cash/UPI/Card/Cheque/NEFT) · `Transaction_Ref` · `Collected_By` ·
`Status` (Success / Bounced / Refunded) ·
`Allocation_Detail` (multi-line, written by the allocator so every rupee is traceable to an
installment)

**19. Announcements** — `Title` · `Body` · `Audience` (All / Class / Section) ·
`Class_Section` · `Publish_From` · `Publish_To` · `Is_Active`

**20. Leave_Requests** — written from the parent portal
`Student` · `From_Date` · `To_Date` · `Reason` · `Status` (Pending/Approved/Rejected) ·
`Approved_By` · `Source` (Parent Portal)

**21. Student_Risk_Flags** — the additional feature (see `06-additional-feature.md`)

**22. Sequence_Counters** — internal. `Counter_Key` (unique) · `Last_Value` · `Lock_Token`.
Backs collision-free Student ID generation.

---

## Relationship map

```
Leads ──(conversion)──> Students ──1:N──> Enrollments ──N:1──> Class_Sections
                            │                  │                    │
                            │                  │                    ├─N:1─> Classes
                            │                  │                    ├─N:1─> Academic_Years
                            │                  │                    ├─N:1─> Teachers (class teacher)
                            │                  │                    └─1:N─> Subject_Allocations ─> Subjects
                            │                  │                                                 └─> Teachers
                            ├──1:N──> Attendance ──N:1──> Enrollment, Class_Section
                            ├──1:N──> Marks ──N:1──> Examinations, Subjects, Exam_Schedules
                            ├──1:N──> Exam_Results ──N:1──> Examinations
                            ├──1:N──> Student_Fees ──1:N──> Fee_Installments
                            │                └──1:N──> Payments
                            └──N:1──> Contacts (Parent) ──1:N──> Students   [portal identity]
```

---

## Field-level integrity (no code required)

| Guard | Mechanism |
|---|---|
| Duplicate attendance for a student on a date | `Attendance_Key` unique field |
| Duplicate mark for student/exam/subject | `Marks_Key` unique field |
| Duplicate enrollment in one year | `Enrollment_Key` unique field |
| Duplicate section in one year | `Section_Key` unique field |
| Duplicate Student ID | `Student_ID` unique field |
| Marks above the paper maximum | Validation Rule on Marks + pre-save Client Script |
| Attendance dated in the future | Validation Rule on Attendance |
| Negative or zero payment | Validation Rule on Payments |

Everything the CRM engine can enforce declaratively is enforced declaratively. Deluge is
used only where a rule must look at *other* records — holidays, enrolment status,
installment balances, rank computation.
