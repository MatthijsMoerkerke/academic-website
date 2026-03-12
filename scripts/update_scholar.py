import requests
import re
from pathlib import Path

SCHOLAR_ID = "Dv9Rx2MAAAAJ"
URL = f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en"

headers = {
    "User-Agent": "Mozilla/5.0"
}

html = requests.get(URL, headers=headers).text

citations = re.search(r'Cited by</a></td><td class="gsc_rsb_std">(\d+)', html)
hindex = re.search(r'h-index</a></td><td class="gsc_rsb_std">(\d+)', html)

citations = citations.group(1) if citations else "0"
hindex = hindex.group(1) if hindex else "0"

data = f"""citations: {citations}
h_index: {hindex}
profile: https://scholar.google.com/citations?user={SCHOLAR_ID}
"""

Path("data/scholar.yaml").write_text(data)

print("Scholar metrics updated.")
