from pathlib import Path

CORPUS_DIR = Path(__file__).parents[2] / "corpus"
REQUIRED_FIELDS = (
    "source",
    "technique",
    "lesson",
    "use_when",
    "avoid_when",
    "example_application",
)


def test_corpus_entries_use_required_lesson_format() -> None:
    missing: list[str] = []

    for path in sorted(CORPUS_DIR.glob("*.md")):
        fields = _parse_lesson_fields(path.read_text())
        for field in REQUIRED_FIELDS:
            if not fields.get(field):
                missing.append(f"{path.name}: missing {field}")

    assert not missing, "Corpus entries missing required fields:\n" + "\n".join(missing)


def test_corpus_entries_map_to_at_least_one_technique() -> None:
    missing: list[str] = []

    for path in sorted(CORPUS_DIR.glob("*.md")):
        fields = _parse_lesson_fields(path.read_text())
        techniques = [
            item.strip()
            for item in fields.get("technique", "").split(",")
            if item.strip()
        ]
        if not techniques:
            missing.append(path.name)

    assert not missing, "Corpus entries missing technique mappings:\n" + "\n".join(missing)


def test_corpus_is_distilled_from_requested_sources() -> None:
    missing: list[str] = []

    for path in sorted(CORPUS_DIR.glob("*.md")):
        content = path.read_text().lower()
        if "atomic habits" not in content or "tiny habits" not in content:
            missing.append(path.name)

    assert not missing, "Corpus entries missing requested sources:\n" + "\n".join(missing)


def _parse_lesson_fields(content: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        field_name = next(
            (
                field
                for field in REQUIRED_FIELDS
                if lower.startswith(f"{field}:")
            ),
            None,
        )
        if field_name is not None:
            current = field_name
            fields[current] = line.split(":", maxsplit=1)[1].strip()
        elif current and line:
            fields[current] = f"{fields[current]} {line}".strip()
    return fields
