from pathlib import Path
import base64
import html
import re

import markdown
import yaml


ROOT = Path(__file__).resolve().parents[1]

SITE_INDEX = ROOT / "content" / "_index.md"
AUTHOR_DATA = ROOT / "data" / "authors" / "me.yaml"
AUTHOR_DIR = ROOT / "content" / "authors" / "matthijs"
PUBLICATIONS_DIR = ROOT / "content" / "publications"
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"
TEMPLATE_FILE = ROOT / "cv" / "template.html"
STYLE_FILE = ROOT / "cv" / "style.css"
OUTPUT_HTML = ROOT / "cv" / "cv_generated.html"


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return path.read_text(encoding="utf-8")


def read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    data = yaml.safe_load(
        path.read_text(encoding="utf-8")
    ) or {}

    return data if isinstance(data, dict) else {}


def make_link(url: str, label: str) -> str:
    """Create a valid HTML hyperlink."""
    if not url:
        return html.escape(str(label))

    safe_url = html.escape(str(url), quote=True)
    safe_label = html.escape(str(label))

    opening_tag = chr(60) + 'a href="' + safe_url + '"' + chr(62)
    closing_tag = chr(60) + "/a" + chr(62)

    return opening_tag + safe_label + closing_tag

def clean_markdown_block(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    cleaned_lines = []

    for line in text.split("\n"):
        line = line.rstrip()
        line = re.sub(r"[ \t]{2,}", " ", line)
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    # Convert bare URLs on separate lines into Markdown links.
    text = re.sub(
        r"(?m)^(https?://\S+)\s*$",
        r"<\1>",
        text,
    )

    return text


def md_to_html(text: str) -> str:
    text = clean_markdown_block(text)

    if not text:
        return ""

    return markdown.markdown(
        text,
        extensions=[
            "extra",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5",
    )


def strip_cv_button_from_bio(text: str) -> str:
    if not text:
        return ""

    # Remove a complete HTML paragraph containing the CV button.
    text = re.sub(
        (
            r'(?is)<p[^>]*>.*?'
            r'<a[^>]*href="[^"]*CV_Matthijs_Moerkerke'
            r'\.pdf[^"]*"[^>]*>.*?</a>.*?</p>'
        ),
        "",
        text,
    )

    # Remove a standalone CV link.
    text = re.sub(
        (
            r'(?is)<a[^>]*href="[^"]*CV_Matthijs_Moerkerke'
            r'\.pdf[^"]*"[^>]*>.*?</a>'
        ),
        "",
        text,
    )

    # Remove a plain-text fallback.
    text = re.sub(
        r"(?im)^\s*Download CV\s*$",
        "",
        text,
    )

    return text.strip()


def extract_block_title(
    site_text: str,
    block_id: str,
    fallback: str,
) -> str:
    pattern = (
        rf"(?ms)^-\s*block:.*?\n"
        rf"\s+id:\s*{re.escape(block_id)}\s*\n"
        rf".*?"
        rf"^\s+content:\s*\n"
        rf".*?"
        rf'^\s+title:\s*"?(.*?)"?\s*$'
    )

    match = re.search(pattern, site_text)

    if not match:
        return fallback

    title = match.group(1).strip()

    return title if title else fallback


def extract_text_block(
    site_text: str,
    block_id: str,
) -> str:
    """
    Extract only the lines belonging to:

      text: |
        ...

    Stop before sibling keys such as button, headings or design.
    """
    lines = site_text.splitlines()

    block_start = None

    for index, line in enumerate(lines):
        if re.match(
            rf"^\s+id:\s*{re.escape(block_id)}\s*$",
            line,
        ):
            block_start = index
            break

    if block_start is None:
        return ""

    text_line_index = None
    text_indent = None

    for index in range(block_start, len(lines)):
        line = lines[index]

        match = re.match(
            r"^(\s+)text:\s*\|\s*$",
            line,
        )

        if match:
            text_line_index = index
            text_indent = len(match.group(1))
            break

        if (
            index > block_start
            and re.match(r"^\s*-\s*block:", line)
        ):
            break

    if text_line_index is None:
        return ""

    collected = []

    for index in range(text_line_index + 1, len(lines)):
        line = lines[index]

        if line.strip() == "":
            collected.append("")
            continue

        indent = len(line) - len(line.lstrip(" "))

        if indent <= text_indent:
            break

        collected.append(line)

    if not collected:
        return ""

    nonempty = [
        line
        for line in collected
        if line.strip()
    ]

    if nonempty:
        min_indent = min(
            len(line) - len(line.lstrip(" "))
            for line in nonempty
        )
    else:
        min_indent = 0

    normalized = [
        line[min_indent:]
        if len(line) >= min_indent
        else line.lstrip()
        for line in collected
    ]

    return clean_markdown_block(
        "\n".join(normalized).strip()
    )


def get_home_sections() -> dict:
    site_text = read_text(SITE_INDEX)

    bio_text = strip_cv_button_from_bio(
        extract_text_block(site_text, "bio")
    )

    return {
        "bio": {
            "title": "About",
            "text": bio_text,
        },
        "training": {
            "title": extract_block_title(
                site_text,
                "training",
                "Additional Training",
            ),
            "text": extract_text_block(
                site_text,
                "training",
            ),
        },
        "teaching": {
            "title": extract_block_title(
                site_text,
                "teaching",
                "Teaching & Mentoring",
            ),
            "text": extract_text_block(
                site_text,
                "teaching",
            ),
        },
        "engagement": {
            "title": extract_block_title(
                site_text,
                "engagement",
                "Scientific Engagement & Outreach",
            ),
            "text": extract_text_block(
                site_text,
                "engagement",
            ),
        },
        "skills": {
            "title": extract_block_title(
                site_text,
                "skills",
                "Skills & Methods",
            ),
            "text": extract_text_block(
                site_text,
                "skills",
            ),
        },
        "awards": {
            "title": extract_block_title(
                site_text,
                "awards",
                "Awards & Grants",
            ),
            "text": extract_text_block(
                site_text,
                "awards",
            ),
        },
        "presentations": {
            "title": extract_block_title(
                site_text,
                "presentations",
                "Presentations",
            ),
            "text": extract_text_block(
                site_text,
                "presentations",
            ),
        },
    }


def find_avatar_data_uri() -> str:
    if not AUTHOR_DIR.exists():
        return ""

    preferred = [
        AUTHOR_DIR / "avatar.jpg",
        AUTHOR_DIR / "avatar.jpeg",
        AUTHOR_DIR / "avatar.png",
        AUTHOR_DIR / "avatar.webp",
    ]

    for img_path in preferred:
        if not img_path.exists():
            continue

        suffix = img_path.suffix.lower()

        if suffix in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif suffix == ".png":
            mime = "image/png"
        elif suffix == ".webp":
            mime = "image/webp"
        else:
            continue

        encoded = base64.b64encode(
            img_path.read_bytes()
        ).decode("ascii")

        return f"data:{mime};base64,{encoded}"

    return ""


def build_bio(
    sections: dict,
    author: dict,
) -> str:
    bio_html = md_to_html(
        sections.get("bio", {}).get("text", "")
    )

    avatar = find_avatar_data_uri()

    name_data = author.get("name", {})

    if isinstance(name_data, dict):
        display_name = name_data.get(
            "display",
            "Matthijs Moerkerke",
        )
    else:
        display_name = str(
            name_data or "Matthijs Moerkerke"
        )

    role = author.get(
        "role",
        "Neuroscientist",
    )

    affiliations = "<br>".join(
        html.escape(str(item.get("name", "")))
        for item in author.get("affiliations", [])
        if (
            isinstance(item, dict)
            and item.get("name")
        )
    )

    email = "matthijs.moerkerke@ugent.be"
    linkedin = ""

    for link in author.get("links", []):
        if not isinstance(link, dict):
            continue

        url = str(link.get("url", "")).strip()

        if url.startswith("mailto:"):
            email = url.replace(
                "mailto:",
                "",
                1,
            ).strip()

        elif "linkedin.com" in url:
            linkedin = url

    avatar_html = ""

    if avatar:
        avatar_html = (
            f'<img class="hero-avatar" '
            f'src="{html.escape(avatar, quote=True)}" '
            f'alt="{html.escape(display_name, quote=True)}">'
        )

    email_html = make_link(
        f"mailto:{email}",
        email,
    )

    linkedin_html = ""

    if linkedin:
        linkedin_display = (
            linkedin
            .replace("https://www.", "")
            .replace("http://www.", "")
            .replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )

        linkedin_html = (
            '<span class="contact-separator">|</span>'
            + make_link(
                linkedin,
                linkedin_display,
            )
        )

    contact_html = f"""
<div class="hero-contact">
  <strong>Contact:</strong>
  {email_html}
  {linkedin_html}
</div>
"""

    return f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-top">
      {avatar_html}

      <div class="hero-title">
        <h1>{html.escape(display_name)}</h1>

        <div class="hero-subtitle">
          {html.escape(str(role))}
        </div>

        <div class="hero-affiliation">
          {affiliations}
        </div>
      </div>
    </div>

    <div class="hero-bio">
      {bio_html}
    </div>

    {contact_html}
  </div>
</div>
"""


def build_markdown_section(
    sections: dict,
    key: str,
    fallback_title: str,
) -> str:
    section = sections.get(key, {})

    title = (
        section.get("title", "")
        or fallback_title
    )

    section_html = md_to_html(
        section.get("text", "")
    )

    if not section_html:
        return ""

    return f"""
<section class="cv-section">
  <h2>{html.escape(str(title))}</h2>
  {section_html}
</section>
"""


def build_card_section(
    title: str,
    cards: list[str],
) -> str:
    if not cards:
        return ""

    return f"""
<section class="cv-section">
  <h2>{html.escape(title)}</h2>

  <div class="card-grid">
    {''.join(cards)}
  </div>
</section>
"""


def build_education(author: dict) -> str:
    cards = []

    for item in author.get("education", []):
        if not isinstance(item, dict):
            continue

        degree = html.escape(
            str(item.get("degree", ""))
        )

        institution = html.escape(
            str(item.get("institution", ""))
        )

        summary = item.get("summary", "")

        button = item.get("button", {}) or {}

        if isinstance(button, dict):
            url = str(
                button.get("url", "")
            ).strip()
        else:
            url = ""

        link_html = ""

        if url:
            link_html = (
                '<div class="card-link">'
                + make_link(
                    url,
                    "Dissertation link",
                )
                + "</div>"
            )

        cards.append(
            f"""
<div class="info-card">
  <div class="card-title">
    {degree}
  </div>

  <div class="card-inst">
    {institution}
  </div>

  <div>
    {md_to_html(summary)}
  </div>

  {link_html}
</div>
"""
        )

    return build_card_section(
        "Education",
        cards,
    )


def build_interests(author: dict) -> str:
    interests = author.get("interests", [])

    if not interests:
        return ""

    pills = "".join(
        (
            '<span class="interest-pill">'
            + html.escape(str(item))
            + "</span>"
        )
        for item in interests
    )

    return f"""
<section class="cv-section">
  <h2>Research Interests</h2>

  <div class="interest-row">
    {pills}
  </div>
</section>
"""


def read_publication_front_matter(
    md_path: Path,
):
    text = md_path.read_text(
        encoding="utf-8"
    )

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)

    if len(parts) < 3:
        return None

    return yaml.safe_load(parts[1])


def collect_publications() -> list:
    entries = []

    if not PUBLICATIONS_DIR.exists():
        return entries

    for folder in PUBLICATIONS_DIR.iterdir():
        if not folder.is_dir():
            continue

        index_file = folder / "index.md"

        if not index_file.exists():
            continue

        front_matter = read_publication_front_matter(
            index_file
        )

        if not front_matter:
            continue

        entries.append(front_matter)

    entries.sort(
        key=lambda item: str(
            item.get("date", "")
        ),
        reverse=True,
    )

    return entries


def read_scholar_metrics() -> dict:
    data = read_yaml(SCHOLAR_FILE)

    return {
        "citations": data.get(
            "citations",
            0,
        ),
        "h_index": data.get(
            "h_index",
            0,
        ),
        "profile": data.get(
            "profile",
            "",
        ),
    }


def format_authors(authors) -> str:
    if not authors:
        return "Unknown authors"

    return ", ".join(
        html.escape(str(author))
        for author in authors
    )


def format_publication_html(
    front_matter: dict,
) -> str:
    authors_text = format_authors(
        front_matter.get("authors", [])
    )

    date = str(
        front_matter.get("date", "")
    )

    year = (
        date[:4]
        if len(date) >= 4
        else "n.d."
    )

    title = html.escape(
        str(
            front_matter.get(
                "title",
                "Untitled",
            )
        )
    )

    publication = html.escape(
        str(
            front_matter.get(
                "publication",
                "",
            )
        )
    )

    doi = str(
        front_matter.get("doi", "")
    ).strip()

    doi = doi.replace(
        "https://doi.org/",
        "",
        1,
    )

    doi = doi.replace(
        "http://doi.org/",
        "",
        1,
    )

    parts = [
        f"{authors_text} ({html.escape(year)}). "
        f"<em>{title}</em>."
    ]

    if publication:
        parts.append(
            f"{publication}."
        )

    if doi:
        doi_url = (
            "https://doi.org/"
            + doi
        )

        parts.append(
            make_link(
                doi_url,
                doi_url,
            )
        )

    return (
        "<li>"
        + " ".join(parts)
        + "</li>"
    )


def build_publications() -> str:
    publications = collect_publications()
    metrics = read_scholar_metrics()

    items = "".join(
        format_publication_html(publication)
        for publication in publications
    )

    return f"""
<section class="cv-section">
  <h2>Publications</h2>

  <div class="metrics-row">
    <div class="metric-box">
      <div class="metric-label">
        Publications
      </div>

      <div class="metric-value">
        {len(publications)}
      </div>
    </div>

    <div class="metric-box">
      <div class="metric-label">
        Citations
      </div>

      <div class="metric-value">
        {metrics.get('citations', 0)}
      </div>
    </div>

    <div class="metric-box">
      <div class="metric-label">
        h-index
      </div>

      <div class="metric-value">
        {metrics.get('h_index', 0)}
      </div>
    </div>
  </div>

  <ol class="pub-list">
    {items}
  </ol>
</section>
"""


def main():
    sections = get_home_sections()
    author = read_yaml(AUTHOR_DATA)

    template = read_text(TEMPLATE_FILE)
    style = read_text(STYLE_FILE)

    replacements = {
        "{{STYLE}}": style,
        "{{BIO}}": build_bio(
            sections,
            author,
        ),
        "{{EDUCATION}}": build_education(
            author
        ),
        "{{INTERESTS}}": build_interests(
            author
        ),
        "{{TRAINING}}": build_markdown_section(
            sections,
            "training",
            "Additional Training",
        ),
        "{{TEACHING}}": build_markdown_section(
            sections,
            "teaching",
            "Teaching & Mentoring",
        ),
        "{{ENGAGEMENT}}": build_markdown_section(
            sections,
            "engagement",
            "Scientific Engagement & Outreach",
        ),
        "{{SKILLS}}": build_markdown_section(
            sections,
            "skills",
            "Skills & Methods",
        ),
        "{{AWARDS}}": build_markdown_section(
            sections,
            "awards",
            "Awards & Grants",
        ),
        "{{PRESENTATIONS}}": build_markdown_section(
            sections,
            "presentations",
            "Presentations",
        ),
        "{{PUBLICATIONS}}": build_publications(),
    }

    output = template

    for key, value in replacements.items():
        output = output.replace(
            key,
            value,
        )

    OUTPUT_HTML.write_text(
        output,
        encoding="utf-8",
    )

    print("CV generated.")


if __name__ == "__main__":
    main()
