import tkinter as tk
from tkinter import ttk
import platform
import sys

# Conditionally import pywinstyles for Windows-specific theming.
try:
    import pywinstyles
    PYWINSTYLES_AVAILABLE = True
except ImportError:
    PYWINSTYLES_AVAILABLE = False


class BaseDialog(tk.Toplevel):
    """
    A base class for custom modal dialogs that are themed and cross-platform.
    """
    def __init__(self, parent, title="", message=""):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.withdraw()
        self.title(title)
        self.resizable(False, False)

        try:
            self.iconphoto(True, parent.iconphoto())
        except tk.TclError:
            pass 
        
        self.main_frame = ttk.Frame(self, padding=(20, 20, 20, 10))
        self.main_frame.pack(expand=True, fill="both")
        
        if message:
            msg_label = ttk.Label(self.main_frame, text=message, wraplength=400, justify="left")
            msg_label.pack(padx=10, pady=(0, 20), anchor="w")

        self.button_frame = ttk.Frame(self.main_frame)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(self.parent)


    def _apply_titlebar_theme(self):
        if PYWINSTYLES_AVAILABLE and platform.system() == "Windows":
            try:
                version = sys.getwindowsversion()
                if version.major == 10 and version.build >= 22000:
                    pywinstyles.change_header_color(self, "#313131")
                elif version.major == 10:
                    pywinstyles.apply_style(self, "dark")
            except Exception:
                pass


    def _center_window(self):
        """
        Centers the dialog relative to its parent window using the requested size,
        which works reliably across all platforms, including scaled Linux desktops.
        """
        # Force Tkinter to calculate the required size for all widgets.
        self.update_idletasks()

        # Get the CALCULATED required size, not the ACTUAL size (which might be 1x1).
        dialog_w = self.winfo_reqwidth()
        dialog_h = self.winfo_reqheight()

        # Get the parent window's position and size.
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()

        # Calculate the centered position relative to the parent.
        x = parent_x + (parent_w // 2) - (dialog_w // 2)
        y = parent_y + (parent_h // 2) - (dialog_h // 2)
        
        self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")


    def _finalize_and_show(self):
        """
        Performs final setup and displays the window, ensuring correct centering.
        """
        self._apply_titlebar_theme()
        self.grab_set()
        self._center_window() # Center just before showing
        self.deiconify()


    def _on_ok(self, event=None):
        self.result = True
        self.destroy()


    def _on_yes(self, event=None):
        self.result = True
        self.destroy()


    def _on_no(self, event=None):
        self.result = False
        self.destroy()


    def _on_close(self):
        self.result = None
        self.destroy()


class InfoDialog(BaseDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent, title, message)
        self.button_frame.columnconfigure(0, weight=1)
        ok_button = ttk.Button(self.button_frame, text="OK", command=self._on_ok, style="Accent.TButton")
        ok_button.grid(row=0, column=1, padx=5)
        ok_button.focus_set()
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.bind("<Return>", self._on_ok)
        self.bind("<Escape>", self._on_ok)
        self._finalize_and_show()


def showinfo(parent, title, message):
    dialog = InfoDialog(parent, title, message)
    parent.wait_window(dialog)


def showwarning(parent, title, message):
    dialog = InfoDialog(parent, f"{title}", message)
    parent.wait_window(dialog)


def showerror(parent, title, message):
    dialog = InfoDialog(parent, f"{title}", message)
    parent.wait_window(dialog)


class AskYesNoDialog(BaseDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent, title, message)
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.columnconfigure(1, weight=1)
        yes_button = ttk.Button(self.button_frame, text="Yes", command=self._on_yes, style="Accent.TButton")
        yes_button.grid(row=0, column=1, padx=(5,0), sticky="ew")
        no_button = ttk.Button(self.button_frame, text="No", command=self._on_no)
        no_button.grid(row=0, column=0, padx=(0,5), sticky="ew")
        yes_button.focus_set()
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.bind("<Return>", self._on_yes)
        self.bind("<Escape>", self._on_no)
        self._finalize_and_show()


def askyesno(parent, title, message):
    dialog = AskYesNoDialog(parent, title, message)
    parent.wait_window(dialog)
    return dialog.result


class AskSuperuserDialog(BaseDialog):
    def __init__(self, parent, title="Create Superuser"):
        super().__init__(parent, title)
        form_frame = ttk.Frame(self.main_frame)
        form_frame.columnconfigure(1, weight=1)
        ttk.Label(form_frame, text="Email:").grid(row=0, column=0, sticky="w", pady=5)
        self.email_entry = ttk.Entry(form_frame)
        self.email_entry.grid(row=0, column=1, sticky="ew", padx=(5,0), pady=5)
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky="w", pady=5)
        self.pass_entry = ttk.Entry(form_frame, show="*")
        self.pass_entry.grid(row=1, column=1, sticky="ew", padx=(5,0), pady=5)
        ttk.Label(form_frame, text="Confirm:").grid(row=2, column=0, sticky="w", pady=5)
        self.confirm_entry = ttk.Entry(form_frame, show="*")
        self.confirm_entry.grid(row=2, column=1, sticky="ew", padx=(5,0), pady=5)
        self.error_label = ttk.Label(form_frame, text="", foreground="red")
        self.error_label.grid(row=3, column=0, columnspan=2, pady=(5, 0))
        form_frame.pack(padx=10, fill="x", expand=True)
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.columnconfigure(1, weight=1)
        ok_button = ttk.Button(self.button_frame, text="Create", command=self._on_ok_credentials, style="Accent.TButton")
        ok_button.grid(row=0, column=1, padx=(5,0), sticky="ew")
        cancel_button = ttk.Button(self.button_frame, text="Cancel", command=self._on_close)
        cancel_button.grid(row=0, column=0, padx=(0,5), sticky="ew")
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.email_entry.focus_set()
        self.bind("<Return>", self._on_ok_credentials)
        self.bind("<Escape>", self._on_close)
        self._finalize_and_show()


    def _on_ok_credentials(self, event=None):
        email, password, confirm = self.email_entry.get().strip(), self.pass_entry.get(), self.confirm_entry.get()
        if not email or "@" not in email or "." not in email:
            self.error_label.config(text="Please enter a valid email address.")
            return
        if not password:
            self.error_label.config(text="Password cannot be empty.")
            return
        if password != confirm:
            self.error_label.config(text="Passwords do not match.")
            return
        self.result = {"email": email, "password": password}
        self.destroy()


def asksuperuser(parent, title):
    dialog = AskSuperuserDialog(parent, title)
    parent.wait_window(dialog)
    return dialog.result