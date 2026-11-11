#!/usr/bin/env python3
"""
Benchmark: how many tokens and turns does an AI coding agent need for typical SDC tasks?
(projects/agents.plan.md, M0/M3; design in projects/agents.architecture.md, section 3)

    python scripts/agent_bench/bench.py selftest [--task ID]       # no agent, no API costs
    python scripts/agent_bench/bench.py seed --task ID              # build one project to look at
    python scripts/agent_bench/bench.py run --condition baseline --runs 3 [--task ID …] [--model M]
    python scripts/agent_bench/bench.py summarize RESULTS.jsonl …
    python scripts/agent_bench/bench.py analyze RESULTS.jsonl …     # runs made with --transcripts

Run it with the Python of the SimpleDomControl development environment (``poetry run``). ``run`` starts
``claude -p`` in temporary projects (by default with an allow-list of tools, see agent.py) and costs API usage
(``--budget`` caps each run).
"""
import argparse
import datetime
import json
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agent import run_claude, summarize_steps, total_input  # noqa: E402
from project import REPO, changed_files, create_project, python, remove_project, env_for  # noqa: E402
from tasks import BY_ID, TASKS  # noqa: E402

RESULTS = REPO / 'projects' / 'agents-bench' / 'results'


def run_check(task, project):
    result = subprocess.run([python(), str(HERE / 'run_check.py'), task.id, str(project)], cwd=project,
                            env=env_for(project), capture_output=True, text=True, timeout=600)
    line = next((l for l in result.stdout.splitlines() if l.startswith('RESULT ')), None)
    if line is None:
        return {'passed': False, 'details': {'runner': {'ok': False, 'detail': result.stderr[-2000:]}}}
    return json.loads(line[len('RESULT '):])


def _tasks(ids):
    if not ids:
        return TASKS
    unknown = [i for i in ids if i not in BY_ID]
    if unknown:
        sys.exit(f"Unknown task(s): {', '.join(unknown)}. Known: {', '.join(BY_ID)}")
    return [BY_ID[i] for i in ids]


def _sdc_version():
    """The version in pyproject.toml of this checkout (the install metadata of an editable install can be stale)."""
    import re
    match = re.search(r'(?m)^version = "([^"]+)"', (REPO / 'pyproject.toml').read_text())
    commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True)
    return f"{match.group(1) if match else 'unknown'}+{commit.stdout.strip() or 'nogit'}"


def cmd_selftest(args):
    """Every check must fail on the seeded project and pass after the reference solution."""
    ok = True
    for task in _tasks(args.task):
        project = create_project(task)
        try:
            before = run_check(task, project)
            task.solve(project)
            after = run_check(task, project)
        finally:
            if not args.keep:
                remove_project(project)
        good = not before['passed'] and after['passed']
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {task.id:<16} before={before['passed']} after={after['passed']}"
              + ('' if args.keep is False else f'  {project}'))
        if not good:
            print('     before:', json.dumps(before['details'])[:600])
            print('     after: ', json.dumps(after['details'])[:600])
    return 0 if ok else 1


def cmd_seed(args):
    task = BY_ID[args.task] if args.task else None
    project = create_project(task, condition=args.condition)
    print(project)
    if task:
        print('\nPrompt:\n' + task.full_prompt)
    return 0


def cmd_run(args):
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RESULTS / f'{datetime.date.today()}-{args.condition}.jsonl'
    if out.exists():
        conditions = {json.loads(line).get('condition') for line in out.read_text().splitlines() if line.strip()}
        if conditions - {args.condition}:
            sys.exit(f'{out} already holds runs of condition(s) {", ".join(sorted(conditions))}; use another --out '
                     f'for condition {args.condition}')
    tasks = _tasks(args.task)
    print(f'{len(tasks)} task(s) x {args.runs} run(s), condition {args.condition}, model {args.model or "default"}'
          f' -> {out}')
    for run in range(1, args.runs + 1):
        for task in tasks:
            project = create_project(task, condition=args.condition)
            try:
                agent = run_claude(project, task.full_prompt, args.model, args.budget, timeout_s=args.timeout,
                                   permissions=args.permissions, transcript=args.transcripts)
                check = run_check(task, project)
                files = changed_files(project)
            finally:
                keep = args.keep or (args.keep_failed and not locals().get('check', {}).get('passed', False))
                if not keep:
                    remove_project(project)
            record = {
                'task': task.id, 'condition': args.condition, 'run': run, 'model': args.model or 'default',
                'permissions': args.permissions,
                'sdc_version': _sdc_version(), 'date': datetime.datetime.now().isoformat(timespec='seconds'),
                'passed': check['passed'], 'checks': check['details'], 'changed_files': files,
                'agent': {k: v for k, v in agent.items() if k != 'steps'}, 'total_input_tokens': total_input(agent),
            }
            if 'steps' in agent:
                record['activity'] = summarize_steps(agent['steps'])
                transcript_dir = out.parent.parent / 'transcripts' / out.stem
                transcript_dir.mkdir(parents=True, exist_ok=True)
                path = transcript_dir / f'{task.id}-run{run}.jsonl'
                path.write_text(''.join(json.dumps(step, ensure_ascii=False) + '\n' for step in agent['steps']))
                record['transcript'] = str(path.relative_to(REPO))
            with out.open('a') as f:
                f.write(json.dumps(record, default=str) + '\n')
            print(f"run {run} {task.id:<16} passed={check['passed']!s:<5} turns={agent.get('turns')} "
                  f"input={record['total_input_tokens']} output={agent.get('output_tokens')} "
                  f"cost={agent.get('cost_usd')} {agent.get('error', '')}"
                  + (f'  kept: {project}' if keep else ''))
    return 0


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def cmd_summarize(args):
    records = [json.loads(line) for path in args.files for line in Path(path).read_text().splitlines()
               if line.strip()]
    groups = {}
    for r in records:
        groups.setdefault((r['task'], r['condition']), []).append(r)
    header = '| task | condition | runs | passed | median input tokens | median output tokens | median turns | ' \
             'median cost USD |'
    lines = [header, '|' + '---|' * 8]
    for (task, condition), rs in sorted(groups.items()):
        lines.append('| {} | {} | {} | {}/{} | {} | {} | {} | {} |'.format(
            task, condition, len(rs), sum(r['passed'] for r in rs), len(rs),
            _median([r['total_input_tokens'] for r in rs]),
            _median([r['agent'].get('output_tokens') for r in rs]),
            _median([r['agent'].get('turns') for r in rs]),
            _median([r['agent'].get('cost_usd') for r in rs])))
    by_condition = {}
    for r in records:
        by_condition.setdefault(r['condition'], []).append(r)
    lines += ['', '| condition | runs | success | total input tokens | total output tokens | total cost USD |',
              '|---|---|---|---|---|---|']
    for condition, rs in sorted(by_condition.items()):
        lines.append('| {} | {} | {:.0%} | {} | {} | {:.2f} |'.format(
            condition, len(rs), sum(r['passed'] for r in rs) / len(rs), sum(r['total_input_tokens'] for r in rs),
            sum(r['agent'].get('output_tokens') or 0 for r in rs), sum(r['agent'].get('cost_usd') or 0 for r in rs)))
    print('\n'.join(lines))
    return 0


