# Additional Feature — Student Early-Warning Engine

*(code: `deluge/crm/07_early_warning_engine.dg`)*

## The problem I picked

A school already holds every signal it needs to catch a child slipping — attendance, marks,
fee status. It just holds them in three different modules that nobody joins.

Individually each signal is weak and gets ignored: one absence is nothing, one bad unit
test is nothing, a late fee instalment is an accounts matter. Together they are the
textbook profile of a student about to drop out or fail the year. In most schools the
pattern only becomes visible at the parent-teacher meeting, which is one to four months
after the point where an intervention would still have worked.

Two facts made me pick this over the more obvious candidates (bulk report-card PDFs, a
transport module, an SMS gateway):

1. **It needs no new data.** Every input is already being captured for other reasons, so
   the feature costs the school nothing in extra data entry — which is the reason most
   school-software features go unused.
2. **It converts data the school already owns into an action a specific person must take
   today.** A dashboard tells you 80 students are at risk. This creates 80 tasks with names
   on them.

## What it does

Nightly, for every active student:

| Signal | Threshold | Weight |
|---|---|---|
| Attendance below target | < 75% (only after 15+ marked days) | 40 |
| Consecutive absences | ≥ 3 school days in a row | 25 |
| Academic decline | last exam ≥ 15 points below the previous | 20 |
| Fee overdue | > 30 days past due | 15 |

Score → band → action:

| Band | Score | Action |
|---|---|---|
| Low | 1–19 | Recorded only |
| Medium | 20–39 | CRM Task for the class teacher, due in 3 days |
| High | 40–64 | Task + email to the parent |
| Critical | 65+ | Task (due tomorrow, Highest priority) + parent email |

Plus a same-day **"your child was marked absent today"** alert — one query, one batched
mail-out, deduplicated by a stamp on the attendance row.

Thresholds and weights live in an `App_Settings` record, not in the code. A school that
runs on 80% attendance changes a number; nobody redeploys a function.

## How it is built, and why that way

The brief said optimisation and scalability matter, and this feature is where they
actually bite — it is the only thing in the system that touches every student every night.

**1. No N+1 queries.** The naive implementation is `for each student → query attendance,
query marks, query fees`. At 2,000 students that is 6,000 API calls a night, which exceeds
the daily credit budget before it finishes and takes hours. Instead the engine runs a fixed
number of **paged COQL sweeps** — one per signal, 200 rows a page — and joins them in memory
by student id in a single pass. Cost becomes `O(total rows / 200)` API calls, roughly 40–60
for a 2,000-student school, and it does not degrade as the data skews.

**2. It reads pre-aggregated numbers.** `Attendance_Percent` is already maintained
incrementally on the Enrollment by the attendance workflow, and exam percentages already
live on `Exam_Results`. The engine never re-aggregates a year of raw attendance rows or
recomputes an exam. The only raw scan is a **14-day window** of absences for streak
detection — bounded, not growing with the year.

**3. It notifies on state *change*, not on state.** A flag is only acted on when the band
moves *up*. Without that rule, a school with 80 at-risk students sends 80 identical emails
every night; parents mute the sender inside a week and the feature is worse than useless.
This is the single most important line in the file.

**4. Writes are batched.** Flags go out through `/upsert` in batches of 100 with `trigger:[]`
suppressing workflows — ~20 write calls for 2,000 students instead of 2,000, and no
workflow storm.

**5. It is idempotent and resumable.** `Risk_Key` is unique, so upsert updates rather than
duplicates; every loop is page-bounded so a runaway data condition cannot spin the
function into the execution ceiling.

**6. Policy is data.** Weights, thresholds and the band cut-offs come from `App_Settings`,
so the counsellor tunes the model, not a developer.

## Complexity

| | Naive | This engine |
|---|---|---|
| API calls (2,000 students) | ~6,000 | ~60 |
| Reads scaling | per student | per 200 rows |
| Raw attendance scanned | full year | 14 days |
| Writes | 2,000 | ~20 |
| Emails on a steady-state night | ~80 | 0 (only on change) |

## What I'd add next

The scoring function is deliberately linear and transparent so a teacher can see exactly
why a child was flagged. The obvious next step is to backtest the weights against the
school's own historical outcomes — which students actually failed or left — and retune
them. Because the weights are already data rather than code, that is a config change, not a
rewrite.
