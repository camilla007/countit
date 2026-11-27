import pytest

from countit import __version__
from countit.cli import default_database, main


def test_version_does_not_create_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"CountIt {__version__}"
    assert not (tmp_path / "countit").exists()


def test_xdg_database(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert default_database() == tmp_path / "countit/countit.db"
    monkeypatch.setenv("XDG_DATA_HOME", "relative")
    assert default_database().is_absolute()


@pytest.mark.parametrize(
    "args",
    [
        ["summary", "--hours", "0"],
        ["export", "--hours", "8761"],
        ["summary", "--hours", "oops"],
        ["serve", "--port", "0"],
        ["serve", "--port", "65536"],
        ["serve", "--port", "oops"],
        ["purge", "--before", "yesterday"],
        ["purge", "--before", "2026-01-01"],
    ],
)
def test_invalid_arguments_do_not_open_database(args, tmp_path):
    database = tmp_path / "never-created.db"
    with pytest.raises(SystemExit) as exc:
        main([*args, "--database", str(database)])
    assert exc.value.code == 2
    assert not database.exists()


def test_summary_export_and_explicit_purge(tmp_path, capsys):
    database = str(tmp_path / "countit.db")
    main(["summary", "--database", database])
    assert "'printable': 0" in capsys.readouterr().out
    main(["export", "--database", database])
    assert capsys.readouterr().out.startswith("minute_utc,printable,")
    main(["purge", "--database", database, "--before", "2026-01-01T00:00:00Z"])
    assert capsys.readouterr().out == "deleted_buckets=0\n"


def test_service_template_is_packaged_and_does_not_install(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    main(["service-template"])
    unit = capsys.readouterr().out
    assert "ExecStart=%h/.local/bin/countit collect" in unit
    assert "/home/camilla" not in unit
    assert not list(tmp_path.iterdir())
