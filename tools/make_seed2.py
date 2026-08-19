#!/usr/bin/env python3
"""
Second seed wave: the transactional data that makes the org demoable —
attendance, an exam cycle with marks and report cards, the fee ledger with
payments, plus admission enquiries and portal leave requests.

Rollups (Enrollment attendance %, Student_Fee paid/outstanding) are computed
here and written back, so the demo org is internally consistent even before the
workflow functions have run against it.
"""
import json, random, datetime as dt

random.seed(4242)
GRADES = list(range(1, 11))
SUBJECTS = [("ENG", "English", 100), ("HIN", "Hindi", 100), ("MAT", "Mathematics", 100),
            ("SCI", "Science", 100), ("SST", "Social Studies", 100), ("CSC", "Computer Science", 50)]

sections = []
for g in GRADES:
    for L in (["A", "B"] if g >= 6 else ["A"]):
        sections.append(("2627-%d-%s" % (g, L), g, L))

students = []          # (sid, section_key, grade, roll)
n = 0
for skey, g, L in sections:
    for r in range(1, 7):
        n += 1
        students.append(("STU-2627-%05d" % n, skey, g, r))

steps = []
def step(module, key, records, op="create"):
    steps.append({"module": module, "key": key, "records": records, "op": op})
def ref(m, k):
    return {"$ref": m + ":" + k}

# ------------------------------------------------------------------ settings
step("App_Settings", "Setting_Key", [
    {"Name": "creator_base_url", "Setting_Key": "creator_base_url",
     "Setting_Value": "https://creatorapp.zoho.in/vidyaviharschool/parent-portal"},
    {"Name": "crm_callback_secret", "Setting_Key": "crm_callback_secret",
     "Setting_Value": "vv-demo-shared-secret-2627"},
    {"Name": "risk_weights", "Setting_Key": "risk_weights",
     "Setting_Value": json.dumps({"w_attendance": 40, "w_consecutive": 25, "w_marks": 20,
                                  "w_fees": 15, "attendance_floor": 75, "streak_days": 3})},
])
step("Sequence_Counters", "Counter_Key", [
    {"Name": "STUDENT-2627", "Counter_Key": "STUDENT-2627", "Last_Value": len(students)},
])

# ------------------------------------------------------------------ exam cycle
step("Examinations", "Name", [
    {"Name": "Unit Test 1 2026-27", "Exam_Name": "Unit Test 1 2026-27",
     "Academic_Year": ref("Academic_Years", "2026-27"), "Exam_Type": "Unit Test 1",
     "Start_Date": "2026-07-13", "End_Date": "2026-07-17", "Weightage_Percent": 10,
     "Results_Published": True},
    {"Name": "Mid Term 2026-27", "Exam_Name": "Mid Term 2026-27",
     "Academic_Year": ref("Academic_Years", "2026-27"), "Exam_Type": "Mid Term",
     "Start_Date": "2026-09-21", "End_Date": "2026-09-30", "Weightage_Percent": 30,
     "Results_Published": False},
])

EXAM = "Unit Test 1 2026-27"
scheds = []
for skey, g, L in sections:
    for i, (code, name, mx) in enumerate(SUBJECTS):
        scheds.append({
            "Name": EXAM + " / " + skey + " / " + code,
            "Schedule_Key": "UT1-" + skey + "-" + code,
            "Examination": ref("Examinations", EXAM),
            "Class_Section": ref("Class_Sections", skey),
            "Subject": ref("Subjects", name),
            "Exam_Date": (dt.date(2026, 7, 13) + dt.timedelta(days=i % 5)).isoformat(),
            "Max_Marks": mx, "Passing_Marks": int(mx * 0.33),
        })
step("Exam_Schedules", "Schedule_Key", scheds)

def grade_of(pct):
    for cut, g in [(90, "A1"), (80, "A2"), (70, "B1"), (60, "B2"), (50, "C1"), (40, "C2"), (33, "D")]:
        if pct >= cut:
            return g
    return "E"

