/* ============================================================================
 * Zoho CRM Client Script
 * Module : Marks
 * Page   : Create / Edit (Standard)
 * Event  : onLoad + onSave
 *
 * Purpose: catch a bad mark BEFORE the record is saved, so the teacher sees the
 * error next to the field instead of getting an email two seconds later. The
 * server-side function school.validateMark is still the authority - this is a
 * usability layer, not the security boundary. Anything that comes in by API or
 * import bypasses this file entirely and is caught server-side.
 * ========================================================================== */

/* ---- onLoad : pull the paper ceiling from the Exam Schedule ---------------- */
var maxForThisPaper = null;
var passForThisPaper = null;

ZDK.Page.getField('Exam_Schedule').onChange(function () {
    var sched = ZDK.Page.getField('Exam_Schedule').getValue();
    if (!sched || !sched.id) {
        return;
    }
    var rec = ZDK.Apps.CRM.Records.get('Exam_Schedules', sched.id);
    if (!rec) {
        return;
    }
    maxForThisPaper  = parseFloat(rec.Max_Marks);
    passForThisPaper = parseFloat(rec.Passing_Marks);

    // Mirror onto the record so the value is visible and stored.
    ZDK.Page.getField('Max_Marks').setValue(maxForThisPaper);
    ZDK.Page.getField('Marks_Obtained').setPlaceholder('0 - ' + maxForThisPaper);
});

/* ---- Absent toggles the marks field ---------------------------------------- */
ZDK.Page.getField('Is_Absent').onChange(function () {
    var absent = ZDK.Page.getField('Is_Absent').getValue();
    if (absent) {
        ZDK.Page.getField('Marks_Obtained').setValue(0);
        ZDK.Page.getField('Marks_Obtained').setReadOnly(true);
    } else {
        ZDK.Page.getField('Marks_Obtained').setReadOnly(false);
    }
});

/* ---- Live feedback as the teacher types ------------------------------------ */
ZDK.Page.getField('Marks_Obtained').onChange(function () {
    var val = parseFloat(ZDK.Page.getField('Marks_Obtained').getValue());
    if (isNaN(val) || maxForThisPaper === null) {
        return;
    }
    if (val > maxForThisPaper) {
        ZDK.Client.showMessage('Maximum for this paper is ' + maxForThisPaper, { type: 'error' });
        return;
    }
    var pct = (val * 100) / maxForThisPaper;
    ZDK.Page.getField('Percentage').setValue(Math.round(pct * 100) / 100);
    ZDK.Page.getField('Result').setValue(val >= passForThisPaper ? 'Pass' : 'Fail');
});

/* ---- onSave : the blocking checks ------------------------------------------ */
ZDK.Page.onSave(function () {
    var absent = ZDK.Page.getField('Is_Absent').getValue();
    var raw    = ZDK.Page.getField('Marks_Obtained').getValue();
    var sched  = ZDK.Page.getField('Exam_Schedule').getValue();

    if (!sched || !sched.id) {
        ZDK.Client.showMessage('Select the Exam Schedule first - it defines the maximum marks.', { type: 'error' });
        return false;
    }
    if (absent) {
        return true;
    }
    if (raw === null || raw === '' || isNaN(parseFloat(raw))) {
        ZDK.Client.showMessage('Enter the marks, or tick Absent.', { type: 'error' });
        return false;
    }

    var val = parseFloat(raw);
    if (val < 0) {
        ZDK.Client.showMessage('Marks cannot be negative.', { type: 'error' });
        return false;
    }
    if (maxForThisPaper !== null && val > maxForThisPaper) {
        ZDK.Client.showMessage('Marks (' + val + ') exceed the paper maximum (' + maxForThisPaper + ').', { type: 'error' });
        return false;
    }
    return true;
});
