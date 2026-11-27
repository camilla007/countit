"""Check built artifacts without importing the source checkout."""

import ast
import os
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = next(
    ast.literal_eval(node.value)
    for node in ast.parse((root / "src/countit/__init__.py").read_text()).body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
)
if os.environ.get("GITHUB_REF_TYPE") == "tag":
    assert os.environ["GITHUB_REF_NAME"] == f"v{version}", "tag must match package version"

expected = {f"countit-{version}.tar.gz", f"countit-{version}-py3-none-any.whl"}
assert {p.name for p in (root / "dist").iterdir()} == expected, "unexpected or stale artifacts"
with zipfile.ZipFile(root / "dist" / f"countit-{version}-py3-none-any.whl") as wheel:
    names = wheel.namelist()
    metadata = BytesParser().parsebytes(wheel.read(f"countit-{version}.dist-info/METADATA"))
    assert metadata["Name"] == "countit"
    assert metadata["Version"] == version
    assert metadata["Requires-Python"] == ">=3.11"
    assert metadata["License-Expression"] == "MIT"
    assert metadata["Description-Content-Type"] == "text/markdown"
    assert "Your keyboard has said enough" in metadata.get_payload()
    assert f"countit-{version}.dist-info/licenses/LICENSE" in names
    assert "countit/data/countit-collector.service" in names
    for name in names:
        assert name.startswith(("countit/", f"countit-{version}.dist-info/")), name
        assert not any(part.startswith(".") for part in Path(name).parts), name
        assert not name.endswith((".db", ".sqlite", ".sqlite3", ".csv", ".pyc")), name
    unit = wheel.read("countit/data/countit-collector.service")
    assert unit == (root / "systemd/countit-collector.service").read_bytes()
    assert b"/home/camilla" not in unit
with tarfile.open(root / "dist" / f"countit-{version}.tar.gz") as source:
    names = {member.name for member in source.getmembers()}
    for required in ("LICENSE", "README.md", "SECURITY.md", "CONTRIBUTING.md", "tests/test_web.py"):
        assert f"countit-{version}/{required}" in names, required
    for name in names:
        assert not name.endswith((".db", ".sqlite", ".sqlite3", ".csv", ".pyc", ".pypirc")), name
        assert not {".git", ".env", ".venv"}.intersection(Path(name).parts), name
print(f"Validated countit {version}: wheel metadata, licence, service template, and source archive")
