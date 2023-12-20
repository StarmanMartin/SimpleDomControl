from channels.testing import WebsocketCommunicator

from main_test.models import Author, Book


class AuthWebsocketCommunicator(WebsocketCommunicator):
    def __init__(self, application, path, headers=None, subprotocols=None, user=None):
        super(AuthWebsocketCommunicator, self).__init__(application, path, headers, subprotocols)
        if user is not None:
            self.scope['user'] = user

class WithMockedElementTest:
    auther_list = []
    book_list = []
    def set_up_elements(self):

        self.auther_list.append( Author.objects.create(name='Martin', age=22) )
        self.auther_list.append( Author.objects.create(name='Nina', age=23) )
        self.auther_list.append( Author.objects.create(name='Artin', age=24) )

        self.book_list.append( Book.objects.create(title='My super Book', author=self.auther_list[0]) )
        self.book_list.append( Book.objects.create(title='Nothing to do', author=self.auther_list[0]) )
        self.book_list.append( Book.objects.create(title='How to read', author=self.auther_list[0]) )

        self.book_list.append( Book.objects.create(title='The black story', author=self.auther_list[1]) )
        self.book_list.append( Book.objects.create(title='The green story', author=self.auther_list[1]) )

        self.book_list.append( Book.objects.create(title='Man i like,...', author=self.auther_list[2]) )