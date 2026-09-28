"""
Command line tool of SDC: ``sdc new --name <project>`` creates a new Django project with SDC.

Installed as the console script ``sdc`` (also ``python -m sdc``).
"""
import os
import re
import shutil
import subprocess
import sys
import venv
from importlib import metadata
from pathlib import Path

import click


def _default_package():
    """The simpledomcontrol version of this installation, so the new project uses the same one."""
    try:
        return f"simpledomcontrol=={metadata.version('SimpleDomControl')}"
    except metadata.PackageNotFoundError:
        return "simpledomcontrol"


def _run(cmd, cwd):
    click.echo(f"$ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise click.ClickException(f"Command failed with exit code {result.returncode}: {' '.join(map(str, cmd))}")


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _add_sdc_core(settings_path: Path):
    text = settings_path.read_text()
    if "'sdc_core'" in text or '"sdc_core"' in text:
        return
    new_text, count = re.subn(r"INSTALLED_APPS\s*=\s*\[", "INSTALLED_APPS = [\n    'sdc_core',", text, count=1)
    if count != 1:
        raise click.ClickException(f"INSTALLED_APPS not found in {settings_path}")
    settings_path.write_text(new_text)


@click.group()
def cli():
    pass


@cli.command(help="Creates a new SDC project in the subdirectory NAME of the current directory.")
@click.option("--name", prompt="Project name", help="Name of the new project (a valid Python identifier).")
@click.option("--package", default=None,
              help="pip requirement used to install SDC into the project's virtualenv "
                   "(default: the installed version, e.g. simpledomcontrol==0.159.0).")
@click.option("--skip-npm", is_flag=True, help="Do not run 'npm install'.")
def new(name, package, skip_npm):
    if not name.isidentifier():
        raise click.BadParameter("The project name must be a valid Python identifier.", param_hint="--name")
    target = Path.cwd() / name
    if target.exists() and any(target.iterdir()):
        raise click.ClickException(f"{target} already exists and is not empty.")
    target.mkdir(parents=True, exist_ok=True)

    # The virtualenv is created in its final location; moving a virtualenv breaks it.
    venv_dir = target / "venv"
    click.echo(f"Creating virtualenv in {venv_dir}")
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = _venv_python(venv_dir)

    _run([python, "-m", "pip", "install", "--upgrade", "pip"], target)
    _run([python, "-m", "pip", "install", package or _default_package()], target)
    _run([python, "-m", "django", "startproject", name, "."], target)
    _add_sdc_core(target / name / "settings.py")
    _run([python, "manage.py", "sdc_init", "-y"], target)

    if skip_npm:
        click.echo("Skipped 'npm install'.")
    elif shutil.which("npm"):
        _run(["npm", "install"], target)
    else:
        click.echo("npm was not found; run 'npm install' in the project directory to install the client.")

    click.echo(f"\nDone. Next steps:\n  cd {name}\n  source venv/bin/activate\n"
               f"  python manage.py migrate\n  npm run develop   # in a second terminal: python manage.py runserver")


if __name__ == '__main__':
    cli()
