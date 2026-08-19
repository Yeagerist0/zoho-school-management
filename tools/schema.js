// ---------------------------------------------------------------------------
// Zoho CRM schema reconciler — declarative spec + idempotent apply.
// Runs in the browser console on crm.zoho.in (session auth + CSRF token).
// Field/picklist creation in the CRM UI is one drag per field; this makes the
// whole 23-module schema a single reviewable artefact that can be re-run.
// ---------------------------------------------------------------------------

const T = (n, o = {}) => ({ api_name: n, data_type: 'text', length: 255, ...o });
const P = (n, opts, o = {}) => ({ api_name: n, data_type: 'picklist', options: opts, ...o });
const L = (n, mod, o = {}) => ({ api_name: n, data_type: 'lookup', lookup_module: mod, ...o });
const N = (n, o = {}) => ({ api_name: n, data_type: 'integer', ...o });
const D = (n, o = {}) => ({ api_name: n, data_type: 'double', decimal_place: 2, ...o });
const C = (n, o = {}) => ({ api_name: n, data_type: 'currency', decimal_place: 2, ...o });
const DT = (n, o = {}) => ({ api_name: n, data_type: 'date', ...o });
const B = (n, o = {}) => ({ api_name: n, data_type: 'boolean', ...o });
const TA = (n, o = {}) => ({ api_name: n, data_type: 'textarea', ...o });

// NOTE: the key is case_sensitive (snake_case). 'casesensitive' is silently ignored
// at create time and the field comes out non-unique.
const UNIQ = { unique: { case_sensitive: false } };

const GENDER = ['Male', 'Female', 'Other'];
const BLOOD = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

