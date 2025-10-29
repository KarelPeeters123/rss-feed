// shared.js
// Shared utilities and data used by index.html and youtube.html

// Full YouTube channel ID list (restored)
const youtubeChannels = [
    "UC-kM5kL9CgjN9s9pim089gg", // @AdamConover
    "UCaN8DZdc8EHo5y1LsQWMiig",  // @BigJoel
    "UCYO_jab_esuFRV4b17AJtAw",  // @3Blue1Browna
    "UC-LM91jkqJdWFvm9B5G-w7Q", // @alanthefisher
    "UCGzP7puUuNiDRnC6_QksAHA", // @artisanalcheese
    "UCI1XS_GkLGDOgf8YLaaXNRA", // @CalebCity
    "UCr3cBLTYmIK9kY0F_OdFWFQ", // @CasuallyExplained
    "UCEHCDn_BBnk3uTK1M64ptyw", // @RanveerBrar
    "UC9-y-6csu5WGm29I7JiwpnA", // @Computerphile
    "UCNvsIonJdJ5E4EXMa65VYpA", // @ContraPoints
    "UCHTM9IknXs4ZHzwHqDjakoQ", // @DAngeloWallace
    "UCCODtTcd5M1JavPCOr_Uydg", // @extrahistory
    "UCuCkxoKLYO_EQ2GeFtbM_bw", // @halfasinteresting
    "UCarEovlrD9QY-fy-Z6apIDQ", // @HasanMinhaj
    "UCv_vLHiWVBh_FR9vbeuiY-A", // @HistoriaCivilis
    "UCN9v4QG3AQEP3zuRvVs2dAg", // @HistoryTime
    "UC1Zc6_BhPXiCWZlrZP4EsEg", // @historywithhilbert
    "UCbuf70y__Wh3MRxZcbj778Q", // @KhadijaMbowe
    "UCG1h-Wqjtwz7uUANw6gazRw", // @LindsayEllisVids
    "UCEeL4jELzooI7cyrouQzoJg", // @littlestjoel
    "UCPdaxSov0mgwh77JvjQO2jQ", // @ManCarryingThing
    "UCpBRZBzWQ_cCc_9zKG08L-g", // @Marxism_Today
    "UCeiYXex_fwgYDonaTcSIk6w", // @MinuteEarth
    "UCUHW94eEFW7hkUMVaZz4eDg", // @MinutePhysics
    "UC0intLFzLaudFG-xAvUEO-A", // @NotJustBikes
    "UCoxcjq-8xIDTYp3uz647V5A", // @numberphile
    "UCodbH5mUeF-m_BsNueRDjcw", // @OverlySarcasticProductions
    "UCedsqpl7jaIb8BiaUFuC9KQ", // @pastagrannies
    "UCdoRUr0SUpfGQC4vsXZeovg", // @PeoplesDispatch
    "UCP5tjEmvPItGyLhmjdwP7Ww", // @RealLifeLore
    "UCKUm503onGg3NatpBtTWHkQ", // @SkipIntroYT
    "UCYIEv9W7RmdpvFkHX7IEmyg", // @taylortomlinsoncomedy
    "UCaTSjmqzOO-P8HmtVW3t7sA", // @ToddintheShadows
    "UCBa659QWEk1AI4Tg--mrJ2A", // @TomScottGo
    "UCHnyfMqiRRG1u-2MsSQLbXA", // @veritasium
    "UCLXo7UDZvByw2ixzpQCufnA", // @Vox
    "UCeYy3kNtk_vhVSxZhi1WGJw", // @WILTY_TV
];

