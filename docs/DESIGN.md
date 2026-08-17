# KiCad SimReady — Design Document

## 1. Purpose

KiCad SimReady validates KiCad schematics for SPICE simulation readiness before the user runs a simulation. It catches common configuration errors early and produces actionable reports.

## 2. Architecture Overview

The system follows a **parse → analyze → report** pipeline with a pluggable rule engine.

```
.kicad_sch file
      │
      ▼
 SchematicParser          (core/parser.py)
      │
      ▼
 Schematic model           (core/models.py)
      │
      ▼
 Analyzer + Rules          (core/analyzer.py + rules/)
      │
      ▼
 AnalysisReport
      │
      ▼
 HtmlReportGenerator       (reports/html_report.py)
      │
      ▼
 HTML report file
```

## 3. Modules

### 3.1 Core (`simready/core/`)

| Module | Responsibility |
|---|---|
| `parser.py` | Parses KiCad `.kicad_sch` S-expression files into structured data |
| `models.py` | Dataclass definitions: `Component`, `Pin`, `Net`, `Schematic`, `CheckResult` |
| `analyzer.py` | Orchestrates rule execution, aggregates results into `AnalysisReport` |

### 3.2 Rules (`simready/rules/`)

Each rule inherits from `BaseRule` and implements a single `check(schematic) → list[CheckResult]` method.

| Rule | Severity | What It Checks |
|---|---|---|
| `SpiceModelRule` | ERROR | Active components missing SPICE models |
| `GroundReferenceRule` | ERROR | Missing GND net or ground symbol |
| `ComponentValueRule` | ERROR | Passives with missing/placeholder values |
| `FootprintRule` | WARNING | Components without footprint assignments |
| `FloatingPinRule` | WARNING | Pins not connected to any net |
| `SimulationParameterRule` | WARNING | Missing `Sim.*` metadata properties |

### 3.3 Reports (`simready/reports/`)

| Module | Responsibility |
|---|---|
| `html_report.py` | Generates self-contained HTML reports with CSS styling |

### 3.4 Plugin (`simready/plugin.py`)

Dual-mode entry point:
- **KiCad mode**: Registers as `pcbnew.ActionPlugin`, shows wx dialog, opens report in browser
- **CLI mode**: `python -m simready.plugin <schematic>` for standalone usage

## 4. Data Flow

### 4.1 Parsing

1. Read `.kicad_sch` file as UTF-8 text
2. Tokenize and parse S-expression structure
3. Extract `(symbol ...)` blocks → `Component` objects with properties and pins
4. Extract `(label ...)`, `(global_label ...)`, `(wire ...)` → build net connectivity
5. Return populated `Schematic` object

### 4.2 Analysis

1. `Analyzer` receives a `Schematic` and iterates registered rules
2. Each rule independently inspects the schematic and returns `CheckResult` list
3. Results are aggregated into `AnalysisReport` with computed summary statistics
4. `is_simulation_ready` is `True` when zero ERROR-severity failures exist

### 4.3 Reporting

1. `HtmlReportGenerator` receives `AnalysisReport`
2. Renders summary cards (total, passed, failed, warnings)
3. Lists failed checks first with severity badges and recommendations
4. Lists passed checks for completeness
5. Writes self-contained HTML file (embedded CSS, no external dependencies)

## 5. Rule Engine Design

### 5.1 BaseRule Interface

```python
class BaseRule(ABC):
    name: str
    description: str

    @abstractmethod
    def check(self, schematic: Schematic) -> list[CheckResult]:
        ...
```

### 5.2 Extensibility

Adding a new rule requires:
1. Create a new file in `simready/rules/`
2. Subclass `BaseRule`, implement `check()`
3. Register in `create_analyzer()` in `plugin.py`
4. Add tests in `tests/test_rules.py`

No changes to the parser, analyzer, or report generator are needed.

### 5.3 Error Handling

If a rule raises an exception during execution, the analyzer catches it and produces an ERROR-severity `CheckResult` with the exception message. Other rules continue executing.

## 6. Data Models

```
Schematic
├── filename: str
├── project_name: str
├── version: str
├── components: list[Component]
│   ├── reference, value, lib_id, footprint
│   ├── properties: dict[str, str]
│   └── pins: list[Pin]
│       ├── number, name, connected, net_name
└── nets: list[Net]
    ├── name: str
    └── connected_pins: list[tuple[str, str]]

CheckResult
├── rule_name: str
├── passed: bool
├── message: str
├── severity: Severity (INFO | WARNING | ERROR)
├── component_ref: str | None
└── recommendation: str
```

## 7. Design Decisions

| Decision | Rationale |
|---|---|
| No KiCad Python package dependency | Enables standalone CLI usage and testing outside KiCad |
| S-expression parser from scratch | KiCad `.kicad_sch` format is stable; avoids heavy dependencies |
| Dataclasses over dicts | Type safety, IDE support, clear schema |
| Pluggable rule engine | Easy to add/remove/customize checks without touching core |
| ERROR vs WARNING severity | Errors block simulation readiness; warnings are advisory |
| Self-contained HTML reports | No server needed; reports open in any browser |

## 8. Limitations

- Net connectivity detection uses wire/label proximity heuristics; complex topologies may have false positives for floating pins
- Hierarchical sheets are not recursively analyzed (single-sheet only)
- SPICE model validation checks for presence, not correctness of model parameters
- Plugin schematic path detection depends on KiCad API availability

## 9. Testing Strategy

| Layer | Test File | Coverage |
|---|---|---|
| S-expression parser | `test_parser.py` | Tokenization, symbol extraction, net building |
| Data models | `test_models.py` | Property accessors, serialization |
| Rule engine | `test_analyzer.py` | Rule orchestration, error handling, summary |
| Individual rules | `test_rules.py` | Pass/fail cases per rule |
| HTML reports | `test_html_report.py` | Content, escaping, file output |
| End-to-end | `test_integration.py` | Full pipeline with sample schematic |
