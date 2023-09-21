import os

MAIN_APP_NAME = "Undefined"
SEP = '    '
PROJECT = 'Undefined'
PROJECT_ROOT = os.getcwd()
SCRIPT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../../'))
REPLACEMENTS = {"<!--§MAIN_APP§-->": MAIN_APP_NAME,"§MAIN_APP§": MAIN_APP_NAME,
                "<!--§PROJECT§-->": PROJECT,"§PROJECT§": PROJECT}

def setPROJECT(project):
    global PROJECT, MAIN_APP_NAME
    MAIN_APP_NAME = project
    PROJECT = project
    REPLACEMENTS['<!--§PROJECT§-->'] = project
    REPLACEMENTS['§PROJECT§'] = project
    REPLACEMENTS['<!--§MAIN_APP§-->'] = project
    REPLACEMENTS['§MAIN_APP§'] = project

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
