#!/usr/bin/env python3
"""
generate_review.py — Genera páginas HTML de reviews para toolsbrief.com
Uso:
  python3 generate_review.py                  # genera todas las de tools_queue.json
  python3 generate_review.py --slug notion-ai # genera solo una
  python3 generate_review.py --list           # muestra la cola pendiente
"""
import json, os, re, sys, argparse, requests
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent

OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:7b"   # mejor inglés que llama3.2


def ollama(prompt, system="You are a professional tech reviewer writing for toolsbrief.com. Tone: direct, honest, no fluff. British/international English."):
    r = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        "options": {"temperature": 0.65, "num_predict": 400},
        "stream": False
    }, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def stars_html(rating):
    full  = int(rating)
    half  = 1 if (rating - full) >= 0.3 else 0
    empty = 5 - full - half
    s  = '<span class="star star-filled">★</span>' * full
    s += '<span class="star star-half">★</span>'   * half
    s += '<span class="star star-empty">★</span>'  * empty
    return s


def rating_bars_html(breakdown):
    bars = ""
    for label, val in breakdown.items():
        pct = int(val / 5 * 100)
        bars += f"""
      <div class="rating-item">
        <span class="rating-label">{label}</span>
        <div class="rating-bar-bg"><div class="rating-bar-fill" style="width:{pct}%"></div></div>
        <span class="rating-val">{val}</span>
      </div>"""
    return bars


def pricing_rows_html(plans):
    rows = ""
    for i, p in enumerate(plans):
        highlight = ' class="plan-highlight"' if i == 1 else ""
        rows += f"""
        <tr{highlight}>
          <td><span class="plan-name">{p['name']}</span></td>
          <td>{p['price']}</td>
          <td>{p['features']}</td>
        </tr>"""
    return rows


def features_html(features):
    cards = ""
    for f in features:
        cards += f"""
      <div class="feature-card">
        <div class="feature-icon">{f['icon']}</div>
        <h3>{f['name']}</h3>
        <p>{f['desc']}</p>
      </div>"""
    return cards


def profiles_html(best_for):
    cards = ""
    for p in best_for:
        cards += f"""
      <div class="profile-card">
        <div class="profile-emoji">{p['emoji']}</div>
        <h3>{p['type']}</h3>
        <p>{p['desc']}</p>
      </div>"""
    return cards


def pros_html(items):
    return "\n".join(f"          <li>{i}</li>" for i in items)


def cons_html(items):
    return "\n".join(f"          <li>{i}</li>" for i in items)


def generate_what_is(tool):
    return ollama(
        f"Write 3 paragraphs (150-200 words total) explaining what {tool['name']} is. "
        f"Cover: what it does, who makes it, how it works, and what problem it solves. "
        f"Category: {tool['category']}. Price: from {tool['price_from']}. "
        f"Do NOT use bullet points. Pure prose only. Do not start with the tool name."
    )


def generate_verdict_extra(tool):
    return ollama(
        f"Write 2 short paragraphs (80-100 words) as a final verdict supplement for {tool['name']}. "
        f"The main verdict is already written: \"{tool['verdict_text'][:200]}...\". "
        f"Add nuance about edge cases or specific user scenarios. "
        f"End with a clear recommendation sentence. No bullet points."
    )


