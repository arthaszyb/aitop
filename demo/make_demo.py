#!/usr/bin/env python3
"""Write a synthetic Claude Code + Codex environment for aitop demos, screenshots and tests.

Usage: python3 demo/make_demo.py DIR [--live-pid PID]

Then point aitop at it:
  CLAUDE_CONFIG_DIR=DIR/claude CODEX_HOME=DIR/codex AITOP_CLAUDE_DESKTOP_DIR=DIR/desktop \
  XDG_STATE_HOME=DIR/state XDG_CACHE_HOME=DIR/cache XDG_CONFIG_HOME=DIR/config aitop serve

Everything is fictional. Timestamps are relative to now, so "this week" always has activity.
Live sessions are registered under --live-pid (default: the calling shell), and stay live while it runs.
"""
import argparse
import json
import os
import random
import sqlite3
import time
import uuid

NOW = time.time()
HOUR, DAY = 3600, 86400
dumps = lambda rec: json.dumps(rec, separators=(',', ':'))  # the agents write compact JSON


def iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(ts)) + f'.{int(ts * 1000) % 1000:03d}Z'


def sid_for(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'aitop-demo/' + name))


def write_jsonl(path, records, mtime):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.writelines(dumps(r) + '\n' for r in records)
    os.utime(path, (mtime, mtime))


# ---------------------------------------------------------------- Claude Code

def claude_transcript(sid, entrypoint, cwd, title, turns, start, model, pending_tool=None):
    """turns: [(prompt, reply, [(tool, input), ...])], spaced 25 minutes apart from start."""
    recs, t = [], start
    base = {'sessionId': sid, 'cwd': cwd, 'entrypoint': entrypoint, 'isSidechain': False}
    for n, (prompt, reply, tools) in enumerate(turns):
        recs.append({**base, 'type': 'user', 'timestamp': iso(t), 'uuid': str(uuid.uuid4()),
                     'message': {'role': 'user', 'content': prompt}})
        for k, (tool, inp) in enumerate(tools):
            t += 40
            mid = f'msg_{sid[:8]}_{n}_{k}'
            recs.append({**base, 'type': 'assistant', 'timestamp': iso(t), 'uuid': str(uuid.uuid4()), 'message': {
                'id': mid, 'model': model, 'role': 'assistant', 'stop_reason': 'tool_use',
                'content': [{'type': 'tool_use', 'id': f'tu_{mid}', 'name': tool, 'input': inp}],
                'usage': {'input_tokens': 6, 'cache_creation_input_tokens': 2200 + 90 * k,
                          'cache_read_input_tokens': 18000 + 4000 * n, 'output_tokens': 260 + 30 * k}}})
            recs.append({**base, 'type': 'user', 'timestamp': iso(t + 5), 'message': {
                'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': f'tu_{mid}', 'content': 'ok'}]}})
        t += 60
        if reply:
            mid = f'msg_{sid[:8]}_{n}_r'
            recs.append({**base, 'type': 'assistant', 'timestamp': iso(t), 'uuid': str(uuid.uuid4()), 'message': {
                'id': mid, 'model': model, 'role': 'assistant', 'stop_reason': 'end_turn',
                'content': [{'type': 'text', 'text': reply}],
                'usage': {'input_tokens': 4, 'cache_creation_input_tokens': 1500,
                          'cache_read_input_tokens': 24000 + 5000 * n, 'output_tokens': 520}}})
        t += 25 * 60
    if pending_tool:
        recs.append({**base, 'type': 'assistant', 'timestamp': iso(t), 'uuid': str(uuid.uuid4()), 'message': {
            'id': f'msg_{sid[:8]}_pending', 'model': model, 'role': 'assistant', 'stop_reason': 'tool_use',
            'content': [{'type': 'tool_use', 'id': 'tu_pending', 'name': pending_tool[0], 'input': pending_tool[1]}],
            'usage': {'input_tokens': 5, 'cache_creation_input_tokens': 800, 'cache_read_input_tokens': 30000,
                      'output_tokens': 140}}})
    recs.append({'type': 'ai-title', 'aiTitle': title, 'sessionId': sid})
    return recs, t


