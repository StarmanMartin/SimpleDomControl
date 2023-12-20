import json
import os

from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.core.files import File
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.test.client import Client
from django.test.utils import override_settings

from SdcTest.asgi import application
from main_test.models import Author, Book, BookSearchForm, AuthorSearchForm, BookContent
from main_test.test_utils import AuthWebsocketCommunicator, WithMockedElementTest

from sdc_core.sdc_extentions.search import handle_search_form


# Create your tests here.
class AccessRightsTest(TestCase):
    users: dict[str, str] = {'admin': 'None', 'staff': 'None', 'editor': 'None', 'user': 'None'}
    passowrd = '12345'

    def setUp(self):
        editor_grop, created = Group.objects.get_or_create(name='Editor')

        user: User = User.objects.create(username='testuser')
        user.set_password(self.passowrd)
        user.save()
        self.users['user'] = user.username

        user: User = User.objects.create(username='teststaff')
        user.set_password(self.passowrd)
        user.save()
        user.is_staff = True
        user.save()
        self.users['staff'] = user.username

        user: User = User.objects.create(username='testeditor')
        user.set_password(self.passowrd)
        user.groups.add(editor_grop)
        user.save()
        self.users['editor'] = user.username

        user: User = User.objects.create_superuser(username='testadmin')
        user.set_password(self.passowrd)
        user.save()
        self.users['admin'] = user.username

    def send_request(self, username, url_path):
        """Send request for different users"""
        c = Client()

        # You'll need to log him in before you can send requests through the client
        c.login(username=username, password=self.passowrd)
        return c.get(f'/sdc_view/main_test/{url_path}', {'_method': 'content'})

    def test_logged_in(self):
        for (user, username) in self.users.items():
            res = self.send_request(username, 'logged_in')
            self.assertEqual(res.status_code, 200)

    def test_editor_no_staff(self):
        res = self.send_request(self.users['editor'], 'editor_no_staff')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['admin'], 'editor_no_staff')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['staff'], 'editor_no_staff')
        self.assertEqual(res.status_code, 301)

        res = self.send_request(self.users['user'], 'editor_no_staff')
        self.assertEqual(res.status_code, 301)

    def test_editor_and_staff(self):
        res = self.send_request(self.users['editor'], 'editor_and_staff')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['admin'], 'editor_and_staff')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['staff'], 'editor_and_staff')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['user'], 'editor_and_staff')
        self.assertEqual(res.status_code, 301)

    def test_staff_and_admin(self):
        res = self.send_request(self.users['editor'], 'staff_and_admin')
        self.assertEqual(res.status_code, 301)

        res = self.send_request(self.users['admin'], 'staff_and_admin')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['staff'], 'staff_and_admin')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['user'], 'staff_and_admin')
        self.assertEqual(res.status_code, 301)

    def test_admin_only(self):
        res = self.send_request(self.users['editor'], 'admin_only')
        self.assertEqual(res.status_code, 301)

        res = self.send_request(self.users['admin'], 'admin_only')
        self.assertEqual(res.status_code, 200)

        res = self.send_request(self.users['staff'], 'admin_only')
        self.assertEqual(res.status_code, 301)

        res = self.send_request(self.users['user'], 'admin_only')
        self.assertEqual(res.status_code, 301)

    def test_main_view(self):
        for (user, username) in self.users.items():
            res = self.send_request(username, 'main_view')
            self.assertEqual(res.status_code, 200)
        c = Client()
        res = c.get(f'/sdc_view/main_test/main_view', {'_method': 'content'})
        self.assertEqual(res.status_code, 403)


