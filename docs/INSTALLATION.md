# KiCad SimReady — Installation Guide

## Requirements

- **KiCad 9.0** or later (for plugin mode)
- **Python 3.10+** (bundled with KiCad, or system Python for CLI)
- No additional pip packages required for plugin operation

## Plugin Installation

### Linux

```bash
git clone https://github.com/yourusername/KiCad-SimReady.git
mkdir -p ~/.local/share/kicad/9.0/scripting/plugins/
cp -r KiCad-SimReady/simready ~/.local/share/kicad/9.0/scripting/plugins/
```

### macOS

```bash
git clone https://github.com/yourusername/KiCad-SimReady.git
mkdir -p ~/Library/Preferences/kicad/9.0/scripting/plugins/
cp -r KiCad-SimReady/simready ~/Library/Preferences/kicad/9.0/scripting/plugins/
```

### Windows

```powershell
git clone https://github.com/yourusername/KiCad-SimReady.git
# Copy the simready folder to:
# %USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\simready\
```

### Verify Installation

1. Restart KiCad (or reload plugins via **Preferences → Plugin and Content Manager**)
2. Open a schematic in Eeschema
3. Navigate to **Tools → External Plugins**
4. **KiCad SimReady** should appear in the list

## CLI Installation (Standalone)

For command-line usage without KiCad:

```bash
git clone https://github.com/yourusername/KiCad-SimReady.git
cd KiCad-SimReady

# Optional: create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dev dependencies (for testing)
pip install -r requirements.txt
```

### CLI Usage

```bash
# From the repository root
python -m simready.plugin examples/sample.kicad_sch

# With output directory
python -m simready.plugin my_project.kicad_sch -o ./reports

# Open report in browser
python -m simready.plugin my_project.kicad_sch --open
```

## Development Setup

```bash
git clone https://github.com/yourusername/KiCad-SimReady.git
cd KiCad-SimReady
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=simready --cov-report=term-missing
```

## Troubleshooting

### Plugin not appearing in KiCad

- Verify the plugin directory path matches your KiCad version (9.0)
- Ensure `plugin.py` is inside the `simready/` folder in the plugins directory
- Check KiCad's scripting console for import errors: **Tools → Scripting Console**
- Restart KiCad completely after copying files

### "Could not determine schematic path"

- Save your KiCad project before running the plugin
- The plugin looks for a `.kicad_sch` file matching the open PCB project
- Use CLI mode as a workaround: `python -m simready.plugin path/to/schematic.kicad_sch`

### Import errors in KiCad

- KiCad bundles its own Python — do not install packages into KiCad's Python
- The plugin uses only standard library modules at runtime
- Ensure the full `simready/` package directory was copied, not just `plugin.py`

### Permission errors on Linux

```bash
chmod -R u+r ~/.local/share/kicad/9.0/scripting/plugins/simready/
```

## Uninstallation

Remove the plugin directory:

```bash
# Linux
rm -rf ~/.local/share/kicad/9.0/scripting/plugins/simready/

# macOS
rm -rf ~/Library/Preferences/kicad/9.0/scripting/plugins/simready/

# Windows
# Delete %USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\simready\
```

Restart KiCad to complete removal.
