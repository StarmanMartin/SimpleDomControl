from django.test import Client


def register_test_user(username, password):
    """
    Logs the user in and prints ``USER_FOR_SDC_TESTS$$$<username>$$$<session key>``.
    Called from the seed script of the JS tests (DB_PYTHON_SCRIPT); the JS test setup
    reads these lines into ``SDC_TEST_USER`` for ``test_utils.login(username)``.

    :raises RuntimeError: if the login fails (wrong password, inactive or missing user)
    """
    client = Client()
    if not client.login(username=username, password=password):
        raise RuntimeError(f"register_test_user: login of '{username}' failed. Check the username and password "
                           f"and that the user is active.")

    print(f'USER_FOR_SDC_TESTS$$${username}$$${client.session.session_key}')
