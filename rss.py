#!/usr/bin/env python3
"""
Poll xkcd RSS feed and forward new entries to a Discord webhook.

Usage:
  - Install dependencies: pip install requests feedparser
  - Run: python rss-feed/xkcd_to_discord.py

Configuration:
  - Set environment variable XKCD_DISCORD_WEBHOOK to override the webhook URL.
  - Set POLL_INTERVAL to number of seconds between checks (default 300 seconds).

This script persists the last seen entry links in .xkcd_state.json next to the script.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import feedparser
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from html import unescape

LOG = logging.getLogger("xkcd_to_discord")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Configuration
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3600"))  # seconds

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, ".xkcd_state.json")

FEEDS = [
    {
        "name": "xkcd",
        "url": "https://xkcd.com/rss.xml",
        "webhook_env": "XKCD_DISCORD_WEBHOOK",
        "default_webhook": "https://discord.com/api/webhooks/1436404104493666486/LG7HPvZBrC1uB_jgSQHahpuguxBMLC7ZIOkRFlcVzFKs2m6gBBTh8H35NmclOn-WPeeF",
    },
    # {
    #     "name": "stuff",
    #     "url": "https://www.stuff.co.nz/rss",
    #     "webhook_env": "STUFF_DISCORD_WEBHOOK",
    #     "default_webhook": "https://discord.com/api/webhooks/1436415585842892894/ymEdOWv65202Cg_g0mCduWnzJxDcxFN_eqHNLAFXhJfuQhG9xMSjL2ka5yVXy7Bu0ZGB",
    # },
    {
        "name": "spinoff",
        # assumption: use thespinoff feed; update if you prefer a different path
        "url": "https://thespinoff.co.nz/feed/",
        "webhook_env": "SPINOFF_DISCORD_WEBHOOK",
        "default_webhook": "https://discord.com/api/webhooks/1436415431241105408/TjQEengj_0kEsGGHSJ_R8faPwYf0POzvxqzcqs6-pNupJXWZ-60j4YPjxT9L3Dh-HUUT",
        "clean_html": True,
    },
]
YOUTUBE_CHANNEL_IDS = [
    "UC-kM5kL9CgjN9s9pim089gg",
    "UCaN8DZdc8EHo5y1LsQWMiig",
    "UCYO_jab_esuFRV4b17AJtAw",
    "UC-LM91jkqJdWFvm9B5G-w7Q",
    "UCGzP7puUuNiDRnC6_QksAHA",
    "UCI1XS_GkLGDOgf8YLaaXNRA",
    "UCr3cBLTYmIK9kY0F_OdFWFQ",
    "UCEHCDn_BBnk3uTK1M64ptyw",
    "UC9-y-6csu5WGm29I7JiwpnA",
    "UCNvsIonJdJ5E4EXMa65VYpA",
    "UCHTM9IknXs4ZHzwHqDjakoQ",
    "UCCODtTcd5M1JavPCOr_Uydg",
    "UCuCkxoKLYO_EQ2GeFtbM_bw",
    "UCarEovlrD9QY-fy-Z6apIDQ",
    "UCv_vLHiWVBh_FR9vbeuiY-A",
    "UCN9v4QG3AQEP3zuRvVs2dAg",
    "UC1Zc6_BhPXiCWZlrZP4EsEg",
    "UCbuf70y__Wh3MRxZcbj778Q",
    "UCG1h-Wqjtwz7uUANw6gazRw",
    "UCEeL4jELzooI7cyrouQzoJg",
    "UCPdaxSov0mgwh77JvjQO2jQ",
    "UCpBRZBzWQ_cCc_9zKG08L-g",
    "UCeiYXex_fwgYDonaTcSIk6w",
    "UCUHW94eEFW7hkUMVaZz4eDg",
    "UC0intLFzLaudFG-xAvUEO-A",
    "UCoxcjq-8xIDTYp3uz647V5A",
    "UCodbH5mUeF-m_BsNueRDjcw",
    "UCedsqpl7jaIb8BiaUFuC9KQ",
    "UCdoRUr0SUpfGQC4vsXZeovg",
    "UCP5tjEmvPItGyLhmjdwP7Ww",
    "UCKUm503onGg3NatpBtTWHkQ",
    "UCYIEv9W7RmdpvFkHX7IEmyg",
    "UCaTSjmqzOO-P8HmtVW3t7sA",
    "UCBa659QWEk1AI4Tg--mrJ2A",
    "UCHnyfMqiRRG1u-2MsSQLbXA",
    "UCLXo7UDZvByw2ixzpQCufnA",
    "UCeYy3kNtk_vhVSxZhi1WGJw",
    "UCC8AgO4FbP11n_WBdFai7DA",
    "UCJQEEltSpi8LXqMH8uTrCQQ",
    "UC1YDVwTL5M_TVivEdTbfKrA",
    "UCbPHHOiOY_tA9BSytK0jDYw",
    "UCT754i47sbjkeIFSTvwqPyA",
    "UCsP7Bpw36J666Fct5M8u-ZA",
    "UC4ltK4Ozg9haG9tK8ibz3dQ",
    "UC0xnzXxUoQ5c-sdWuORrkhA",
    "UC2Kyj04yISmHr1V-UlJz4eg",
    "UC2hDF4_VrJ7t-Bvc0v0CZzw",
    "UCCR3xZ8j5Zc0UOgUGB0D6-w",
    "UCJaTzWgaz4r94ZwpT4OscIA",
    "UCsaGKqPZnGp_7N80hcHySGQ",
];

for ch in YOUTUBE_CHANNEL_IDS:
    FEEDS.append({
        "name": f"youtube:{ch}",
        "url": f"https://www.youtube.com/feeds/videos.xml?channel_id={ch}",
        "webhook_env": "YOUTUBE_DISCORD_WEBHOOK",
        "default_webhook": "https://discord.com/api/webhooks/1436420445065707520/YswjSscfNtWxq6injmBm4v0M0xvf3H8dz6KGM-8JTAdWiE_WNZKbU1EHqzfv2b_8zVUS",
        "clean_html": False,
    })


def webhook_for_feed(feed_cfg: Dict) -> Optional[str]:
    return os.environ.get(feed_cfg.get("webhook_env")) or feed_cfg.get("default_webhook")


def load_state() -> Dict[str, Dict[str, List[str]]]:
    if not os.path.exists(STATE_FILE):
        return {"feeds": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        LOG.exception("Failed to read state file, starting fresh")
        return {"feeds": {}}


def save_state(state: Dict[str, Dict[str, List[str]]]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        LOG.exception("Failed to save state")


IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def extract_all_images(entry) -> List[str]:
    """Return a list of image URLs found in the entry from several common locations.

    Order is roughly: media_thumbnail, media_content, enclosures/links, images in HTML content/summary,
    and images inside <noscript> fallbacks.
    """
    imgs: List[str] = []

    # 1) feedparser media_thumbnail / media_content
    try:
        mt = entry.get("media_thumbnail")
        if mt:
            if isinstance(mt, list):
                for item in mt:
                    url = (item.get("url") if isinstance(item, dict) else None) or getattr(item, "url", None)
                    if url:
                        imgs.append(url)
            elif isinstance(mt, dict):
                url = mt.get("url") or mt.get("href")
                if url:
                    imgs.append(url)
    except Exception:
        pass

    try:
        mc = entry.get("media_content")
        if mc:
            if isinstance(mc, list):
                for item in mc:
                    url = (item.get("url") if isinstance(item, dict) else None) or getattr(item, "url", None)
                    if url:
                        imgs.append(url)
            elif isinstance(mc, dict):
                url = mc.get("url") or mc.get("href")
                if url:
                    imgs.append(url)
    except Exception:
        pass

    try:
        if hasattr(entry, "content") and entry.content:
            for c in entry.content:
                val = None
                t = None
                if isinstance(c, dict):
                    val = c.get("value") or c.get("text")
                    t = c.get("type")
                else:
                    val = getattr(c, "value", None)
                    t = getattr(c, "type", None)
                if val and (t is None or "html" in (t or "")):
                    for m in IMG_RE.findall(val):
                        imgs.append(m)
    except Exception:
        pass

    try:
        for enc in entry.get("enclosures", []) or []:
            url = enc.get("href") or enc.get("url")
            if url and (enc.get("type", "").startswith("image") or url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))):
                imgs.append(url)
    except Exception:
        pass

    try:
        for ln in entry.get("links", []) or []:
            if ln.get("rel") in ("enclosure", "related"):
                url = ln.get("href") or ln.get("url")
                if url and ln.get("type", "").startswith("image"):
                    imgs.append(url)
    except Exception:
        pass

    # 3) HTML content: content[] then summary
    html = ""
    if hasattr(entry, "content") and entry.content:
        try:
            html = entry.content[0].value
        except Exception:
            html = ""
    if not html and entry.get("summary"):
        html = entry.get("summary", "")
    if html:
        for m in IMG_RE.findall(html):
            imgs.append(m)

    # 4) noscript fallbacks
    try:
        soup = BeautifulSoup(html, "html.parser") if html else None
        if soup:
            nos = soup.find("noscript")
            if nos:
                try:
                    nsoup = BeautifulSoup(nos.decode_contents(), "html.parser")
                    for img in nsoup.find_all("img"):
                        src = img.get("src")
                        if src:
                            imgs.append(src)
                except Exception:
                    pass
    except Exception:
        pass

    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for u in imgs:
        if not u:
            continue
        # strip whitespace
        u2 = u.strip()
        if u2 and u2 not in seen:
            seen.add(u2)
            out.append(u2)
    return out


def clean_html_summary(entry) -> Tuple[str, Optional[str]]:
    """Return (text_summary, image_url) cleaned from the HTML content of the entry.
    Prefer content[] if available, otherwise summary. Use BeautifulSoup to extract paragraphs and first image.
    """
    html = ""
    if hasattr(entry, "content") and entry.content:
        try:
            html = entry.content[0].value
        except Exception:
            html = ""
    if not html:
        html = entry.get("summary", "") or entry.get("description", "") or ""

    soup = BeautifulSoup(html, "html.parser")

    # remove ads and script/style tags
    for tag in soup.select(".ad, .advert, script, style, iframe"):
        tag.decompose()

    # Find first useful image: prefer <img> with non-data src, otherwise look inside <noscript>
    img_url = None
    img = soup.find("img")
    if img:
        src = img.get("src") or ""
        if src.startswith("data:") or src.strip() == "":
            # try noscript
            nos = soup.find("noscript")
            if nos:
                try:
                    nsoup = BeautifulSoup(nos.decode_contents(), "html.parser")
                    nimg = nsoup.find("img")
                    if nimg and nimg.get("src"):
                        img_url = nimg.get("src")
                except Exception:
                    img_url = None
        else:
            img_url = src

    # Collect paragraphs / headings into plain text, limit to first ~6 paragraphs
    parts = []
    for el in soup.find_all(["h1", "h2", "h3", "p"]):
        text = el.get_text(strip=True)
        if text:
            parts.append(unescape(text))
        if len(parts) >= 6:
            break

    summary = "\n\n".join(parts)[:4000]
    return summary, img_url


def validate_image_url(image_url: str) -> Optional[str]:
    """Return the image_url if it looks valid and reachable, otherwise None."""
    if not image_url:
        return None
    if not image_url.startswith("http"):
        return None
    try:
        # Prefer a lightweight HEAD; some servers don't respond properly so fall back to GET
        resp = requests.head(image_url, timeout=6, allow_redirects=True)
        if resp.status_code >= 400 or not resp.headers.get("content-type"):
            resp = requests.get(image_url, stream=True, timeout=6)
        ct = resp.headers.get("content-type", "")
        if resp.status_code < 400 and ct.startswith("image"):
            return image_url
        LOG.debug("Image URL rejected by validation (status=%s, content-type=%s): %s", resp.status_code, ct, image_url)
        return None
    except Exception:
        LOG.debug("Exception validating image url %s", image_url, exc_info=True)
        return None


def send_to_discord(title: str, link: str, webhook_url: str, summary: str = "", image_url: Optional[str] = None) -> bool:
    headers = {"Content-Type": "application/json"}
    # Truncate fields to Discord limits (conservative)
    safe_title = (title or "").strip()[:256]
    safe_description = (summary or "").strip()[:4000]

    embed: Dict = {
        "title": safe_title,
        "url": link,
        "description": safe_description,
    }
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 204):
            LOG.info("Sent to Discord: %s", title)
            return True
        else:
            LOG.warning("Discord webhook returned %s: %s", resp.status_code, resp.text)
            # If embed was rejected (400), try a simpler fallback message
            if resp.status_code == 400:
                try:
                    fallback = {"content": f"{safe_title}\n{link}\n\n{safe_description[:1900]}"}
                    resp2 = requests.post(webhook_url, json=fallback, headers=headers, timeout=15)
                    if resp2.status_code in (200, 204):
                        LOG.info("Fallback text message sent for: %s", title)
                        return True
                    else:
                        LOG.warning("Fallback also failed %s: %s", resp2.status_code, resp2.text)
                        return False
                except Exception:
                    LOG.exception("Fallback send failed for %s", title)
                    return False
            return False
    except Exception:
        LOG.exception("Failed to send webhook for %s", title)
        return False


def fetch_entries(feed_url: str):
    """Fetch the feed using requests and parse with feedparser.
    """
    resp = None
    try:
        headers = {"User-Agent": "rss-to-discord/1.0 (+https://example.com)"}
        resp = requests.get(feed_url, timeout=10, headers=headers)
        if resp.status_code != 200:
            LOG.warning("HTTP %s fetching %s", resp.status_code, feed_url)
        content = resp.content
        feed = feedparser.parse(content)
    except Exception:
        LOG.debug("requests fetch failed for %s, falling back to feedparser.fetch", feed_url, exc_info=True)
        feed = feedparser.parse(feed_url)

    if getattr(feed, "bozo", False):
        LOG.warning("Feed parser reported bozo for %s (malformed feed): %s", feed_url, getattr(feed, "bozo_exception", ""))
        # Try a recovery for common encoding mismatches using apparent_encoding
        try:
            if resp is not None:
                enc = resp.apparent_encoding or "utf-8"
                text = resp.content.decode(enc, errors="replace")
                feed2 = feedparser.parse(text)
                if not getattr(feed2, "bozo", False):
                    LOG.info("Recovered feed parse for %s using apparent_encoding=%s", feed_url, enc)
                    return feed2
        except Exception:
            LOG.debug("Recovery parse failed for %s", feed_url, exc_info=True)

    return feed


def main():
    LOG.info("Starting multi-feed -> Discord forwarder. Poll interval=%s seconds", POLL_INTERVAL)
    state = load_state()

    while True:
        try:
            for feed_cfg in FEEDS:
                name = feed_cfg["name"]
                url = feed_cfg["url"]
                webhook = webhook_for_feed(feed_cfg)

                if not webhook:
                    LOG.info("No webhook configured for feed '%s' (env %s); skipping", name, feed_cfg.get("webhook_env"))
                    continue

                LOG.info("Checking feed %s -> %s", name, url)
                parsed = fetch_entries(url)
                entries = parsed.entries

                seen_links = set(state.get("feeds", {}).get(name, []))

                # Process oldest first so Discord receives items in chronological order
                for entry in reversed(entries):
                    link = entry.get("link")
                    if not link:
                        continue
                    if link in seen_links:
                        continue

                    # If this is a YouTube feed and the link is a Shorts URL, skip it
                    if name.startswith("youtube:") and "/shorts/" in (link or ""):
                        LOG.info("Skipping YouTube Short: %s", link)
                        # mark as seen so we don't retry repeatedly
                        seen_links.add(link)
                        state.setdefault("feeds", {})[name] = list(seen_links)
                        save_state(state)
                        continue

                    title = entry.get("title", name)
                    # Default summary and image
                    summary = ""
                    image = None

                    # Special handling for YouTube feeds: omit summary, use the channel/video thumbnail
                    if name.startswith("youtube:"):
                        # Try feedparser's media_thumbnail field (commonly present)
                        try:
                            mt = entry.get("media_thumbnail") or entry.get("media_thumbnail", None)
                            if mt:
                                # media_thumbnail may be a list of dicts
                                if isinstance(mt, list) and mt:
                                    image = mt[0].get("url") or mt[0].get("href")
                                elif isinstance(mt, dict):
                                    image = mt.get("url") or mt.get("href")
                        except Exception:
                            image = None

                        # Fallback to any <img> found in content/summary
                        if not image:
                            imgs = extract_all_images(entry)
                            # Prefer Spinoff-hosted images when available
                            if name == "spinoff":
                                for i, u in enumerate(imgs):
                                    if u.startswith("https://images.thespinoff.co.nz"):
                                        imgs.insert(0, imgs.pop(i))
                                        break
                            image = imgs[0] if imgs else None

                        # Last resort: construct thumbnail from video id in the link or yt:videoId
                        if not image:
                            vid = entry.get("yt_videoid") or entry.get("videoId") or entry.get("video_id")
                            if not vid:
                                link_for_vid = entry.get("link", "")
                                m = re.search(r"(?:v=|/videos/|/embed/|/shorts/)([A-Za-z0-9_-]{6,})", link_for_vid)
                                if m:
                                    vid = m.group(1)
                            if vid:
                                image = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                        # No description for YouTube; summary remains empty
                    else:
                        # Non-YouTube: extract images and optionally clean HTML for nicer summary
                        imgs = extract_all_images(entry)
                        # Prefer Spinoff-hosted images when available
                        if name == "spinoff":
                            for i, u in enumerate(imgs):
                                if u.startswith("https://images.thespinoff.co.nz"):
                                    imgs.insert(0, imgs.pop(i))
                                    break
                        image = imgs[0] if imgs else None
                        if feed_cfg.get("clean_html"):
                            cleaned_summary, cleaned_img = clean_html_summary(entry)
                            summary = cleaned_summary
                            if cleaned_img and not image:
                                image = cleaned_img
                        else:
                            summary = entry.get("summary", "")
                    # Remove description for xkcd feed (user preference)
                    if name == "xkcd":
                        summary = ""
                    # Resolve relative image URLs against feed URL
                    if image and not image.startswith("http"):
                        try:
                            image = urljoin(url, image)
                        except Exception:
                            LOG.debug("Failed to resolve image URL %s for feed %s", image, name)
                    # Validate image URL to avoid Discord embed validation errors
                    if image:
                        valid_image = validate_image_url(image)
                        if not valid_image:
                            LOG.info("Dropping image for %s because validation failed: %s", name, image)
                            image = None
                        else:
                            image = valid_image

                    sent = send_to_discord(title=title, link=link, webhook_url=webhook, summary=summary, image_url=image)
                    if sent:
                        seen_links.add(link)
                        state.setdefault("feeds", {})[name] = list(seen_links)
                        save_state(state)
                    else:
                        LOG.warning("Will retry this entry later: %s", link)

        except Exception:
            LOG.exception("Unexpected error in main loop")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOG.info("Interrupted, exiting")
