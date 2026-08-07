## 📋 L.I.S.A. Pull Request Checklist

### 🏛️ Architecture & Governance
- [ ] Adheres strictly to **The Contract Runtime Pattern** (`SUBSYSTEM_TEMPLATE.md`).
- [ ] No direct imports of concrete providers in Runtime (`core/`, `runtime/`, `engine/`).
- [ ] Pure dataclass contracts (`Manifest`, `Context`, `Request`, `Result`) remain behavioral-method free.
- [ ] Architectural Decision Record (ADR) added to `DECISIONS.md` if changing boundaries.

### 🧪 Quality & Tests
- [ ] Unit & Resilience tests pass (`PYTHONPATH=. python -m unittest discover -s tests`).
- [ ] Automated Architectural Rule Enforcement tests pass (`test_architecture_rules.py`).
- [ ] Zero-mock integration tests pass against `examples/golden_project`.