class SearchTest(TestCase, WithMockedElementTest):
    def setUp(self):
        self.set_up_elements()

    def test_search_book(self):
        form = BookSearchForm(data={'search': 'story',
                                    'order_by': 'title',
                                    'range_start': 0,
                                    '_method': 'search'})

        res = handle_search_form(Book.objects, form, range=20)
        books = list(res['instances'].values_list('title', flat=True))
        self.assertListEqual(books, ['The black story', 'The green story'])

    def test_search_book_by_author(self):
        form = BookSearchForm(data={'search': 'Martin',
                                    'order_by': 'title',
                                    'range_start': 0,
                                    '_method': 'search'})

        res = handle_search_form(Book.objects, form, range=20)
        books = list(res['instances'].values_list('title', flat=True))
        self.assertListEqual(books, ['How to read', 'My super Book', 'Nothing to do'])

    def test_search_author(self):
        form = AuthorSearchForm(data={'search': 'Nothing to do',
                                      'order_by': 'age',
                                      'range_start': 0,
                                      '_method': 'search'})

        res = handle_search_form(Author.objects, form, range=20)
        books = list(res['instances'].values_list('name', flat=True))
        self.assertListEqual(books, ['Martin'])

    def test_search_order_author(self):
        form = AuthorSearchForm(data={'search': 'Artin',
                                      'order_by': 'age',
                                      'range_start': 0,
                                      '_method': 'search'})

        res = handle_search_form(Author.objects, form, range=20)
        books = list(res['instances'].values_list('name', flat=True))
        self.assertEqual(books[0], 'Martin')

        form = AuthorSearchForm(data={'search': 'Artin',
                                      'order_by': 'name',
                                      'range_start': 0,
                                      '_method': 'search'})

        res = handle_search_form(Author.objects, form, range=20)
        books = list(res['instances'].values_list('name', flat=True))
        self.assertEqual(books[0], 'Artin')


