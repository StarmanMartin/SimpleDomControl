import {test_utils} from 'sdc_client';
import {} from "#root/src/models/src.js";
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
    let books = controller.querySet('Book');
    await books.load();
    expect(books.length).toBe(6);
    books.close();
  });

  test('All books titles', async () => {
    let books = controller.querySet('Book');
    await books.load();
    let book_titles = [];
    for (let book of [...books]) {
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
    let books = controller.querySet('Book', {'author': 2});
    await books.load();
    let book_titles = [];
    for (let book of books) {
      book_titles.push(book.title);
    }
    expect(book_titles).toStrictEqual([
      "My super Book",
      "Nothing to do",
      "How to read"
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
    books2.setFilter({'author': 2});
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
    let books = controller.querySet('Book');
    await books.new({'title': 'Last of the books!', 'author': 2}).create({});
    expect(books[0].author.id).toBe(2)
    expect(books[0].title).toBe("Last of the books!");
    const auth = books[0].author;
    await auth.load()
    expect(auth.age).toBe(22);
    books.close();

  });


  test('create Book on_create', async () => {
    let books = controller.querySet('Book');
    let is_on_create = false;
    books.on_create = (res) => {
      is_on_create = true;
      expect(res[0].toJson()).toMatchObject({"author": expect.any(Number), "title": "First of the books!"});
    }
    await books.create({data: {'title': 'First of the books!', 'author': 2}});

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
    let books = controller.querySet('Book', {'pk': 1});
    let is_on_create = false;
    books.on_create = () => {
      is_on_create = true;
    }
    await books.create({data: {'title': 'The real last of the books!', 'author': 2}});

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
    let books = await controller.querySet('Book', {'pk': 1}).get();

    books.title = "My super doper Book";
    await books.save();
    await books.load();

    expect(books.title).toBe("My super doper Book");
    books.close();
  });

  test('Changed Book name [no filter]', async () => {
    let books = controller.querySet('Book');
    await books.load();

    books[0].title = "My super doper doper Book";
    await books.save();
    await books.load();

    expect(books[0].title).toBe("My super doper doper Book");
    books.close();
  });


  test('Changed Book name [save filter]', async () => {
    let books = controller.querySet('Book');
    await books.load();

    books.byId(1).title = "My super doper doper doper Book";
    await books.byId(1).save();
    await books.load();

    expect(books.byId(1).title).toBe("My super doper doper doper Book");
    books.close();
  });


  test('update Book after change', async () => {
    let books = controller.querySet('Book');
    let is_updated = false;
    books.on_update = () => {
      is_updated = true;
    }
    await books.load();

    books.byId(1).title = "My super doper doper doper Book";
    await books.save({pk: 1});
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
    let books = controller.querySet('Book');

    await books.load();

    books.byId(1).sub_title = "My super doper doper doper Book";
    await books.save({pk: 1});
    books.close();
    books = controller.querySet('Book');
    await books.load();
    expect(books.byId(1).sub_title).toBe(undefined);
    books.close();

  });


  test('Update Book wrong id change', async () => {
    let books = controller.querySet('Book');

    await books.load();

    try {
      books.byId(99).title = "My super doper doper doper Book";
      expect(false).toBe(true);
    } catch (e) {
    }

    let reason = await books.save({pk: 99}).catch(reason => reason);
    expect(reason.is_error).toBe(true);
    books.close();

  });


  test('no update Book after change', async () => {
    let booksSave = controller.querySet('Book');
    let books = controller.querySet('Book', {'author': 2});
    let is_updated = false;
    books.on_update = () => {
      is_updated = true;
    }
    await booksSave.load();

    booksSave.byId(1).title = "My super doper doper doper Book";
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
    let books = await controller.querySet('Book').get({'pk': 1}, true);
    await new Promise((resolv) => {
      controller.find('.edit_form').append(books.form({cbResolve: resolv}));
    });
    expect(controller.find('.edit_form').hasClass('sdc-model-edit-form')).toBe(true);
    books.close();
  });


  test('Book named form to model', async () => {
    let books = await controller.querySet('Book', {'pk': 1}).get(null, true);

    await new Promise((resolv) => {
      controller.find('.edit_form').empty().append(books.namedForm({formName: 'test', cbResolve: resolv}));
    });
    controller.find('.edit_form #id_title').val('My super Noval');
    expect(controller.find('.edit_form #id_author').length).toBe(0);
    books.syncForm();
    expect(books.title).toBe(controller.find('.edit_form #id_title').val());
    books.close();
  });


  test('Book edit form to model', async () => {
    let books = await controller.newModel('Book').get({'pk': 1}, true);
    let res_pk = -1;
    books.save = (res) => {
      res_pk = res.data.title;
      return Promise.resolve();
    };
    await new Promise((resolv) => {
      controller.find('.edit_form').append(books.form({cbResolve: resolv}));
    });
    controller.find('.edit_form').submit();
    expect(res_pk).toBe('My super Noval');
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
    let books = controller.querySet('BookContent');
    let o_save = books.create.bind(books);
    let g_resolve;
    const book = books.new();
    let sevRes = new Promise((resolve) => {
      g_resolve = resolve;
    });

    books.create = (pk) => {
      let res = o_save(pk);
      return res.then((x) => {
        g_resolve();
        return x;
      });
    }

    await new Promise((resolv) => {
      controller.find('.edit_form').append(book.form({cbResolve: resolv}));
    });

    const file = new File(['file contents'], 'manage.txt', {type: 'text/plain'});

    const changeEvent = new Event('change', {bubbles: true});
    Object.defineProperty(controller.find('.edit_form #id_text')[0], 'files', {value: [file]});
    controller.find('.edit_form #id_text')[0].dispatchEvent(changeEvent);
    controller.find('.edit_form #id_user').val(2);
    controller.find('.edit_form').submit();
    await sevRes

    expect(controller.find('.edit_form').hasClass('sdc-model-create-form')).toBe(true);
    books.close();
  });

  test('Check reloaded content of file field', async () => {
    let books = controller.querySet('BookContent');
    const fileNew = new File(['file contents 1'], 'manage.txt', {type: 'text/plain'});
    const book1 = books.new({text: fileNew});
    await book1.create()
    const ob = await controller.querySet('BookContent').get({pk: book1.id});
    const textRes = await ob.text.text();
    // Media cannot be loaded
    expect(textRes).toBe('');
    books.close();
    ob.close();
  });

  test('Check empty content of file field', async () => {
    let books = controller.querySet('BookContent');
    const book1 = books.new();

    expect(book1.text).toBe(null);
    books.close();
  });


  test('Check content of file field', async () => {
    let books = controller.querySet('BookContent');
    const fileNew = new File(['file contents 1'], 'manage.txt', {type: 'text/plain'});
    const book1 = books.new({text: fileNew});
    await book1.create()
    const book2 = books.new({text: fileNew});
    await book2.create()

    await new Promise((resolv, reject) => {
      controller.find('.edit_form').safeEmpty().append(book1.form({cbResolve: resolv, cbReject: reject}));
    });


    await new Promise((resolv, reject) => {
      book2.form({cbResolve: resolv, cbReject: reject});
    });

    const file = new File(['file contents NEW'], 'manage.txt', {type: 'text/plain'});

    const changeEvent = new Event('change', {bubbles: true});
    Object.defineProperty(controller.find('.edit_form #id_text')[0], 'files', {value: [file]});
    controller.find('.edit_form #id_text')[0].dispatchEvent(changeEvent);

    expect(book1.text instanceof File).toBe(true);

    const ft = await book1.text.text();
    expect(ft).toBe("file contents NEW");
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
    let books = controller.querySet('BookContent');
    const file = new File(['file contents'], 'manage.txt', {type: 'text/plain'});
    const elem = await books.create({data: {text: file}})
    await new Promise((resolv) => {
      controller.find('.edit_form').safeEmpty().append(books.detailView({
        pk: elem.id, cbResolve: () => {
          throw new Error()
        }, cbReject: resolv
      }));
    });

    expect(controller.find('.edit_form div').html()).toBe("");
    books.close();
  });


  test('Book no details exist', async () => {
    let books = controller.querySet('Book').new();
    await new Promise((resolv) => {
      controller.find('.edit_form').safeEmpty().append(books.detailView({
        cbResolve: () => {
          throw new Error()
        }, cbReject: resolv
      }));
    });

    expect(controller.find('.edit_form div').html()).toBe("");
    books.close();
  });


  test('Book details exist', async () => {
    let books = controller.newModel('Book');
    await new Promise((resolv) => {
      controller.find('.edit_form').safeEmpty().append(books.detailView({pk: 1, cbResolve: resolv}));
    });

    let expectedRes = "\n\n<div class=\"container-fluid\">\n\n<h3>Book object (1)</h3></div>"

    expect(controller.find('.edit_form').html()).toBe(expectedRes);
    books.close();
  });


  test('Book content no list exist', async () => {
    let books = controller.querySet('BookContent');
    await new Promise((resolv) => {
      controller.find('.edit_form').safeEmpty().append(books.listView({
        cbResolve: () => {
          throw new Error()
        },
        cbReject: resolv
      }));
    });

    expect(controller.find('.edit_form div').html()).toBe("");
    books.close();
  });


  test('Book list exist', async () => {
    let books = controller.querySet('Book');
    await new Promise((resolv) => {
      controller.find('.edit_form').safeEmpty().append(books.listView({cbResolve: resolv}));
    });

    let expectedRes = "Book object (";

    expect(controller.find('.edit_form').html()).toContain(expectedRes);
    books.close();
  });

});


describe('SDC Model Submodel', () => {
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
    let books = controller.querySet('Book');
    await books.create({data: {'title': 'Last of the books!', 'author': 2}})
    expect(books[0].title).toBe("Last of the books!")

    await books[0].author.load();
    expect(books[0].author.age).toBe(22);
    expect(books[0].author.name).toBe('Martin');
    expect(books[0].author.id).toBe(2);
    books.close();

  });
});