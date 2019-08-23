from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    help = 'Checks if a SDC controller exists'


    def add_arguments(self, parser):
        parser.add_argument('controller_name', type=str, help='The name of the controller as snake_case')

    def handle(self, *args, **options):
        c_name_sc = options['controller_name']
        url_name = "scd_view_" + c_name_sc

        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name):
                self.stdout.write(self.style.ERROR("TRUE"))
                exit(1)
        self.stdout.write(self.style.SUCCESS("FALSE"))
        