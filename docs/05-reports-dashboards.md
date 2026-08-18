# Reports & Dashboards

The filter is simple: **would a principal act differently after seeing this?** A report that
just lists records is a search box, not a report.

---

## Reports

### Admissions

| Report | Type | Answers |
|---|---|---|
| Admission Funnel by Stage | Summary — Leads grouped by `Lead_Status` × `Target_Academic_Year` | Where enquiries are stalling |
| Enquiry Source Effectiveness | Summary — Leads by `Enquiry_Source`, count + % converted | Which channel to spend on next season |
| Class-wise Seat Fill | Class_Sections: `Max_Strength`, `Current_Strength`, computed vacancy | Which grades still need to sell seats |
| Ageing Enquiries | Leads, `Lead_Status = New/Contacted` and `Modified_Time` older than 3 days | Which counsellor is sitting on leads |
| Conversion Time | Leads converted, average days from `Created_Time` to `Converted_On` | How long admissions actually takes |

### Students & academics

| Report | Type | Answers |
|---|---|---|
| Active Student Roll | Students by class → section, `Status = Active` | The daily headcount |
| Student Strength Trend | Enrollments grouped by `Academic_Year` × Class | Is the school growing or leaking students |
| Subject–Teacher Allocation Matrix | Subject_Allocations by Class_Section | Unstaffed subjects; teacher workload |
| Alumni & Exits | Students `Status != Active` by year and reason | Retention |

### Attendance

| Report | Type | Answers |
|---|---|---|
| Attendance % by Section | Summary — Enrollments, avg `Attendance_Percent` by Class_Section | Which section has a discipline problem |
| Chronic Absentees | Enrollments where `Attendance_Percent < 75` and `Days_Marked >= 15` | The list a class teacher should call today |
| Daily Attendance Register | Attendance for today, grouped by section, with count of Absent | Whether every section actually marked |
| Unmarked Sections Today | Class_Sections with no Attendance row dated today | The single most useful operational report in the system |
| Monthly Attendance Trend | Attendance by month × status | Seasonality, exam-week dips |

### Examinations

| Report | Type | Answers |
|---|---|---|
| Exam Performance Summary | Exam_Results by Examination × Class_Section: avg %, pass count, fail count | Class-level performance |
| Subject Difficulty Analysis | Marks by Subject: avg %, fail % | Whether a subject or a teacher needs support |
| Top & Bottom Performers | Exam_Results sorted by `Percentage`, ranked | Prize list and intervention list from one report |
| Improvement / Decline | Exam_Results across the last two exams per student, delta | Who is trending the wrong way |
| Pass Percentage by Class | Exam_Results grouped by Class | Board-exam readiness |

### Fees

| Report | Type | Answers |
|---|---|---|
| Fee Collection Summary | Student_Fees by Academic_Year × Class: total, collected, outstanding | The number the trustees ask for |
| **Outstanding Fee List** | Student_Fees `Status` in (Partially Paid, Overdue), sorted by `Outstanding` desc | Who to call, biggest first |
| Overdue Ageing | Student_Fees by days overdue bucket (0-30 / 31-60 / 61-90 / 90+) | How bad the ageing is |
| Daily Collection Register | Payments today by `Mode` and `Collected_By` | Reconciling the cash box |
| Concession Register | Student_Fees where `Concession_Amount > 0`, by reason | Discount governance |
| Installment Due This Week | Fee_Installments due in the next 7 days | Proactive follow-up |

### Early warning (additional feature)

| Report | Answers |
|---|---|
| At-Risk Students by Band | Student_Risk_Flags by `Risk_Band` × Class_Section |
| Risk Trend | Count by band by week |
| Open Intervention Tasks | Tasks from the engine, `Status != Completed`, by teacher |

---

## Dashboards

### 1. Principal's Dashboard

| Component | Type |
|---|---|
| Active students, this year vs last | KPI comparison |
| Fee collected vs outstanding | Donut |
| Average attendance % this month | KPI with target line at 85% |
| Pass % by class, latest exam | Column chart |
| At-risk students by band | Funnel |
| Admission funnel | Funnel |

### 2. Admissions Dashboard

Enquiries this month (KPI) · Funnel by stage · Source-wise conversion (bar) ·
Seat availability by class (heat-map style column) · Ageing enquiries (list) ·
Counsellor leaderboard (conversion rate, not raw lead count)

### 3. Academics Dashboard

Section-wise average % (bar) · Subject-wise pass % (bar) · Attendance % by section
(bar, with a 75% reference line) · Top 10 and bottom 10 students (two lists) ·
Improvement vs decline (delta column chart)

### 4. Accounts Dashboard

Collection vs target, month by month (line) · Outstanding ageing buckets (stacked bar) ·
Collection by payment mode (pie) · Class-wise outstanding (bar) ·
Today's collection register (list) · Top 20 defaulters (list)

---

## A note on how these are built

Almost every report above reads a **stored, maintained field** — `Attendance_Percent`,
`Outstanding`, `Percentage`, `Class_Rank` — rather than aggregating raw rows at render
time. That is the payoff of maintaining rollups in the workflows: the reports are fast on
day one and still fast at 5,000 students, and the numbers on a dashboard always match the
numbers on the record and in the parent portal, because there is only one place they are
computed.