// module -> fields that must exist with exactly these picklist options
const SPEC = {
  Leads: [
    T('Student_First_Name'), T('Student_Last_Name'), DT('Student_DOB'),
    P('Gender', GENDER),
    L('Applying_For_Class', 'Classes'), L('Target_Academic_Year', 'Academic_Years'),
    T('Previous_School'),
    P('Enquiry_Source', ['Walk-in', 'Website', 'Referral', 'Advertisement', 'Social Media', 'Education Fair']),
    T('Application_No', UNIQ),
    D('Assessment_Score'), TA('Rejection_Reason'),
    P('Relationship', ['Father', 'Mother', 'Guardian']),
    T('Generated_Student_ID'), DT('Converted_On'),
  ],
  Contacts: [
    P('Relationship', ['Father', 'Mother', 'Guardian']),
    T('Occupation'), B('Portal_Enabled'),
    { api_name: 'Alternate_Mobile', data_type: 'phone' },
  ],
  Academic_Years: [
    T('Year_Code', UNIQ), DT('Start_Date'), DT('End_Date'), B('Is_Current'),
    N('Total_Working_Days'), N('Min_Attendance_For_Promotion'),
  ],
  Classes: [N('Level'), P('Stream', ['Science', 'Commerce', 'Arts', 'General'])],
  Class_Sections: [
    L('Academic_Year', 'Academic_Years'), L('Class', 'Classes'),
    P('Section', ['A', 'B', 'C', 'D', 'E', 'F']),
    L('Class_Teacher', 'Teachers'), T('Room_No'),
    N('Max_Strength'), N('Current_Strength'), B('Is_Active'), T('Section_Key', UNIQ),
  ],
  Teachers: [
    T('Employee_ID', UNIQ), { api_name: 'Mobile', data_type: 'phone' },
    DT('Date_Of_Joining'), T('Qualification'),
    P('Department', ['Science', 'Mathematics', 'Languages', 'Social Studies', 'Computer Science', 'Arts', 'Physical Education', 'Administration']),
    P('Status', ['Active', 'On Leave', 'Resigned']),
  ],
  Subjects: [
    T('Subject_Code', UNIQ), L('Applicable_Class', 'Classes'),
    N('Default_Max_Marks'), B('Is_Elective'), B('Has_Practical'),
  ],
  Subject_Allocations: [
    L('Academic_Year', 'Academic_Years'), L('Class_Section', 'Class_Sections'),
    L('Subject', 'Subjects'), L('Teacher', 'Teachers'),
    N('Periods_Per_Week'), T('Allocation_Key', UNIQ),
  ],
  Students: [
    T('Student_ID', UNIQ), T('Student_Name'), DT('DOB'),
    P('Gender', GENDER), P('Blood_Group', BLOOD), DT('Admission_Date'),
    L('Parent', 'Contacts'), L('Secondary_Parent', 'Contacts'),
    L('Current_Enrollment', 'Enrollments'), L('Current_Class_Section', 'Class_Sections'),
    P('Status', ['Active', 'Alumni', 'Transferred Out', 'Suspended']),
    L('Source_Lead', 'Leads'),
    TA('Address'), T('City'), T('Pincode'), B('Transport_Opted'), TA('Medical_Notes'),
  ],
  Enrollments: [
    L('Student', 'Students'), L('Academic_Year', 'Academic_Years'), L('Class_Section', 'Class_Sections'),
    N('Roll_No'), DT('Enrollment_Date'),
    P('Status', ['Active', 'Promoted', 'Detained', 'Left']),
    N('Days_Marked'), N('Days_Present'), D('Attendance_Percent'),
    D('Final_Percentage'), P('Final_Result', ['Pass', 'Fail', 'Pending']),
    T('Enrollment_Key', UNIQ),
  ],
  Holidays: [
    DT('Holiday_Date'), P('Type', ['Holiday', 'Weekly Off', 'Vacation', 'Exam Break']),
    L('Academic_Year', 'Academic_Years'), T('Holiday_Key', UNIQ),
  ],
  Attendance: [
    L('Student', 'Students'), L('Enrollment', 'Enrollments'), L('Class_Section', 'Class_Sections'),
    DT('Attendance_Date'),
    P('Status', ['Present', 'Absent', 'Late', 'Half Day', 'Approved Leave']),
    L('Marked_By', 'Teachers'), TA('Remarks'), T('Attendance_Key', UNIQ),
  ],
  Examinations: [
    T('Exam_Name'), L('Academic_Year', 'Academic_Years'),
    P('Exam_Type', ['Unit Test 1', 'Unit Test 2', 'Mid Term', 'Pre-Final', 'Final']),
    DT('Start_Date'), DT('End_Date'), D('Weightage_Percent'), B('Results_Published'),
  ],
  Exam_Schedules: [
    L('Examination', 'Examinations'), L('Class_Section', 'Class_Sections'), L('Subject', 'Subjects'),
    DT('Exam_Date'), N('Max_Marks'), N('Passing_Marks'), T('Schedule_Key', UNIQ),
  ],
  Marks: [
    L('Student', 'Students'), L('Examination', 'Examinations'), L('Subject', 'Subjects'),
    L('Exam_Schedule', 'Exam_Schedules'),
    D('Marks_Obtained'), D('Max_Marks'), B('Is_Absent'), D('Percentage'), T('Grade'),
    P('Result', ['Pass', 'Fail']), L('Entered_By', 'Teachers'),
    TA('Validation_Error'), T('Marks_Key', UNIQ),
  ],
  Exam_Results: [
    L('Student', 'Students'), L('Examination', 'Examinations'), L('Enrollment', 'Enrollments'),
    L('Class_Section', 'Class_Sections'),
    D('Total_Obtained'), D('Total_Max'), D('Percentage'), T('Overall_Grade'),
    N('Subjects_Failed'), P('Result', ['Pass', 'Fail']),
    N('Class_Rank'), N('Section_Rank'), T('Result_Key', UNIQ),
  ],
  Fee_Structures: [
    L('Academic_Year', 'Academic_Years'), L('Class', 'Classes'),
    C('Tuition_Fee'), C('Transport_Fee'), C('Lab_Fee'), C('Exam_Fee'), C('Misc_Fee'),
    C('Total_Fee'), N('No_of_Installments'), TA('Installment_Plan'),
  ],
  Student_Fees: [
    L('Student', 'Students'), L('Academic_Year', 'Academic_Years'), L('Fee_Structure', 'Fee_Structures'),
    C('Total_Fee'), C('Concession_Amount'), T('Concession_Reason'),
    C('Net_Payable'), C('Amount_Paid'), C('Outstanding'),
    P('Status', ['Not Started', 'Partially Paid', 'Paid', 'Overdue']),
    DT('Next_Due_Date'), C('Next_Due_Amount'),
    DT('Last_Reminder_Sent'), B('Escalated'),
  ],
  Fee_Installments: [
    L('Student_Fee', 'Student_Fees'), N('Installment_No'), DT('Due_Date'),
    C('Amount_Due'), C('Amount_Paid'), C('Balance'),
    P('Status', ['Pending', 'Partially Paid', 'Paid', 'Overdue']),
  ],
  Payments: [
    T('Receipt_No', UNIQ), L('Student', 'Students'), L('Student_Fee', 'Student_Fees'),
    DT('Payment_Date'), C('Amount'),
    P('Mode', ['Cash', 'UPI', 'Card', 'Cheque', 'NEFT']),
    T('Transaction_Ref'), L('Collected_By', 'Teachers'),
    P('Status', ['Success', 'Bounced', 'Refunded']), TA('Allocation_Detail'),
  ],
  Announcements: [
    TA('Body'), P('Audience', ['All', 'Class', 'Section']),
    L('Class_Section', 'Class_Sections'), DT('Publish_From'), DT('Publish_To'), B('Is_Active'),
  ],
  App_Settings: [T('Setting_Key', UNIQ), TA('Setting_Value')],
  Sequence_Counters: [T('Counter_Key', UNIQ), N('Last_Value'), T('Lock_Token')],
  Leave_Requests: [
    L('Student', 'Students'), DT('From_Date'), DT('To_Date'), TA('Reason'),
    P('Status', ['Pending', 'Approved', 'Rejected']),
    L('Approved_By', 'Teachers'),
    P('Source', ['Parent Portal', 'Front Desk']),
    { api_name: 'Requested_By_Email', data_type: 'email' },
    T('Creator_Record_ID'),
    P('Sync_Status', ['Pending', 'Synced', 'Failed']),
  ],
  Student_Risk_Flags: [
    T('Risk_Key', UNIQ), L('Student', 'Students'), L('Academic_Year', 'Academic_Years'),
    L('Class_Section', 'Class_Sections'),
    N('Risk_Score'), P('Risk_Band', ['None', 'Low', 'Medium', 'High', 'Critical']),
    TA('Reasons'), D('Attendance_At_Flag'), DT('Last_Evaluated'),
  ],
};

