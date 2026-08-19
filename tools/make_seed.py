#!/usr/bin/env python3
"""
Generate demo data for the school org.

Emits tools/seed.json: an ordered list of steps the in-page loader replays
against /crm/v7/<Module>. Lookups are written symbolically as
{"$ref": "Module:key"} and resolved to record ids from what earlier steps
created, so the file stays readable and re-generatable.
"""
import json, random, datetime as dt

random.seed(20260819)

FIRST_M = "Aarav Vivaan Aditya Vihaan Arjun Reyansh Krishna Ishaan Rudra Kabir Aryan Atharv Devansh Ayaan Sai".split()
FIRST_F = "Ananya Diya Aadhya Saanvi Aarohi Anika Navya Riya Myra Kiara Ishita Avni Pari Siya Meera".split()
LAST = "Sharma Verma Iyer Nair Reddy Gupta Mehta Patel Joshi Rao Bose Kulkarni Chawla Menon Pillai".split()
SUBJECTS = [
    ("ENG", "English", 100), ("HIN", "Hindi", 100), ("MAT", "Mathematics", 100),
    ("SCI", "Science", 100), ("SST", "Social Studies", 100), ("CSC", "Computer Science", 50),
]
DEPTS = ["Languages", "Languages", "Mathematics", "Science", "Social Studies", "Computer Science"]

steps = []
def step(module, key, records):
    steps.append({"module": module, "key": key, "records": records})

def ref(module, key):
    return {"$ref": module + ":" + key}

# ---------------------------------------------------------------- reference data
step("Academic_Years", "Name", [
    {"Name": "2025-26", "Year_Code": "2526", "Start_Date": "2025-04-01", "End_Date": "2026-03-31",
     "Is_Current": False, "Total_Working_Days": 220, "Min_Attendance_For_Promotion": 75},
    {"Name": "2026-27", "Year_Code": "2627", "Start_Date": "2026-04-01", "End_Date": "2027-03-31",
     "Is_Current": True, "Total_Working_Days": 220, "Min_Attendance_For_Promotion": 75},
])

GRADES = list(range(1, 11))
step("Classes", "Name", [
    {"Name": "Grade %d" % g, "Level": g, "Stream": "General"} for g in GRADES
])

step("Subjects", "Name", [
    {"Name": s[1], "Subject_Code": s[0], "Default_Max_Marks": s[2],
     "Is_Elective": s[0] == "CSC", "Has_Practical": s[0] in ("SCI", "CSC")}
    for s in SUBJECTS
])

teachers = []
for i in range(14):
    nm = random.choice(FIRST_F + FIRST_M) + " " + random.choice(LAST)
    teachers.append({
        "Name": nm, "Employee_ID": "EMP%03d" % (i + 1),
        "Email": "teacher%02d@vidyavihar.example" % (i + 1),
        "Mobile": "98%08d" % random.randint(0, 99999999),
        "Date_Of_Joining": "20%02d-06-01" % random.randint(15, 24),
        "Qualification": random.choice(["M.Sc, B.Ed", "M.A, B.Ed", "B.Tech, B.Ed", "M.Com, B.Ed"]),
        "Department": DEPTS[i % len(DEPTS)], "Status": "Active",
    })
step("Teachers", "Employee_ID", teachers)

step("Holidays", "Holiday_Key", [
    {"Name": n, "Holiday_Key": "2627-" + d, "Holiday_Date": d, "Type": t,
     "Academic_Year": ref("Academic_Years", "2026-27")}
    for n, d, t in [
        ("Independence Day", "2026-08-15", "Holiday"),
        ("Ganesh Chaturthi", "2026-09-14", "Holiday"),
        ("Gandhi Jayanti", "2026-10-02", "Holiday"),
        ("Diwali Break", "2026-11-09", "Vacation"),
        ("Diwali Break", "2026-11-10", "Vacation"),
    ]
])

# ---------------------------------------------------------------- sections
sections = []
for g in GRADES:
    letters = ["A", "B"] if g >= 6 else ["A"]
    for li, L in enumerate(letters):
        sections.append({
            "Name": "2026-27 / Grade %d / %s" % (g, L),
            "Section_Key": "2627-%d-%s" % (g, L),
            "Academic_Year": ref("Academic_Years", "2026-27"),
            "Class": ref("Classes", "Grade %d" % g),
            "Section": L,
            "Class_Teacher": ref("Teachers", "EMP%03d" % (((g + li) % 14) + 1)),
            "Room_No": "%d%02d" % (g, li + 1),
            "Max_Strength": 40, "Current_Strength": 0, "Is_Active": True,
        })
