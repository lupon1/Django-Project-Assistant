# Django Project Assistant

A cross-platform desktop application designed to automate the repetitive tasks of setting up a new Django project. This tool solves the problem of manual, error-prone initial project configuration by providing a simple GUI to handle everything from virtual environment creation to advanced setup like custom user models. It's built for Django developers who want to bootstrap projects faster and more consistently.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Table of Contents
- [Installation](#installation)
- [Quick Usage Guide](#quick-usage-guide)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)
- [Authors](#authors)

## Installation

This application is designed to be run from the source code. Follow these steps to get it up and running.

**Prerequisites:**
*   **Python 3.8+**: Ensure you have a modern version of Python installed.
*   **Git**: Required to clone the repository.
*   **uv**: This is a mandatory external tool for virtual environment and package management. Please install it from [astral.sh/uv](https://astral.sh/uv).

### 1. Clone the Repository
First, clone this repository to your local machine:
```sh
git clone https://github.com/lupon1/Django-Project-Assistant.git
cd Django-Project-Assistant
```

### 2. Create and Activate a Virtual Environment
It is highly recommended to run this application in its own dedicated virtual environment.

```sh
# Create the virtual environment
uv venv

# Activate it
# On Windows (cmd.exe):
venv\Scripts\activate
# On Linux / macOS (bash/zsh):
source venv/bin/activate
```

### 3. Install Requirements (Windows Only)
If you are on Windows, there is one dependency for themed window styles.
```sh
uv pip install pywinstyles
```
On Linux and macOS, no Python dependencies are required.
On Linux, it may be necessary install the tkinter libraries

### 4. Running the Application
Once the environment is active, you can launch the application with:
```sh
python main.py
```

**Pro Tip: Create a Shortcut**
For easier access, you can create a desktop shortcut that executes the run command directly.
*   **Windows:** Create a shortcut, and in the "Target" field, enter `path\to\your\venv\Scripts\python.exe path\to\your\project\main.py`. Set the "Start in" field to your project's folder.
*   **Linux/macOS:** Create a simple shell script (`.sh`) with the activation and run commands and make it executable.

## Quick Usage Guide

The application interface is divided into several sections:

*   **Project**:
    *   **Project name**: The name for your new Django project (e.g., `my_cool_site`). Only letters, numbers, and underscores are allowed.
    *   **Projects Parent Folder**: The directory where your new project folder will be created (e.g., `C:\Users\You\Documents\Projects`).

*   **Virtual Environment**:
    *   **Python version**: Select an installed Python version for the project's virtual environment. `uv` automatically detects available versions.
    *   **Venvs Parent Folder**: The directory where the new virtual environment folder will be created (e.g., `C:\Users\You\Documents\venvs`).
    *   **Django packages**: Select optional third-party Django packages to install and configure automatically (e.g., `django-allauth`).

*   **Web Framework**:
    *   **Template Collection**: Choose a set of starting HTML templates. The options are dynamically scanned from the `html_templates/` directory.
    *   **External libraries**: Select external CSS/JS libraries (like FontAwesome or HTMX) to be injected into your base template.

*   **Other options**:
    *   **Use custom user model**: Creates a dedicated `accounts` app with a custom User model that uses email for login.
    *   **Create superuser**: If the custom user model is enabled, this option will prompt you for credentials to create an admin user after the project is built.
    *   **Open browser on start**: Automatically starts the Django development server and opens your project in a web browser upon completion.

## Configuration

This application is highly configurable via the `config.json` and template files.

### Adding Python Packages
To add a new optional Python package:
1.  Open `config.json`.
2.  Navigate to the `django_packages` list.
3.  Add a new JSON object with the package details, for example:
    ```json
    {
      "name": "djangorestframework",
      "selected": false,
      "apps": ["rest_framework"],
      "middleware": [],
      "other_settings": ""
    }
    ```

### Adding External Web Libraries
To add a new CSS or JS library:
1.  Open `config.json`.
2.  Navigate to the `external_libraries` list.
3.  Add a new object. Use `head_links` for CSS files and `body_scripts` for JavaScript files.
    ```json
    {
      "name": "Alpine.js",
      "selected": false,
      "head_links": [],
      "body_scripts": ["//unpkg.com/alpinejs"]
    }
    ```

### Creating New HTML Templates
To add a new "Template Collection" to the dropdown:
1.  Create a new folder inside the `html_templates/` directory (e.g., `html_templates/my_new_style`).
2.  Inside your new folder, create the required app structure, for example:
    *   `html_templates/my_new_style/core/base.html`
    *   `html_templates/my_new_style/core/index.html`
    *   (Optional) `html_templates/my_new_style/accounts/login.html`
3.  The application will automatically detect the new folder and add it as an option.
4.  **Important**: Ensure your `base.html` contains the placeholders `<!-- DJANGO_ASSISTANT_HEAD_LINKS -->` and `<!-- DJANGO_ASSISTANT_BODY_SCRIPTS -->` for external library injection to work.

## Contributing

Contributions are welcome! If you have ideas for improvements, new features, or find a bug, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Authors

*   **Francesco Esposito** - *Initial Work & Development*

***
*This project was developed with the assistance of an AI language model (LLM) to help optimize the application, write documentation, and craft this README file.*