// Lead_Status is a stock picklist re-valued to the admission funnel.
const STOCK_PICKLISTS = {
  Leads: {
    Lead_Status: ['New', 'Contacted', 'Campus Visit Scheduled', 'Application Submitted',
      'Assessment Done', 'Admission Offered', 'Admission Confirmed', 'Rejected', 'Dropped'],
  },
};

const NEW_MODULES = [
  { plural_label: 'Leave Requests', singular_label: 'Leave Request' },
  { plural_label: 'Student Risk Flags', singular_label: 'Student Risk Flag' },
];

// --------------------------------------------------------------------- engine
const ORG = '60083663008';
const ck = Object.fromEntries(document.cookie.split('; ').map(s => { const i = s.indexOf('='); return [s.slice(0, i), s.slice(i + 1)]; }));
const HDR = {
  'X-ZCSRF-TOKEN': 'crmcsrfparam=' + ck['crmcsr'],
  'X-CRM-ORG': ORG, 'Accept': 'application/json', 'Content-Type': 'application/json',
};
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: HDR, credentials: 'include', ...opts });
  const t = await r.text();
  try { return { s: r.status, j: JSON.parse(t) }; } catch (e) { return { s: r.status, t: t.slice(0, 400) }; }
};
const label = n => n.replace(/_/g, ' ');

async function ensureModules(log) {
  const cur = (await api('/crm/v7/settings/modules')).j.modules.map(m => m.api_name);
  const profiles = (await api('/crm/v7/settings/profiles')).j.profiles.map(p => ({ id: p.id }));
  for (const m of NEW_MODULES) {
    const apiName = m.plural_label.replace(/ /g, '_');
    if (cur.includes(apiName)) { log.push('module ok ' + apiName); continue; }
    const r = await api('/crm/v7/settings/modules', {
      method: 'POST', body: JSON.stringify({ modules: [{ ...m, profiles }] }),
    });
    log.push('module ' + apiName + ' -> ' + JSON.stringify(r.j).slice(0, 200));
  }
}

