# School Management System — Zoho CRM + Zoho Creator

Assignment implementation kit: data model, Deluge functions, Creator parent portal,
integration design, reports, and the submission write-up.

**Start here:** [`docs/07-submission-writeup.md`](docs/07-submission-writeup.md) — this is
the document to send to `sagar@it-guy.tech`.
**To build the org:** [`docs/02-crm-build-guide.md`](docs/02-crm-build-guide.md) — step by
step, in dependency order.

---

## Contents

| Path | What |
|---|---|
| `docs/01-data-model.md` | 22 modules, every field, relationship map, integrity rules |
| `docs/02-crm-build-guide.md` | Build order: connections → modules → functions → workflows → schedules → profiles |
| `docs/03-creator-app-guide.md` | Parent portal: forms, pages, portal auth, page snippet pattern |
| `docs/04-integration.md` | Why pull instead of sync; the three channels; change handling; idempotency |
| `docs/05-reports-dashboards.md` | 25 reports + 4 dashboards |
| `docs/06-additional-feature.md` | Early-warning engine: problem, design, complexity analysis |
| `docs/07-submission-writeup.md` | The submission document |
| `deluge/crm/00_utils.dg` | COQL paging, batch insert/update/upsert, grade band, day diff |
| `deluge/crm/01_student_id_generator.dg` | Per-year sequential Student IDs, race-safe |
| `deluge/crm/02_admission_lead_conversion.dg` | Lead → Contact + Student + Enrollment + Fee ladder, with rollback |
| `deluge/crm/03_attendance.dg` | Exception-based section marking, layered duplicate guards, incremental rollups, nightly reconciliation |
| `deluge/crm/04_marks_and_results.dg` | Mark validation, result computation, dense ranking, batched upsert |
| `deluge/crm/05_fees_and_payments.dg` | FIFO installment allocation, receipts, due/overdue scheduler |
| `deluge/crm/06_year_end_promotion.dg` | Promotion that preserves history instead of overwriting it |
| `deluge/crm/07_early_warning_engine.dg` | **Additional feature** |
| `deluge/crm/08_creator_sync.dg` | The only two CRM → Creator pushes |
| `deluge/creator/01_portal_identity.dg` | Parent resolution, the authorisation gate, access log |
| `deluge/creator/02_portal_data.dg` | Dashboard / attendance / results / fees, live from CRM |
| `deluge/creator/03_leave_request_writeback.dg` | The one write path, with bounded retry |
| `clientscript/marks_entry_validation.js` | Pre-save mark validation in the CRM UI |
| `webform/admission-enquiry-webform.md` | Webform fields, settings, and the workflows behind it |

---

## Before deploying

1. **Data centre** — every `invokeurl` targets `https://www.zohoapis.in`. Replace with
   `.com` / `.eu` / `.com.au` to match your org.
2. **Function namespace** — all CRM functions live under a Deluge category named `school`
   (hence `school.foo`), Creator functions under `portal`. Create those categories first.
3. **Connections** — four of them, listed in `docs/02-crm-build-guide.md` Step 1. The two
   Creator-side connections must be authorised by a dedicated low-privilege integration
   user, not by an admin.
4. **Unique fields** — set them before loading any data. Several functions rely on the
   platform rejecting duplicates.
5. **Seed order** — Academic Year → Classes → Sections → Teachers → Subjects → Subject
   Allocations → Fee Structures → Holidays, then run the webform.
