#!/usr/bin/env python3
"""
Second round of CRM-Deluge dialect fixes, again driven by the compiler's errors.

4. There is no counted loop either: `for each index i in 1 to N` is rejected
   ("Expecting '{', Found 'to'"). The only iteration construct CRM Deluge has is
   `for each x in <list>`, so the bound is materialised as a list.
5. The `in` position of a for-each must be a plain variable — a chained
   expression such as `resp.get("data").toList()` is an "Improper Statement".
6. Two more zoho.crm.deleteRecord calls in the admission rollback path.
"""
import glob, os, re

BOUNDED = '''

/* ----------------------------------------------------------------------------
 * school.boundedSeq - CRM Deluge has neither a while loop nor a counted loop;
 * `for each x in <list>` is the only iteration construct there is. Every paged
 * read in this project needs a hard ceiling on the API calls it can make, so
 * that ceiling is materialised as a list once and iterated.
 * -------------------------------------------------------------------------- */
list school.boundedSeq(int upto)
{
    digits = {0,1,2,3,4,5,6,7,8,9};
    out    = List();
    for each h in digits
    {
        if(h * 100 <= upto)
        {
            for each t in digits
            {
                for each u in digits
                {
                    n = h * 100 + t * 10 + u + 1;
                    if(n <= upto)
                    {
                        out.add(n);
                    }
                }
            }
        }
    }
    return out;
}
'''

DEL_OLD = {
    '            zoho.crm.deleteRecord("Enrollments", createdEnrollmentId.toLong());':
    '''            invokeurl
            [
                url        : "https://www.zohoapis.in/crm/v5/Enrollments/" + createdEnrollmentId
                type       : DELETE
                connection : "crmconn"
            ];''',
    '            zoho.crm.deleteRecord("Students", createdStudentId.toLong());':
    '''            invokeurl
            [
                url        : "https://www.zohoapis.in/crm/v5/Students/" + createdStudentId
                type       : DELETE
                connection : "crmconn"
            ];''',
}

COUNTED = re.compile(r'^(\s*)for each index (loopGuard\d+) in 1 to (\d+)\s*$')
FOREACH = re.compile(r'^(\s*)for each (\w+) in (.+?)\s*$')

for p in sorted(glob.glob('deluge/crm/*.dg')):
    lines = open(p).read().split('\n')
    out, n = [], 0
    for line in lines:
        if line in DEL_OLD:
            out.append(DEL_OLD[line]); n += 1; continue
        m = COUNTED.match(line)
        if m:
            pad, var, lim = m.groups()
            out.append('%sloopSeq%s = school.boundedSeq(%s);' % (pad, var[9:], lim))
            out.append('%sfor each %s in loopSeq%s' % (pad, var, var[9:]))
            n += 1
            continue
        m = FOREACH.match(line)
        # hoist anything that is not already a bare variable
        if m and not re.fullmatch(r'\w+', m.group(3)):
            pad, var, expr = m.groups()
            n += 1
            name = 'iter_' + var
            out.append('%s%s = %s;' % (pad, name, expr))
            out.append('%sfor each %s in %s' % (pad, var, name))
            continue
        out.append(line)
    s = '\n'.join(out)
    if p.endswith('00_utils.dg'):
        s = s.rstrip() + '\n' + BOUNDED
        n += 1
    open(p, 'w').write(s)
    if n:
        print('%-34s %d fixes' % (os.path.basename(p), n))