step("Class_Sections", "Section_Key", sections)

allocs = []
for s in sections:
    for si, (code, name, _) in enumerate(SUBJECTS):
        allocs.append({
            "Name": s["Section_Key"] + "-" + code,
            "Allocation_Key": s["Section_Key"] + "-" + code,
            "Academic_Year": ref("Academic_Years", "2026-27"),
            "Class_Section": ref("Class_Sections", s["Section_Key"]),
            "Subject": ref("Subjects", name),
            "Teacher": ref("Teachers", "EMP%03d" % ((si * 2 + 1) % 14 + 1)),
            "Periods_Per_Week": 6 if code in ("ENG", "MAT") else 4,
        })
step("Subject_Allocations", "Allocation_Key", allocs)

# ---------------------------------------------------------------- people
parents, students, enrollments = [], [], []
n = 0
for s in sections:
    grade = int(s["Section_Key"].split("-")[1])
    for r in range(1, 7):                      # 6 students per section
        n += 1
        male = random.random() < 0.5
        first = random.choice(FIRST_M if male else FIRST_F)
        last = random.choice(LAST)
        sid = "STU-2627-%05d" % n
        pmail = "parent%03d@vidyavihar.example" % n
        parents.append({
            "Last_Name": last, "First_Name": random.choice(FIRST_M), "Email": pmail,
            "Phone": "97%08d" % random.randint(0, 99999999),
            "Relationship": "Father", "Occupation": random.choice(
                ["Engineer", "Teacher", "Shopkeeper", "Doctor", "Farmer", "Accountant"]),
            "Portal_Enabled": True,
        })
        students.append({
            "Name": first + " " + last, "Student_Name": first + " " + last,
            "Student_ID": sid,
            "DOB": "%d-%02d-%02d" % (2026 - 5 - grade, random.randint(1, 12), random.randint(1, 28)),
            "Gender": "Male" if male else "Female",
            "Blood_Group": random.choice(["A+", "B+", "O+", "AB+", "O-"]),
            "Admission_Date": "2026-04-05", "Status": "Active",
            "Parent": ref("Contacts", pmail),
            "Current_Class_Section": ref("Class_Sections", s["Section_Key"]),
            "City": "Bengaluru", "Pincode": "5600%02d" % random.randint(1, 99),
            "Transport_Opted": random.random() < 0.4,
        })
        enrollments.append({
            "Name": sid + " / " + s["Name"],
            "Enrollment_Key": sid + "-2627",
            "Student": ref("Students", sid),
            "Academic_Year": ref("Academic_Years", "2026-27"),
            "Class_Section": ref("Class_Sections", s["Section_Key"]),
            "Roll_No": r, "Enrollment_Date": "2026-04-05", "Status": "Active",
            "Days_Marked": 0, "Days_Present": 0, "Attendance_Percent": 0,
        })
step("Contacts", "Email", parents)
step("Students", "Student_ID", students)
step("Enrollments", "Enrollment_Key", enrollments)

# ---------------------------------------------------------------- money
fee_structures = []
for g in GRADES:
    tuition = 24000 + g * 2000
    fee_structures.append({
        "Name": "2026-27 / Grade %d" % g,
        "Academic_Year": ref("Academic_Years", "2026-27"),
        "Class": ref("Classes", "Grade %d" % g),
        "Tuition_Fee": tuition, "Transport_Fee": 9000, "Lab_Fee": 1500 if g >= 6 else 0,
        "Exam_Fee": 1200, "Misc_Fee": 800,
        "Total_Fee": tuition + 9000 + (1500 if g >= 6 else 0) + 1200 + 800,
        "No_of_Installments": 4,
        "Installment_Plan": json.dumps([{"no": i, "percent": 25, "due_offset_days": (i - 1) * 90}
                                        for i in range(1, 5)]),
    })
step("Fee_Structures", "Name", fee_structures)

json.dump(steps, open('tools/seed.json', 'w'), indent=1)
print("steps: %d, records: %d" % (len(steps), sum(len(s['records']) for s in steps)))
for s in steps:
    print("  %-22s %4d" % (s['module'], len(s['records'])))