def cmd_analyze(args):
    """Where the turns and tokens go: tools, files, skills and commands per task (runs with --transcripts)."""
    from collections import Counter
    records = [json.loads(line) for path in args.files for line in Path(path).read_text().splitlines()
               if line.strip()]
    records = [r for r in records if 'activity' in r]
    if not records:
        sys.exit('No runs with transcripts (run with --transcripts)')
    for task in sorted({r['task'] for r in records}):
        runs = [r for r in records if r['task'] == task]
        print(f"\n## {task} ({len(runs)} runs, median turns {_median([r['agent'].get('turns') for r in runs])})")
        tools = Counter()
        for r in runs:
            tools.update(r['activity']['tools'])
        print('tools:', ', '.join(f'{t} {n / len(runs):.1f}' for t, n in tools.most_common()))
        skills = Counter(s for r in runs for s in set(r['activity']['skills_read']))
        print('skills read (runs):', ', '.join(f'{s} {n}' for s, n in skills.most_common()) or '-')
        files = Counter(f.rsplit('library_site/', 1)[-1] for r in runs for f in r['activity']['files_read'])
        print('files read:', ', '.join(f'{f} ×{n}' for f, n in files.most_common(args.top)))
        commands = Counter(' '.join(c.split()[:4]) for r in runs for c in r['activity']['bash'])
        print('commands:', ', '.join(f'{c} ×{n}' for c, n in commands.most_common(args.top)))
        big = []
        for r in runs:
            steps = [json.loads(line) for line in (REPO / r['transcript']).read_text().splitlines()]
            big += [(s.get('result_chars', 0), s.get('tool'), s.get('input', '')[:80]) for s in steps if s.get('tool')]
        print('largest tool results:', '; '.join(f'{c} chars {t} {i}' for c, t, i in sorted(big, reverse=True)[:3]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('selftest', help='check every task with its reference solution (no agent)')
    p.add_argument('--task', action='append')
    p.add_argument('--keep', action='store_true', help='keep the projects')
    p = sub.add_parser('seed', help='build one seeded project and print its path')
    p.add_argument('--task')
    p.add_argument('--condition', default='baseline', choices=['baseline', 'kit'])
    p = sub.add_parser('run', help='run the agent on the tasks (costs API usage)')
    p.add_argument('--condition', default='baseline', choices=['baseline', 'kit'])
    p.add_argument('--task', action='append')
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--model', help='claude --model (default: the CLI default)')
    p.add_argument('--budget', type=float, default=3.0, help='max USD per run (claude --max-budget-usd)')
    p.add_argument('--timeout', type=int, default=1800, help='seconds per run')
    p.add_argument('--out', help='results file (default projects/agents-bench/results/<date>-<condition>.jsonl)')
    p.add_argument('--keep', action='store_true', help='keep the projects')
    p.add_argument('--keep-failed', action='store_true', help='keep the projects of failed runs for inspection')
    p.add_argument('--transcripts', action='store_true',
                   help='record tool calls and context size per turn (projects/agents-bench/transcripts/; no file '
                        'contents)')
    p.add_argument('--permissions', default='restricted', choices=['restricted', 'bypass'],
                   help='restricted (default): file tools + python/ls/cat/git status|diff; bypass: no permission '
                        'checks, only in a container or VM')
    p = sub.add_parser('summarize', help='median tokens, turns, cost and success per task and condition')
    p.add_argument('files', nargs='+')
    p = sub.add_parser('analyze', help='tools, files, skills and commands per task (runs with --transcripts)')
    p.add_argument('files', nargs='+')
    p.add_argument('--top', type=int, default=8)
    args = parser.parse_args()
    return {'selftest': cmd_selftest, 'seed': cmd_seed, 'run': cmd_run, 'summarize': cmd_summarize,
            'analyze': cmd_analyze}[
        args.command](args)


if __name__ == '__main__':
    sys.exit(main())
