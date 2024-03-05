import {test_utils} from 'sdc_client';
import {} from "#root/src/main_test/main_test.organizer.js";
import '#root/src/sdc_tools/sdc_tools.organizer.js'
import '#root/src/sdc_user/sdc_user.organizer.js'
import Cookies from 'js-cookie';


describe('SDC Model [load]', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });

    test('All books lenght', async () => {
        let books = controller.newModel('Book');
        await books.load();
        expect(books.length()).toBe(6);
        books.close();
    });

    test('All books titles', async () => {
        let books = controller.newModel('Book');
        await books.load();
        let book_titles = [];
        for (let book of books) {
            book_titles.push(book.title);
        }
        expect(book_titles).toStrictEqual([
            "My super Book",
            "Nothing to do",
            "How to read",
            "The black story",
            "The green story",
            "Man i like,..."
        ]);
        books.close();
    });

    test('Nina books titles', async () => {
        let books = controller.newModel('Book', {'author': 2});
        await books.load();
        let book_titles = [];
        for (let book of books) {
            book_titles.push(book.title);
        }
        expect(book_titles).toStrictEqual([
            "The black story",
            "The green story"
        ]);
        books.close();
    });

    test('Nina books titles 2', async () => {
        let books = controller.newModel('Book', {'author': 2});
        await books.load();
        let book_titles = [];
        for (let book of books) {
            book_titles.push(book.title);
        }
        let books2 = controller.newModel('Book');
        books2.filter({'author': 2});
        await books2.load();
        let book2_titles = [];
        for (let book of books2) {
            book2_titles.push(book.title);
        }
        expect(book_titles).toStrictEqual(book2_titles);
        books.close();
        books2.close();
    });

    test('No correct Author books', async () => {
        let books = controller.newModel('Book', {'author': -1});
        await books.load();
        let book_titles = [];
        for (let book of books) {
            book_titles.push(book.title);
        }

        expect(book_titles).toStrictEqual([]);
        books.close();
    });

    test('No correct filter key', async () => {
        let books = controller.newModel('Book', {'xxxx': -1});
        const reason = await books.load().catch(reason => {
            return reason;
        });

        expect(reason.is_error).toBe(true);
        books.close();
    });

});

describe('SDC Model [create]', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });

    test('create Book', async () => {
        let books = controller.newModel('Book');
        await books.create({'title': 'Last of the books!', 'author': 2})
        expect(books.values).toMatchObject({"author": 2, "title": "Last of the books!"});
        books.close();
    });


    test('create Book on_create', async () => {
        let books = controller.newModel('Book');
        let is_on_create = false;
        books.on_create = (res) => {
            is_on_create = true;
            expect(res[0]).toMatchObject({"author": 2, "title": "First of the books!"});
        }
        await books.create({'title': 'First of the books!', 'author': 2});

        for (let i = 0; i < 5; ++i) {
            await new Promise((resolve) => setTimeout(resolve, 50));
            if (is_on_create) {
                break;
            }
        }
        expect(is_on_create).toBe(true);
        books.close();
    });


    test('create Book no on_create', async () => {
        let books = controller.newModel('Book', {'pk': 1});
        let is_on_create = false;
        books.on_create = () => {
            is_on_create = true;
        }
        await books.create({'title': 'The real last of the books!', 'author': 2});

        for (let i = 0; i < 5; ++i) {
            await new Promise((resolve) => setTimeout(resolve, 50));
            if (is_on_create) {
                break;
            }
        }
        expect(is_on_create).toBe(false);
        books.close();
    });

});


