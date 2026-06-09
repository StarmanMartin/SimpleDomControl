import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode

from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files import File
from django.test import TestCase
from django.contrib.auth.models import Group
from django.test.client import Client
from django.test.utils import override_settings
import yaml

from SdcTest.asgi import application
from main_test.models import Author, Book, BookSearchForm, AuthorSearchForm, BookContent
from main_test.test_utils import AuthWebsocketCommunicator, WithMockedElementTest

from sdc_core.sdc_extentions.search import handle_search_form

User = get_user_model()

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
        self.user: User = User.objects.create_superuser(username='testuser')
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
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'args', 'is_error'])

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
        self.assertListEqual(list(message.keys()), ['type', 'event_id', 'html', 'args', 'is_error'])

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
                "pk": 1,
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
        self.assertTrue('media/TEST_FILE' in json.loads(message['data']['instance'])[0]['fields']['text']['url'])
        with open(settings.BASE_DIR / 'test_media/TEST_FILE.txt', 'r') as f:
            self.assertEqual(f.read(), ''.join(file_content))
        os.remove(settings.BASE_DIR / 'test_media/TEST_FILE.txt')


class OpenApiHttpApiTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        openapi_path = Path(settings.BASE_DIR) / "openapi.generated.yaml"

        class OpenApiLoader(yaml.SafeLoader):
            pass

        def construct_python_object_new(loader, tag_suffix, node):
            if isinstance(node, yaml.SequenceNode):
                value = loader.construct_sequence(node)
                if len(value) == 1:
                    return value[0]
                return value
            return loader.construct_scalar(node)

        OpenApiLoader.add_multi_constructor(
            "tag:yaml.org,2002:python/object/new:",
            construct_python_object_new,
        )
        with open(openapi_path, "r") as f:
            cls.openapi = yaml.load(f, Loader=OpenApiLoader)

    def setUp(self):
        self.password = "api-test-password"
        self.user = User.objects.create_user(username="api-user", password=self.password)
        self.other_user = User.objects.create_user(username="other-api-user", password=self.password)

        self.martin = Author.objects.create(name="Martin", age=22)
        self.nina = Author.objects.create(name="Nina", age=23)
        self.book = Book.objects.create(title="My super Book", author=self.martin)
        Book.objects.create(title="The black story", author=self.nina)

        self.media_root = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_root.cleanup)

        self.book_content = BookContent.objects.create(
            user=self.user,
            text=ContentFile("mine", name="api_mine.txt"),
        )
        BookContent.objects.create(
            user=self.other_user,
            text=ContentFile("other", name="api_other.txt"),
        )

        login_data = self.login()
        self.access_token = login_data["access_token"]
        self.refresh_token = login_data["refresh_token"]

    def login(self):
        response = self.client.post(
            "/sdc_api/login",
            data=json.dumps({"username": self.user.username, "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def assert_documented_response(self, path, method, status_code):
        operation = self.openapi["paths"][path][method]
        self.assertIn(str(status_code), operation["responses"])

    def assert_openapi_schema_fields(self, schema_name, actual_fields):
        schema = self.openapi["components"]["schemas"][schema_name]
        self.assertEqual(set(schema["properties"]), set(actual_fields))

    def auth_headers(self, token=None):
        return {"HTTP_AUTHORIZATION": f"Bearer {token or self.access_token}"}

    def api_url(self, model_name, pk=None):
        if pk is None:
            return f"/sdc_api/{model_name}"
        return f"/sdc_api/{model_name}/{pk}"

    def form_body(self, data):
        return urlencode(data)

    def flatten_sdc_instance(self, data):
        return {"id": data["pk"], **data["fields"]}

    def test_login_and_refresh_tokens_match_openapi_description(self):
        self.assert_documented_response("/sdc_api/login/", "post", 200)
        self.assert_documented_response("/sdc_api/login/", "get", 200)
        self.assert_documented_response("/sdc_api/login/", "post", 401)

        token_fields = self.openapi["paths"]["/sdc_api/login/"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]["properties"]
        self.assertEqual(set(token_fields), {"access_token", "refresh_token", "token_type"})

        login_data = self.login()
        self.assertEqual(set(login_data), set(token_fields))
        self.assertEqual(login_data["token_type"], "bearer")

        refresh_response = self.client.get(
            "/sdc_api/login",
            **self.auth_headers(login_data["refresh_token"]),
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(set(refresh_response.json()), set(token_fields))

        invalid_response = self.client.post(
            "/sdc_api/login",
            data=json.dumps({"username": self.user.username, "password": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(invalid_response.status_code, 401)

    def test_model_endpoints_require_bearer_token(self):
        self.assertEqual(self.openapi["security"], [{"BearerAuth": []}])
        response = self.client.get(self.api_url("Author"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Missing Authorization header"})

    def test_author_list_detail_create_replace_and_patch(self):
        self.assert_documented_response("/sdc_api/author/", "get", 200)
        self.assert_documented_response("/sdc_api/author/{id}/", "get", 200)
        self.assert_documented_response("/sdc_api/author/{id}/", "put", 200)
        self.assert_documented_response("/sdc_api/author/{id}/", "patch", 200)

        list_response = self.client.get(self.api_url("Author"), **self.auth_headers())
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertTrue(list_data["success"])
        self.assertEqual(
            [self.flatten_sdc_instance(item)["name"] for item in list_data["data"]],
            ["Martin", "Nina"],
        )
        self.assert_openapi_schema_fields("Author", self.flatten_sdc_instance(list_data["data"][0]).keys())

        detail_response = self.client.get(self.api_url("Author", self.martin.pk), **self.auth_headers())
        self.assertEqual(detail_response.status_code, 200)
        detail_data = self.flatten_sdc_instance(detail_response.json()["data"])
        self.assertEqual(detail_data, {"id": self.martin.pk, "name": "Martin", "age": 22})

        create_response = self.client.post(
            self.api_url("Author"),
            data={"name": "Ada", "age": 36},
            **self.auth_headers(),
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json(), {"success": True, "data": {"name": "Ada", "age": 36}})
        created_author = Author.objects.get(name="Ada")

        replace_response = self.client.put(
            self.api_url("Author", created_author.pk),
            data=self.form_body({"name": "Ada Lovelace", "age": 37}),
            content_type="application/x-www-form-urlencoded",
            **self.auth_headers(),
        )
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(
            replace_response.json(),
            {"success": True, "data": {"name": "Ada Lovelace", "age": 37}},
        )

        patch_response = self.client.patch(
            self.api_url("Author", created_author.pk),
            data=self.form_body({"age": 38}),
            content_type="application/x-www-form-urlencoded",
            **self.auth_headers(),
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(
            patch_response.json(),
            {"success": True, "data": {"name": "Ada Lovelace", "age": 38}},
        )

    def test_book_list_and_detail_match_openapi_description(self):
        self.assert_documented_response("/sdc_api/book/", "get", 200)
        self.assert_documented_response("/sdc_api/book/{id}/", "get", 200)

        list_response = self.client.get(self.api_url("Book"), **self.auth_headers())
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertTrue(list_data["success"])
        self.assertEqual(
            [self.flatten_sdc_instance(item)["title"] for item in list_data["data"]],
            ["My super Book", "The black story"],
        )
        self.assert_openapi_schema_fields("Book", self.flatten_sdc_instance(list_data["data"][0]).keys())

        detail_response = self.client.get(self.api_url("Book", self.book.pk), **self.auth_headers())
        self.assertEqual(detail_response.status_code, 200)
        detail_data = self.flatten_sdc_instance(detail_response.json()["data"])
        self.assertEqual(
            detail_data,
            {"id": self.book.pk, "title": "My super Book", "author": self.martin.pk},
        )

    def test_book_content_is_authenticated_and_scoped_to_current_user(self):
        self.assert_documented_response("/sdc_api/bookcontent/", "get", 200)
        self.assert_documented_response("/sdc_api/bookcontent/{id}/", "get", 200)

        list_response = self.client.get(self.api_url("BookContent"), **self.auth_headers())
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertTrue(list_data["success"])
        self.assertEqual(len(list_data["data"]), 1)

        content_data = self.flatten_sdc_instance(list_data["data"][0])
        self.assert_openapi_schema_fields("BookContent", content_data.keys())
        self.assertEqual(content_data["id"], self.book_content.pk)
        self.assertEqual(content_data["user"], self.user.pk)
        self.assertEqual(content_data["text"]["name"], "api_mine.txt")

        detail_response = self.client.get(self.api_url("BookContent", self.book_content.pk), **self.auth_headers())
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(self.flatten_sdc_instance(detail_response.json()["data"])["id"], self.book_content.pk)

        other_content = BookContent.objects.get(user=self.other_user)
        forbidden_detail = self.client.get(self.api_url("BookContent", other_content.pk), **self.auth_headers())
        self.assertEqual(forbidden_detail.status_code, 404)
