import os.path

from django.apps import AppConfig


class SdcCoreConfig(AppConfig):
    name = 'sdc_core'
    def ready(self):
        import sys
        from django.conf import settings

        if settings.DEBUG and os.path.exists('./Assets'):
            env_vars = {}
            if os.path.exists('./Assets/.sdc_env'):
                with open('./Assets/.sdc_env', 'r', encoding='utf8') as f_read:
                    for line in f_read:
                        if not line.startswith('#') and line.strip():
                            key, value = line.strip().split('=', 1)
                            env_vars[key] = value
            env_vars['JSON_DATA_DUMP'] = env_vars.get('JSON_DATA_DUMP', f'"Assets/tests/dumps/test_data_dump.json"')
            env_vars['COPY_DEFAULT_DB'] = env_vars.get('COPY_DEFAULT_DB', "1 # 0 for false or 1 for true")
            env_vars['DB_PYTHON_SCRIPT'] = env_vars.get('DB_PYTHON_SCRIPT', "0 # Add path to pythonscript to prepare DB")
            with open('./Assets/.sdc_env', 'w+', encoding='utf8') as f:
                f.write('\n'.join([f'{x}={y}' for (x,y) in env_vars.items()]))

            with open('./Assets/.sdc_python_env', 'w+', encoding='utf8') as f:
                f.write(f'PYTHON="{sys.executable}"')