describe('SDC Model [save]', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });


    test('Changed Book name [model filter]', async () => {
        let books = controller.newModel('Book', {'pk': 1});
        await books.load();

        books.values.title = "My super doper Book";
        await books.save();
        await books.load();

        expect(books.values.title).toBe("My super doper Book");
        books.close();
    });

    test('Changed Book name [no filter]', async () => {
        let books = controller.newModel('Book');
        await books.load();

        books.values_list[0].title = "My super doper doper Book";
        await books.save();
        await books.load();

        expect(books.values_list[0].title).toBe("My super doper doper Book");
        books.close();
    });


    test('Changed Book name [save filter]', async () => {
        let books = controller.newModel('Book');
        await books.load();

        books.byPk(1).title = "My super doper doper doper Book";
        await books.save(1);
        await books.load();

        expect(books.byPk(1).title).toBe("My super doper doper doper Book");
        books.close();
    });


    test('update Book after change', async () => {
        let books = controller.newModel('Book');
        let is_updated = false;
        books.on_update = () => {
            is_updated = true;
        }
        await books.load();

        books.byPk(1).title = "My super doper doper doper Book";
        await books.save(1);
        for (let i = 0; i < 10; ++i) {
            await new Promise((resolve) => setTimeout(resolve, 50));
            if (is_updated) {
                break;
            }
        }
        expect(is_updated).toBe(true);
        books.close();
    });


    test('Update Book wrong property change', async () => {
        let books = controller.newModel('Book');

        await books.load();

        books.byPk(1).sub_title = "My super doper doper doper Book";
        await books.save(1);
        books.close();
        books = controller.newModel('Book');
        books.load();
        expect(books.byPk(1).sub_title).toBe(undefined);
        books.close();

    });


    test('Update Book wrong id change', async () => {
        let books = controller.newModel('Book');

        await books.load();

        books.byPk(99).title = "My super doper doper doper Book";
        let reason = await books.save(99).catch(reason => reason);
        expect(reason.is_error).toBe(true);
        books.close();

    });


    test('no update Book after change', async () => {
        let booksSave = controller.newModel('Book');
        let books = controller.newModel('Book', {'author': 2});
        let is_updated = false;
        books.on_update = () => {
            is_updated = true;
        }
        await booksSave.load();

        booksSave.byPk(1).title = "My super doper doper doper Book";
        await booksSave.save(1);
        for (let i = 0; i < 5; ++i) {
            await new Promise((resolve) => setTimeout(resolve, 50));
            if (is_updated) {
                break;
            }
        }
        expect(is_updated).toBe(false);
        books.close();
        booksSave.close();
    });

});

describe('SDC Model [form]', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });


    test('Book edit form', async () => {
        let books = controller.newModel('Book', {'pk': 1});
        await new Promise((resolv) => {
            controller.find('.edit_form').append(books.editForm(-1, resolv));
        });
        expect(controller.find('.edit_form').hasClass('sdc-model-edit-form')).toBe(true);
        books.close();
    });


    test('Book edit form to model', async () => {
        let books = controller.newModel('Book', {'pk': 1});
        await new Promise((resolv) => {
            controller.find('.edit_form').append(books.editForm(-1, resolv));
        });
        controller.find('.edit_form #id_title').val('My super doper doper doper doper Book');
        controller.find('.edit_form #id_author').val(2);
        books.syncForm();
        expect(books.values.title).toBe(controller.find('.edit_form #id_title').val());
        expect(books.values.id_author).toBe(controller.find('.edit_form #id_id_author').val());
        books.close();
    });


    test('Book edit form to model', async () => {
        let books = controller.newModel('Book', {'pk': 1});
        let res_pk = -1;
        books.save = (res) => {
            res_pk = res;
            return Promise.resolve();
        };
        await new Promise((resolv) => {
            controller.find('.edit_form').append(books.editForm(-1, resolv));
        });
        controller.find('.edit_form').submit();
        expect(res_pk).toBe(1);
        books.close();
    });
});

describe('SDC Model [form & file]', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });


    test('Book content create form', async () => {
        let books = controller.newModel('BookContent');
        let o_save = books.create.bind(books);
        let g_resolve;

        let sevRes = new Promise((resolve) => {
            g_resolve = resolve;
        });

        books.create = (pk)=> {
            let res = o_save(pk);
            return res.then((x)=> {
                g_resolve();
                return x;
            });
        }

        await new Promise((resolv) => {
            controller.find('.edit_form').append(books.createForm(resolv));
        });

        const file = new File(['file contents'], 'manage.txt', { type: 'text/plain' });

        const changeEvent = new Event('change', { bubbles: true });
        Object.defineProperty( controller.find('.edit_form #id_text')[0], 'files', { value: [file] });
        controller.find('.edit_form #id_text')[0].dispatchEvent(changeEvent);
        controller.find('.edit_form #id_user').val(2);
        controller.find('.edit_form').submit();
        await sevRes

        expect(controller.find('.edit_form').hasClass('sdc-model-create-form')).toBe(true);
        books.close();
    });


    test('Check content of file field', async () => {
        let books = controller.newModel('BookContent', {'pk': 1});
        await books.load();

        expect(books.values.text.substring(0,13)).toBe('/media/manage');
        books.close();
    });


    test('Check content of file field', async () => {
        let books = controller.newModel('BookContent', {'pk': 1});
        await books.load();

        expect(books.values.text.substring(0,13)).toBe('/media/manage');
        books.close();
    });


    test('Check content of file field', async () => {
        let books = controller.newModel('BookContent', {'pk': 1});


        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.editForm(1, resolv));
        });

        books.syncForm();

        expect(books.values.text).toBe(undefined);
        books.close();
    });


    test('Check content of file field', async () => {
        let books = controller.newModel('BookContent', {'pk': 1});


        await new Promise((resolv, reject) => {
            controller.find('.edit_form').safeEmpty().append(books.editForm(1, resolv, reject));
        });


        await new Promise((resolv, reject) => {
            books.editForm(2, reject, resolv);
        });

        const file = new File(['file contents NEW'], 'manage.txt', { type: 'text/plain' });

        const changeEvent = new Event('change', { bubbles: true });
        Object.defineProperty( controller.find('.edit_form #id_text')[0], 'files', { value: [file] });
        controller.find('.edit_form #id_text')[0].dispatchEvent(changeEvent);

        books.syncForm();

        expect(books.values.text instanceof File).toBe(true);
        books.close();
    });
});


