#!/usr/bin/env python3
"""Database-level tests for the workflows.

The SQL is read straight out of workflows/*.json, so the tests exercise the
queries n8n will run, against db/schema.sql, on a real PostgreSQL server.
They cover what can be checked without n8n, Telegram or SMTP: schema setup,
every query, approval rules, claim concurrency and stale-claim recovery.

Needs python3, the psql/createdb/dropdb client tools, and a PostgreSQL server
reachable through the usual PG* environment variables. tests/run.sh starts a
throwaway server in Docker and runs this file. `node` is optional and enables
the button-parser tests.
"""
import base64, glob, json, os, shutil, subprocess, sys, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES, CODE = {}, {}
for path in sorted(glob.glob(os.path.join(ROOT, 'workflows', '*.json'))):
    wf = os.path.basename(path)[:3]
    for n in json.load(open(path, encoding='utf-8'))['nodes']:
        if n['type'].endswith('.postgres'):
            QUERIES[(wf, n['name'])] = n['parameters']['query']
        if n['type'].endswith('.code'):
            CODE[(wf, n['name'])] = n['parameters']['jsCode']

used, failures, counts = set(), [], [0]


def psql(db, sql):
    r = subprocess.run(['psql', '-d', db, '-X', '-A', '-t', '-F', '|', '-q', '-v', 'ON_ERROR_STOP=1'],
                       input=sql, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def lit(v):
    return "'" + str(v).replace("'", "''") + "'"


def build(key, params, mode, expr=None):
    """Return the workflow query with its parameters filled in.

    mode 'inline' writes the values as quoted literals, mode 'bind' sends them
    as server-side parameters of unknown type. n8n's Postgres node passes
    queryReplacement values as text, so both forms are checked.
    """
    used.add(key)
    q = QUERIES[key]
    for k, v in (expr or {}).items():
        q = q.replace(k, v)
    assert '{{' not in q, key
    q = q.rstrip().rstrip(';')
    if mode == 'inline' or not params:
        for i in range(len(params), 0, -1):
            q = q.replace('$%d' % i, lit(params[i - 1]))
        return q + ';\n'
    return q + ' \\bind ' + ' '.join(lit(p) for p in params) + ' \\g\n'


def check(label, got, cond):
    counts[0] += 1
    ok = bool(cond(got))
    print(('  ok   ' if ok else '  FAIL ') + label + ('' if ok else '  -> ' + repr(got)))
    if not ok:
        failures.append(label)


def fresh(db):
    subprocess.run(['dropdb', '--if-exists', db], capture_output=True)
    subprocess.run(['createdb', db], check=True)


b = lambda s: base64.b64encode((' ' + (s or '')).encode()).decode()   # as the WF1 code nodes do
b64 = lambda s: base64.b64encode(s.encode()).decode()
SCHEMA = open(os.path.join(ROOT, 'db', 'schema.sql'), encoding='utf-8').read()
APPLICANT = open(os.path.join(ROOT, 'db', 'applicant.example.sql'), encoding='utf-8').read()


def lifecycle(mode):
    db = 'wf_test_' + mode
    fresh(db)
    R = lambda key, params=(), expr=None: psql(db, build(key, params, mode, expr))
    S = lambda sql: psql(db, sql)
    D = lambda action, tid, appl, ver: R(('WF1', 'Apply decision'), (action, tid, appl, ver))
    rows = lambda r: [x for x in r[1].splitlines() if x]

    print('== schema and setup (%s parameters)' % mode)
    check('schema.sql applies', S(SCHEMA), lambda r: r[0] == 0 and 'ERROR' not in r[2])
    check('schema.sql applies a second time', S(SCHEMA), lambda r: r[0] == 0)
    check('applicant.example.sql applies', S(APPLICANT), lambda r: r[0] == 0)
    check('offset starts at 0', R(('WF1', 'Get offset')), lambda r: r[1] == '0')
    check('offset is saved', R(('WF1', 'Save offset'), expr={"{{ Math.max(...$json.result.map(u => u.update_id)) + 1 }}": '987654321'}), lambda r: r[0] == 0)
    check('saved offset is read back', R(('WF1', 'Get offset')), lambda r: r[1] == '987654321')
    check('re-running schema.sql keeps the offset', (S(SCHEMA), R(('WF1', 'Get offset'))), lambda r: r[1][1] == '987654321')
    check('allowlist lists the applicant', R(('WF1', 'Applicants')), lambda r: r[1] == '1|123456789')

    print('== entry')
    data = b64(json.dumps({'company': "Société d'Exemple, S.à r.l.", 'email': 'info@exemple.lu'}, ensure_ascii=False))
    check('no dialog session yet', R(('WF1', 'Load session'), (123456789,)), lambda r: r[0] == 0 and r[1] == '')
    check('session insert', R(('WF1', 'Save session'), (123456789, 'address', data)), lambda r: r[1] == 'address')
    check('session upsert', R(('WF1', 'Save session'), (123456789, 'confirm', data)), lambda r: r[1] == 'confirm')
    check('session JSON round-trips', R(('WF1', 'Load session'), (123456789,)),
          lambda r: json.loads(r[1].split('|', 1)[1])['company'] == "Société d'Exemple, S.à r.l.")
    ins = lambda key, company, email, addr='', pc='', hr='', hre='': R(key, (1, b(company), email, email.split('@')[1], b(addr), b(pc), b(hr), b(hre)))
    check('dialog insert', ins(('WF1', 'Insert dialog target'), "Société d'Exemple, S.à r.l.", 'info@exemple.lu', "12 rue de l'Exemple", 'L-1234 Ville', 'Madame Exemple', 'rh@exemple.lu'), lambda r: r[1] == '1')
    check('bulk insert with empty optional fields', ins(('WF1', 'Insert target'), 'Garage Exemple', 'contact@garage-exemple.lu'), lambda r: r[1] == '2')
    check('same company name in another case is a duplicate', ins(('WF1', 'Insert target'), 'GARAGE EXEMPLE', 'x@autre.lu'), lambda r: r[0] == 0 and r[1] == '')
    check('same email domain is a duplicate', ins(('WF1', 'Insert dialog target'), 'Autre Société', 'jobs@exemple.lu'), lambda r: r[0] == 0 and r[1] == '')
    check('text decoded, empty optionals stored as NULL', S("SELECT company, address IS NULL, contact, status, draft_version FROM targets ORDER BY id;"),
          lambda r: r[1] == "Société d'Exemple, S.à r.l.|f|Madame Exemple|new|0\nGarage Exemple|t||new|0")

    print('== MX check')
    check('claim takes both new rows', R(('WF2', 'Lock new')), lambda r: len(rows(r)) == 2)
    check('second claim takes nothing', R(('WF2', 'Lock new')), lambda r: r[0] == 0 and r[1] == '')
    check('claim time recorded', S("SELECT count(*) FROM targets WHERE status='checking' AND claimed_at IS NOT NULL;"), lambda r: r[1] == '2')
    check('pass saved', R(('WF2', 'Save check'), ('email_found', 'true', 1)), lambda r: r[1] == '1|email_found')
    check('fail saved', R(('WF2', 'Save check'), ('no_email', 'false', 2)), lambda r: r[1] == '2|no_email')

    print('== drafting')
    check('claim returns draft version 1', R(('WF3', 'Lock drafting')), lambda r: r[0] == 0 and '|1|123456789|' in r[1])
    check('compilation error recorded', R(('WF3', 'Mark error'), (b64('Compilation LaTeX : erreur'), 1)), lambda r: r[1] == '1')
    S("UPDATE targets SET status='email_found' WHERE id=1;")              # operator retries after fixing the template
    check('re-drafting gives version 2', R(('WF3', 'Lock drafting')), lambda r: '|2|123456789|' in r[1])
    save = lambda: R(('WF3', 'Save draft'), (b64('Candidature spontanée – Exemple'), b64("Corps, avec virgule et 'apostrophe'."), '/data/jobs/1/letter.pdf', 1))
    check('draft saved before the preview is sent', save(), lambda r: r[1] == '1')
    check('saving again does nothing', save(), lambda r: r[0] == 0 and r[1] == '')
    check('draft stored, error cleared', S("SELECT status, subject, email_body, error IS NULL FROM targets WHERE id=1;"),
          lambda r: r[1] == "awaiting_approval|Candidature spontanée – Exemple|Corps, avec virgule et 'apostrophe'.|t")

    print('== preview delivery failure')
    check('failed preview goes back to drafting', R(('WF3', 'Preview failed'), (1, 2)), lambda r: r[1] == '1|email_found')
    check('re-drafting gives version 3', R(('WF3', 'Lock drafting')), lambda r: '|3|123456789|' in r[1])
    save()
    check('failure report for an older version is ignored', R(('WF3', 'Preview failed'), (1, 2)), lambda r: r[0] == 0 and r[1] == '')
    S("UPDATE targets SET draft_version=5 WHERE id=1;")
    check('fifth failed preview stops with an error', R(('WF3', 'Preview failed'), (1, 5)), lambda r: r[1] == '1|error')
    S("UPDATE targets SET status='awaiting_approval', draft_version=3, error=NULL WHERE id=1;")

    print('== approval buttons')
    check('button works as soon as the draft is saved', S("SELECT status FROM targets WHERE id=1;"), lambda r: r[1] == 'awaiting_approval')
    check('Refaire on the current preview (v3)', D('redo', 1, 1, 3), lambda r: r[1].endswith('|email_found'))
    R(('WF3', 'Lock drafting')); save()                                    # preview v4 is sent
    check('stale button: Envoyer on preview v3 is refused', D('approve', 1, 1, 3), lambda r: r[0] == 0 and r[1] == '')
    check('stale button: Refaire on preview v3 is refused', D('redo', 1, 1, 3), lambda r: r[0] == 0 and r[1] == '')
    check('stale button: Ignorer on preview v3 is refused', D('skip', 1, 1, 3), lambda r: r[0] == 0 and r[1] == '')
    check('button without a version is refused once a draft exists', D('approve', 1, 1, 0), lambda r: r[0] == 0 and r[1] == '')
    check('unknown action is refused', D('invalid', 1, 1, 4), lambda r: r[0] == 0 and r[1] == '')
    check('button from another applicant is refused', D('approve', 1, 99, 4), lambda r: r[0] == 0 and r[1] == '')
    check('row untouched by refused buttons', S("SELECT status, draft_version, approved_at IS NULL FROM targets WHERE id=1;"), lambda r: r[1] == 'awaiting_approval|4|t')
    check('Envoyer on the current preview (v4)', D('approve', 1, 1, 4), lambda r: r[1].endswith('|queued'))
    check('repeated approval is refused', D('approve', 1, 1, 4), lambda r: r[0] == 0 and r[1] == '')
    check('approval time recorded once', S("SELECT approved_at IS NOT NULL FROM targets WHERE id=1;"), lambda r: r[1] == 't')
    S("UPDATE targets SET status='awaiting_approval', draft_version=1 WHERE id=2;")
    check('Ignorer', D('skip', 2, 1, 1), lambda r: r[1].endswith('|skipped'))

    print('== sending')
    check('claim returns the queued application', R(('WF4', 'Pick one')), lambda r: r[1].startswith('1|') and '|/data/assets/cv.pdf|Camille Exemple||123456789' in r[1])
    check('second claim takes nothing', R(('WF4', 'Pick one')), lambda r: r[0] == 0 and r[1] == '')
    check('SMTP error recorded', R(('WF4', 'Mark send error'), (b64('535 auth'), 1)), lambda r: r[1] == '1')
    check('late success report cannot overwrite the error', R(('WF4', 'Mark sent'), (1,)), lambda r: r[0] == 0 and r[1] == '')
    S("UPDATE targets SET status='sending' WHERE id=1;")
    check('sent recorded', R(('WF4', 'Mark sent'), (1,)), lambda r: r[1] == '1')
    check('sent only once', R(('WF4', 'Mark sent'), (1,)), lambda r: r[0] == 0 and r[1] == '')
    check('sent_at set, error cleared', S("SELECT status, sent_at::date = current_date, error IS NULL FROM targets WHERE id=1;"), lambda r: r[1] == 'sent|t|t')
    S("UPDATE applicants SET daily_limit=1; INSERT INTO targets (applicant_id,company,email,email_domain,status,approved_at) VALUES (1,'Troisième','a@trois.lu','trois.lu','queued',now());")
    check('daily limit reached: nothing is claimed', R(('WF4', 'Pick one')), lambda r: r[0] == 0 and r[1] == '')
    S("UPDATE targets SET status='sending', sent_at=NULL WHERE id=1;")
    check('an application still being sent counts towards the limit', R(('WF4', 'Pick one')), lambda r: r[0] == 0 and r[1] == '')
    check('stats', R(('WF1', 'Stats'), (1,)), lambda r: r[1] == 'queued|1\nsending|1\nskipped|1')
    check('unknown status is rejected by the schema', S("UPDATE targets SET status='bogus' WHERE id=1;"), lambda r: r[0] != 0)
    subprocess.run(['dropdb', '--if-exists', db], capture_output=True)


def seeded(db, extra):
    fresh(db)
    rc, out, err = psql(db, SCHEMA + APPLICANT + extra)
    assert rc == 0, err


def parallel(db, sql, n):
    out = [None] * n
    def run(i):
        out[i] = psql(db, sql)
    ts = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return out


def concurrency():
    db = 'wf_test_concurrency'
    claimed = lambda res: sum(len([x for x in r[1].splitlines() if x]) for r in res)
    Q = "INSERT INTO targets (applicant_id,company,email,email_domain,status,approved_at) VALUES "

    print('== concurrent sending')
    pick = build(('WF4', 'Pick one'), (), 'inline')
    seeded(db, Q + "(1,'A','a@a.lu','a.lu','queued',now());")
    res = parallel(db, pick, 12)
    check('12 simultaneous runs, 1 queued application: claimed exactly once', res, lambda r: claimed(r) == 1 and all(x[0] == 0 for x in r))

    seeded(db, Q + "(1,'A','a@a.lu','a.lu','queued',now() - interval '2 min'), (1,'B','b@b.lu','b.lu','queued',now());")
    hold = threading.Thread(target=psql, args=(db, "BEGIN;\n" + pick + "SELECT pg_sleep(2);\nCOMMIT;\n"))
    hold.start(); time.sleep(0.7)
    check('while one run holds an applicant, an overlapping run claims nothing', psql(db, pick), lambda r: r[0] == 0 and r[1] == '')
    hold.join()
    check('the first run claimed the oldest approval', psql(db, "SELECT company FROM targets WHERE status='sending';"), lambda r: r[1] == 'A')
    check('the next run then takes the next application', psql(db, pick), lambda r: r[1].startswith('2|'))

    seeded(db, "UPDATE applicants SET daily_limit=3;" + Q + ",".join("(1,'C%d','c@c%d.lu','c%d.lu','queued',now())" % (i, i, i) for i in range(8)) + ";")
    for _ in range(6):
        parallel(db, pick, 6)
    check('repeated overlapping runs never exceed the daily limit', psql(db, "SELECT count(*) FROM targets WHERE status='sending';"), lambda r: r[1] == '3')

    print('== concurrent drafting and checking')
    seeded(db, Q.replace('approved_at', 'attempts') + "(1,'A','a@a.lu','a.lu','email_found',0);")
    res = parallel(db, build(('WF3', 'Lock drafting'), (), 'inline'), 10)
    check('10 simultaneous drafting runs: claimed exactly once', res, lambda r: claimed(r) == 1)
    check('draft version incremented exactly once', psql(db, "SELECT draft_version FROM targets;"), lambda r: r[1] == '1')
    seeded(db, Q.replace(',status,approved_at', '') .replace("VALUES ", "VALUES ") + ",".join("(1,'N%d','n@n%d.lu','n%d.lu')" % (i, i, i) for i in range(25)) + ";")
    res = parallel(db, build(('WF2', 'Lock new'), (), 'inline'), 8)
    check('8 simultaneous MX runs over 25 rows: every row claimed once', (res, psql(db, "SELECT count(*) FROM targets WHERE status='checking';")),
          lambda r: claimed(r[0]) == 25 and r[1][1] == '25')

    print('== stale claims')
    seeded(db, Q.replace('approved_at', 'claimed_at') +
           "(1,'old check','a@a.lu','a.lu','checking',now() - interval '20 min'),"
           "(1,'fresh check','b@b.lu','b.lu','checking',now() - interval '5 min'),"
           "(1,'old draft','c@c.lu','c.lu','drafting',now() - interval '20 min'),"
           "(1,'fresh draft','d@d.lu','d.lu','drafting',now() - interval '5 min'),"
           "(1,'old send','e@e.lu','e.lu','sending',now() - interval '3 hours');")
    check('MX check takes back only the check claimed 20 minutes ago', psql(db, build(('WF2', 'Lock new'), (), 'inline')), lambda r: r[1].startswith('1|old check|'))
    check('drafting takes back only the draft claimed 20 minutes ago', psql(db, build(('WF3', 'Lock drafting'), (), 'inline')), lambda r: r[1].startswith('3|old draft|'))
    check('an interrupted send is never taken back automatically', (psql(db, build(('WF4', 'Pick one'), (), 'inline')), psql(db, "SELECT status FROM targets WHERE id=5;")),
          lambda r: r[0][1] == '' and r[1][1] == 'sending')

    print('== upgrading an existing installation')
    fresh(db)
    old = SCHEMA.replace("    draft_version integer NOT NULL DEFAULT 0,    -- incremented each time WF3 drafts the letter\n", "").replace("    claimed_at   timestamptz,                    -- when a worker last claimed the row\n", "")
    old = old[:old.index('-- Upgrade path')] + 'COMMIT;\n'
    assert 'draft_version' not in old and 'claimed_at' not in old
    psql(db, old + APPLICANT + "INSERT INTO targets (applicant_id,company,email,email_domain,status) VALUES (1,'Existing','a@a.lu','a.lu','awaiting_approval');")
    check('older table has no version column', psql(db, "SELECT draft_version FROM targets;"), lambda r: r[0] != 0)
    check('schema.sql adds the missing columns', psql(db, SCHEMA), lambda r: r[0] == 0)
    check('existing rows are kept, with version 0', psql(db, "SELECT company, status, draft_version, claimed_at IS NULL FROM targets;"), lambda r: r[1] == 'Existing|awaiting_approval|0|t')
    check('a preview sent before the upgrade can still be approved', psql(db, build(('WF1', 'Apply decision'), ('approve', 1, 1, 0), 'inline')), lambda r: r[1].endswith('|queued'))
    subprocess.run(['dropdb', '--if-exists', db], capture_output=True)


def button_parser():
    print('== button parser (WF1 "Parse callback")')
    if not shutil.which('node'):
        print('  skip  node is not installed'); return
    cases = {'approve:42:3': ['approve', 42, 3], 'redo:42:1': ['redo', 42, 1], 'skip:7': ['skip', 7, 0],
             'drop:42:1': ['invalid', 0, 1], 'approve:x:1': ['invalid', 0, 1], 'approve:42:1;x': ['invalid', 0, 0], '': ['invalid', 0, 0]}
    js = ("const f=new Function('$json',%s);const o={};for(const d of %s){const j=f({data:d}).json;o[d]=[j.action,j.id,j.version];}console.log(JSON.stringify(o));"
          % (json.dumps(CODE[('WF1', 'Parse callback')]), json.dumps(list(cases))))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    got = json.loads(r.stdout) if r.returncode == 0 else {}
    for d, want in cases.items():
        check('%r -> %s' % (d, want), got.get(d), lambda g, want=want: g == want)


if __name__ == '__main__':
    for mode in ('inline', 'bind'):
        lifecycle(mode)
    concurrency()
    button_parser()
    missing = sorted(set(QUERIES) - used)
    print('\nworkflow queries: %d, executed: %d%s' % (len(QUERIES), len(used), '' if not missing else ', NOT executed: %s' % missing))
    print('%d checks, %d failed%s' % (counts[0], len(failures), '' if not failures else ':\n  ' + '\n  '.join(failures)))
    sys.exit(1 if failures or missing else 0)
