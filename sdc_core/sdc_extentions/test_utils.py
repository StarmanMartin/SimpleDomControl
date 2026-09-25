import os

from django.test import Client

def register_test_user(username, password):
    client = Client()
    client.login(username=username, password=password)

    print(f'USER_FOR_SDC_TESTS$$${username}$$${client.session.session_key}')

