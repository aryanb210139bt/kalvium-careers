#!/usr/bin/env python3
"""Build the Kalvium Careers static site from jobs.json.

For every job with status "active" or "closed" it:
  1. renders a 1200x630 hiring poster (templates/poster.html -> headless Chrome -> JPEG)
  2. writes careers/<slug>/index.html with server-side Open Graph + Twitter tags
Then it writes the listing page, sitemap, robots.txt, 404 page and the HR helper (/admin/).

Usage:  python3 build.py            (output in _site/)
Needs:  Python 3.9+, Pillow, Google Chrome / Chromium (set CHROME=/path if not found)
"""
import hashlib, html, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
TPL = ROOT / "templates"
STATUSES = {"active", "closed", "draft"}
REQUIRED = ["slug", "status", "title", "city", "location", "work_mode", "experience", "ctc",
            "description", "application_url"]
MODE_SHORT = {"work from office": "WFO", "remote": "Remote", "hybrid": "Hybrid", "work from home": "WFH"}
MAX_IMAGE_KB = 300  # WhatsApp is unreliable with large og:images; keep posters well under this


def esc(v):
    return html.escape(str(v or ""), quote=True)


def fill(template, values):
    """Replace {{key}} placeholders. Values are inserted as given (escape before calling)."""
    def rep(m):
        k = m.group(1)
        if k not in values:
            raise KeyError(f"template placeholder {{{{{k}}}}} has no value")
        return str(values[k])
    return re.sub(r"\{\{(\w+)\}\}", rep, template)


def headline_html(text):
    t = esc(text)
    return t[:-1] + "<b>!</b>" if t.endswith("!") else t


def find_chrome():
    cands = [os.environ.get("CHROME"),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             shutil.which("google-chrome"), shutil.which("google-chrome-stable"),
             shutil.which("chromium"), shutil.which("chromium-browser")]
    for c in cands:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome/Chromium not found. Install it or set CHROME=/path/to/chrome")


def validate(data):
    errors, seen = [], set()
    site = data.get("site", {})
    if not str(site.get("base_url", "")).startswith("https://"):
        errors.append("site.base_url must be an https:// URL")
    for i, j in enumerate(data.get("jobs", [])):
        name = j.get("slug") or f"job #{i + 1}"
        for k in REQUIRED:
            if not str(j.get(k, "")).strip():
                errors.append(f"{name}: missing '{k}'")
        slug = j.get("slug", "")
        if slug and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            errors.append(f"{name}: slug must be lowercase letters, numbers and hyphens only")
        if slug in seen:
            errors.append(f"{name}: duplicate slug")
        seen.add(slug)
        if j.get("status") not in STATUSES:
            errors.append(f"{name}: status must be one of {sorted(STATUSES)}")
        for k in ("application_url", "jd_url"):
            if j.get(k) and not str(j[k]).startswith("https://"):
                errors.append(f"{name}: {k} must start with https://")
    if errors:
        sys.exit("jobs.json has problems:\n  - " + "\n  - ".join(errors))


def share_description(j):
    if j.get("share_description"):
        return j["share_description"]
    mode = MODE_SHORT.get(j["work_mode"].strip().lower(), j["work_mode"])
    return f'{j["title"]} | {j["city"]} ({mode}) | {j["experience"]} | {j["ctc"]}'


def poster_values(site, title, subtitle, location, experience, ctc, footer, assets):
    return {
        "assets": assets,
        "headline": headline_html(site["headline"]),
        "subhead": esc(site["subhead"]),
        "title": esc(title), "subtitle": esc(subtitle),
        "location": esc(location), "experience": esc(experience), "ctc": esc(ctc),
        "employment": "", "work_mode": "", "footer": esc(footer),
    }


def job_poster_fields(j):
    mode = MODE_SHORT.get(j["work_mode"].strip().lower(), j["work_mode"])
    footer = " · ".join(x for x in [j.get("employment_type"), j["work_mode"], j.get("experience_note")] if x)
    return dict(title=j.get("poster_title") or j["title"], subtitle=j.get("poster_subtitle", ""),
                location=f'{j["city"]} · {mode}', experience=j["experience"], ctc=j["ctc"], footer=footer)