FOREGROUND_CLAUDE = [
    # (name, entrypoint, project, title, hours ago, live status, desktop summary, turns)
    ('flaky-checkout', 'claude-vscode', 'checkout-service', 'Fix flaky checkout retry test', 2.5, 'waiting', None, [
        ('The payment retry test fails about one run in ten on CI. Find out why and fix it.',
         'The test waits on a fixed 200 ms sleep while the retry backoff jitters up to 250 ms. I replaced the sleep '
         'with a fake clock so the backoff is deterministic.',
         [('Read', {'file_path': 'src/payments/retry.ts'}), ('Edit', {'file_path': 'test/payments/retry.test.ts'})]),
        ('Run the whole suite before we push.', '', []),
    ]),
    ('rate-limiter', 'claude-vscode', 'billing-api', 'Billing API rate limiter', 0.6, 'busy', None, [
        ('Add a per-tenant token bucket to the invoice endpoints, 50 requests per second with a burst of 100.',
         'Added a Redis-backed token bucket keyed by tenant id, with 429 responses that carry Retry-After.',
         [('Edit', {'file_path': 'billing/ratelimit.py'}), ('Edit', {'file_path': 'billing/routes/invoices.py'}),
          ('Bash', {'command': 'pytest tests/test_ratelimit.py', 'description': 'Run rate limiter tests'})]),
        ('Now load test it against staging.', '', [('Bash', {'command': 'k6 run load/invoices.js',
                                                             'description': 'Load test invoice endpoints'})]),
    ]),
    ('terraform-plan', 'claude-vscode', 'infra-terraform', 'Terraform state cleanup plan', 0.9, 'idle', None, [
        ('List resources in the prod state that no longer exist in code.',
         'Found 14 orphaned resources: 9 old security groups, 3 unused IAM roles and 2 detached volumes. '
         'None are referenced by running services.', [('Bash', {'command': 'terraform state list',
                                                                'description': 'List state resources'})]),
        ('Draft the removal plan, but do not apply anything.',
         'The plan removes the 14 resources from state in three batches, security groups first. '
         'Review it in docs/state-cleanup.md before anything is applied.',
         [('Write', {'file_path': 'docs/state-cleanup.md'})]),
    ]),
    ('release-notes', 'cli', 'checkout-service', 'Release notes for v2.3', 50, None, None, [
        ('Write release notes for v2.3 from the merged PRs since v2.2.',
         'Release notes are in CHANGELOG.md: 6 features, 11 fixes, and the retry change called out as behavior-visible. '
         'I opened PR #418 with them.', [('Edit', {'file_path': 'CHANGELOG.md'})]),
    ]),
    ('capacity-forecast', 'claude-desktop', 'capacity-planning', 'Q4 capacity forecast', 26,
     None, ('blocked', 'Choose: keep three regions or consolidate to two before the forecast is final'), [
        ('Forecast Q4 compute for checkout and billing using the last 90 days of peak traffic.',
         'At the current growth rate checkout needs 38% more cores by the December peak, billing 12%. '
         'Consolidating to two regions saves 18% but removes headroom for a regional failover.', []),
    ]),
    ('onboarding-doc', 'claude-desktop', 'docs-site', 'Onboarding guide refresh', 70,
     None, ('completed', 'Onboarding guide updated with the new local setup and on-call basics.'), [
        ('Update the onboarding guide for the new dev container setup.',
         'Rewrote the setup section around the dev container, removed the Homebrew steps, and added an on-call primer.',
         [('Edit', {'file_path': 'content/onboarding.md'})]),
    ]),
]

BACKGROUND_TOPICS = [
    ('checkout-service', ['Profile the cart pricing endpoint', 'Add idempotency keys to order creation',
                          'Review the payment provider timeout settings']),
    ('billing-api', ['Backfill missing invoice line items', 'Explain the proration rounding bug',
                     'Add audit logging to refunds']),
    ('infra-terraform', ['Tighten S3 bucket policies', 'Right-size the staging node pool',
                         'Rotate the CI deploy credentials']),
    ('data-pipeline', ['Speed up the nightly revenue rollup', 'Alert when the events lag passes 10 minutes',
                       'Document the warehouse schema']),
    ('docs-site', ['Fix broken links in the API reference', 'Add examples to the webhooks guide']),
]


