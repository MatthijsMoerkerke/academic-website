from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS_DIR = ROOT / "content" / "publications"
TEMPLATE_FILE = ROOT / "cv" / "template.md"
PRESENTATIONS_FILE = ROOT / "cv" / "presentations.md"
OUTPUT_MD = ROOT / "cv" / "cv_generated.md"

def read_front_matter(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])

def pub_type_label(pub_type: str) -> str:
    mapping = {
        "article-journal": "",
        "preprint": "Preprint.",
        "paper-conference": "Conference paper.",
        "thesis": "PhD dissertation.",
    }
    return mapping.get(pub_type, "")

def format_publication(front_matter: dict) -> str:
    authors = front_matter.get("authors", [])
    authors_text = ", ".join(authors) if authors else "Unknown authors"

    date = str(front_matter.get("date", ""))
    year = date[:4] if len(date) >= 4 else "n.d."

    title = front_matter.get("title", "Untitled")
    publication = front_matter.get("publication", "")
    pub_types = front_matter.get("publication_types", [])
    pub_type = pub_types[0] if pub_types else ""
    label = pub_type_label(pub_type)

    line = f"- {authors_text} ({year}). *{title}*."
    if publication:
        line += f" {publication}."
    if label:
        line += f" {label}"
    return line

def collect_publications():
    entries = []
    if not PUBLICATIONS_DIR.exists():
        return entries

    for folder in PUBLICATIONS_DIR.iterdir():
        if not folder.is_dir():
            continue
        index_file = folder / "index.md"
        if not index_file.exists():
            continue
        fm = read_front_matter(index_file)
        if not fm:
            continue
        entries.append(fm)

    entries.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    return entries

def load_presentations():
    if not PRESENTATIONS_FILE.exists():
        return ""
    return PRESENTATIONS_FILE.read_text(encoding="utf-8").strip()

def main():
    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    pubs = collect_publications()
    pub_lines = [format_publication(p) for p in pubs]
    pub_block = "\n".join(pub_lines)

    presentations_block = load_presentations()

    output = template.replace("{{PUBLICATIONS}}", pub_block)
    output = output.replace("{{PRESENTATIONS}}", presentations_block)

    OUTPUT_MD.write_text(output, encoding="utf-8")
    print(f"Generated {OUTPUT_MD}")

if __name__ == "__main__":
    main()
