# Admission Enquiry Webform (Zoho CRM → Leads)

**Setup > Developer Space > Webforms > Leads > Create Form**

## Fields on the form

| Order | Field (Leads) | Type | Required | Note |
|---|---|---|---|---|
| 1 | `Student_First_Name` | Single line | ✅ | |
| 2 | `Student_Last_Name` | Single line | ✅ | |
| 3 | `Student_DOB` | Date | ✅ | age band validated by the workflow |
| 4 | `Gender` | Picklist | ✅ | |
| 5 | `Applying_For_Class` | Lookup → Classes | ✅ | rendered as a dropdown |
| 6 | `Target_Academic_Year` | Lookup → Academic_Years | ✅ | default = current |
| 7 | `Last_Name` | Single line | ✅ | **parent's** last name (Leads' mandatory field) |
| 8 | `First_Name` | Single line | | parent's first name |
| 9 | `Relationship` | Picklist | ✅ | Father / Mother / Guardian |
| 10 | `Email` | Email | ✅ | **this becomes the parent portal login** |
| 11 | `Mobile` | Phone | ✅ | |
| 12 | `Previous_School` | Single line | | |
| 13 | `Street`, `City`, `Zip_Code` | | | |
| 14 | `Enquiry_Source` | Picklist | | Website / Walk-in / Referral / Social / Newspaper |
| 15 | `Description` | Multi-line | | "anything you'd like us to know" |

Hidden/system: `Lead_Source` = `Web Form`, `Lead_Status` = `New`, `Application_No` = auto-number.

## Form settings

- **reCAPTCHA:** ON (mandatory — this URL is public).
- **Duplicate check:** on `Email` → *update existing record* is **off**; a second
  enquiry from the same parent for a second child is a legitimate new lead.
- **Approval:** OFF — leads land straight in the funnel; the admission team triages.
- **Auto-response:** ON, "We've received your enquiry, reference `${Application_No}`".
- **Assignment rule:** round-robin across the admission counsellors, with
  `Applying_For_Class.Level >= 9` routed to the senior-school counsellor.
- **Return URL:** a thank-you page carrying the application number.

## Workflows attached to Leads

| # | Trigger | Action |
|---|---|---|
| 1 | Create, `Lead_Source = Web Form` | Instant email to parent (auto-response) + a Task for the assigned counsellor, due in 1 working day |
| 2 | Create | `school.validateEnquiry(leadId)` — checks the DOB against the age band for the applied class and flags `Age_Mismatch` for the counsellor rather than rejecting the enquiry |
| 3 | Edit → `Lead_Status = Campus Visit Scheduled` | Confirmation email + calendar event |
| 4 | Edit → `Lead_Status = Admission Confirmed` | **`school.confirmAdmission(leadId)`** — the conversion (see `02_admission_lead_conversion.dg`) |
| 5 | Edit → `Lead_Status = Rejected` | Requires `Rejection_Reason` (validation rule) + polite closure email |
| 6 | Time-based: `Lead_Status = New` and no activity for 3 days | Reminder task + escalation to the admission head |

## Why the funnel lives in Leads and not a custom module

An enquiry is not yet a student. Leads already ships with assignment rules, web-to-lead,
duplicate checks, an activity timeline, follow-up tasks and conversion tracking — every
one of which the admission process needs. Building a "Admission_Enquiries" custom module
means re-implementing all of that by hand, and losing the standard funnel reports.

The conversion is deliberately **not** the native "Convert Lead" action: native conversion
produces Contact + Account + Deal, which is a sales shape, not a school one. A confirmed
admission has to produce a Student, an Enrollment, a section seat and a fee ladder — so a
custom function owns it, and the Lead is retained and linked as `Source_Lead` for audit.