def make_claude(root, live_pid, rnd):
    projects = os.path.join(root, 'claude', 'projects')
    os.makedirs(os.path.join(root, 'claude', 'sessions'), exist_ok=True)
    for n, (name, entrypoint, proj, title, hours, live, desktop, turns) in enumerate(FOREGROUND_CLAUDE):
        sid, cwd = sid_for(name), f'/home/demo/acme/{proj}'
        pending = ('Bash', {'command': 'npm test', 'description': 'Run the full test suite'}) if live == 'waiting' else None
        recs, last = claude_transcript(sid, entrypoint, cwd, title, turns, NOW - hours * HOUR, 'claude-sonnet-4-5', pending)
        if name == 'release-notes':
            recs.append({'type': 'pr-link', 'sessionId': sid, 'prNumber': 418, 'prRepository': 'acme/checkout-service',
                         'prUrl': 'https://github.com/acme/checkout-service/pull/418', 'timestamp': iso(last)})
        write_jsonl(os.path.join(projects, '-home-demo-acme-' + proj, sid + '.jsonl'), recs, min(last, NOW))
        if live:
            entry = {'pid': live_pid, 'sessionId': sid, 'cwd': cwd, 'startedAt': int((NOW - hours * HOUR) * 1000),
                     'kind': 'interactive', 'entrypoint': entrypoint, 'name': title, 'nameSource': 'auto',
                     'status': live, 'updatedAt': int(NOW * 1000), 'statusUpdatedAt': int((NOW - 300) * 1000)}
            if live == 'waiting':
                entry['waitingFor'] = 'Bash: npm test (run the full test suite)'
            with open(os.path.join(root, 'claude', 'sessions', f'{live_pid}-{n}.json'), 'w') as f:
                json.dump(entry, f)
        if desktop:
            local = 'local_' + sid_for(name + '/desktop')
            folder = os.path.join(root, 'desktop', 'account', 'org')
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, local + '.json'), 'w') as f:
                json.dump({'sessionId': local, 'cliSessionId': sid, 'cwd': cwd, 'title': title, 'isArchived': False,
                           'createdAt': int((NOW - hours * HOUR) * 1000), 'lastActivityAt': int(min(last, NOW) * 1000),
                           'lastFocusedAt': int((NOW - hours * HOUR) * 1000),
                           'postTurnSummary': {'status_category': desktop[0], 'status_detail': desktop[1],
                                               'needs_action': desktop[1] if desktop[0] == 'blocked' else ''}}, f)

    # Four weeks of finished sessions so the charts and briefings have history.
    for n in range(26):
        proj, titles = rnd.choice(BACKGROUND_TOPICS)
        title = rnd.choice(titles)
        start = NOW - rnd.uniform(1.2, 27) * DAY
        start -= (time.localtime(start).tm_hour - rnd.choice([9, 10, 11, 14, 15, 16, 17])) * HOUR
        entrypoint = rnd.choice(['claude-vscode', 'claude-vscode', 'claude-vscode', 'cli', 'claude-desktop'])
        sid = sid_for(f'bg-{n}')
        turns = [(f'{title}.', f'Done: {title.lower()}. Changes are on a branch and the tests pass.',
                  [('Edit', {'file_path': f'src/{proj}/module_{n % 5}.py'})])
                 for _ in range(rnd.randint(1, 4))]
        recs, last = claude_transcript(sid, entrypoint, f'/home/demo/acme/{proj}', title, turns, start,
                                       rnd.choice(['claude-sonnet-4-5', 'claude-opus-4-1']))
        write_jsonl(os.path.join(projects, '-home-demo-acme-' + proj, sid + '.jsonl'), recs, min(last, NOW))


# ---------------------------------------------------------------- Codex

def codex_rollout(tid, cwd, originator, source, provider, model, turns, start, running=False):
    t = start
    recs = [{'timestamp': iso(t), 'type': 'session_meta', 'payload': {
        'id': tid, 'timestamp': iso(t), 'cwd': cwd, 'originator': originator, 'source': source,
        'thread_source': 'user', 'model_provider': provider}}]
    total = [0, 0, 0]
    for n, (prompt, reply, cmd) in enumerate(turns):
        last_turn = n == len(turns) - 1
        recs.append({'timestamp': iso(t), 'type': 'turn_context', 'payload': {'model': model}})
        recs.append({'timestamp': iso(t), 'type': 'event_msg', 'payload': {'type': 'task_started'}})
        recs.append({'timestamp': iso(t), 'type': 'response_item', 'payload': {
            'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}})
        t += 30
        recs.append({'timestamp': iso(t), 'type': 'response_item', 'payload': {
            'type': 'function_call', 'name': 'exec_command', 'arguments': json.dumps({'cmd': cmd})}})
        last = [42000 + 6000 * n, 36000 + 5000 * n, 900]
        total = [a + b for a, b in zip(total, last)]
        recs.append({'timestamp': iso(t + 20), 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
            'total_token_usage': {'input_tokens': total[0], 'cached_input_tokens': total[1], 'output_tokens': total[2]},
            'last_token_usage': {'input_tokens': last[0], 'cached_input_tokens': last[1], 'output_tokens': last[2]}}}})
        if running and last_turn:
            break
        t += 90
        recs.append({'timestamp': iso(t), 'type': 'response_item', 'payload': {
            'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': reply}]}})
        recs.append({'timestamp': iso(t), 'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': reply}})
        t += 40 * 60
    return recs, t


