# KiCad SimReady

**Simulation readiness checker for KiCad 9 schematics.**

KiCad SimReady is an Eeschema Action Plugin that analyzes your schematic before SPICE simulation, catching missing models, unconnected pins, missing values, and other common issues — before you hit "Run Simulation."

---

## Overview

Designing for simulation in KiCad requires more than a correct schematic — components need SPICE models, proper values, ground references, and simulation metadata. KiCad SimReady automates these checks and produces a clear HTML report with actionable recommendations.

## Features

- **SPICE Model Detection** — Flags active components (transistors, op-amps, diodes) missing `Sim.Device` or SPICE model assignments
- **Ground Reference Check** — Ensures a GND net or power symbol exists (required for SPICE node 0)
- **Component Value Validation** — Detects resistors, capacitors, and inductors with missing or placeholder values
- **Footprint Assignment** — Warns about components without PCB footprints
- **Floating Pin Detection** — Identifies pins that appear unconnected
- **Simulation Metadata** — Checks for `Sim.Device`, `Sim.Pins`, and `Sim.Params` properties
- **HTML Reports** — Generates styled, self-contained reports with severity levels and recommendations
- **CLI Support** — Run analysis from the command line without opening KiCad
- **Zero External Dependencies** — Core engine uses only Python standard library; KiCad provides wxPython at runtime

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    KiCad Eeschema                        │
│              (Action Plugin Entry Point)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   simready/plugin.py                     │
│         CLI entry point · KiCad registration             │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌───────────┐ ┌─────────────┐
   │   Parser   │ │ Analyzer  │ │ HTML Report │
   │ (.kicad_sch│ │ (Rule     │ │ Generator   │
   │  S-expr)   │ │  Engine)  │ │             │
   └─────┬──────┘ └─────┬─────┘ └─────────────┘
         │              │
         ▼              ▼
   ┌──────────┐   ┌──────────────────────────┐
   │  Models  │   │         Rules            │
   │ Component│   │ SpiceModel · Ground ·    │
   │ Pin · Net│   │ Value · Footprint ·      │
   │ Schematic│   │ FloatingPin · Simulation │
   └──────────┘   └──────────────────────────┘
```

See [docs/DESIGN.md](docs/DESIGN.md) for detailed architecture documentation.

## Installation

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for full instructions.

**Quick install (KiCad 9 plugin):**

```bash
# Clone the repository
git clone https://github.com/yourusername/KiCad-SimReady.git

# Copy to KiCad plugin directory
# Linux:
cp -r KiCad-SimReady/simready ~/.local/share/kicad/9.0/scripting/plugins/

# macOS:
cp -r KiCad-SimReady/simready ~/Library/Preferences/kicad/9.0/scripting/plugins/

# Windows:
# Copy simready/ to %USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\
```

Restart KiCad Eeschema. The plugin appears under **Tools → External Plugins → KiCad SimReady**.

## Usage

### Inside KiCad

1. Open your schematic in Eeschema
2. Go to **Tools → External Plugins → KiCad SimReady**
3. Review the summary dialog
4. The HTML report opens automatically in your browser

### Command Line

```bash
# Analyze a schematic
python -m simready.plugin examples/sample.kicad_sch

# Specify output directory and open report
python -m simready.plugin examples/sample.kicad_sch -o ./reports --open
```

### Python API

```python
from simready.core.parser import SchematicParser
from simready.plugin import create_analyzer
from simready.reports.html_report import HtmlReportGenerator

parser = SchematicParser()
schematic = parser.parse_file("my_circuit.kicad_sch")

analyzer = create_analyzer()
report = analyzer.analyze(schematic)

print(f"Simulation ready: {report.is_simulation_ready}")
print(f"Passed: {report.pass_count}, Failed: {report.fail_count}")

HtmlReportGenerator().generate_file(report, "report.html")
```

## Screenshots

> _Screenshot placeholders — add images after running the plugin in KiCad._

| Schematic Analysis | HTML Report |
|---|---|
| _[Plugin dialog screenshot]_ | _[HTML report screenshot]_ |

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=simready --cov-report=term-missing
```

## Project Structure

```
KiCad-SimReady/
├── simready/
│   ├── plugin.py              # KiCad Action Plugin + CLI
│   ├── core/
│   │   ├── parser.py          # .kicad_sch S-expression parser
│   │   ├── models.py          # Dataclass models
│   │   └── analyzer.py        # Rule engine orchestrator
│   ├── rules/
│   │   ├── base_rule.py       # Abstract rule base class
│   │   ├── spice_rule.py      # SPICE model checks
│   │   ├── ground_rule.py     # Ground reference checks
│   │   ├── value_rule.py      # Component value checks
│   │   ├── footprint_rule.py  # Footprint assignment checks
│   │   ├── floating_pin_rule.py
│   │   └── simulation_rule.py # Sim.* metadata checks
│   └── reports/
│       └── html_report.py     # HTML report generator
├── examples/
│   └── sample.kicad_sch       # Sample RC filter schematic
├── tests/                     # pytest test suite
├── docs/
│   ├── DESIGN.md
│   └── INSTALLATION.md
├── README.md
├── LICENSE
└── requirements.txt
```

## Future Improvements

- **Netlist export validation** — Cross-check schematic connectivity against exported SPICE netlists
- **Custom rule configuration** — YAML/JSON config to enable/disable rules and set severity thresholds
- **KiCad 9 Simulation Model Editor integration** — Direct links to fix issues in-model
- **Batch project analysis** — Analyze all schematics in a KiCad project at once
- **PDF report export** — Alternative report format for documentation
- **Power net detection** — Validate VCC/VDD supply nets and decoupling capacitors
- **Hierarchical sheet support** — Recursive analysis across multi-sheet schematics
- **CI/CD integration** — GitHub Action for simulation readiness checks on schematic changes

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.
