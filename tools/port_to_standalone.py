#!/usr/bin/env python3
"""
Port the CRM Deluge kit to Zoho CRM's standalone-function contract.

Zoho CRM refuses to compile a standalone function whose declared return type is
anything but `string` ("Invalid return Type list. Category standalone returns
string"). Standalone is also the only category a function can be called from
another function, so every helper here has to return a string.

The port is therefore mechanical but has to be done at both ends:
  * definitions   `list school.coql(...)`  -> `string standalone.coql(...)`
                  and each `return x;`     -> `return x.toString();`
  * call sites    `school.coql(q)`         -> `standalone.coql(q).toJSONList()`
so the value seen by the caller keeps its original type.

Emits tools/functions.json — one entry per function, ready to POST+PUT.
"""
import json, os, re, sys

SRC = 'deluge/crm'
SIG = re.compile(r'^(void|int|bigint|string|list|map|bool|boolean|decimal|date|datetime)\s+school\.([A-Za-z_]\w*)\s*\(([^)]*)\)\s*$')

# original return type -> conversion the CALLER must apply to the string it gets
CAST = {
    'list': '.toJSONList()',
    'map': '.toMap()',
    'int': '.toLong()',
    'bigint': '.toLong()',
    'decimal': '.toDecimal()',
    'boolean': '.toBoolean()',
    'bool': '.toBoolean()',
    'string': '',
    'void': '',
}
# Deluge declared type -> the type name the function API expects for arguments
ARGTYPE = {'string': 'string', 'int': 'int', 'bigint': 'bigint', 'decimal': 'decimal',
           'bool': 'boolean', 'boolean': 'boolean', 'date': 'date', 'datetime': 'datetime',
           'list': 'list', 'map': 'map'}


def split_top_level(s):
    """Split a parameter list on commas that are not nested in brackets."""
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out if x.strip()]


def parse_file(path):
    lines = open(path).read().split('\n')
    fns, i = [], 0
    while i < len(lines):
        m = SIG.match(lines[i].strip())
        if not m:
            i += 1
            continue
        ret, name, raw = m.group(1), m.group(2), m.group(3)
        params = []
        for p in split_top_level(raw):
            t, _, n = p.rpartition(' ')
            params.append({'name': n.strip(), 'type': ARGTYPE[t.strip()]})
        # brace-match the body
        j = i + 1
        while lines[j].strip() != '{':
            j += 1
        depth, k = 0, j
        while True:
            depth += lines[k].count('{') - lines[k].count('}')
            if depth == 0:
                break
            k += 1
        body = '\n'.join(lines[j + 1:k])
        fns.append({'file': os.path.basename(path), 'name': name, 'ret': ret,
                    'params': params, 'body': body, 'lineno': i + 1})
        i = k + 1
    return fns


def port_calls(text, rettypes):
    """Rewrite school.f(...) -> standalone.f(...)<cast>, matching parens."""
    out, i = '', 0
    while True:
        m = re.compile(r'school\.([A-Za-z_]\w*)\s*\(').search(text, i)
        if not m:
            out += text[i:]
            return out
        name = m.group(1)
        # walk to the matching close paren
        depth, k = 1, m.end()
        while depth:
            if text[k] == '(':
                depth += 1
            elif text[k] == ')':
                depth -= 1
            k += 1
        cast = CAST[rettypes.get(name, 'void')]
        # A call used as a bare statement stays a statement — `f(x).toLong();`
        # is not a valid Deluge statement, `f(x);` is.
        line_start = text.rfind('\n', 0, m.start()) + 1
        if not text[line_start:m.start()].strip() and text[k:k + 1] == ';':
            cast = ''
        out += text[i:m.start()] + 'standalone.' + name + text[m.end() - 1:k] + cast
        i = k


def port_returns(body, ret):
    """A string-returning function must hand back a string."""
    if ret == 'void':
        body = re.sub(r'\breturn\s*;', 'return "";', body)
        return body.rstrip() + '\nreturn "";\n'
    if ret == 'string':
        return body
    # list / map / int / decimal: stringify whatever is being returned
    def fix(m):
        expr = m.group(1).strip()
        return 'return ' + expr + '.toString();'
    return re.sub(r'\breturn\s+(.+?);', fix, body)


def main():
    fns = []
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.dg'):
            fns += parse_file(os.path.join(SRC, f))
    rettypes = {f['name']: f['ret'] for f in fns}
    dup = [n for n in rettypes if [x['name'] for x in fns].count(n) > 1]
    if dup:
        sys.exit('duplicate function names: ' + str(dup))

    for f in fns:
        w = port_returns(port_calls(f['body'], rettypes), f['ret'])
        # a parse straight back into a string is a no-op round trip
        for c in ('.toJSONList()', '.toMap()', '.toLong()', '.toDecimal()', '.toBoolean()'):
            w = w.replace(c + '.toString()', '')
        f['workflow'] = w

    json.dump(fns, open('tools/functions.json', 'w'), indent=1)
    print('%d functions' % len(fns))
    for f in fns:
        print('  %-28s %-8s -> string  args=%s' % (
            f['name'], f['ret'], ','.join(p['name'] + ':' + p['type'] for p in f['params']) or '-'))


main()
