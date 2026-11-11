import sys

from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from sdc_core.management.commands.init_add.add_model_manager import AddModelManager

from sdc_core.management.commands.init_add import options, settings_manager
from sdc_core.management.commands.sdc_update_links import make_model_link
from sdc_core.management.commands.utils import can_prompt, cli_select, missing_argument


class Command(BaseCommand):
    help = 'This function add a new SDC/Django model in your django project'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        manage_py_file_path = sys.argv[0] if len(sys.argv) > 0 else 'manage.py'
        self.sdc_settings = settings_manager.SettingsManager(manage_py_file_path)

    def add_arguments(self, parser):
        all_apps = self.sdc_settings.get_apps()
        parser.add_argument('-m', '--model_name', type=str, help='The name of the new django model class')
        parser.add_argument('-a', '--app_name', type=str, help='The name of the django app: [%s]' % ', '.join(all_apps))

    def handle(self, *args, **ops):

        self.sdc_settings.check_settings()

        self.sdc_settings.find_and_set_project_name()
        self.sdc_settings.find_and_set_whitespace_sep()
        all_apps = self.sdc_settings.get_apps()


        app_name = ops.get('app_name')
        if app_name is None or not app_name in all_apps:
            app_name = cli_select("Select an django App:", all_apps, flag='-a/--app_name')
        model_name = ops.get('model_name')
        if model_name is None:
            if not can_prompt():
                raise missing_argument('-m/--model_name', 'model class name (CamelCase)')
            text = "Enter the name of the new Model class name (use CamelCase):"
            model_name = str(input(text))

        if model_name in [model.__name__ for model in apps.get_app_config(app_name).get_models()]:
            raise CommandError(f"The model {model_name} already exists in {app_name}", 1)
        if len(model_name) == 0:
            raise CommandError("The model name must not be empty", 1)

        add_sdc_core = AddModelManager(app_name, model_name)


        add_sdc_core.add_model()
        add_sdc_core.add_model_form()
        add_sdc_core.add_model_template()
        make_model_link(app_name, model_name)