def build_html(tool, what_is_text):
    month_year  = datetime.now().strftime("%B %Y")
    year        = datetime.now().year
    date_iso    = datetime.now().strftime("%Y-%m-%d")
    rating      = tool["rating"]
    rating_int  = int(rating * 10)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{tool['name']} Review {year}: Honest Assessment | toolsbrief</title>
  <meta name="description" content="Honest {tool['name']} review for {year}. We tested it thoroughly. Full breakdown of features, pricing, pros & cons — and a clear verdict.">
  <link rel="canonical" href="https://toolsbrief.com/reviews/{tool['slug']}">
  <meta property="og:title" content="{tool['name']} Review {year}: Honest Assessment">
  <meta property="og:description" content="Full {tool['name']} review — features, pricing, who it's for. No fluff.">
  <meta property="og:url" content="https://toolsbrief.com/reviews/{tool['slug']}">
  <meta property="og:type" content="article">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Review",
    "name": "{tool['name']} Review {year}",
    "reviewBody": "{tool['verdict_text'][:250].replace(chr(34), chr(39))}",
    "reviewRating": {{
      "@type": "Rating",
      "ratingValue": "{rating}",
      "bestRating": "5",
      "worstRating": "1"
    }},
    "author": {{"@type": "Organization", "name": "toolsbrief"}},
    "itemReviewed": {{
      "@type": "SoftwareApplication",
      "name": "{tool['name']}",
      "applicationCategory": "{tool['category']}"
    }},
    "datePublished": "{date_iso}",
    "publisher": {{"@type": "Organization", "name": "toolsbrief", "url": "https://toolsbrief.com"}}
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://toolsbrief.com"}},
      {{"@type": "ListItem", "position": 2, "name": "Reviews", "item": "https://toolsbrief.com/reviews"}},
      {{"@type": "ListItem", "position": 3, "name": "{tool['name']} Review", "item": "https://toolsbrief.com/reviews/{tool['slug']}"}}
    ]
  }}
  </script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #0F0F11; color: #FAFAFA; line-height: 1.7; font-size: 1rem; }}
    a {{ color: #818CF8; text-decoration: none; }} a:hover {{ color: #6366F1; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 0 1.5rem; }}
    .breadcrumb {{ padding: 1rem 0; font-size: 0.8rem; color: #A1A1AA; display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }}
    .breadcrumb a {{ color: #A1A1AA; }} .breadcrumb a:hover {{ color: #FAFAFA; }} .breadcrumb-sep {{ color: #3F3F46; }}
    .hero {{ padding: 2.5rem 0 2rem; border-bottom: 1px solid #27272A; }}
    .hero-meta {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.25rem; }}
    .badge-category {{ background: rgba(99,102,241,0.15); color: #818CF8; border: 1px solid rgba(99,102,241,0.3); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }}
    .badge-updated {{ background: #18181B; color: #A1A1AA; border: 1px solid #27272A; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 500; }}
    .badge-paid {{ background: rgba(249,115,22,0.15); color: #F97316; border: 1px solid rgba(249,115,22,0.3); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }}
    .badge-free {{ background: rgba(34,197,94,0.15); color: #22C55E; border: 1px solid rgba(34,197,94,0.3); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }}
    .hero h1 {{ font-size: clamp(1.75rem, 4vw, 2.5rem); font-weight: 900; letter-spacing: -0.03em; line-height: 1.15; margin-bottom: 0.75rem; }}
    .hero-subtitle {{ font-size: 1.1rem; color: #A1A1AA; max-width: 640px; margin-bottom: 1.5rem; }}
    .rating-row {{ display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }}
    .stars {{ display: flex; gap: 0.2rem; }} .star {{ font-size: 1.3rem; }}
    .star-filled {{ color: #F59E0B; }} .star-half {{ color: #F59E0B; }} .star-empty {{ color: #3F3F46; }}
    .rating-num {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em; }}
    .rating-max {{ color: #A1A1AA; font-size: 0.9rem; margin-left: 0.2rem; }}
    .price-tag {{ font-size: 1rem; color: #A1A1AA; }} .price-tag strong {{ color: #FAFAFA; font-size: 1.1rem; }}
    .quick-box {{ background: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 1.5rem; margin: 2rem 0; }}
    .quick-box h3 {{ font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #A1A1AA; margin-bottom: 1rem; }}
    .pros-cons {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
    @media (max-width: 600px) {{ .pros-cons {{ grid-template-columns: 1fr; }} }}
    .pros-list, .cons-list {{ list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }}
    .pros-list li::before {{ content: "✓ "; color: #22C55E; font-weight: 700; }}
    .cons-list li::before {{ content: "✗ "; color: #F97316; font-weight: 700; }}
    .pros-list li, .cons-list li {{ font-size: 0.9rem; color: #D4D4D8; }}
    .pros-title {{ font-weight: 700; color: #22C55E; font-size: 0.85rem; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .cons-title {{ font-weight: 700; color: #F97316; font-size: 0.85rem; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .section {{ padding: 2.5rem 0; border-bottom: 1px solid #27272A; }}
    .section h2 {{ font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 1.25rem; }}
    .section p {{ color: #D4D4D8; margin-bottom: 1rem; }} .section p:last-child {{ margin-bottom: 0; }}
    .features-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
    .feature-card {{ background: #18181B; border: 1px solid #27272A; border-radius: 10px; padding: 1.25rem; transition: border-color 0.2s; }}
    .feature-card:hover {{ border-color: #3F3F46; }}
    .feature-icon {{ font-size: 1.5rem; margin-bottom: 0.75rem; }}
    .feature-card h3 {{ font-size: 0.95rem; font-weight: 700; margin-bottom: 0.4rem; }}
    .feature-card p {{ font-size: 0.85rem; color: #A1A1AA; margin: 0; }}
    .pricing-table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; font-size: 0.9rem; }}
    .pricing-table th {{ background: #18181B; color: #A1A1AA; font-weight: 600; text-align: left; padding: 0.75rem 1rem; border: 1px solid #27272A; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .pricing-table td {{ padding: 0.75rem 1rem; border: 1px solid #27272A; color: #D4D4D8; vertical-align: top; }}
    .pricing-table tr:hover td {{ background: #18181B; }}
    .plan-name {{ font-weight: 700; color: #FAFAFA; }}
    .plan-highlight {{ background: rgba(99,102,241,0.07) !important; }}
    .plan-highlight td {{ border-color: rgba(99,102,241,0.2) !important; }}
    .profiles-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
    .profile-card {{ background: #18181B; border: 1px solid #27272A; border-radius: 10px; padding: 1.25rem; }}
    .profile-emoji {{ font-size: 2rem; margin-bottom: 0.75rem; }}
    .profile-card h3 {{ font-size: 0.95rem; font-weight: 700; margin-bottom: 0.4rem; }}
    .profile-card p {{ font-size: 0.85rem; color: #A1A1AA; margin: 0; }}
    .verdict {{ background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(79,70,229,0.1) 100%); border: 1px solid rgba(99,102,241,0.35); border-radius: 14px; padding: 2rem; margin: 2.5rem 0; }}
    .verdict-label {{ font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #818CF8; margin-bottom: 0.75rem; }}
    .verdict h2 {{ font-size: 1.4rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 1rem; }}
    .verdict p {{ color: #D4D4D8; margin-bottom: 0.75rem; }} .verdict p:last-child {{ margin-bottom: 0; }}
    .verdict-score {{ display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); padding: 0.4rem 1rem; border-radius: 999px; font-weight: 700; font-size: 1rem; color: #FAFAFA; margin-top: 1rem; }}
    .cta-section {{ text-align: center; padding: 2.5rem 0; }}
    .cta-btn {{ display: inline-block; background: #6366F1; color: #FAFAFA; font-weight: 700; font-size: 1.05rem; padding: 0.9rem 2.25rem; border-radius: 10px; text-decoration: none; transition: background 0.2s, transform 0.15s; }}
    .cta-btn:hover {{ background: #4F46E5; color: #FAFAFA; transform: translateY(-1px); }}
    .cta-affiliate-note {{ font-size: 0.78rem; color: #71717A; margin-top: 0.6rem; }}
    .disclosure {{ background: #18181B; border: 1px solid #27272A; border-radius: 8px; padding: 1rem 1.25rem; font-size: 0.8rem; color: #71717A; margin: 1.5rem 0; }}
    .rating-breakdown {{ margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }}
    .rating-item {{ display: flex; align-items: center; gap: 1rem; font-size: 0.85rem; }}
    .rating-label {{ color: #A1A1AA; width: 140px; flex-shrink: 0; }}
    .rating-bar-bg {{ flex: 1; background: #27272A; border-radius: 999px; height: 6px; overflow: hidden; }}
    .rating-bar-fill {{ background: linear-gradient(90deg, #6366F1, #818CF8); height: 6px; border-radius: 999px; }}
    .rating-val {{ color: #FAFAFA; font-weight: 600; width: 28px; text-align: right; flex-shrink: 0; }}
  </style>
</head>
<body>

<nav style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.5rem;border-bottom:1px solid #27272A;position:sticky;top:0;background:rgba(15,15,17,0.95);backdrop-filter:blur(8px);z-index:50;">
  <a href="/" style="font-size:1.15rem;font-weight:900;letter-spacing:-0.04em;color:#FAFAFA;text-decoration:none;">tools<span style="color:#818CF8">brief</span></a>
  <div style="display:flex;gap:1.5rem;font-size:0.85rem;color:#A1A1AA;">
    <a href="/reviews" style="color:#A1A1AA;text-decoration:none;">Reviews</a>
    <a href="/comparisons" style="color:#A1A1AA;text-decoration:none;">Comparisons</a>
    <a href="/best-tools" style="color:#A1A1AA;text-decoration:none;">Best Tools</a>
  </div>
</nav>

<div class="container">

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">Home</a><span class="breadcrumb-sep">›</span>
    <a href="/reviews">Reviews</a><span class="breadcrumb-sep">›</span>
    <span style="color:#FAFAFA;">{tool['name']}</span>
  </nav>

  <div class="hero">
    <div class="hero-meta">
      <span class="badge-category">{tool['category']}</span>
      <span class="badge-{'free' if tool['pricing_type'] == 'FREEMIUM' else 'paid'}">{tool['pricing_type']}</span>
      <span class="badge-updated">Updated {month_year}</span>
    </div>
    <h1>{tool['name']} Review {year}: {tool['verdict_title'].split(':')[1].strip() if ':' in tool['verdict_title'] else 'Full Honest Assessment'}</h1>
    <p class="hero-subtitle">{tool['verdict_text'][:160].rstrip()}...</p>
    <div class="rating-row">
      <div style="display:flex;align-items:center;gap:0.75rem;">
        <div class="stars" aria-label="{rating} out of 5 stars">
          {stars_html(rating)}
        </div>
        <span class="rating-num">{rating}</span><span class="rating-max">/5</span>
      </div>
      <div class="price-tag">From <strong>{tool['price_from']}</strong></div>
    </div>
  </div>

  <div class="quick-box">
    <h3>Quick Summary</h3>
    <div class="pros-cons">
      <div>
        <div class="pros-title">Pros</div>
        <ul class="pros-list">
{pros_html(tool['pros'])}
        </ul>
      </div>
      <div>
        <div class="cons-title">Cons</div>
        <ul class="cons-list">
{cons_html(tool['cons'])}
        </ul>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>What is {tool['name']}?</h2>
    {chr(10).join(f'    <p>{p.strip()}</p>' for p in what_is_text.split(chr(10)) if p.strip())}
  </div>

  <div class="section">
    <h2>Rating Breakdown</h2>
    <div class="rating-breakdown">
{rating_bars_html(tool['ratings_breakdown'])}
    </div>
  </div>

  <div class="section">
    <h2>Key Features</h2>
    <div class="features-grid">
{features_html(tool['features'])}
    </div>
  </div>

  <div class="section">
    <h2>{tool['name']} Pricing ({year})</h2>
    <p>{tool['price_note']}. Plans start from {tool['price_from']}.</p>
    <table class="pricing-table">
      <thead>
        <tr><th>Plan</th><th>Price</th><th>Key Features</th></tr>
      </thead>
      <tbody>
{pricing_rows_html(tool['pricing_plans'])}
      </tbody>
    </table>
  </div>

  <div class="section">
    <h2>Who Is {tool['name']} For?</h2>
    <div class="profiles-grid">
{profiles_html(tool['best_for'])}
    </div>
  </div>

  <div class="verdict">
    <div class="verdict-label">⚡ The Verdict</div>
    <h2>{tool['verdict_title']}</h2>
    {chr(10).join(f'    <p>{p.strip()}</p>' for p in tool['verdict_text'].split(chr(10)) if p.strip())}
    <div class="verdict-score"><span>★</span> <span>{rating} / 5 — {('Highly Recommended' if rating >= 4.5 else 'Recommended' if rating >= 4.0 else 'Worth Considering')}</span></div>
  </div>

  <div class="cta-section">
    <a href="{tool['affiliate_url']}?ref=toolsbrief" class="cta-btn" rel="nofollow sponsored" target="_blank">Try {tool['name']} →</a>
    <div class="cta-affiliate-note">(affiliate link — we may earn a commission at no cost to you)</div>
  </div>

  <div class="disclosure">
    <strong>Affiliate Disclosure:</strong> This review may contain affiliate links. If you purchase through our link, toolsbrief may earn a commission at no additional cost to you. This does not influence our rating or editorial opinion. Read our full <a href="/affiliate-disclosure">affiliate disclosure policy</a>.
  </div>

</div>

<footer style="border-top:1px solid #27272A;padding:2rem 1.5rem;text-align:center;font-size:0.78rem;color:#A1A1AA;">
  <div style="margin-bottom:0.5rem;"><strong style="color:#FAFAFA">toolsbrief.com</strong> — Honest reviews of AI &amp; software tools</div>
  <div style="display:flex;gap:1.5rem;justify-content:center;margin-bottom:0.5rem;flex-wrap:wrap;">
    <a href="/reviews" style="color:#A1A1AA;text-decoration:none;">Reviews</a>
    <a href="/comparisons" style="color:#A1A1AA;text-decoration:none;">Comparisons</a>
    <a href="/affiliate-disclosure" style="color:#A1A1AA;text-decoration:none;">Affiliate Disclosure</a>
    <a href="/privacy" style="color:#A1A1AA;text-decoration:none;">Privacy</a>
  </div>
  <div>Some links are affiliate links. We may earn a commission at no extra cost to you.</div>
</footer>

</body>
</html>"""


def update_sitemap(slugs):
    sitemap_path = ROOT / "sitemap.xml"
    existing = sitemap_path.read_text()
    date = datetime.now().strftime("%Y-%m-%d")
    added = 0
    for slug in slugs:
        url = f"https://toolsbrief.com/reviews/{slug}"
        if url not in existing:
            entry = f'  <url><loc>{url}</loc><priority>0.9</priority><changefreq>monthly</changefreq><lastmod>{date}</lastmod></url>\n'
            existing = existing.replace("</urlset>", entry + "</urlset>")
            added += 1
    sitemap_path.write_text(existing)
    print(f"Sitemap: {added} URLs añadidas")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="Generar solo este slug")
    parser.add_argument("--list", action="store_true", help="Mostrar cola pendiente")
    args = parser.parse_args()

    queue = json.loads((ROOT / "tools_queue.json").read_text())
    reviews_dir = ROOT / "reviews"

    if args.list:
        for t in queue:
            exists = (reviews_dir / f"{t['slug']}.html").exists()
            status = "✅ ya existe" if exists else "⏳ pendiente"
            print(f"  {t['slug']:30} {status}")
        return

    tools_to_process = [t for t in queue if t["slug"] == args.slug] if args.slug else queue

    new_slugs = []
    for tool in tools_to_process:
        out_path = reviews_dir / f"{tool['slug']}.html"
        if out_path.exists() and not args.slug:
            print(f"  Saltando {tool['slug']} (ya existe)")
            continue

        print(f"\n  Generando: {tool['name']}...")
        print(f"    → Generando 'What is' con Ollama...", end=" ", flush=True)
        what_is = generate_what_is(tool)
        print("OK")

        html = build_html(tool, what_is)
        out_path.write_text(html, encoding="utf-8")
        new_slugs.append(tool["slug"])
        print(f"    → Guardado: reviews/{tool['slug']}.html")

    if new_slugs:
        update_sitemap(new_slugs)
        print(f"\n✅ {len(new_slugs)} reviews generadas: {', '.join(new_slugs)}")
    else:
        print("\nNada nuevo que generar.")


if __name__ == "__main__":
    main()
