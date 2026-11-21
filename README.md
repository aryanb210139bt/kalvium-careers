# Kalvium Careers – job pages with WhatsApp link previews

Paste a job link into WhatsApp and the chat shows a Kalvium hiring poster, the headline **"We're Hiring at Kalvium!"** and a one-line summary of the role. Tapping the preview opens the job page, and its **Apply now** button goes to the application form.

This uses WhatsApp's normal link preview, which reads Open Graph tags. There is no WhatsApp Business API and nothing to pay for.

| | |
|---|---|
| All open roles | https://aryanb210139bt.github.io/kalvium-careers/careers/ |
| Sample job (Noida) | https://aryanb210139bt.github.io/kalvium-careers/careers/academic-relationship-manager-noida/ |
| Bengaluru | https://aryanb210139bt.github.io/kalvium-careers/careers/academic-relationship-manager-bengaluru/ |
| Coimbatore | https://aryanb210139bt.github.io/kalvium-careers/careers/academic-relationship-manager-coimbatore/ |
| HR poster builder | https://aryanb210139bt.github.io/kalvium-careers/admin/ |
| Job list to edit | https://github.com/aryanb210139bt/kalvium-careers/edit/main/jobs.json |

---

## For HR: add a new job

1. Open the **HR poster builder** (link above) and fill in the role. The poster and an approximate WhatsApp preview update as you type.
   - **Poster title** is the short title that goes on the image, e.g. "Academic Relationship Manager".
   - The **URL slug** is filled in for you. Don't change it after the link has been shared.
2. Click **Copy job entry**.
3. Click **Open jobs.json on GitHub**. You must be signed in to GitHub with edit access to the repo.
   - Paste the entry inside `"jobs": [ … ]`.
   - Put a comma between job blocks: `}, {`.
4. Click **Commit changes**.
5. After 1–2 minutes the job page and poster are live at `…/careers/<slug>/`. You can watch progress in the repo's **Actions** tab, where a green tick means it's live.

If you make a mistake in `jobs.json`, such as a missing field, a bad link or a duplicate slug, the build stops with a clear message in the Actions tab. The live site keeps the last good version.

**Edit a job:** in the builder, choose it under "Start from an existing job", change what you need, copy, and replace that job's block in `jobs.json`.

**Close a job:** set `"status": "closed"`.
- The page stays up so links already shared don't break.
- It shows "no longer accepting applications" and has no Apply button.
- It drops off the listing, and the preview title becomes "[Closed] We're Hiring at Kalvium!".

**Hide a job before launch:** set `"status": "draft"`. No page is built.

### Job fields

| Field | Required | Example |
|---|---|---|
| `slug` | ✓ | `academic-relationship-manager-noida` (lowercase, hyphens) |
| `status` | ✓ | `active`, `closed` or `draft` |
| `title` | ✓ | Academic Relationship Manager (ARM) – Counsellor |
| `poster_title` / `poster_subtitle` | | Academic Relationship Manager / ARM – Counsellor |
| `department`, `employment_type` | | Admissions, Full-time |
| `city`, `location` | ✓ | Noida, "Noida, Sector 2" |
| `address` | | Full office address (shown on the page) |
| `work_mode` | ✓ | Work from Office / Hybrid / Remote (shown as WFO / Hybrid / Remote) |
| `experience`, `experience_note` | ✓ / | 0–3 Years, Freshers welcome |
| `ctc`, `fixed_salary`, `variable_salary` | ✓ / / | ₹5 LPA, ₹4 LPA, ₹1 LPA |
| `languages` | | English and Hindi |
| `description` | ✓ | One or two sentences |
| `highlights`, `requirements` | | Lists of short points |
| `application_url` | ✓ | Where **Apply now** goes (https) |
| `jd_url` | | Full JD (e.g. a public Google Drive link) |
| `share_description` | | Overrides the auto preview line |

The preview line is built automatically as **Title | City (WFO) | Experience | CTC**. For example:
`Academic Relationship Manager (ARM) – Counsellor | Noida (WFO) | 0–3 Years | ₹5 LPA`.

---

## Short "I'm interested" form

Give a job a `short_link` (for example `"noida"`) and a `jd_url`, and the build creates a tiny form at `…/kalvium-careers/noida/`. The form has:
- Full name
- Email ID
- a **Read the JD** button
- a required tickbox: *"I have gone through the JD and I'm interested in this job role."*

