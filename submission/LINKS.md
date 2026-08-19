# Submission links

| Form question | Answer |
|---|---|
| **Completed Zoho CRM Implementation** | `https://crm.zoho.in/crm/org60083663008/tab/Home/begin` — org **Vidya Vihar School**. Share access with sagar@it-guy.tech from Setup → Users → Add User. |
| **Zoho Creator Parent Application** | `https://creatorapp.zoho.in/vidyaviharschool/parent-portal` — app **Parent Portal**. Share from the app's Users/Portal settings. |
| **Zoho CRM Webform** | **https://yeagerist0.github.io/admission.html** (live, submits into the Leads module) |
| Data Structure / Integration / Additional Feature | see `form-answers.md` |

Portfolio (not asked for, but useful): **https://yeagerist0.github.io**

## What is actually built

**Zoho CRM — complete**
- 23 modules, 204 fields, all picklists carrying real domain values, unique keys on every
  duplicate guard
- 52 Deluge functions deployed from version-controlled files through the settings API
- 10 workflow rules, 4 daily scheduled jobs, 3 validation rules
- 1,564 seeded records: 90 students across 15 section instances, a published exam with
  ranked report cards, three weeks of attendance, the full fee ledger, an admission funnel
- Admission Enquiry webform on Leads, hosted at the link above

**Zoho Creator — partially complete**
- App **Parent Portal** (`parent-portal`) created
- All 4 forms built with the exact field names and types the Deluge expects:
  `Parent_Portal_User`, `Portal_Access_Log`, `Leave_Request`, `App_Config`
- 11 of 16 `portal.*` functions deployed and compiling, under a real `portal` namespace
- **Not finished:** the 6 portal Pages, the Creator-side connections (`crm_conn`,
  `crm_write_conn`), and the Customer Portal permission set. Five functions are blocked on
  those connections. The design for all of it is in `docs/03-creator-app-guide.md`.

## Platform limits found by building this for real

- CRM standalone functions may only return `string`, and `standalone` is the only category
  callable from another function — so every helper returns JSON and callers parse it back
- CRM Deluge has no `while` loop and no counted loop; `for each x in <list>` is all there is
- The for-each iterable must be a plain variable, not a chained expression
- `invokeurl` needs a literal HTTP verb; there is no `zoho.crm.deleteRecord` task
- Workflow rules can only call `automation`-category functions, and schedules only
  `schedule`-category ones — hence the thin adapter layer in `deluge/automation/`
- A merge field on a lookup yields the display name, not the id
- Webforms do not expose lookup fields at all, and publish only as embed code
