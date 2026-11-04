"""
Oracle model for validating an evaluation task suite: an OpenAI-compatible chat server that answers every task with
its ``reference`` solution instead of a language model.

Running the suite against it checks that every reference solution passes the task's checks in the real
application, i.e. that the expected paths, arguments, form values and answers are right:

    python eval/oracle_server.py eval/sdctest/tasks --port 18777 &
    OPENAI_API_KEY=oracle python manage.py sdc_eval_ai eval/sdctest/tasks --condition none \\
        --model oracle=openai-compatible:oracle@http://127.0.0.1:18777/v1 --runs 1 \\
        --users-file eval/sdctest/users.yaml --fixture eval/sdctest/fixture.json -o /tmp/oracle.jsonl

The task is found by the first user message of the conversation (one of its prompts); the step is the number of
assistant messages so far. A step is ``{tool: input}`` or ``{answer: text}``. ``fill_form`` may name the form by
``model`` (SdcModelName, optionally ``pk``), ``controller`` (fields outside a ``<form>``) or ``field`` (a field name it contains) instead of ``form`` (index);
the index is taken from the last ``read_page`` result. Tasks with a ``judge`` rubric are not graded by the oracle
(use --judge-model or check the answers by hand).
"""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml


def load_tasks(paths):
    tasks = []
    for path in paths:
        files = [os.path.join(r, n) for r, _, ns in os.walk(path) for n in ns if n.endswith(('.yaml', '.yml'))] \
            if os.path.isdir(path) else [path]
        for file in sorted(files):
            with open(file, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            tasks += data if isinstance(data, list) else [data]
    by_prompt = {}
    for task in tasks:
        prompts = task['prompt'] if isinstance(task['prompt'], list) else [task['prompt']]
        for prompt in prompts:
            by_prompt[prompt.strip()] = task
    return by_prompt


def last_page(messages):
    """The last read_page result (a dict with 'forms') in the conversation."""
    for m in reversed(messages):
        if m.get('role') == 'tool':
            try:
                content = json.loads(m.get('content') or '')
            except ValueError:
                continue
            if isinstance(content, dict) and 'forms' in content:
                return content
    return None


def resolve_fill_form(args, messages):
    if 'form' in args:
        return {'form': args['form'], 'values': args['values']}
    page = last_page(messages) or {'forms': []}
    for form in page['forms']:
        if 'model' in args and form.get('sdc_model_name') != args['model']:
            continue
        if 'pk' in args and form.get('sdc_model_pk') != args['pk']:
            continue
        if 'controller' in args and form.get('controller') != args['controller']:
            continue
        if 'field' in args and not any(f['name'] == args['field'] for f in form.get('fields', [])):
            continue
        return {'form': form['index'], 'values': args['values']}
    return {'form': 999, 'values': args['values']}  # no matching form: the browser reports the error


def chunk(delta=None, finish=None, usage=None):
    c = {'id': 'oracle', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'oracle',
         'choices': [] if usage else [{'index': 0, 'delta': delta or {}, 'finish_reason': finish}]}
    if usage:
        c['usage'] = usage
    return c


def make_handler(tasks):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = body['messages']
            first_user = next((m['content'] for m in messages if m['role'] == 'user'), '')
            task = tasks.get((first_user or '').strip())
            step_index = sum(1 for m in messages if m['role'] == 'assistant')
            steps = (task or {}).get('reference') or []
            step = steps[step_index] if step_index < len(steps) else {'answer': 'Done.' if task else 'Unknown task.'}
            name, args = next(iter(step.items()))
            if body.get('tool_choice') == 'none' and name != 'answer':
                name, args = 'answer', 'Stopped: tool round limit.'
            if name == 'answer':
                chunks = [chunk({'role': 'assistant', 'content': str(args)}), chunk(finish='stop')]
            else:
                if name == 'fill_form':
                    args = resolve_fill_form(args, messages)
                call = {'index': 0, 'id': f'call_{step_index}', 'type': 'function',
                        'function': {'name': name, 'arguments': json.dumps(args or {})}}
                chunks = [chunk({'role': 'assistant', 'tool_calls': [call]}), chunk(finish='tool_calls')]
            if (body.get('stream_options') or {}).get('include_usage'):
                chunks.append(chunk(usage={'prompt_tokens': len(messages[0]['content']) // 4,
                                           'completion_tokens': 10}))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for c in chunks:
                self.wfile.write(f'data: {json.dumps(c)}\n\n'.encode())
            self.wfile.write(b'data: [DONE]\n\n')

        def log_message(self, *args):
            pass

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('tasks', nargs='+')
    parser.add_argument('--port', type=int, default=18777)
    ops = parser.parse_args()
    tasks = load_tasks(ops.tasks)
    print(f'Oracle for {len(tasks)} prompts on http://127.0.0.1:{ops.port}/v1', flush=True)
    ThreadingHTTPServer(('127.0.0.1', ops.port), make_handler(tasks)).serve_forever()