FOREGROUND_CODEX = [
    ('cron-migration', 'Migrate cron jobs to the workflow engine', 'data-pipeline', 'codex_work_desktop', 'vscode',
     'openai', 5, False, [
         ('Move the three nightly cron jobs into the workflow engine with retries.',
          'All three jobs now run as workflows with 3 retries and alerting on final failure. The crontab entries are '
          'commented out, not deleted, until one clean night has passed.', 'grep -r cron deploy/'),
     ]),
    ('latency', 'Investigate p99 latency regression', 'checkout-service', 'codex_work_desktop', 'vscode',
     'team', 0.2, True, [
         ('p99 on /checkout went from 380 ms to 610 ms after Tuesday\'s deploy. Find the cause.',
          '', 'git log --since=tuesday --oneline'),
     ]),
    ('openapi', 'Add OpenAPI examples', 'billing-api', '', 'cli', 'openai', 140, False, [
        ('Add request and response examples to every invoice endpoint in the OpenAPI spec.',
         'Added examples to 9 endpoints and a CI check that fails when an endpoint has none.', 'ls openapi/'),
    ]),
]


def make_codex(root, rnd):
    codex = os.path.join(root, 'codex')
    os.makedirs(codex, exist_ok=True)
    with open(os.path.join(codex, 'config.toml'), 'w') as f:
        f.write('model_provider = "openai"\n\n[model_providers.team]\nname = "Team gateway"\n')
    db = sqlite3.connect(os.path.join(codex, 'state_5.sqlite'))
    db.execute("""create table threads (id text primary key, rollout_path text, created_at integer, updated_at integer,
                  created_at_ms integer, updated_at_ms integer, source text, originator text, model_provider text,
                  cwd text, title text, name text, first_user_message text, archived integer, thread_source text)""")
    threads = [(f'fg-{name}', title, proj, originator, source, provider, NOW - hours * HOUR, running, turns)
               for name, title, proj, originator, source, provider, hours, running, turns in FOREGROUND_CODEX]
    for n in range(12):
        proj, titles = rnd.choice(BACKGROUND_TOPICS)
        title = rnd.choice(titles)
        start = NOW - rnd.uniform(1.5, 27) * DAY
        threads.append((f'bg-{n}', title, proj, rnd.choice(['codex_work_desktop', 'codex_work_desktop', '']),
                        rnd.choice(['vscode', 'cli']), rnd.choice(['openai', 'team']), start, False,
                        [(f'{title}.', f'Finished: {title.lower()}.', 'git status')] * rnd.randint(1, 3)))
    for key, title, proj, originator, source, provider, start, running, turns in threads:
        tid = sid_for('codex/' + key)
        cwd = f'/home/demo/acme/{proj}'
        recs, last = codex_rollout(tid, cwd, originator, source, provider, 'gpt-5-codex', turns, start, running)
        day = time.strftime('%Y/%m/%d', time.localtime(start))
        path = os.path.join(codex, 'sessions', day, f'rollout-{time.strftime("%Y-%m-%dT%H-%M-%S", time.localtime(start))}-{tid}.jsonl')
        write_jsonl(path, recs, NOW if running else min(last, NOW))
        db.execute('insert into threads values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (tid, path, int(start), int(min(last, NOW)), int(start * 1000), int(min(last, NOW) * 1000), source,
                    originator, provider, cwd, title, title, turns[0][0], 0, 'user'))
    db.commit()
    db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dir')
    ap.add_argument('--live-pid', type=int, default=os.getppid(), help='process the live sessions belong to')
    args = ap.parse_args()
    if os.path.exists(args.dir) and os.listdir(args.dir):
        raise SystemExit(f'{args.dir} is not empty; give a new or empty directory')
    rnd = random.Random(42)
    make_claude(args.dir, args.live_pid, rnd)
    make_codex(args.dir, rnd)
    d = os.path.abspath(args.dir)
    print(f'export CLAUDE_CONFIG_DIR={d}/claude CODEX_HOME={d}/codex AITOP_CLAUDE_DESKTOP_DIR={d}/desktop '
          f'XDG_STATE_HOME={d}/state XDG_CACHE_HOME={d}/cache XDG_CONFIG_HOME={d}/config')


if __name__ == '__main__':
    main()