describe('SDC Model [list & details]', () => {
    let controller;



    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });


    test('Book content no details exist', async () => {
        let books = controller.newModel('BookContent');
        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.detailView(1, ()=> {throw new Error()}, resolv));
        });

        expect(controller.find('.edit_form div').html()).toBe("");
        books.close();
    });


    test('Book no details exist', async () => {
        let books = controller.newModel('Book');
        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.detailView(199, ()=> {throw new Error()}, resolv));
        });

        expect(controller.find('.edit_form div').html()).toBe("");
        books.close();
    });


    test('Book details exist', async () => {
        let books = controller.newModel('Book');
        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.detailView(1, resolv));
        });

        let expectedRes = "\n\n<div class=\"container-fluid\">\n\n<div class=\"container-fluid\">\n    <div class=\"row\">\n        <div class=\"col-8\">\n            <h3>Book object (1)</h3>\n        </div>\n        <div class=\"col-4\">\n            <button type=\"button\" class=\"btn btn-danger\" data-bs-toggle=\"modal\" data-bs-target=\"#deleteBookModal_detail\">\n                Remove\n            </button>\n            <!-- Modal -->\n            <div class=\"modal fade\" id=\"deleteBookModal_detail\" tabindex=\"-1\" aria-labelledby=\"deleteBookModal_detil_label\" aria-hidden=\"true\">\n                <div class=\"modal-dialog\">\n                    <div class=\"modal-content\">\n                        <div class=\"modal-header\">\n                            <h5 class=\"modal-title\" id=\"deleteBookModal_detil_label\">Are you sure</h5>\n                            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                        </div>\n                        <div class=\"modal-body\">\n                            Do you want to delete Book object (1)?\n                        </div>\n                        <div class=\"modal-footer\">\n                            <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Close</button>\n                            <button sdc_click=\"removeInstance\" data-instance-pk=\"1\" type=\"button\" class=\"btn btn-danger\" data-bs-dismiss=\"modal\">Remove Book object (1)</button>\n                        </div>\n                    </div>\n                </div>\n            </div>\n        </div>\n    </div>\n</div></div>"

        expect(controller.find('.edit_form').html()).toBe(expectedRes);
        books.close();
    });


    test('Book content no list exist', async () => {
        let books = controller.newModel('BookContent');
        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.listView({}, ()=> {throw new Error()}, resolv));
        });

        expect(controller.find('.edit_form div').html()).toBe("");
        books.close();
    });


    test('Book list exist', async () => {
        let books = controller.newModel('Book');
        await new Promise((resolv) => {
            controller.find('.edit_form').safeEmpty().append(books.listView({}, resolv));
        });

        let expectedRes = "\n\n<div class=\"container-fluid\">\n<p>Book object (8)</p>\n\n<p>Book object (3)</p>\n\n<p>Book object (7)</p>\n\n<p>Book object (6)</p>\n\n<p>Book object (1)</p>\n\n<p>Book object (2)</p>\n\n<p>Book object (4)</p>\n\n<p>Book object (5)</p>\n\n<p>Book object (9)</p>\n</div>";

        expect(controller.find('.edit_form').html()).toBe(expectedRes);
        books.close();
    });

})