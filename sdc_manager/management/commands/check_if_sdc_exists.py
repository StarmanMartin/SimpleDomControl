from django.core.management.base import BaseCommand
from .init_add.add_controller_manager import AddControllerManager


class Command(BaseCommand):
    help = 'Checks if a SDC controller exists'

    def add_arguments(self, parser):
        parser.add_argument('controller_name', type=str, help='The name of the controller as snake_case')



    def handle(self, *args, **options):
        c_name_sc = options['controller_name']
        if AddControllerManager.check_controller_name(c_name_sc):
            self.stdout.write(self.style.ERROR("TRUE"))
        else:
            self.stdout.write(self.style.SUCCESS("FALSE"))