def render_poster(chrome, poster_tpl, values, dest):
    """Render poster HTML to a 1200x630 JPEG (supersampled at 2x for crisp text)."""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "poster.html"
        png = Path(td) / "poster.png"
        src.write_text(fill(poster_tpl, values), encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--window-size=1200,630",
                        "--virtual-time-budget=4000", "--allow-file-access-from-files",
                        f"--screenshot={png}", src.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        img = Image.open(png).convert("RGB")
        if img.size != (2400, 1260):
            img = img.crop((0, 0, 2400, 1260))
        img = img.resize((1200, 630), Image.LANCZOS)
        img.save(dest, "JPEG", quality=88, optimize=True, progressive=True)
    kb = dest.stat().st_size / 1024
    if kb > MAX_IMAGE_KB:
        Image.open(dest).save(dest, "JPEG", quality=78, optimize=True, progressive=True)
        kb = dest.stat().st_size / 1024
    return kb


def version_of(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
    return h.hexdigest()[:10]


def ul_section(title, items):
    if not items:
        return ""
    lis = "".join(f"<li>{esc(x)}</li>" for x in items)
    return f'<section class="card"><h2>{esc(title)}</h2><ul>{lis}</ul></section>'


def build_job_page(job_tpl, site, j, url, image, assets, home):
    closed = j["status"] == "closed"
    desc = share_description(j)
    split = (f'{j["fixed_salary"]} fixed + {j["variable_salary"]} variable'
             if j.get("fixed_salary") and j.get("variable_salary") else "")
    apply_btns = (f'<div class="btns"><a class="btn p" href="{esc(j["application_url"])}" rel="noopener">Apply now →</a>'
                  + (f'<a class="btn s" href="{esc(j["jd_url"])}" rel="noopener">View full JD</a>' if j.get("jd_url") else "")
                  + "</div>")
    addr = (f'<section class="card"><h2>Work location</h2><p class="addr">{esc(j["address"])}</p></section>'
            if j.get("address") else "")
    long_desc = j["description"]
    if j.get("languages"):
        long_desc += f' You should be comfortable speaking {j["languages"]}.'
    return fill(job_tpl, {
        "page_title": esc(f'{j["title"]} – {j["city"]} | {site["site_name"]}'),
        "description": esc(desc),
        "url": esc(url), "image": esc(image), "assets": assets, "home": home,
        "site_name": esc(site["site_name"]),
        "og_title": esc(("[Closed] " if closed else "") + site["share_title"]),
        "image_alt": esc(f'Kalvium is hiring: {j["title"]}, {j["city"]}, {j["experience"]}, {j["ctc"]}'),
        "robots": '<meta name="robots" content="noindex">' if closed else "",
        "closed_banner": '<div class="closed">This role is no longer accepting applications. See other open roles below.</div>' if closed else "",
        "department": esc(j.get("department", "Kalvium")), "employment_type": esc(j.get("employment_type", "")),
        "title": esc(j["title"]), "long_description": esc(long_desc),
        "location": esc(j["location"]), "work_mode": esc(j["work_mode"]),
        "experience": esc(j["experience"]), "experience_note": esc(j.get("experience_note", "")),
        "ctc": esc(j["ctc"]), "ctc_split": esc(split),
        "apply_block": "" if closed else apply_btns,
        "highlights": ul_section("What you'll do", j.get("highlights")),
        "requirements": ul_section("Who we're looking for", j.get("requirements")),
        "address_block": addr,
        "apply_bottom": "" if closed else f'<div class="cta-end">{apply_btns}</div>',
    })


def listing_page(site, jobs, base, image, url, assets):
    cards = "".join(
        f'<a class="job" href="{esc(base)}/careers/{j["slug"]}/"><h3>{esc(j["title"])}</h3>'
        f'<div class="meta">{esc(j["location"])} · {esc(j["work_mode"])} · {esc(j["experience"])} · {esc(j["ctc"])}</div>'
        f'<div class="go">View &amp; apply →</div></a>' for j in jobs) or '<p class="empty">No open roles right now. Check back soon.</p>'
    d = esc(site["default_description"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(site["site_name"])} – Open roles at Kalvium</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(site["site_name"])}">
<meta property="og:title" content="{esc(site["share_title"])}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(image)}">
<meta property="og:image:secure_url" content="{esc(image)}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Kalvium is hiring">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(site["share_title"])}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{esc(image)}">
<meta name="theme-color" content="#0A0A0C">
<link rel="icon" type="image/png" href="{assets}/favicon.png">
<link rel="stylesheet" href="{assets}/site.css">
</head><body>
<header class="top"><div class="in"><a class="brand" href="{esc(base)}/careers/"><img src="{assets}/kalvium-logo.png" alt="Kalvium logo">Kalvium <span>Careers</span></a></div></header>
<main class="in">
<section class="hero"><h1>{headline_html(site["headline"])}</h1><p>{esc(site["subhead"])}</p></section>
<div class="jobs">{cards}</div>
</main>
<footer class="foot"><div class="in">© Kalvium · <a href="https://kalvium.com/">kalvium.com</a></div></footer>
</body></html>
"""


def main():
    data = json.loads((ROOT / "jobs.json").read_text(encoding="utf-8"))
    validate(data)
    site = data["site"]
    base = site["base_url"].rstrip("/")
    chrome = find_chrome()
    poster_tpl = (TPL / "poster.html").read_text(encoding="utf-8")
    job_tpl = (TPL / "job.html").read_text(encoding="utf-8")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posters").mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    logo = Image.open(ROOT / "assets" / "kalvium-logo.png").convert("RGBA")
    logo.thumbnail((64, 64), Image.LANCZOS)
    fav = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    fav.paste(logo, ((64 - logo.width) // 2, (64 - logo.height) // 2), logo)
    fav.save(OUT / "assets" / "favicon.png")
    (OUT / ".nojekyll").write_text("")

    asset_bytes = b"".join(p.read_bytes() for p in sorted((ROOT / "assets").rglob("*")) if p.is_file())
    local_assets = (ROOT / "assets").as_uri()
    built, report = [], []

    for j in data["jobs"]:
        if j["status"] == "draft":
            report.append(f'  skip   {j["slug"]} (draft)')
            continue
        values = poster_values(site, assets=local_assets, **job_poster_fields(j))
        ver = version_of(poster_tpl, json.dumps(values, sort_keys=True), asset_bytes)
        kb = render_poster(chrome, poster_tpl, values, OUT / "posters" / f'{j["slug"]}.jpg')
        url = f'{base}/careers/{j["slug"]}/'
        image = f'{base}/posters/{j["slug"]}.jpg?v={ver}'
        page = build_job_page(job_tpl, site, j, url, image, f"{base}/assets", f"{base}/careers/")
        d = OUT / "careers" / j["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        built.append(j)
        report.append(f'  {j["status"]:<6} {url}   (poster {kb:.0f} KB)')

    active = [j for j in built if j["status"] == "active"]
    cities = list(dict.fromkeys(j["city"] for j in active))
    gen = poster_values(site, title="Explore open roles",
                        subtitle=f"{len(active)} open role{'s' if len(active) != 1 else ''} · Apply online",
                        location=" · ".join(cities) if len(cities) <= 3 else f"{len(cities)} cities",
                        experience="", ctc="", footer="Kalvium Careers", assets=local_assets)
    gver = version_of(poster_tpl, json.dumps(gen, sort_keys=True), asset_bytes)
    render_poster(chrome, poster_tpl, gen, OUT / "posters" / "careers.jpg")
    gimage = f"{base}/posters/careers.jpg?v={gver}"
    listing = listing_page(site, active, base, gimage, f"{base}/careers/", f"{base}/assets")
    (OUT / "careers").mkdir(exist_ok=True)
    (OUT / "careers" / "index.html").write_text(listing, encoding="utf-8")
    (OUT / "index.html").write_text(listing, encoding="utf-8")
    (OUT / "404.html").write_text(listing.replace("<main class=\"in\">",
        "<main class=\"in\"><div class=\"closed\" style=\"margin-top:20px\">That page doesn't exist. Here are our open roles.</div>", 1),
        encoding="utf-8")

    urls = [f"{base}/careers/"] + [f'{base}/careers/{j["slug"]}/' for j in active]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nDisallow: /admin/\nSitemap: {base}/sitemap.xml\n")

    # HR helper: same poster template, filled in the browser for a live preview
    (OUT / "admin").mkdir()
    shutil.copy(ROOT / "admin" / "index.html", OUT / "admin" / "index.html")
    (OUT / "admin" / "poster-template.html").write_text(poster_tpl, encoding="utf-8")
    (OUT / "admin" / "site.json").write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
    shutil.copy(ROOT / "jobs.json", OUT / "admin" / "jobs.json")

    print("Built", len(built), "job page(s) into", OUT)
    print("\n".join(report))
    print(f"  list   {base}/careers/")


if __name__ == "__main__":
    main()
