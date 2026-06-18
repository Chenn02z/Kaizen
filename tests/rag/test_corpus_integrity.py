from pathlib import Path

CORPUS_DIR = Path(__file__).parents[2] / "corpus"
REQUIRED_FIELDS = (
    "source:",
    "technique:",
    "lesson:",
    "use_when:",
    "avoid_when:",
    "example_application:",
)


def test_corpus_entries_use_required_lesson_format() -> None:
    missing: list[str] = []

    for path in sorted(CORPUS_DIR.glob("*.md")):
        content = path.read_text().lower()
        for field in REQUIRED_FIELDS:
            if field not in content:
                missing.append(f"{path.name}: missing {field}")

    assert not missing, "Corpus entries missing required fields:\n" + "\n".join(missing)


def test_corpus_is_distilled_from_requested_sources() -> None:
    missing: list[str] = []

    for path in sorted(CORPUS_DIR.glob("*.md")):
        content = path.read_text().lower()
        if "atomic habits" not in content or "tiny habits" not in content:
            missing.append(path.name)

    assert not missing, "Corpus entries missing requested sources:\n" + "\n".join(missing)
