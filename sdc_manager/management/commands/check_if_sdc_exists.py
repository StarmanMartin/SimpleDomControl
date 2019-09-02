from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    help = 'Checks if a SDC controller exists'

    def add_arguments(self, parser):
        parser.add_argument('controller_name', type=str, help='The name of the controller as snake_case')

    @staticmethod
    def check_controller_name(c_name_sc):
        url_name = "scd_view_" + c_name_sc

        for i in get_resolver().reverse_dict.keys():
            if str(i).endswith(url_name):
                return True

        return False

    def handle(self, *args, **options):
        c_name_sc = options['controller_name']
        if self.check_controller_name(c_name_sc):
            self.stdout.write(self.style.ERROR("TRUE"))
        else:
            self.stdout.write(self.style.SUCCESS("FALSE"))
