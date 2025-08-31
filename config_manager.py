"""
Manages loading and saving the application's configuration from a JSON file.
"""

import json
from os import path

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    # UI state and cache
    "last_project_path": "",
    "last_venv_path": "",
    "cached_python_versions": [],
    "remember_custom_user": False,
    "remember_open_browser": True,
    "remember_create_superuser": False,

    "django_packages": [
        {
            "name": "django-environ", "selected": False,
            "apps": [], "middleware": [], "other_settings": ""
        },
        {
            "name": "django-allauth", "selected": False,
            "apps": ['django.contrib.sites', 'allauth', 'allauth.account', 'allauth.socialaccount'],
            "middleware": ["allauth.account.middleware.AccountMiddleware"],
            "other_settings": "SITE_ID = 1"
        },
        {
            "name": "django-cors-headers", "selected": False,
            "apps": ["corsheaders"],
            "middleware": ["corsheaders.middleware.CorsMiddleware"],
            "other_settings": "CORS_ALLOW_ALL_ORIGINS = True"
        }
    ],
    "external_libraries": [
        {
            "name": "FontAwesome", "selected": False,
            "head_links": ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"],
            "body_scripts": []
        },
        {
            "name": "HTMX", "selected": False,
            "head_links": [],
            "body_scripts": ["https://unpkg.com/htmx.org@1.9.10"]
        }
    ]
}


def load_config():
    """
    Loads configuration from CONFIG_FILE.
    
    If the file doesn't exist or is invalid, returns defaults.
    It robustly merges defaults to ensure all keys exist, even after an update.
    """
    if not path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = DEFAULT_CONFIG.copy()
    
    # Ensure all top-level keys from the default config are present.
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            
    # Ensure nested keys in lists of dictionaries are present.
    # This handles cases where a new key (like "selected") is added to the app.
    for key in ["django_packages", "external_libraries"]:
        if DEFAULT_CONFIG.get(key) and cfg.get(key):
            default_item_keys = DEFAULT_CONFIG[key][0].keys()
            for item in cfg[key]:
                for default_key in default_item_keys:
                    if default_key not in item:
                        default_item = next((d for d in DEFAULT_CONFIG[key] if d.get('name') == item.get('name')), None)
                        if default_item:
                            item[default_key] = default_item.get(default_key)
    return cfg


def save_config(cfg):
    """Saves the given configuration dictionary to CONFIG_FILE."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
