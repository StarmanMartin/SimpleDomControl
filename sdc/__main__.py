import os
import shutil
import stat
import subprocess
from tempfile import mktemp

import click

@click.group()
def cli():
    pass


@cli.command(help="Creates a  new Project in a Subdirectory.")
@click.option("--name", prompt="Project name", help="Name of your new project.")
def new(name):
    tp = mktemp()
    targetdir = os.path.join(os.getcwd(), name)
    wkdir = os.path.join(tp, 'sdc')
    click.echo(wkdir)
    os.makedirs(wkdir)
    init_src = os.path.join(os.path.dirname(__file__), 'init.sh')
    init_des = os.path.join(wkdir, 'init.sh')
    shutil.copyfile(init_src, init_des)
    st = os.stat(init_des)
    os.chmod(init_des, st.st_mode | stat.S_IEXEC)

    my_env = os.environ.copy()
    my_env["PROJECT_NAME"] = name

    session = subprocess.Popen(['sh', './init.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wkdir, env=my_env)
    stdout, stderr = session.communicate()
    click.echo(stdout)
    os.remove(init_des)

    shutil.move(wkdir, targetdir)

if __name__ == '__main__':
    cli()