The page shows the same poster card in WhatsApp. Responses land in the **Interested** tab of the responses Sheet. The columns are Submitted At, Name, Email, Role, City, JD Link, Read JD & Interested and Status (New / Contacted / Applied / Not interested).

Answers are sent to the Apps Script web app (`doPost` in `Code.gs`), whose address is `site.interest_endpoint` in `jobs.json`.

| City | Short form |
|---|---|
| Noida | https://aryanb210139bt.github.io/kalvium-careers/noida/ |
| Bengaluru | https://aryanb210139bt.github.io/kalvium-careers/bengaluru/ |
| Coimbatore | https://aryanb210139bt.github.io/kalvium-careers/coimbatore/ |

---

## Sharing on WhatsApp

1. Copy the job's link, e.g. `https://aryanb210139bt.github.io/kalvium-careers/careers/academic-relationship-manager-noida/`.
2. Paste it into a WhatsApp chat or group. **Wait 2–3 seconds** for the preview card (poster, title, description) to appear above the text box, then send.
   - If you send before the card appears, the message goes out as a plain link.
3. You can write your own message before or after the link. The preview is built from the first link in the message.

For broadcasts, send it to yourself first ("Message yourself") to check the preview, then forward that message. Forwarding keeps the preview.

### Caching: why an old preview can still show

WhatsApp builds the preview **when the message is written** and attaches it to the message. So:

- **Messages already sent never change.** Fixing a typo in the poster won't update cards already in people's chats.
- WhatsApp can also reuse a preview it fetched recently for the **same URL**. If you've changed a job and still see the old card, share the link with a version tag so WhatsApp treats it as new:
  `…/careers/academic-relationship-manager-noida/?v=2`. The page is the same; only the preview is re-fetched.
- The poster image URL already carries a version stamp (`…jpg?v=1f97828d53`) that changes whenever the poster changes. A fresh fetch of the page therefore always picks up the new image.
- GitHub Pages tells caches to keep files for up to 10 minutes. After a change, wait about 10 minutes before re-testing.
- [Meta's Sharing Debugger](https://developers.facebook.com/tools/debug/) (needs a Facebook login) shows the tags Meta's crawler sees and can "Scrape Again". This refreshes Facebook's own cache. It does **not** guarantee WhatsApp's cache refreshes; use `?v=2` for that.

---

## How it works

```
jobs.json ──► build.py ──► _site/
               │  ├─ posters/<slug>.jpg       1200×630 poster (templates/poster.html → headless Chrome → JPEG ~105 KB)
               │  ├─ careers/<slug>/index.html job page with Open Graph + Twitter tags in the HTML (templates/job.html)
               │  ├─ careers/index.html        all open roles (fallback tags + general poster)
               │  ├─ admin/                    HR poster builder (uses the same poster template)
               │  └─ sitemap.xml, robots.txt, 404.html
               └─ runs on every push to main via .github/workflows/deploy.yml → GitHub Pages
```

- **Server-rendered tags.** All tags are written into the HTML at build time, and no JavaScript is needed to read them. WhatsApp's crawler sees them on the first request.
- **Poster template.** `templates/poster.html` uses `{{placeholders}}`. Change the design there once and every poster updates on the next build.
  - Brand colours: red `#F2232A`, background `#0A0A0C`.
  - Fonts are bundled in `assets/fonts` (Bebas Neue for the headline, Inter for text).
  - The logo is `assets/kalvium-logo.png`.
- **Image rules for WhatsApp.**
  - JPEG, 1200×630, about 105 KB. The build keeps it under 300 KB.
  - Public HTTPS with no login or cookies.
  - The `og:image:width` and `og:image:height` tags are set.

### Build locally (optional)

Needs Python 3.9+, Pillow (`pip install Pillow`) and Google Chrome.

```bash
python3 build.py
```

```bash
open _site/posters/academic-relationship-manager-noida.jpg
```

### Custom domain (optional, later)

To use e.g. `careers.kalvium.com`:

1. Add a DNS **CNAME** record `careers → aryanb210139bt.github.io`.
2. In the repo, go to **Settings → Pages → Custom domain**, enter the domain and tick **Enforce HTTPS**.
3. Change `site.base_url` in `jobs.json` to `https://careers.kalvium.com` and commit.

Links already shared on the github.io address will stop working once the domain changes, so switch before sharing widely.

## Costs

**₹0 recurring.**
- GitHub Pages and GitHub Actions are free for public repositories.
- WhatsApp link previews are free.
- No database, image API or paid service is used.

The only optional cost is a custom domain, if Kalvium doesn't already own a suitable one.
