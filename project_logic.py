"""
Contains all the core business logic for creating a Django project.
This module is GUI-agnostic and can be used independently.
"""

import ast
import platform
import re
import shutil
import subprocess
from pathlib import Path
import os


# --- Command Execution ---
def run_subprocess(cmd, cwd=None, env=None, capture_output=True, text=True):
    """
    A wrapper around subprocess.run to execute external commands.
    Returns:
        tuple: A (return_code, output_string) tuple.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=capture_output, text=text, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except Exception as e:
        return 1, str(e)


# --- Environment and Tooling Checks ---
def find_venv_python(venv_path: Path):
    """
    Locates the Python executable within a virtual environment path.
    Handles differences between Windows and POSIX systems.
    """
    if platform.system() == "Windows":
        py = venv_path / "Scripts" / "python.exe"
    else:
        py = venv_path / "bin" / "python"
    return py if py.exists() else None


def get_python_versions_via_uv_blocking():
    """
    Runs `uv python list` to find available Python versions on the system.
    Raises:
        FileNotFoundError: If 'uv' is not in the system's PATH.
    """
    try:
        proc = subprocess.run(["uv", "python", "list"], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise
    out = proc.stdout.strip()
    if not out:
        return []
    versions, seen = [], set()
    for line in out.splitlines():
        line = line.strip()
        if not line: continue
        m = re.search(r'\d+\.\d+(?:\.\d+)?', line)
        ver = m.group(0) if m else line
        if ver not in seen:
            versions.append(ver)
            seen.add(ver)
    return versions


_installed_cache = {}
def is_python_version_installed(ver):
    """
    A heuristic check to see if a Python version (e.g., '3.11') is installed.
    Caches results for performance.
    """
    mm = re.match(r'^(\d+)\.(\d+)', ver)
    if not mm: return False
    key = f"{mm.group(1)}.{mm.group(2)}"
    if key in _installed_cache: return _installed_cache[key]

    installed = False
    if platform.system() == "Windows" and shutil.which("py"):
        try:
            proc = subprocess.run(["py", f"-{key}", "--version"], capture_output=True, text=True, check=False)
            if key in (proc.stdout or proc.stderr or ""):
                installed = True
        except Exception:
            pass

    if not installed:
        candidates = [f"python{key}", f"python{key.replace('.','')}", f"python{mm.group(1)}", "python3", "python"]
        for exe in candidates:
            path = shutil.which(exe)
            if not path: continue
            try:
                proc = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
                if key in (proc.stdout or proc.stderr or ""):
                    installed = True
                    break
            except Exception:
                continue
    _installed_cache[key] = installed
    return installed


def check_uv_available():
    """Checks if the 'uv' command is available in the system's PATH."""
    return shutil.which("uv") is not None


# --- Project Creation Steps ---
def create_venv_with_uv(venv_path: Path, python_version: str, status_callback, log_callback):
    """Creates a virtual environment using 'uv venv'."""
    cmd = ["uv", "venv", str(venv_path), "--python", python_version]
    status_callback(f"Running: {' '.join(cmd)}")
    rc, out = run_subprocess(cmd)
    log_callback(out)
    return rc == 0


def pip_install_packages(venv_python: str, packages: list, status_callback, log_callback):
    """Installs Python packages into the venv using 'uv pip install'."""
    if not packages: return True
    cmd = ["uv", "pip", "install"] + packages + ["--python", venv_python]
    status_callback(f"pip installing: {' '.join(packages)}")
    rc, out = run_subprocess(cmd)
    log_callback(out)
    return rc == 0


def django_manage_command(venv_python: str, project_path: Path, args: list, status_callback, log_callback):
    """Runs a Django manage.py command within the project context."""
    cmd = [venv_python, "manage.py"] + args
    status_callback("Running: " + " ".join(cmd))
    rc, out = run_subprocess(cmd, cwd=str(project_path))
    log_callback(out)
    return rc, out


def django_startproject(venv_python: str, project_name: str, project_path: Path, status_callback, log_callback):
    """Runs the 'django-admin startproject' command."""
    status_callback("Creating Django project...")
    cmd = [venv_python, "-m", "django", "startproject", project_name, "."]
    rc, out = run_subprocess(cmd, cwd=str(project_path))
    log_callback(out)
    return rc == 0


def patch_settings(settings_path: Path, django_packages: list, custom_user_flag: bool):
    """
    Safely modifies the Django settings.py file using Python's AST module.
    It adds apps, middleware, and other settings.
    """
    txt = settings_path.read_text(encoding="utf-8")
    tree = ast.parse(txt)
    settings_dict = {"INSTALLED_APPS": [], "MIDDLEWARE": []}

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in settings_dict:
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    settings_dict[target.id] = [ast.literal_eval(el) for el in node.value.elts]

    other_settings_lines = []
    for pkg in django_packages:
        if pkg.get("apps"):
            apps_to_add = pkg["apps"] if isinstance(pkg["apps"], list) else [pkg["apps"]]
            for app in apps_to_add:
                if app and app not in settings_dict["INSTALLED_APPS"]: settings_dict["INSTALLED_APPS"].append(app)
        if pkg.get("middleware"):
            mw_to_add = pkg["middleware"] if isinstance(pkg["middleware"], list) else [pkg["middleware"]]
            for mw in mw_to_add:
                if mw and mw not in settings_dict["MIDDLEWARE"]:
                    if "CorsMiddleware" in mw: settings_dict["MIDDLEWARE"].insert(0, mw)
                    else: settings_dict["MIDDLEWARE"].append(mw)
        if pkg.get("other_settings"): other_settings_lines.append(pkg["other_settings"])

    settings_dict["INSTALLED_APPS"].append("core")
    if custom_user_flag: settings_dict["INSTALLED_APPS"].append("accounts")

    def format_list(name, items):
        formatted = ",\n    ".join([f"'{i}'" for i in items])
        return f"{name} = [\n    {formatted},\n]\n"

    new_txt = txt
    for name, items in settings_dict.items():
        if items:
            block = format_list(name, items)
            new_txt = re.sub(rf"{name}\s*=\s*\[.*?\]", block.strip(), new_txt, flags=re.DOTALL)
    
    if "import os" not in new_txt.splitlines()[0:10]: new_txt = "import os\n" + new_txt
    if "TEMPLATES" in new_txt: new_txt = re.sub(r"'DIRS'\s*:\s*\[\s*\]", r"'DIRS': [os.path.join(BASE_DIR, 'html_templates')]", new_txt)
    if custom_user_flag and "AUTH_USER_MODEL" not in new_txt: new_txt += "\nAUTH_USER_MODEL = 'accounts.User'\n"
    if other_settings_lines: new_txt += "\n\n# Extra settings from packages\n" + "\n".join(other_settings_lines)

    if new_txt != txt:
        settings_path.write_text(new_txt, encoding="utf-8")
        return True
    return False


