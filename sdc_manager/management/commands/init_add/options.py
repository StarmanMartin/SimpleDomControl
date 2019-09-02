import os

MAIN_APP_NAME = "sdc_core"
SEP = '    '
PROJECT_ROOT = os.getcwd()
SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
REPLACEMENTS = {"<!--§MAIN_APP§-->": MAIN_APP_NAME,"§MAIN_APP§": MAIN_APP_NAME}

class CMD_COLORS:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def as_error(cls, text):
        return "%s%s%s" % (cls.FAIL,text,cls.ENDC)

    @classmethod
    def as_warning(cls, text):
        return "%s%s%s" % (cls.WARNING,text,cls.ENDC) \

    @classmethod
    def as_important(cls, text):
        return "%s%s%s%s" % (cls.BOLD, cls.HEADER,text,cls.ENDC)
