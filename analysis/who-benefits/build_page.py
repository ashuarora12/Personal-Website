"""Embed output/dashboard_data.json into page_template.html -> the site page."""
from pathlib import Path

HERE = Path(__file__).parent
SITE_PAGE = HERE.parent.parent / "ashu-arora-complete-website" / "who-benefits.html"

template = (HERE / "page_template.html").read_text()
data = (HERE / "output" / "dashboard_data.json").read_text()
assert "/*__DATA__*/null" in template
# keep the JSON from closing the script tag
data = data.replace("</", "<\\/")
SITE_PAGE.write_text(template.replace("/*__DATA__*/null", data))
print(f"wrote {SITE_PAGE} ({SITE_PAGE.stat().st_size / 1024:.0f} KB)")