marks, results = [], []
# marks for the three lower-secondary sections - enough for real report cards
mark_sections = {"2627-6-A", "2627-6-B", "2627-7-A"}
for sid, skey, g, roll in students:
    if skey not in mark_sections:
        continue
    tot_o = tot_m = 0
    failed = 0
    for code, name, mx in SUBJECTS:
        absent = random.random() < 0.04
        obtained = 0 if absent else max(8, min(mx, int(random.gauss(mx * 0.68, mx * 0.16))))
        pct = round(obtained * 100.0 / mx, 2)
        passed = (not absent) and obtained >= mx * 0.33
        if not passed:
            failed += 1
        tot_o += obtained
        tot_m += mx
        marks.append({
            "Name": sid + "-UT1-" + code, "Marks_Key": sid + "-UT1-" + code,
            "Student": ref("Students", sid),
            "Examination": ref("Examinations", EXAM),
            "Subject": ref("Subjects", name),
            "Exam_Schedule": ref("Exam_Schedules", "UT1-" + skey + "-" + code),
            "Marks_Obtained": obtained, "Max_Marks": mx, "Is_Absent": absent,
            "Percentage": pct, "Grade": grade_of(pct),
            "Result": "Pass" if passed else "Fail",
        })
    tpct = round(tot_o * 100.0 / tot_m, 2)
    results.append({
        "Name": "RES-UT1-" + sid, "Result_Key": "UT1-" + sid,
        "Student": ref("Students", sid),
        "Examination": ref("Examinations", EXAM),
        "Enrollment": ref("Enrollments", sid + "-2627"),
        "Class_Section": ref("Class_Sections", skey),
        "Total_Obtained": tot_o, "Total_Max": tot_m, "Percentage": tpct,
        "Overall_Grade": grade_of(tpct), "Subjects_Failed": failed,
        "Result": "Fail" if failed else "Pass",
        "_pct": tpct, "_sec": skey,
    })
# ranks
for skey in mark_sections:
    cohort = sorted([r for r in results if r["_sec"] == skey], key=lambda r: -r["_pct"])
    for i, r in enumerate(cohort):
        r["Section_Rank"] = i + 1
        r["Class_Rank"] = i + 1
for r in results:
    r.pop("_pct"); r.pop("_sec")
step("Marks", "Marks_Key", marks)
step("Exam_Results", "Result_Key", results)

# ------------------------------------------------------------------ attendance
HOLIDAYS = {"2026-08-15"}
days = []
d = dt.date(2026, 8, 3)
while len(days) < 15:
    if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
        days.append(d.isoformat())
    d += dt.timedelta(days=1)

att = []
rollup = {}
att_sections = mark_sections
for sid, skey, g, roll in students:
    if skey not in att_sections:
        continue
    marked = present = 0
    # one deliberately at-risk student per section so the early-warning demo has teeth
    risky = roll == 3
    for ds in days:
        p = 0.55 if risky else 0.93
        st = "Present" if random.random() < p else random.choice(["Absent", "Absent", "Late", "Half Day"])
        marked += 1
        present += 1 if st in ("Present", "Late") else (0.5 if st == "Half Day" else 0)
        att.append({
            "Name": sid + "-" + ds, "Attendance_Key": sid + "-" + ds,
            "Student": ref("Students", sid),
            "Enrollment": ref("Enrollments", sid + "-2627"),
            "Class_Section": ref("Class_Sections", skey),
            "Attendance_Date": ds, "Status": st,
        })
    rollup[sid] = (marked, present)
step("Attendance", "Attendance_Key", att)

step("Enrollments", "Enrollment_Key", [
    {"$id": ref("Enrollments", sid + "-2627"), "Days_Marked": m, "Days_Present": int(p),
     "Attendance_Percent": round(p * 100.0 / m, 2)}
    for sid, (m, p) in rollup.items()
], op="update")

# ------------------------------------------------------------------ fees
fees, insts, pays = [], [], []
receipt = 0
for sid, skey, g, roll in students:
    total = (24000 + g * 2000) + 9000 + (1500 if g >= 6 else 0) + 1200 + 800
    concession = 5000 if roll == 1 else 0
    net = total - concession
    per = round(net / 4.0, 2)
    # how far this family has got through the ladder
    paid_count = random.choice([0, 1, 1, 2, 2, 3, 4])
    paid = round(per * paid_count, 2)
    due_dates = [(dt.date(2026, 4, 15) + dt.timedelta(days=90 * (i - 1))).isoformat() for i in range(1, 5)]
    nxt = next((i for i in range(4) if i >= paid_count), 3)
    status = "Not Started" if paid_count == 0 else ("Paid" if paid_count == 4 else "Partially Paid")
    fees.append({
        "Name": "FEE-" + sid, "Student": ref("Students", sid),
        "Academic_Year": ref("Academic_Years", "2026-27"),
        "Fee_Structure": ref("Fee_Structures", "2026-27 / Grade %d" % g),
        "Total_Fee": total, "Concession_Amount": concession,
        "Concession_Reason": "Sibling concession" if concession else "",
        "Net_Payable": net, "Amount_Paid": paid, "Outstanding": round(net - paid, 2),
        "Status": status,
        "Next_Due_Date": due_dates[nxt] if paid_count < 4 else None,
        "Next_Due_Amount": per if paid_count < 4 else 0,
    })
    for i in range(1, 5):
        ip = per if i <= paid_count else 0
        insts.append({
            "Name": "INST-" + sid + "-" + str(i),
            "Student_Fee": ref("Student_Fees", "FEE-" + sid),
            "Installment_No": i, "Due_Date": due_dates[i - 1],
            "Amount_Due": per, "Amount_Paid": ip, "Balance": round(per - ip, 2),
            "Status": "Paid" if ip else ("Overdue" if due_dates[i - 1] < "2026-08-19" else "Pending"),
        })
    for i in range(1, paid_count + 1):
        receipt += 1
        pays.append({
            "Name": "RCPT-%05d" % receipt, "Receipt_No": "RCPT-%05d" % receipt,
            "Student": ref("Students", sid), "Student_Fee": ref("Student_Fees", "FEE-" + sid),
            "Payment_Date": due_dates[i - 1], "Amount": per,
            "Mode": random.choice(["UPI", "UPI", "Cash", "NEFT", "Card"]),
            "Transaction_Ref": "TXN%09d" % random.randint(0, 999999999),
            "Status": "Success",
            "Allocation_Detail": "Installment %d of 4" % i,
        })