class ServerCallTest(TestCase):
    def setUp(self) -> None:
        password = "asd"
        self.user: User = User.objects.create(username='testuser')
        self.user.set_password(password)
        self.user.save()

    async def test_my_consumer(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/ws/", user=self.user)

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        args = {"a": 1, "b": True, "c": "Hallo"}

        await communicator.send_json_to({
            "event": 'sdc_call',
            "id": 123,
            "controller": "main-view",
            "app": "main_test",
            "function": "test_echo_call",
            "args": args
        })

        # Test on connection welcome message
        message = await communicator.receive_from()
        self.assertEqual(json.loads(message)['link'], '<a href="/logged-in">Redirector</a>', )

        message = await communicator.receive_from()
        self.assertDictEqual(json.loads(message)['data'], args)
        await communicator.disconnect()

    @override_settings(DEBUG=True)
    async def test_my_error_consumer(self):
        communicator = WebsocketCommunicator(application, "/sdc_ws/ws/")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        args = {"a": 1, "b": True, "c": "Hallo"}

        await communicator.send_json_to({
            "event": 'sdc_call',
            "id": 123,
            "controller": "mainview",
            "app": "main_test",
            "function": "test_echo_call",
            "args": args
        })

        # Test on connection welcome message
        message = await communicator.receive_from()
        self.assertTrue("module 'main_test.sdc_views' has no attribute 'Mainview'" in message)

        await communicator.send_json_to({
            "event": 'sdccall',
            "id": 123,
            "controller": "main_view",
            "app": "main_test",
            "function": "test_echo_call",
            "args": args
        })

        # Test on connection welcome message
        message = await communicator.receive_from()
        self.assertTrue("event must be sdc_call" in message)

        await communicator.send_json_to({
            "event": 'sdc_call',
            "id": 123,
            "controller": "main-view",
            "app": "main_test",
            "function": "test_echo_call",
            "args": args
        })

        # Test on connection welcome message
        message = await communicator.receive_from()
        self.assertTrue("403 Not allowed" in message)


class ServerModelTest(TestCase, WithMockedElementTest):
    def setUp(self) -> None:
        self.set_up_elements()
        password = "asd"
        self.user: User = User.objects.create(username='testuser')
        self.user.set_password(password)
        self.user.save()
        with open('./main_test/Assets/TEST_FIXED.txt', 'r') as f:
            BookContent.objects.create(user=self.user, text = File(f))

    async def test_connect(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'connect',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "model_query": {}
            }
        })
        message = await communicator.receive_from()
        self.assertFalse(json.loads(message)["is_error"])

    async def test_connect_fails(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'None',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "model_query": {}
            }
        })
        message = await communicator.receive_from()
        self.assertTrue(json.loads(message)["is_error"])

    async def test_load(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'load',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertListEqual([x['fields']['name'] for x in json.loads(message['args']['data'])],
                             ['Martin', 'Nina', 'Artin'])
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'args', 'is_error'])

    async def test_edit_form(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'edit_form',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "pk": 1,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertTrue('html' in message)
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'is_error'])

    async def test_create_form(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'create_form',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertTrue('html' in message)
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'is_error'])

    async def test_list_view(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'list_view',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertTrue('html' in message)
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'is_error'])

    async def test_detail_view(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'detail_view',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "pk": 1,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertTrue('html' in message)
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'is_error'])

    async def test_create(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        new_autor_data = {
            "name": "New Author",
            "age": 33
        }

        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'create',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "data": new_autor_data,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        instance = json.loads(message['data']['instance'])[0]
        self.assertEqual(instance['pk'], 4)
        self.assertDictEqual(instance['fields'], new_autor_data)
        self.assertListEqual(list(message.keys()), ['header', 'msg', 'type', 'event_id', 'data', 'html', 'is_error'])

    async def test_save(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        new_autor_data = {
            "name": "Martin",
            "pk": 1,
            "age": 50
        }

        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'save',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "data": new_autor_data,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        instance = json.loads(message['data']['instance'])[0]
        del new_autor_data['pk']
        self.assertEqual(instance['pk'], 1)
        self.assertDictEqual(instance['fields'], new_autor_data)
        self.assertListEqual(list(message.keys()), ['header', 'msg', 'type', 'event_id', 'data', 'html', 'is_error'])

    async def test_delete(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/Author", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'delete',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "pk": 1,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'is_error'])
        self.assertFalse(message['is_error'])

        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'delete',
            "event_id": 'id',
            "args": {
                "model_name": "Author",
                "pk": 1,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertListEqual(list(message.keys()), ['type', 'is_error', 'msg', 'event_id', 'header'])
        self.assertTrue(message['is_error'])

    async def test_not_allowd(self):
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/BookContent")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'load',
            "event_id": 'idxx',
            "args": {
                "model_name": "BookContent",
                "pk": 1,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertEqual(message['msg'], '403 Not allowed!')
        self.assertListEqual(list(message.keys()), ['type', 'is_error', 'msg', 'event_id', 'header'])


    @override_settings(MEDIA_ROOT = settings.BASE_DIR / 'test_media')
    async def test_upload(self):
        file = settings.BASE_DIR / 'test_media/TEST_FILE.txt'
        if os.path.exists(file):
            os.remove(file)
        communicator = AuthWebsocketCommunicator(application, "/sdc_ws/model/BookContent", user=self.user)
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        file_content = ["I am a long", " long file"]
        key = "text"
        file_name = "TEST_FILE.txt"
        id = "upload_TEST_FILE.txt"
        file_size = len(file_content[0]) + len(file_content[1])
        files = {
            key: {
                'id': id,
                'file_name': file_name,
                'field_name': key,
                'content_length': file_size,
            }
        }

        for i in range(len(file_content)):
            await communicator.send_json_to({
                "event": 'model',
                "event_type": 'upload',
                "event_id": id,
                "args": {
                    "chunk": file_content[i],
                    "idx": i,
                    "number_of_chunks": 2,
                    "file_name": file_name,
                    "field_name": key,
                    "content_length": file_size,
                    "content_type": "text",
                    "model_name": 'BookContent',
                    "model_query": {}
                }
            })
        message = json.loads(await communicator.receive_from())
        self.assertFalse(message['is_error'])
        await communicator.send_json_to({
            "event": 'model',
            "event_type": 'create',
            "event_id": 'id',
            "args": {
                "model_name": "BookContent",
                "data": {'user': self.user.pk},
                "files": files,
                "model_query": {}
            }
        })
        message = json.loads(await communicator.receive_from())
        self.assertListEqual(list(message.keys()), ['header', 'msg', 'type', 'event_id', 'data', 'html', 'is_error'])
        self.assertTrue('media/TEST_FILE' in json.loads(message['data']['instance'])[0]['fields']['text'])
        with open(settings.BASE_DIR / 'test_media/TEST_FILE.txt', 'r') as f:
            self.assertEqual(f.read(), ''.join(file_content))
        os.remove(settings.BASE_DIR / 'test_media/TEST_FILE.txt')

