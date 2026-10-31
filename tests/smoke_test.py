#!/usr/bin/env python3
"""End-to-end smoke test on synthetic data. Run with the Python you want to check:

    python3 tests/smoke_test.py
    /usr/bin/python3 tests/smoke_test.py     # e.g. macOS's built-in 3.9

It never touches your real ~/.claude or ~/.codex: every path aitop reads or writes points into a temp directory.
Briefing generation is not exercised, since it calls an LLM.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from importlib.machinery import SourceFileLoader

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AITOP = os.path.join(REPO, 'aitop')
failures = []


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        failures.append(what)


def run(*args):
    p = subprocess.run([sys.executable, AITOP, *args], capture_output=True, text=True, env={**os.environ, 'COLUMNS': '200'})
    return p.returncode, p.stdout, p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix='aitop-smoke-')
    try:
        subprocess.run([sys.executable, os.path.join(REPO, 'demo', 'make_demo.py'), tmp, '--live-pid', str(os.getpid())],
                       check=True, capture_output=True)
        os.environ.update({'CLAUDE_CONFIG_DIR': f'{tmp}/claude', 'CODEX_HOME': f'{tmp}/codex',
                           'AITOP_CLAUDE_DESKTOP_DIR': f'{tmp}/desktop', 'XDG_STATE_HOME': f'{tmp}/state',
                           'XDG_CACHE_HOME': f'{tmp}/cache', 'XDG_CONFIG_HOME': f'{tmp}/config'})
        # One damaged transcript must show up as unreadable without breaking anything else.
        broken = os.path.join(tmp, 'claude', 'projects', '-home-demo-broken', 'bad-session.jsonl')
        os.makedirs(os.path.dirname(broken))
        with open(broken, 'w') as f:
            f.write('{"type":"user","timestamp":"2026-01-01T00:00:00.000Z"}\n{not json\n' + '{"type":"x"}\n' * 3)

        code, out, err = run('--version')
        check(code == 0 and out.startswith('aitop '), f'--version prints a version ({out.strip()})')
        code, out, err = run('list')
        check(code == 0 and 'waiting' in out and 'running' in out, 'list shows live waiting and running sessions')
        code, out, err = run('list', '--all')
        check(code == 0 and 'Could not read this session' in out, 'list --all shows the damaged session with its error')
        check('could not read claude session bad-session' in err, 'the damaged session is reported on stderr')
        code, out, err = run('catchup')
        check(code == 0 and 'needs you: Bash: npm test' in out, 'catchup puts the permission prompt first')
        check('Choose: keep three regions' in out, 'catchup shows the Claude Desktop decision')
        code, out, err = run('week')
        check(code == 0 and 'New this week' in out, 'week prints both sections')
        code, out, err = run('ack', '--all')
        check(code == 0 and out.startswith('acked'), f'ack --all works ({out.strip()})')
        code, out, err = run('catchup')
        check(code == 0 and '0 new replies' in out, 'catchup is empty after ack --all, except waiting sessions')

        a = SourceFileLoader('aitop', AITOP).load_module()
        s = a.stats('30d')
        check(s['kpi']['sessions'][0] >= 30 and s['kpi']['tokens'][0] > 0, f'stats: {s["kpi"]["sessions"][0]} sessions, '
              f'{s["kpi"]["tokens"][0]:,} tokens in 30 days')
        check({'vscode', 'codex-app'} <= set(s['runtimes']), f'stats covers several runtimes ({", ".join(s["runtimes"])})')
        check(a.codex_provider_label('team') == 'Team gateway', 'provider names come from config.toml')

        server = a.ThreadingHTTPServer(('127.0.0.1', 0), a.PortalHandler)
        port = server.server_address[1]
        server.allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def get(path, host=None):
            req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers={'Host': host} if host else {})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        status, body = get('/')
        check(status == 200 and b'<title>aitop</title>' in body, 'portal serves the page')
        for path in ('/api/catchup?since=7d', '/api/week', '/api/list?all=1', '/api/stats?range=all',
                     '/api/brief?kind=weekly'):
            status, body = get(path)
            check(status == 200 and json.loads(body), f'GET {path}')
        status, body = get('/api/catchup?since=7d')
        check(status == 200 and len(json.loads(body)['running']) > 0, 'catchup lists the running sessions')
        status, body = get('/api/list?all=1')
        rows = json.loads(body)['rows']
        check(all(r['topic'] == '' for r in rows), 'sessions have no topic before any briefing exists')
        # A briefing names sessions by their 8-character id prefix; its category becomes their topic.
        sid = rows[0]['id']
        os.makedirs(a.BRIEF_DIR, exist_ok=True)
        with open(os.path.join(a.BRIEF_DIR, 'weekly-2026-01-05.json'), 'w') as f:
            json.dump({'generated_at': 1, 'report': {'priorities': [{'name': 'Old topic', 'projects': [
                {'name': 'p', 'tasks': [{'title': 't', 'sessions': [sid[:8]]}]}]}]}}, f)
        with open(os.path.join(a.BRIEF_DIR, 'weekly-2026-01-12.json'), 'w') as f:
            json.dump({'generated_at': 2, 'report': {'priorities': [{'name': 'Business reliability', 'projects': [
                {'name': 'p', 'tasks': [{'title': 't', 'sessions': [sid[:8]]}]}]}]}}, f)
        status, body = get('/api/list?all=1')
        topics = {r['id']: r['topic'] for r in json.loads(body)['rows']}
        check(topics[sid] == 'Business reliability', 'the newest briefing sets the topic of a session')
        check(sum(bool(t) for t in topics.values()) == 1, 'sessions outside every briefing have an empty topic')
        status, body = get('/api/catchup?since=7d')
        c = json.loads(body)
        check(all('topic' in r for r in c['waiting'] + c['running'] + c['fresh']), 'catchup rows carry a topic')
        status, _ = get('/api/week', host='evil.example')
        check(status == 403, 'requests for another Host are refused')
        server.shutdown()
    finally:
        shutil.rmtree(tmp)
    print(f'\n{len(failures)} failed' if failures else '\nall checks passed')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
