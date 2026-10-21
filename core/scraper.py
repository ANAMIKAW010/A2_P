"""Polite, best-effort species enrichment from Wikipedia pages."""
from __future__ import annotations
import re
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "BioEcho/1.0 (educational bioacoustic inventory; contact: local app)"}

def fetch_species_enrichment(species_name: str) -> dict[str, str]:
    empty = {"image_url": "", "summary": "Species information could not be retrieved.", "habitat": "Not available on the page.", "diet": "Not available on the page.", "behavior": "Not available on the page.", "source_url": ""}
    if not species_name.strip(): return empty
    url = "https://en.wikipedia.org/wiki/" + quote(species_name.strip().replace(" ", "_"))
    result = dict(empty)
    result["source_url"] = url
    try:
        response = requests.get(url, headers=HEADERS, timeout=(3.05, 8))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if not content: return result
        image = content.select_one("table.infobox img")
        if image:
            src = image.get("src", "")
            result["image_url"] = "https:" + src if src.startswith("//") else src

        paragraphs = [p.get_text(" ", strip=True) for p in content.find_all("p", recursive=False) if p.get_text(strip=True)]
        result["summary"] = re.sub(r"\[\d+\]", "", " ".join(paragraphs[:1])) or result["summary"]

        labels = {"habitat": ("habitat",), "diet": ("diet", "feeding"), "behavior": ("behavior", "behaviour", "lifestyle")}
        for key, terms in labels.items():
            for heading in content.find_all(["h2", "h3"]):
                title = heading.get_text(" ", strip=True).lower()
                if any(term in title for term in terms):
                    pieces = []
                    for node in heading.find_all_next():
                        if node.name in ("h2", "h3"): break
                        if node.name == "p":
                            text = node.get_text(" ", strip=True)
                            if text: pieces.append(text)
                        if sum(map(len, pieces)) > 300: break
                    if pieces:
                        text_chunk = re.sub(r"\[\d+\]", "", " ".join(pieces))[:350]
                        result[key] = text_chunk + ("..." if len(text_chunk) == 350 else "")
                    break
    except (requests.RequestException, ValueError, AttributeError):
        pass
    finally:
        pass
    return result