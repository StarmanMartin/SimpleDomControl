from asgiref.sync import async_to_sync
from django.core.exceptions import PermissionDenied

import json
from channels.generic.websocket import WebsocketConsumer
from django.utils.translation import ugettext as _f
from sdc_tools.django_extension.response import  sdc_link_factory, sdc_link_obj_factory


importlist = []

class SDCConsumer(WebsocketConsumer):

    def connect(self):
        self.scope["session"]["channel_name"] = self.channel_name
        self.scope["session"].save()
        self.accept()
        self.group_list = []

    def disconnect(self, close_code):
        for group in self.group_list:
            async_to_sync(self.channel_layer.group_discard)(
                group,
                self.channel_name
            )

    def state_sdc_event(self, event):
        self.send(text_data=json.dumps({
            'type': 'sdc_event',
            'event': event.get('event', False),
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'payload': event.get('payload', False),
            'is_error': False
        }))

    def state_redirect(self, event):
        if 'controller' in event:
            event['link'] = sdc_link_factory(event.get('controller'), event.get('args'))

        self.send(text_data=json.dumps({
            'type': 'sdc_redirect',
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'link': sdc_link_obj_factory(event.get('link', False)),
            'is_error': False
        }))


    def state_error(self, event):
        self.send(text_data=json.dumps({
            'type': 'error',
            'is_error': True,
            'msg': event.get('msg', ''),
            'header': event.get('header', ''),
        }))

    @staticmethod
    def to_camel_case(snake_str):
        components = snake_str.split('-')
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        return ''.join(x.title() for x in components)

    def receive(self, text_data=None, bytes_data=None):
        try:
            json_data = json.loads(text_data)
            if json_data['event'] == 'sdc_call':
                controller_name = self.to_camel_case(json_data['controller'])
                controller = getattr(globals()[json_data['app']], controller_name)
                method = getattr(controller(), json_data['function'])
                return_vals = method(channel=self, **json_data['args'])
                if return_vals is not None:
                    self.send(text_data=json.dumps({
                        'id': json_data['id'],
                        'type': 'sdc_recall',
                        'data': return_vals,
                        'is_error': False
                    }))
            elif json_data['event'] == 'sdc_add_group':
                if json_data['group'] not in self.group_list:
                    self.group_list.append(json_data['group'])
                    async_to_sync(self.channel_layer.group_discard)(
                        json_data['group'],
                        self.channel_name
                    )
            elif json_data['event'] == 'sdc_remove_group':
                if json_data['group'] in self.group_list:
                    self.group_list.remove(json_data['group'])
                    async_to_sync(self.channel_layer.gr)(
                        json_data['group'],
                        self.channel_name
                    )

        except PermissionDenied:
            self.state_error({
                'msg': _f('403 Not allowed!'),
                'header': _f('Upps!!')
            })

        except:
            self.state_error({
                'msg': _f('Something went wrong'),
                'header': _f('Upps!!')
            })