// Format date/time
function formatDate(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    if (isNaN(d)) return "";
    return d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

proxyList: [
    url => `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`,
    url => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    url => `https://thingproxy.freeboard.io/fetch/${url}`,
]

async function fetchFeed(url) {
    const parser = new DOMParser();

    for (const makeProxyUrl of this.proxyList) {
        const apiUrl = makeProxyUrl(url);
        try {
            const res = await fetch(apiUrl);
            if (!res.ok) throw new Error(`Proxy failed: ${res.status}`);

            // Handle AllOrigins JSON vs direct XML
            const text = apiUrl.includes("allorigins")
                ? (await res.json()).contents
                : await res.text();

            const xml = parser.parseFromString(text, "text/xml");
            if (xml.querySelector("parsererror")) throw new Error("Invalid XML");
            return xml;
        } catch (err) {
            console.warn(`Proxy failed for ${url} via ${apiUrl}:`, err.message);
            continue; // Try next proxy
        }
    }

    throw new Error(`All proxies failed for ${url}`);
}

// Parse a YouTube channel feed (videos.xml) and return an array of video objects
async function fetchYouTubeChannelFeed(channelId) {
    const url = `https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`;
    const xml = await fetchFeed(url);
    const channelTitle = xml.querySelector("feed > title")?.textContent || "Unknown Channel";
    const entries = Array.from(xml.querySelectorAll("entry"));

    const videos = entries.map(entry => {
        const link = entry.querySelector("link")?.getAttribute("href") || "#";
        // prefer yt:videoId if present (safer)
        const videoId = entry.querySelector("yt\\:videoId, videoId")?.textContent ||
            (new URL(link).searchParams.get("v") || "");
        const isShort = link.includes("/shorts/");
        const thumb = entry.querySelector("media\\:thumbnail")?.getAttribute("url") ||
            (videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : "");
        return {
            title: entry.querySelector("title")?.textContent || "No title",
            link,
            pubDate: entry.querySelector("published")?.textContent || "",
            source: channelTitle,
            videoId,
            isShort,
            thumbnail: thumb
        };
    });

    return videos;
}

// Create DOM node for a video (thumbnail + meta). Clicking thumbnail swaps to an embed <iframe>.
function createVideoElement(video) {
    const container = document.createElement("div");
    container.className = "feed-item";
    container.style.display = "flex";
    container.style.alignItems = "flex-start";
    container.style.gap = "12px";
    container.style.marginBottom = "12px";

    const imgBox = document.createElement("div");
    imgBox.style.flexShrink = "0";
    imgBox.style.width = "160px";
    imgBox.style.height = "90px";
    imgBox.style.overflow = "hidden";
    imgBox.style.borderRadius = "6px";
    imgBox.style.background = "#ddd";

    const img = document.createElement("img");
    img.src = video.thumbnail;
    img.alt = video.title;
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.objectFit = "cover";
    img.style.display = "block";
    img.style.cursor = "pointer";

    // On click: replace thumbnail with embedded player
    img.addEventListener("click", () => {
        const iframe = document.createElement("iframe");
        iframe.width = "320";
        iframe.height = "180";
        iframe.frameBorder = "0";
        iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
        iframe.allowFullscreen = true;
        // Prefer videoId embed when available, otherwise fallback to full link as embed
        const id = video.videoId || extractVideoIdFromUrl(video.link);
        iframe.src = id ? `https://www.youtube-nocookie.com/embed/${id}` : video.link;
        // Replace imgBox contents with iframe
        imgBox.innerHTML = "";
        imgBox.style.width = "320px";
        imgBox.style.height = "180px";
        imgBox.appendChild(iframe);
    });

    imgBox.appendChild(img);

    const meta = document.createElement("div");
    meta.style.flex = "1";
    const dateStr = formatDate(video.pubDate);
    meta.innerHTML = `
    <h2 style="margin:0 0 4px;">
      <a href="${video.link}" target="_blank" rel="noopener">${escapeHtml(video.title)}</a>
      ${video.isShort ? '<span class="shorts-badge">SHORT</span>' : ""}
    </h2>
    <div class="source">Channel: ${escapeHtml(video.source)}</div>
    ${dateStr ? `<small>${escapeHtml(dateStr)}</small>` : ""}
  `;

    container.appendChild(imgBox);
    container.appendChild(meta);
    return container;
}

// small helpers
function extractVideoIdFromUrl(url) {
    try {
        const u = new URL(url);
        if (u.pathname.startsWith("/shorts/")) return u.pathname.split("/shorts/")[1];
        if (u.searchParams.get("v")) return u.searchParams.get("v");
        // youtube watch short forms: youtu.be/<id>
        if (u.hostname === "youtu.be") return u.pathname.substring(1);
        return "";
    } catch (e) {
        return "";
    }
}

function escapeHtml(s) {
    if (!s) return "";
    return s.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// Expose to global scope (browser)
window.shared = {
    youtubeChannels,
    formatDate,
    fetchFeed,
    fetchYouTubeChannelFeed,
    createVideoElement,
    extractVideoIdFromUrl
};
