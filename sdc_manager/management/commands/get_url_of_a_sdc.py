from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    help = 'Get the url of a SDC controller if it exists'

    def add_arguments(self, parser):
        parser.add_argument('controller_name', type=str, help='The name of the controller as snake_case')

    @staticmethod
    def get_url(c_name_sc):
        url_name = "scd_view_" + c_name_sc

        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name):
                url_to_sdc = "/" + get_resolver().reverse_dict[i][0][0][0]
                return url_to_sdc
        return ''

    def handle(self, *args, **options):
        c_name_sc = options['controller_name']
        return self.get_url(c_name_sc)