def create_accounts_user_model(accounts_dir: Path):
    """Creates files for a custom user model by copying from code templates."""
    accounts_dir.mkdir(parents=True, exist_ok=True)
    source_templates_dir = Path("code_templates") / "accounts"
    template_files = { "models.py.template": "models.py", "admin.py.template": "admin.py", "apps.py.template": "apps.py" }

    for template_name, final_name in template_files.items():
        source_path, dest_path = source_templates_dir / template_name, accounts_dir / final_name
        if not source_path.exists():
            print(f"Warning: Code template not found at {source_path}")
            continue
        content = source_path.read_text(encoding="utf-8")
        dest_path.write_text(content, encoding="utf-8")


def create_core_app_files(project_path: Path):
    """Creates minimal view, URL, and config for the 'core' app."""
    core_dir = project_path / "core"
    (core_dir / "views.py").write_text("from django.shortcuts import render\n\ndef index(request):\n    return render(request, 'core/index.html')\n", encoding="utf-8")
    (core_dir / "urls.py").write_text("from django.urls import path\nfrom . import views\n\nurlpatterns = [path('', views.index, name='index')]\n", encoding="utf-8")
    (core_dir / "apps.py").write_text("from django.apps import AppConfig\n\nclass CoreConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'core'\n", encoding="utf-8")


def patch_project_urls(project_path: Path, project_name: str):
    """Adds `include('core.urls')` to the main urls.py."""
    urls_path = project_path / project_name / "urls.py"
    if not urls_path.exists(): return False
    txt = urls_path.read_text(encoding="utf-8")
    if "include('core.urls')" in txt: return True
    txt = txt.replace("from django.urls import path", "from django.urls import path, include")
    m = re.search(r'urlpatterns\s*=\s*\[', txt)
    if m:
        idx = txt.find('[', m.start())
        ins = "\n    path('', include('core.urls')),"
        txt = txt[:idx+1] + ins + txt[idx+1:]
        urls_path.write_text(txt, encoding="utf-8")
        return True
    return False


def create_templates(template_collection: str, project_path: Path, custom_user_flag: bool):
    """Copies template files from a source directory based on the selected collection."""
    base_templates = Path("html_templates") / template_collection
    if not base_templates.exists():
        raise FileNotFoundError(f"Template collection '{template_collection}' not found.")
    
    src_core = base_templates / "core"
    dst_core = project_path / "core" / "templates" / "core"
    if src_core.exists():
        dst_core.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_core, dst_core, dirs_exist_ok=True)
    
    if custom_user_flag:
        src_accounts = base_templates / "accounts"
        dst_accounts = project_path / "accounts" / "templates" / "accounts"
        if src_accounts.exists():
            dst_accounts.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_accounts, dst_accounts, dirs_exist_ok=True)


def inject_external_libraries(project_path: Path, selected_libs: list):
    """Injects CSS links and JS scripts into the base.html template using placeholders."""
    base_html_path = project_path / "core" / "templates" / "core" / "base.html"
    if not base_html_path.exists(): return
    content = base_html_path.read_text(encoding="utf-8")
    head_injection, body_injection = [], []

    for lib in selected_libs:
        for link_url in lib.get("head_links", []):
            head_injection.append(f'  <link rel="stylesheet" href="{link_url}">')
        for script_url in lib.get("body_scripts", []):
            body_injection.append(f'  <script src="{script_url}"></script>')

    content = content.replace("<!-- DJANGO_ASSISTANT_HEAD_LINKS -->", "\n".join(head_injection))
    content = content.replace("<!-- DJANGO_ASSISTANT_BODY_SCRIPTS -->", "\n".join(body_injection))
    base_html_path.write_text(content, encoding="utf-8")


def django_create_superuser(venv_python: str, project_path: Path, email: str, password: str, status_callback, log_callback):
    """
    Creates a superuser non-interactively using environment variables.
    This is the method recommended by Django for automated creation.
    """
    status_callback("Creating superuser...")
    env = os.environ.copy()
    env["DJANGO_SUPERUSER_EMAIL"] = email
    env["DJANGO_SUPERUSER_PASSWORD"] = password
    cmd = [venv_python, "manage.py", "createsuperuser", "--no-input"]
    rc, out = run_subprocess(cmd, cwd=str(project_path), env=env)
    log_callback(out)

    if "Superuser created successfully" in out:
        status_callback("Superuser created successfully.")
        return True
    else:
        status_callback("Warning: Superuser creation may have failed. Check console log.")
        return False
