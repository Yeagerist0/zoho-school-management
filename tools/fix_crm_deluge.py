#!/usr/bin/env python3
"""
Three things the kit assumed that Zoho CRM's Deluge dialect does not support.
Found by deploying and reading the compiler's own errors, fixed at the source.

1. `while (...)` — CRM Deluge has no while loop ("The syntax is incorrect").
   Rewritten as a bounded `for each index ... in 1 to N` with an explicit break,
   which is what the paging loops wanted anyway: a hard ceiling on API calls.
2. `type : method` in invokeurl — the HTTP verb must be a literal, not a variable
   ("Invalid HTTP method 'type' detected").
3. `zoho.crm.deleteRecord` does not exist as a Deluge task; deletion goes over
   the REST API through the same connection.
"""
import re, sys

def fix_while(text, fname):
    out, n = [], 0
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        m = re.match(r'^(\s*)while\((.+)\)\s*$', lines[i])
        if not m or not lines[i + 1].strip() == '{':
            out.append(lines[i]); i += 1; continue
        n += 1
        pad, cond = m.group(1), m.group(2).strip()
        bound = re.search(r'<=\s*(\d+)', cond)
        limit = bound.group(1) if bound else '1000'
        out += [
            pad + '// CRM Deluge has no while loop - bounded loop with an explicit exit.',
            pad + 'for each index loopGuard%d in 1 to %s' % (n, limit),
            pad + '{',
            pad + '    if(!(%s)) { break; }' % cond,
        ]
        i += 2
    return '\n'.join(out), n


PUSH_OLD = '''    resp = invokeurl
    [
        url        : "https://www.zohoapis.in/crm/v5/" + moduleName
        type       : method
        parameters : body.toString()
        headers    : {"Content-Type":"application/json"}
        connection : "crmconn"
    ];'''

PUSH_NEW = '''    // invokeurl needs a literal HTTP verb, so the two paths are spelled out.
    resp = Map();
    if(method == "POST")
    {
        resp = invokeurl
        [
            url        : "https://www.zohoapis.in/crm/v5/" + moduleName
            type       : POST
            parameters : body.toString()
            headers    : {"Content-Type":"application/json"}
            connection : "crmconn"
        ];
    }
    else
    {
        resp = invokeurl
        [
            url        : "https://www.zohoapis.in/crm/v5/" + moduleName
            type       : PUT
            parameters : body.toString()
            headers    : {"Content-Type":"application/json"}
            connection : "crmconn"
        ];
    }'''

DEL_OLD = '''    insts = zoho.crm.searchRecords("Fee_Installments", "(Student_Fee:equals:" + feeId + ")");
    for each i in insts
    {
        zoho.crm.deleteRecord("Fee_Installments", i.get("id").toLong());
    }
    zoho.crm.deleteRecord("Student_Fees", feeId.toLong());'''

DEL_NEW = '''    // There is no zoho.crm.deleteRecord task - deletion goes over REST.
    insts = zoho.crm.searchRecords("Fee_Installments", "(Student_Fee:equals:" + feeId + ")");
    for each i in insts
    {
        invokeurl
        [
            url        : "https://www.zohoapis.in/crm/v5/Fee_Installments/" + i.get("id")
            type       : DELETE
            connection : "crmconn"
        ];
    }
    invokeurl
    [
        url        : "https://www.zohoapis.in/crm/v5/Student_Fees/" + feeId
        type       : DELETE
        connection : "crmconn"
    ];'''

import glob, os
total = 0
for p in sorted(glob.glob('deluge/crm/*.dg')):
    s = open(p).read()
    orig = s
    s = s.replace(PUSH_OLD, PUSH_NEW).replace(DEL_OLD, DEL_NEW)
    s, n = fix_while(s, p)
    total += n
    if s != orig:
        open(p, 'w').write(s)
        print('%-34s while->%d %s' % (os.path.basename(p), n,
              'invokeurl' if PUSH_NEW in s or DEL_NEW in s else ''))
print('total while loops rewritten:', total)
