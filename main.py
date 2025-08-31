"""
Django Project Assistant - A GUI tool to automate Django project setup.
"""

import ctypes
import platform
import sys
import threading
import time
import webbrowser
from os import path
from pathlib import Path
from tkinter import PhotoImage, filedialog, ttk
import subprocess
import os
import signal
import re
import tkinter as tk

# Conditionally import pywinstyles for Windows-specific theming.
try:
    import pywinstyles
    PYWINSTYLES_AVAILABLE = True
except ImportError:
    PYWINSTYLES_AVAILABLE = False

import config_manager
import project_logic
import custom_dialogs

__version__ = "1.0.0"


class DjangoAssistantApp:
    """The main application class that orchestrates the GUI and business logic."""
    def __init__(self, root):
        self.root = root
        self.cfg = config_manager.load_config()
        self.server_process = {"proc": None}
        self._setup_window()
        self._init_vars()
        self._create_widgets()
        self._populate_python_versions_from_cache()


    def _setup_window(self):
        """Configures the main Tkinter window properties."""
        self.root.title(f"Django Project Assistant - v{__version__}")
        base_path = path.dirname(__file__)
        app_icon = PhotoImage(file=path.join(base_path, "imgs", "django-icon.png"))
        self.loading_icon = PhotoImage(file=path.join(base_path, "imgs", "django-loading.png"))
        self.root.iconphoto(True, app_icon)
        window_width, window_height = 960, 720
        self.root.minsize(window_width, window_height)

        # Center the window on screen (Windows-specific for accuracy).
        if platform.system() == "Windows":
            try:
                SPI_GETWORKAREA = 0x0030
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
                work_width, work_height = rect.right - rect.left, rect.bottom - rect.top
                x, y = rect.left + (work_width - window_width) // 2, rect.top + (work_height - window_height) // 2
                self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            except Exception:
                self.root.geometry(f"{window_width}x{window_height}")
        else:
            self.root.geometry(f"{window_width}x{window_height}")

        self.root.tk.call('source', path.join(base_path, "themes", "forest-dark.tcl"))
        ttk.Style().theme_use('forest-dark')
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)


    def _init_vars(self):
        """Initializes all Tkinter variables and application state variables."""
        self.project_name_var = tk.StringVar()
        self.project_path_var = tk.StringVar(value=self.cfg.get("last_project_path", ""))
        self.python_version_var = tk.StringVar()
        self.venv_path_var = tk.StringVar(value=self.cfg.get("last_venv_path", ""))
        self.open_browser_var = tk.BooleanVar(value=self.cfg.get("remember_open_browser", True))
        self.custom_user_var = tk.BooleanVar(value=self.cfg.get("remember_custom_user", False))
        self.template_collection_var = tk.StringVar()
        self.create_superuser_var = tk.BooleanVar(value=self.cfg.get("remember_create_superuser", False))
        self.pkg_vars, self.ext_vars = {}, {}
        self.active_project_path, self.active_venv_python = None, None
        

    def _create_widgets(self):
        """Builds the entire GUI by calling helper methods for each section."""
        self.main_frame = ttk.Frame(self.root, padding=12)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Display a temporary loading label while the title bar theme is applied.
        loading_label = ttk.Label(self.root, text="Loading, please wait...", image=self.loading_icon, compound="top")
        loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.root.update_idletasks()
        self._apply_titlebar_theme()
        loading_label.destroy()
        
        self._create_project_frame(self.main_frame)
        self._create_venv_frame(self.main_frame)
        self._create_web_framework_frame(self.main_frame)
        self._create_other_options_frame(self.main_frame)
        self._create_console_output(self.main_frame)
        self._create_action_buttons(self.main_frame)
        
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(4, weight=1)


    def _apply_titlebar_theme(self):
        """Applies dark theme to the title bar on Windows, if available."""
        if PYWINSTYLES_AVAILABLE and platform.system() == "Windows":
            try:
                version = sys.getwindowsversion()
                if version.major == 10 and version.build >= 22000:
                    pywinstyles.change_header_color(self.root, "#313131")
                elif version.major == 10:
                    pywinstyles.apply_style(self.root, "dark")
                    self.root.wm_attributes("-alpha", 0.99)
                    self.root.wm_attributes("-alpha", 1.0)
            except Exception:
                pass


    def _toggle_widgets_state(self, parent_widget, new_state='disabled'):
        """
        Recursively disables or enables all interactive widgets.
        'disabled' sets Entries to readonly to keep text visible.
        'normal' restores their normal interactive state.
        """
        for child in parent_widget.winfo_children():
            widget_class = child.winfo_class()
            if widget_class in ('TButton', 'TCheckbutton'):
                # Do not disable the "Stop Server" button when it's active.
                if child == getattr(self, 'btn_start', None) and child['text'] == "Stop Server":
                    continue
                child.configure(state=new_state)
            elif widget_class in ('TEntry', 'TCombobox'):
                if new_state == 'disabled':
                    child.configure(state='readonly')
                else:
                    final_state = 'normal' if widget_class == 'TEntry' else 'readonly'
                    child.configure(state=final_state)
            if child.winfo_children():
                self._toggle_widgets_state(child, new_state)


    def _scan_for_template_collections(self):
        """Scans the 'templates' directory for available template collections."""
        try:
            templates_dir = Path(path.dirname(__file__)) / "html_templates"
            if not templates_dir.is_dir():
                self._append_to_console("Warning: 'templates' directory not found.")
                return []
            return sorted([d.name for d in templates_dir.iterdir() if d.is_dir()])
        except Exception as e:
            self._append_to_console(f"Error scanning templates: {e}")
            return []


    # --- Widget Creation Sections ---
    def _create_project_frame(self, parent):
        lf = ttk.LabelFrame(parent, text="Project")
        lf.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="Project name:").grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ttk.Entry(lf, textvariable=self.project_name_var).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ttk.Label(lf, text="Projects Parent Folder:").grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        ttk.Entry(lf, textvariable=self.project_path_var).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(lf, text="Browse...", command=lambda: self._browse_dir("last_project_path", self.project_path_var)).grid(row=1, column=2, sticky="ew", padx=6, pady=6)
    
    
    def _create_venv_frame(self, parent):
        lf = ttk.LabelFrame(parent, text="Virtual Environment")
        lf.grid(row=1, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="Python version:").grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.combo_python = ttk.Combobox(lf, textvariable=self.python_version_var, state="readonly")
        self.combo_python.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(lf, text="Refresh versions", command=self._start_refresh_python_versions).grid(row=0, column=2, sticky="ew", padx=6, pady=6)
        ttk.Label(lf, text="Venvs Parent Folder:").grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        ttk.Entry(lf, textvariable=self.venv_path_var).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(lf, text="Browse...", command=lambda: self._browse_dir("last_venv_path", self.venv_path_var)).grid(row=1, column=2, sticky="ew", padx=6, pady=6)
        ttk.Label(lf, text="Django packages:").grid(row=2, column=0, sticky="nw", padx=6, pady=6)
        pkgs_frame = ttk.Frame(lf)
        pkgs_frame.grid(row=2, column=1, columnspan=2, sticky="nw", padx=2, pady=6)
        for i, pkg in enumerate(self.cfg.get("django_packages", [])):
            name, var = pkg['name'], tk.BooleanVar(value=pkg.get("selected", False))
            ttk.Checkbutton(pkgs_frame, text=name, variable=var).grid(row=0, column=i, sticky="w", pady=2)
            self.pkg_vars[name] = var
    
    
    def _create_web_framework_frame(self, parent):
        lf = ttk.LabelFrame(parent, text="Web Framework")
        lf.grid(row=2, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        lf.columnconfigure(1, weight=1)
        ttk.Label(lf, text="Template Collection:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        template_names = self._scan_for_template_collections()
        combo_templates = ttk.Combobox(lf, textvariable=self.template_collection_var, values=template_names, state="readonly")
        if template_names: combo_templates.current(0)
        else:
            combo_templates.set("No templates found")
            combo_templates.config(state="disabled")
        combo_templates.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Label(lf, text="External libraries:").grid(row=1, column=0, sticky="nw", padx=6, pady=6)
        libs_frame = ttk.Frame(lf)
        libs_frame.grid(row=1, column=1, columnspan=2, sticky="nw", padx=2, pady=6)
        for i, lib in enumerate(self.cfg.get("external_libraries", [])):
            name, var = lib.get("name"), tk.BooleanVar(value=lib.get("selected", False))
            ttk.Checkbutton(libs_frame, text=name, variable=var).grid(row=0, column=i, sticky="w", pady=0)
            self.ext_vars[name] = var
    
    
    def _create_other_options_frame(self, parent):
        lf = ttk.LabelFrame(parent, text="Other options")
        lf.grid(row=3, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        def _toggle_superuser_option():
            if self.custom_user_var.get(): self.chk_superuser.config(state='normal')
            else:
                self.chk_superuser.config(state='disabled')
                self.create_superuser_var.set(False)
        chk_custom_user = ttk.Checkbutton(lf, text="Use custom user model", variable=self.custom_user_var, command=_toggle_superuser_option)
        chk_custom_user.grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.chk_superuser = ttk.Checkbutton(lf, text="Create superuser", variable=self.create_superuser_var)
        self.chk_superuser.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Checkbutton(lf, text="Open browser on start", variable=self.open_browser_var).grid(row=0, column=2, sticky="w", padx=6, pady=6)
        _toggle_superuser_option()
    
    
    def _create_console_output(self, parent):
        treeFrame = ttk.Frame(parent)
        treeFrame.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=6, pady=10)
        treeScroll = ttk.Scrollbar(treeFrame)
        treeScroll.pack(side="right", fill="y")
        self.console_tree = ttk.Treeview(treeFrame, show="headings", columns=("message",), selectmode="none", yscrollcommand=treeScroll.set)
        self.console_tree.pack(expand=True, fill="both")
        self.console_tree.heading("message", text=" Console Output:", anchor="w")
        treeScroll.config(command=self.console_tree.yview)
    
    
    def _create_action_buttons(self, parent):
        self.btn_start = ttk.Button(parent, text="Create Project", command=self._on_start, style="Accent.TButton")
        self.btn_start.grid(row=5, column=1, sticky="ew", padx=6, pady=10)
        ttk.Button(parent, text="Exit", command=self.root.destroy).grid(row=5, column=2, sticky="ew", padx=6, pady=10)


    # --- Core Application Logic ---
    def _append_to_console(self, text):
        if not text: return
        for line in text.splitlines():
            if line.strip(): self.console_tree.insert("", "end", values=(line.strip(),))
        self.console_tree.yview_moveto(1.0)
    
    
    def _browse_dir(self, config_key, tk_var):
        dir_path = filedialog.askdirectory()
        if dir_path: tk_var.set(dir_path)


    def _on_start(self):
        """Handles the 'Create Project' button click event."""
        if not all([self.project_name_var.get(), self.project_path_var.get(), self.venv_path_var.get(), self.python_version_var.get()]):
            custom_dialogs.showwarning(self.root, "Validation", "Please fill in all project and virtual environment fields.")
            return
        project_name = self.project_name_var.get().strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', project_name):
            custom_dialogs.showwarning(self.root, "Invalid Project Name", "Project name must contain only letters, numbers, and underscores.")
            return
        if not self.template_collection_var.get() or self.template_collection_var.get() == "No templates found":
            custom_dialogs.showwarning(self.root, "Validation", "No template collection selected or found.")
            return

        superuser_credentials = None
        if self.create_superuser_var.get():
            superuser_credentials = custom_dialogs.asksuperuser(self.root, "Create Superuser")
            if not superuser_credentials:
                custom_dialogs.showinfo(self.root, "Cancelled", "Project creation cancelled by user.")
                return

        self._save_ui_choices_to_config()
        data = { "project_name": project_name.lower(), "project_path": self.project_path_var.get().strip(), "python_version": self.python_version_var.get().split(" ")[0], "venv_path": self.venv_path_var.get().strip(), "open_browser": self.open_browser_var.get(), "custom_user_model": self.custom_user_var.get(), "template_collection": self.template_collection_var.get(), "superuser_credentials": superuser_credentials, "selected_packages": [p for p, v in self.pkg_vars.items() if v.get()], "all_packages_config": self.cfg["django_packages"], "selected_libraries": [lib for lib in self.cfg["external_libraries"] if lib.get("selected")] }
        
        self.console_tree.delete(*self.console_tree.get_children())
        self._toggle_widgets_state(self.main_frame, 'disabled')
        worker = threading.Thread(target=self._project_worker_thread, args=(data,), daemon=True)
        worker.start()


    def _save_ui_choices_to_config(self):
        """Saves the current state of all UI choices to the config file."""
        self.cfg["last_project_path"], self.cfg["last_venv_path"] = self.project_path_var.get(), self.venv_path_var.get()
        self.cfg["remember_custom_user"], self.cfg["remember_open_browser"] = self.custom_user_var.get(), self.open_browser_var.get()
        self.cfg["remember_create_superuser"] = self.create_superuser_var.get()
        for pkg in self.cfg["django_packages"]:
            if pkg["name"] in self.pkg_vars: pkg["selected"] = self.pkg_vars[pkg["name"]].get()
        for lib in self.cfg["external_libraries"]:
            if lib["name"] in self.ext_vars: lib["selected"] = self.ext_vars[lib["name"]].get()
        config_manager.save_config(self.cfg)


    def _project_worker_thread(self, data):
        """
        The main worker function that runs in a background thread.
        Orchestrates all project creation steps.
        """
        start_time = time.time()
        def status_callback(msg): self.root.after(0, self._append_to_console, msg)
        def log_callback(log_text): self.root.after(0, self._append_to_console, log_text)

        try:
            status_callback("Validating paths...")
            self.active_project_path = Path(data["project_path"]) / data["project_name"]
            venv_path = Path(data["venv_path"]) / data["project_name"]
            if self.active_project_path.is_dir() and any(self.active_project_path.iterdir()):
                raise RuntimeError(f"Project directory '{self.active_project_path.name}' already exists and is not empty.")
            if venv_path.is_dir() and any(venv_path.iterdir()):
                raise RuntimeError(f"Virtual environment directory '{venv_path.name}' already exists and is not empty.")
            
            status_callback("Starting project creation...")
            if not project_logic.check_uv_available():
                # Provide helpful link if uv is not found.
                raise RuntimeError("'uv' is not found in PATH. Please install it from https://astral.sh/uv")
            
            self.active_project_path.mkdir(parents=True, exist_ok=True)
            status_callback(f"Project folder ready: {self.active_project_path}")
            venv_path.parent.mkdir(parents=True, exist_ok=True)
            if not project_logic.create_venv_with_uv(venv_path, data["python_version"], status_callback, log_callback):
                raise RuntimeError("Failed to create virtual environment.")
            self.active_venv_python = project_logic.find_venv_python(venv_path)
            if not self.active_venv_python: raise RuntimeError("Could not find Python executable in venv.")
            packages_to_install = ["django"] + data["selected_packages"]
            if not project_logic.pip_install_packages(str(self.active_venv_python), packages_to_install, status_callback, log_callback):
                raise RuntimeError("Failed to install packages.")
            if not project_logic.django_startproject(str(self.active_venv_python), data["project_name"], self.active_project_path, status_callback, log_callback):
                raise RuntimeError("Django startproject failed.")
            project_logic.django_manage_command(str(self.active_venv_python), self.active_project_path, ["startapp", "core"], status_callback, log_callback)
            project_logic.create_core_app_files(self.active_project_path)
            project_logic.patch_project_urls(self.active_project_path, data["project_name"])
            if data["custom_user_model"]:
                project_logic.django_manage_command(str(self.active_venv_python), self.active_project_path, ["startapp", "accounts"], status_callback, log_callback)
                project_logic.create_accounts_user_model(self.active_project_path / "accounts")
            status_callback("Patching settings.py...")
            settings_path = self.active_project_path / data["project_name"] / "settings.py"
            selected_pkg_configs = [p for p in data["all_packages_config"] if p["name"] in data["selected_packages"]]
            project_logic.patch_settings(settings_path, selected_pkg_configs, data["custom_user_model"])
            status_callback("Creating templates...")
            project_logic.create_templates(data["template_collection"].lower(), self.active_project_path, data["custom_user_model"])
            if data["selected_libraries"]:
                status_callback("Injecting external libraries into base.html...")
                project_logic.inject_external_libraries(self.active_project_path, data["selected_libraries"])
            status_callback("Running migrations...")
            project_logic.django_manage_command(str(self.active_venv_python), self.active_project_path, ["makemigrations"], status_callback, log_callback)
            project_logic.django_manage_command(str(self.active_venv_python), self.active_project_path, ["migrate"], status_callback, log_callback)
            
            if data.get("superuser_credentials"):
                creds = data["superuser_credentials"]
                project_logic.django_create_superuser(str(self.active_venv_python), self.active_project_path, creds["email"], creds["password"], status_callback, log_callback)
            
            total_time = time.time() - start_time
            final_msg = f"Project '{data['project_name']}' created at: {self.active_project_path}\nTotal time: {total_time:.2f} seconds."
            status_callback(f"Done! Total time: {total_time:.2f} seconds")
            
            if data["open_browser"]:
                self.root.after(0, self._start_dev_server)
                self.root.after(100, lambda: custom_dialogs.showinfo(self.root, "Success", final_msg + "\n\nServer is starting up."))
            else:
                self.root.after(0, lambda: custom_dialogs.showinfo(self.root, "Success", final_msg))
                self.root.after(0, lambda: self._toggle_widgets_state(self.main_frame, 'normal'))
        except Exception as e:
            self.root.after(0, lambda: custom_dialogs.showerror(self.root, "Process Stopped", str(e)))
            status_callback(f"Process aborted: {e}")
            self.root.after(0, lambda: self._toggle_widgets_state(self.main_frame, 'normal'))


    def _start_dev_server(self):
        self._append_to_console("Starting development server...")
        try:
            popen_kwargs = {'cwd': str(self.active_project_path), 'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 'text': True}
            if platform.system() == "Windows":
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            else:
                popen_kwargs['start_new_session'] = True
            proc = subprocess.Popen([str(self.active_venv_python), "manage.py", "runserver"], **popen_kwargs)
            self.server_process["proc"] = proc
            threading.Thread(target=self._stream_server_output, daemon=True).start()
            self.root.after(0, self._update_ui_for_server_running)
            time.sleep(3) 
            webbrowser.open("http://127.0.0.1:8000")
        except Exception as e:
            custom_dialogs.showerror(self.root, "Server Error", f"Failed to start dev server: {e}")
            self.root.after(0, lambda: self._toggle_widgets_state(self.main_frame, 'normal'))
    
    
    def _stream_server_output(self):
        proc = self.server_process.get("proc")
        if not proc or not proc.stdout: return
        for line in iter(proc.stdout.readline, ''): self.root.after(0, self._append_to_console, line)
        self.root.after(0, self._update_ui_for_server_stopped)
    
    
    def _on_stop_server(self):
        proc = self.server_process.get("proc")
        if proc and proc.poll() is None:
            self._append_to_console("Stopping development server...")
            try:
                if platform.system() == "Windows": subprocess.run(f"taskkill /PID {proc.pid} /F /T", check=False, capture_output=True)
                else: os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception as e: self._append_to_console(f"Error while stopping server: {e}")
    
    
    def _update_ui_for_server_running(self):
        self._toggle_widgets_state(self.main_frame, 'disabled')
        self.btn_start.config(text="Stop Server", command=self._on_stop_server, style="TButton")
        self.btn_start.config(state='normal')
    
    
    def _update_ui_for_server_stopped(self):
        self._append_to_console("Server stopped.")
        self.server_process["proc"] = None
        self.btn_start.config(text="Create Project", command=self._on_start, style="Accent.TButton")
        self._toggle_widgets_state(self.main_frame, 'normal')
    
    
    def _populate_python_versions_from_cache(self, first_call=True):
        self.combo_python['values'] = []
        cached = self.cfg.get("cached_python_versions", [])
        displays = [f"{v}{' (Installed)' if project_logic.is_python_version_installed(v) else ''}" for v in cached]
        self.combo_python['values'] = displays
        if displays: self.combo_python.current(0)
        else:
            self.combo_python.set("")
            self.combo_python['state'] = 'disabled'
            self._append_to_console("No cached Python versions. Press 'Refresh versions' to fetch from 'uv'.")
        if first_call and displays: self._append_to_console("Using cached Python versions. Press 'Refresh versions' to fetch new ones.")
    
    
    def _start_refresh_python_versions(self):
        self._toggle_widgets_state(self.main_frame, 'disabled')
        self._append_to_console("Refreshing Python versions via 'uv'...")
        thread = threading.Thread(target=self._refresh_worker, daemon=True)
        thread.start()
    
    
    def _refresh_worker(self):
        try:
            versions = project_logic.get_python_versions_via_uv_blocking()
            self.cfg["cached_python_versions"] = versions
            config_manager.save_config(self.cfg)
            self.root.after(0, self._finish_refresh, True)
        except FileNotFoundError:
            message = "'uv' not found in PATH.\nPlease install it from https://astral.sh/uv"
            self.root.after(0, lambda: custom_dialogs.showerror(self.root, "uv not found", message))
            self.root.after(0, self._finish_refresh, False)
    
    
    def _finish_refresh(self, success):
        if success:
            self._populate_python_versions_from_cache(first_call=False)
            self._append_to_console("Python versions refreshed and cached.")
        else:
            self._append_to_console("Refresh failed. 'uv' command might not be available.")
        self.root.after(0, lambda: self._toggle_widgets_state(self.main_frame, 'normal'))
    
    
    def _on_close(self):
        self._save_ui_choices_to_config()
        proc = self.server_process.get("proc")
        if proc and proc.poll() is None: self._on_stop_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DjangoAssistantApp(root)
    root.mainloop()
