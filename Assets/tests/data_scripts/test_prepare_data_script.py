from main_test.models import Author, Book
from django.test import Client
from django.contrib.auth.models import User

auther_list = []
book_list = []

auther_list.append(Author.objects.create(name='Martin', age=22))
auther_list.append(Author.objects.create(name='Nina', age=23))
auther_list.append(Author.objects.create(name='Artin', age=24))

book_list.append(Book.objects.create(title='My super Book', author=auther_list[0]))
book_list.append(Book.objects.create(title='Nothing to do', author=auther_list[0]))
book_list.append(Book.objects.create(title='How to read', author=auther_list[0]))

book_list.append(Book.objects.create(title='The black story', author=auther_list[1]))
book_list.append(Book.objects.create(title='The green story', author=auther_list[1]))

book_list.append(Book.objects.create(title='Man i like,...', author=auther_list[2]))

client = Client()

user = User.objects.create_superuser("TestUser", "test@test.test", "123")

client.login(username="TestUser", password="123")


print(client.session.session_key)