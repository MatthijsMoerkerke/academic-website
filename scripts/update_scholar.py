from pathlib import Path
import re
import time

import requests
import yaml
from bs4 import BeautifulSoup


SCHOLAR_ID = "Dv9Rx2MAAAAJ"

ROOT = Path(__file__).resolve().parents[1]
SCHOLAR_FILE = ROOT / "data" / "scholar.yaml"

PROFILE_URL = (
    "https://scholar.google.com/citations"
    f"?user={SCHOLAR_ID}&hl=en"
)


def read_existing_metrics() -> dict:
    """
    Read the existing metrics so they are preserved when
    Google Scholar temporarily blocks the request.
    """
    if not SCHOLAR_FILE.exists():
        return {
            "citations": 0,
            "h_index": 0,
            "profile": PROFILE_URL,
        }

    data = yaml.safe_load(
        SCHOLAR_FILE.read_text(encoding="utf-8")
    ) or {}

    return {
        "citations": int(data.get("citations", 0) or 0),
        "h_index": int(data.get("h_index", 0) or 0),
        "profile": PROFILE_URL,
    }


def extract_integer(text: str) -> int:
    """
    Convert values such as '1,234' into 1234.
    """
    cleaned = re.sub(r"[^\d]", "", text or "")

    if not cleaned:
        return 0

    return int(cleaned)


def retrieve_scholar_metrics() -> dict:
    """
    Retrieve total citations and h-index directly from the
    public Google Scholar profile.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    }

    response = requests.get(
        PROFILE_URL,
        headers=headers,
        timeout=30,
    )

    print(
        "Google Scholar response:",
        response.status_code,
    )

    response.raise_for_status()

    page_text = response.text.lower()

    blocked_markers = [
        "unusual traffic",
        "not a robot",
        "captcha",
        "our systems have detected",
    ]

    if any(marker in page_text for marker in blocked_markers):
        raise RuntimeError(
            "Google Scholar returned a bot-verification page."
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    metric_cells = soup.select(
        "#gsc_rsb_st td.gsc_rsb_std"
    )

    if len(metric_cells) < 4:
        raise RuntimeError(
            "Google Scholar metrics table was not found. "
            "The request may have been blocked or the page "
            "structure may have changed."
        )

    # Google Scholar table:
    # 0 = citations all
    # 1 = citations since recent year
    # 2 = h-index all
    # 3 = h-index since recent year
    citations = extract_integer(
        metric_cells[0].get_text(strip=True)
    )

    h_index = extract_integer(
        metric_cells[2].get_text(strip=True)
    )

    if citations <= 0:
        raise RuntimeError(
            "A valid citation count was not found."
        )

    return {
        "citations": citations,
        "h_index": h_index,
        "profile": PROFILE_URL,
    }


def write_metrics(data: dict) -> None:
    SCHOLAR_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    SCHOLAR_FILE.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def main() -> None:
    existing = read_existing_metrics()

    last_error = None

    for attempt in range(1, 4):
        try:
            print(
                f"Retrieving Scholar metrics, attempt "
                f"{attempt} of 3..."
            )

            updated = retrieve_scholar_metrics()

            print(
                "Scholar metrics retrieved:",
                f"citations={updated['citations']},",
                f"h-index={updated['h_index']}",
            )

            write_metrics(updated)

            print(
                f"Scholar metrics written to {SCHOLAR_FILE}"
            )

            return

        except Exception as error:
            last_error = error

            print(
                f"Attempt {attempt} failed: {error}"
            )

            if attempt < 3:
                time.sleep(15 * attempt)

    print(
        "Google Scholar could not be reached after "
        "three attempts."
    )

    print(
        "Preserving existing metrics:",
        f"citations={existing['citations']},",
        f"h-index={existing['h_index']}",
    )

    write_metrics(existing)

    print(
        "Scholar metrics were not updated because Google Scholar "
        "blocked the request. Existing metrics were preserved."
    )

    return
    main()