step("Student_Fees", "Name", fees)
step("Fee_Installments", "Name", insts)
step("Payments", "Receipt_No", pays)

# ------------------------------------------------------------------ front of house
step("Announcements", "Name", [
    {"Name": "Parent-Teacher Meeting", "Body": "PTM for all sections on Saturday 29 August, 9am-1pm.",
     "Audience": "All", "Publish_From": "2026-08-17", "Publish_To": "2026-08-30", "Is_Active": True},
    {"Name": "Unit Test 1 results published", "Body": "Report cards are now visible in the parent portal.",
     "Audience": "All", "Publish_From": "2026-07-24", "Publish_To": "2026-08-24", "Is_Active": True},
    {"Name": "Grade 6A science field trip", "Body": "Consent forms due by 25 August.",
     "Audience": "Section", "Class_Section": ref("Class_Sections", "2627-6-A"),
     "Publish_From": "2026-08-15", "Publish_To": "2026-08-25", "Is_Active": True},
])

leads = []
funnel = ["New", "Contacted", "Campus Visit Scheduled", "Application Submitted",
          "Assessment Done", "Admission Offered"]
for i, st in enumerate(funnel):
    leads.append({
        "Last_Name": ["Krishnan", "Bhat", "Deshpande", "Saxena", "Thomas", "Qureshi"][i],
        "First_Name": ["Ramesh", "Sunita", "Mahesh", "Pooja", "Alex", "Farah"][i],
        "Email": "enquiry%02d@example.com" % (i + 1),
        "Phone": "96%08d" % random.randint(0, 99999999),
        "Lead_Status": st,
        "Student_First_Name": ["Nikhil", "Tara", "Rohan", "Ira", "Sara", "Zoya"][i],
        "Student_Last_Name": ["Krishnan", "Bhat", "Deshpande", "Saxena", "Thomas", "Qureshi"][i],
        "Student_DOB": "2018-0%d-1%d" % (i % 9 + 1, i),
        "Gender": ["Male", "Female", "Male", "Female", "Female", "Female"][i],
        "Applying_For_Class": ref("Classes", "Grade 3"),
        "Target_Academic_Year": ref("Academic_Years", "2026-27"),
        "Previous_School": "Little Scholars Public School",
        "Enquiry_Source": random.choice(["Walk-in", "Website", "Referral", "Education Fair"]),
        "Application_No": "APP-2627-%03d" % (i + 1),
        "Assessment_Score": round(random.uniform(55, 92), 1) if i >= 4 else None,
        "Relationship": "Father" if i % 2 == 0 else "Mother",
    })
step("Leads", "Application_No", leads)

lv = []
for i, (sid, skey, g, roll) in enumerate([s for s in students if s[1] in mark_sections][:4]):
    lv.append({
        "Name": "LV-" + sid + "-%d" % i,
        "Student": ref("Students", sid),
        "From_Date": "2026-08-2%d" % (i + 1), "To_Date": "2026-08-2%d" % (i + 2),
        "Reason": ["Fever", "Family function", "Medical check-up", "Travel"][i],
        "Status": ["Pending", "Approved", "Pending", "Rejected"][i],
        "Source": "Parent Portal",
        "Requested_By_Email": "parent%03d@vidyavihar.example" % (students.index((sid, skey, g, roll)) + 1),
        "Sync_Status": "Synced",
    })
step("Leave_Requests", "Name", lv)

json.dump(steps, open('tools/seed2.json', 'w'), indent=1)
print("steps: %d, records: %d" % (len(steps), sum(len(s['records']) for s in steps)))
for s in steps:
    print("  %-22s %5d  %s" % (s['module'], len(s['records']), s['op']))