function createPayload(f) {
  // f.owner is the module the field is being added to
  const p = { field_label: label(f.api_name), api_name: f.api_name, data_type: f.data_type };
  if (f.data_type === 'text') p.length = f.length || 255;
  // textarea rejects `length`; it wants a textarea.type of small|large|rich_text
  if (f.data_type === 'textarea') p.textarea = { type: 'large' };
  if (f.data_type === 'double' || f.data_type === 'currency') { p.decimal_place = f.decimal_place || 2; p.length = 16; }
  if (f.data_type === 'integer') p.length = 9;
  if (f.data_type === 'picklist') p.pick_list_values = f.options.map((o, i) => ({ display_value: o, actual_value: o, sequence_number: i + 1 }));
  // display_label is the related-list title rendered on the TARGET module and must be
  // unique among that module's related lists — hence the qualifier.
  if (f.data_type === 'lookup') p.lookup = {
    module: { api_name: f.lookup_module },
    display_label: f.owner.replace(/_/g, ' ') + ' (' + label(f.api_name) + ')',
  };
  if (f.unique) p.unique = f.unique;
  return p;
}

// Bring one picklist's options in line with the spec: add what is missing,
// retire ("unused") what Zoho seeded as Option 1 / Option 2 or what we dropped.
function picklistOps(live, want) {
  const active = live.pick_list_values.filter(o => o.type !== 'unused');
  const have = active.map(o => o.display_value);
  const ops = [];
  want.forEach((o, i) => {
    if (!have.includes(o)) ops.push({ display_value: o, actual_value: o, sequence_number: i + 2 });
  });
  active.filter(o => o.display_value !== '-None-' && !want.includes(o.display_value))
    .forEach(o => ops.push({ id: o.id, display_value: o.display_value, actual_value: o.actual_value, _delete: null }));
  return ops;
}

async function reconcile(mod, log) {
  const spec = SPEC[mod];
  const r = await api('/crm/v7/settings/fields?module=' + mod + '&type=all');
  if (r.s !== 200) { log.push(mod + ' FIELDS-READ-FAIL ' + JSON.stringify(r).slice(0, 120)); return; }
  const live = Object.fromEntries(r.j.fields.map(f => [f.api_name, f]));

  const toCreate = spec.filter(f => !live[f.api_name]).map(f => createPayload({ ...f, owner: mod }));
  for (let i = 0; i < toCreate.length; i += 5) {
    const chunk = toCreate.slice(i, i + 5);
    const res = await api('/crm/v7/settings/fields?module=' + mod, { method: 'POST', body: JSON.stringify({ fields: chunk }) });
    (res.j.fields || [res]).forEach((x, k) => {
      if (x.status !== 'success') log.push(mod + '.' + chunk[k].api_name + ' CREATE-FAIL ' + JSON.stringify(x.details || x).slice(0, 160));
      else log.push(mod + '.' + chunk[k].api_name + ' created');
    });
  }

  const patches = [];
  for (const f of spec) {
    const lv = live[f.api_name];
    if (!lv || f.data_type !== 'picklist') continue;
    const ops = picklistOps(lv, f.options);
    if (ops.length) { patches.push({ id: lv.id, pick_list_values: ops }); log.push(mod + '.' + f.api_name + ' picklist x' + ops.length); }
  }
  for (const [fname, opts] of Object.entries(STOCK_PICKLISTS[mod] || {})) {
    const lv = live[fname];
    if (!lv) continue;
    const ops = picklistOps(lv, opts);
    if (ops.length) { patches.push({ id: lv.id, pick_list_values: ops }); log.push(mod + '.' + fname + ' picklist x' + ops.length); }
  }
  for (let i = 0; i < patches.length; i += 5) {
    const res = await api('/crm/v7/settings/fields?module=' + mod, { method: 'PATCH', body: JSON.stringify({ fields: patches.slice(i, i + 5) }) });
    (res.j.fields || []).forEach(x => { if (x.status !== 'success') log.push(mod + ' PATCH-FAIL ' + JSON.stringify(x.details || x).slice(0, 160)); });
  }
}

window.__zoho = { api, SPEC, reconcile, ensureModules, createPayload, picklistOps, NEW_MODULES };
'schema.js loaded: ' + Object.keys(SPEC).length + ' modules in spec';
