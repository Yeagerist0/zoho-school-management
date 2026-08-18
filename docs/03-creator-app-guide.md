# Zoho Creator — Parent Portal build guide

App name: **Parent Portal** (link name `parent-portal`)

---

## The shape of the app

This is a **pages-first** Creator app, not a forms-and-reports app. That is the whole
design decision, and it follows directly from the brief's *"avoid unnecessary duplicate
data"*:

- A conventional Creator app would replicate Students, Attendance, Marks and Fees into
  Creator forms and keep them in step with a sync job. That gives you two copies of every
  number, a sync window in which they disagree, and a second place bugs can live.
- Instead, every screen is a **Page** whose Deluge HTML snippet calls a function in
  `02_portal_data.dg`, which reads **live from CRM over COQL**. Creator holds three tiny
  forms — an identity cache, an access log, and the leave requests it originates.

So the portal cannot show stale marks, because it has no marks of its own to be stale.

---

## Forms (all Creator holds)

**1. `Parent_Portal_User`** — identity cache, not data
`Email` (unique) · `CRM_Contact_ID` · `Students_JSON` (multi-line) · `Last_Synced` (datetime)
30-minute TTL; CRM invalidates it on any change to a parent↔student link.

**2. `Portal_Access_Log`** — append only
`Email` · `Event` (AUTH_OK / AUTH_FAIL_NO_CONTACT / AUTH_FAIL_NO_STUDENT / ACCESS_DENIED)
· `Detail` · `Logged_At`

**3. `Leave_Request`** — the one thing parents create
`Student_Record_ID` · `From_Date` · `To_Date` · `Reason` · `Status` · `CRM_Record_ID` ·
`Sync_Status` · `Sync_Message` · `Retry_Count`

**4. `App_Config`** — `Config_Key` (unique) · `Config_Value`. Holds the CRM callback secret.

---

## Pages

| Page | Function it calls | Shows |
|---|---|---|
| **Home** | `portal.resolveParent()` | Child picker (a parent with three children gets three cards), announcements strip |
| **Profile** | `portal.getDashboard`, `portal.getSubjectsAndTeachers` | Photo, Student ID, class/section/roll no, class teacher, subject–teacher table |
| **Attendance** | `portal.getAttendance` | Month calendar colour-coded by status, month summary tiles, year-to-date % gauge, month navigation |
| **Results** | `portal.getExamResults` | One collapsible card per published exam: subject table, total, %, grade, section & class rank |
| **Fees** | `portal.getFeeStatus` | Total / collected / outstanding tiles, installment ladder with due dates and status chips, receipt-wise payment history |
| **Apply for Leave** | `Leave_Request` form + `portal.submitLeaveRequest` | The only write path |

Every page's first line of Deluge is the same:

```
ctx = portal.resolveParent();
if(!ctx.get("ok")) { … render the "contact the school office" panel … }
stuId = if(input.stu != null && input.stu != "", input.stu, ctx.get("students").get(0).get("id"));
```

…and every data function then re-checks that `stuId` through `portal.assertStudentAccess`.
The URL parameter is a *hint about which child to show*, never a grant of access.

---

## Authentication — how a parent gets in

1. App → **Settings → Users → Customer Portal** → enable, permission set
   `Parent` (access to the six pages, no access to any report or form except
   `Leave_Request`).
2. Portal invitations are sent **from CRM**, not typed by hand: a scheduled function
   invites the `Parent.Email` of every Active student who is not yet a portal user.
3. The parent signs up with that email. Creator authenticates them; `zoho.loginuser` is
   then the same string as `Contacts.Email` in CRM, which is what
   `portal.resolveParent()` matches on.

**No student ID, roll number or DOB is ever used as a credential.** Those are guessable and
are printed on every report card, which makes them an access-control disaster in a portal
where the object ids are sequential.

---

## Why the identity cache is safe

It stores only `email → contactId → [studentIds]`. Even if someone read the whole form
they would learn which parent has which child — information the school already prints on
the class list. Marks, attendance and fees are never written to Creator, so the portal
database is not a second copy of the school's sensitive data.

Cache correctness is handled at both ends: a 30-minute TTL bounds the staleness, and CRM
actively invalidates on the events that matter (new sibling admitted, guardian email
changed, student marked Left). A parent whose access is revoked in CRM loses the portal
within seconds, not within the TTL.

---

## Page snippet pattern (Attendance, abbreviated)

```
%%
ctx = portal.resolveParent();
if(!ctx.get("ok"))
{
    return "<div class='card'>" + ctx.get("message") + "</div>";
}
stuId  = if(input.stu != null, input.stu, ctx.get("students").get(0).get("id"));
month  = if(input.m != null, input.m.toDate(), zoho.currentdate.toStartOfMonth());

data = portal.getAttendance(stuId, month);
if(!data.get("ok"))
{
    return "<div class='card error'>" + data.get("message") + "</div>";
}

s    = data.get("summary");
html = "<div class='tiles'>";
html = html + "<div class='tile'><span>" + s.get("present")  + "</span><label>Present</label></div>";
html = html + "<div class='tile'><span>" + s.get("absent")   + "</span><label>Absent</label></div>";
html = html + "<div class='tile'><span>" + s.get("monthPct") + "%</span><label>This month</label></div>";
html = html + "<div class='tile'><span>" + ifnull(s.get("ytdPct"),0) + "%</span><label>Year to date</label></div>";
html = html + "</div><table class='cal'>";
for each d in data.get("days")
{
    cls = d.get("status").toLowerCase().replaceAll(" ", "-");
    html = html + "<tr class='" + cls + "'><td>" + d.get("date") + "</td><td>" + d.get("status") + "</td><td>" + d.get("remarks") + "</td></tr>";
}
html = html + "</table>";
return html;
%%
```

Same three-line skeleton on every page: resolve → authorise → render.
