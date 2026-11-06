"""
Writes eval/sdctest/fixture.json (the data of the SdcTest evaluation, manage.py sdc_eval_ai) and
eval/sdctest/fixture_large.json (the same plus long lists, for tasks_large/).

Run from SimpleDomControl/:  python manage.py shell -c "exec(open('eval/sdctest/build_fixture.py').read())"

The expected answers of the tasks in eval/sdctest/tasks depend on this data; change both together.
Password hashes use a fixed salt so that the file is reproducible. All users have the password in PASSWORD.
"""
import json
import os

from django.contrib.auth.hashers import make_password

PASSWORD = 'eval-pass-123'
OUT = os.path.join('eval', 'sdctest', 'fixture.json')
JOINED = '2026-01-15T09:00:00Z'

# role: regular (no group), editor (group Editor), staff (is_staff), admin (superuser)
USERS = [
    (1, 'jane', 'Jane', 'Doe', 'jane@example.org', False, False, [], True),
    (2, 'eddie', 'Eddie', 'Editor', 'eddie@example.org', False, False, [1], True),
    (3, 'sam', 'Sam', 'Staff', 'sam@example.org', True, False, [], True),
    (4, 'root', 'Ruth', 'Admin', 'admin@example.org', True, True, [], True),
]
AUTHORS = [  # (pk, name, age)
    (1, 'Test', 0), (2, 'Martin', 22), (3, 'Nina', 23), (4, 'Artin', 24), (5, 'Grace Hopper', 85),
    (6, 'Ada Lovelace', 36),
]
BOOKS = [  # (pk, title, author)
    (1, 'My super Book', 2), (2, 'Nothing to do', 2), (3, 'How to read', 2), (4, 'The black story', 3),
    (5, 'The green story', 3), (6, 'Man i like,...', 4), (7, 'Notes on the Analytical Engine', 6),
    (8, 'Compiler Design Basics', 5), (9, 'The red story', 3),
]
CONTENTS = [  # (pk, user, file)
    (1, 1, 'eval/jane_notes.txt'), (2, 1, 'eval/jane_summary.txt'), (3, 2, 'eval/eddie_notes.txt'),
]

data = [{'model': 'auth.group', 'pk': 1, 'fields': {'name': 'Editor', 'permissions': []}}]
for pk, username, first, last, email, staff, superuser, groups, confirmed in USERS:
    data.append({'model': 'sdc_user.sdcuser', 'pk': pk, 'fields': {
        'password': make_password(PASSWORD, salt=f'sdceval{username}'), 'last_login': None,
        'is_superuser': superuser, 'username': username, 'first_name': first, 'last_name': last, 'email': email,
        'is_staff': staff, 'is_active': True, 'date_joined': JOINED, 'email_confirmed': confirmed,
        'groups': groups, 'user_permissions': []}})
data += [{'model': 'main_test.author', 'pk': pk, 'fields': {'name': name, 'age': age}} for pk, name, age in AUTHORS]
data += [{'model': 'main_test.book', 'pk': pk, 'fields': {'title': title, 'author': author}}
         for pk, title, author in BOOKS]
data += [{'model': 'main_test.bookcontent', 'pk': pk, 'fields': {'user': user, 'text': text}}
         for pk, user, text in CONTENTS]

with open(OUT, 'w') as f:
    json.dump(data, f, indent=1)
    f.write('\n')
print(f'Wrote {OUT}: {len(data)} objects')

# Large-list variant for the tasks in tasks_large/: the same data plus 300 authors and 1000 books, so that lists
# need searching and paging (the book list shows 20 rows per page, ordered by title: "Atlas 0000" comes first).
# Book "Atlas NNNN" (pk 101 + NNNN) is written by "Writer MMM" with MMM = NNNN % 300 + 1 (author pk 100 + MMM).
LARGE_OUT = os.path.join('eval', 'sdctest', 'fixture_large.json')
large = list(data)
large += [{'model': 'main_test.author', 'pk': 100 + i, 'fields': {'name': f'Writer {i:03d}', 'age': 20 + i % 60}}
          for i in range(1, 301)]
large += [{'model': 'main_test.book', 'pk': 101 + i, 'fields': {'title': f'Atlas {i:04d}', 'author': 100 + i % 300 + 1}}
          for i in range(1000)]
with open(LARGE_OUT, 'w') as f:
    json.dump(large, f, indent=1)
    f.write('\n')
print(f'Wrote {LARGE_OUT}: {len(large)} objects')
