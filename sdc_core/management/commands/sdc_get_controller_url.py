from django.core.management.base import BaseCommand
from .init_add.add_controller_manager import AddControllerManager


class Command(BaseCommand):
    help = 'Get the django url path of a SDC controller if it exists'

    def add_arguments(self, parser):
        parser.add_argument('controller_name', type=str, help='The name of the controller as snake_case')



    def handle(self, *args, **options):
        c_name_sc = options['controller_name']
        return AddControllerManager.get_url(c_name_sc)
