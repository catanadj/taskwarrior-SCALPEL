# Packaging & Release Checklist (PyPI)

Use this checklist when preparing a SCALPEL release.

## 1. Preflight

- Confirm the target package name is available on PyPI (current distribution name: `taskwarrior-scalpel`).
- Update `version` in `pyproject.toml` for the release.
- Review `README.md` and `CHANGELOG.md` for release notes and breaking changes.

## 2. Validate the repo

Run the contract suite:

```bash
./scripts/scalpel_test_contract.sh
```

Optional local CI gate:

```bash
./scripts/scalpel_ci.sh
```

## 3. Build artifacts

Install release tooling:

```bash
python3 -m pip install -U '.[release]'
```

Build wheel + sdist:

```bash
python3 -m build
```

If `python3 -m build` is unavailable in your environment, install/upgrade `build` in a virtualenv first.

## 4. Check package metadata

```bash
python3 -m twine check dist/*
```

## 5. Test install locally

Install from the built wheel into an isolated target dir:

```bash
rm -rf /tmp/scalpel_pkg_test
python3 -m pip install --no-deps --target /tmp/scalpel_pkg_test dist/*.whl
PYTHONPATH=/tmp/scalpel_pkg_test python3 -m scalpel.cli --help
```

## 6. TestPyPI (recommended)

Upload to TestPyPI first:

```bash
python3 -m twine upload --repository testpypi dist/*
```

Verify install from TestPyPI in a fresh virtualenv (package name `taskwarrior-scalpel`).

## 7. Publish to PyPI

```bash
python3 -m twine upload dist/*
```

## 8. Post-release smoke check

- Install the published version in a clean virtualenv (`python -m pip install taskwarrior-scalpel`).
- Run `scalpel --help`.
- Run `scalpel-smoke-build --help`.
- Run one end-to-end local smoke generation command.
