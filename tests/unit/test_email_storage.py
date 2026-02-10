import json

from src.storage.email_storage import EmailStorage


def _write_email_file(path, year, emails):
    payload = {
        "metadata": {
            "fetch_date": "2026-02-10T10:00:00",
            "year": year,
            "email_count": len(emails),
        },
        "emails": emails,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def test_load_emails_by_year(tmp_path):
    storage = EmailStorage(storage_dir=str(tmp_path))
    _write_email_file(tmp_path / "emails_2026_001.json", 2026, [{"id": "a"}])
    _write_email_file(tmp_path / "emails_2026_002.json", 2026, [{"id": "b"}])
    _write_email_file(tmp_path / "emails_2025_001.json", 2025, [{"id": "c"}])

    emails = storage.load_emails(year=2026)

    assert [email["id"] for email in emails] == ["a", "b"]


def test_load_emails_specific_file(tmp_path):
    storage = EmailStorage(storage_dir=str(tmp_path))
    target = tmp_path / "emails_2026_999.json"
    _write_email_file(target, 2026, [{"id": "only"}])

    emails = storage.load_emails(specific_file=str(target))

    assert emails == [{"id": "only"}]


def test_load_emails_specific_relative_file(tmp_path):
    storage = EmailStorage(storage_dir=str(tmp_path))
    target = tmp_path / "emails_2026_123.json"
    _write_email_file(target, 2026, [{"id": "relative"}])

    emails = storage.load_emails(specific_file="emails_2026_123.json")

    assert emails == [{"id": "relative"}]
