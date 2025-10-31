// shared.js
// Optimized shared utilities for index.html and youtube.html

const youtubeChannels = [
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
  "UCsaGKqPZnGp_7N80hcHySGQ"
];

// Cache DOMParser instance
const parser = new DOMParser();

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return isNaN(d)
    ? ""
    : d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
}

const proxies = [
  u => `https://api.allorigins.win/get?url=${encodeURIComponent(u)}`,
  u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
  u => `https://thingproxy.freeboard.io/fetch/${u}`
];

// Race between proxies for speed
async function fetchFeed(url) {
  const attempts = proxies.map(makeUrl => {
    const apiUrl = makeUrl(url);
    return fetch(apiUrl)
      .then(res => {
        if (!res.ok) throw new Error(res.statusText);
        return apiUrl.includes("allorigins")
          ? res.json().then(j => j.contents)
          : res.text();
      })
      .then(text => {
        const xml = parser.parseFromString(text, "text/xml");
        if (xml.querySelector("parsererror")) throw new Error("Invalid XML");
        return xml;
      });
  });
  return Promise.any(attempts);
}

// Parallel channel loading
async function fetchYouTubeChannelFeed(channelId) {
  const url = `https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`;
  const xml = await fetchFeed(url);
  const channelTitle = xml.querySelector("feed > title")?.textContent || "Unknown Channel";

  return Array.from(xml.querySelectorAll("entry")).map(entry => {
    const link = entry.querySelector("link")?.getAttribute("href") || "#";
    const videoId =
      entry.querySelector("yt\\:videoId, videoId")?.textContent ||
      new URL(link, "https://youtube.com").searchParams.get("v") ||
      "";
    const isShort = link.includes("/shorts/");
    const thumb =
      entry.querySelector("media\\:thumbnail")?.getAttribute("url") ||
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
}

// Create optimized DOM node
function createVideoElement(video) {
  const container = document.createElement("div");
  container.className = "feed-item";
  container.style.display = "flex";
  container.style.alignItems = "flex-start";
  container.style.gap = "12px";
  container.style.marginBottom = "12px";

  const imgBox = document.createElement("div");
  Object.assign(imgBox.style, {
    flexShrink: "0",
    width: "160px",
    height: "90px",
    overflow: "hidden",
    borderRadius: "6px",
    background: "#ddd"
  });

  const img = document.createElement("img");
  img.src = video.thumbnail;
  img.alt = video.title;
  Object.assign(img.style, {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    cursor: "pointer"
  });

  img.addEventListener("click", () => {
    const iframe = document.createElement("iframe");
    iframe.width = "320";
    iframe.height = "180";
    iframe.frameBorder = "0";
    iframe.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
    iframe.allowFullscreen = true;
    iframe.loading = "lazy";
    iframe.src = `https://www.youtube-nocookie.com/embed/${video.videoId}`;
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

// Batch append
async function renderYouTubeFeed(container, channels = youtubeChannels) {
  const fragment = document.createDocumentFragment();
  const results = await Promise.allSettled(channels.map(fetchYouTubeChannelFeed));
  const videos = results
    .filter(r => r.status === "fulfilled")
    .flatMap(r => r.value)
    .sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate))
    .slice(0, 100);

  for (const video of videos) fragment.appendChild(createVideoElement(video));
  container.appendChild(fragment);
}

function escapeHtml(s) {
  return s
    ? s.replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[c]))
    : "";
}

window.shared = {
  youtubeChannels,
  formatDate,
  fetchFeed,
  fetchYouTubeChannelFeed,
  createVideoElement,
  renderYouTubeFeed
};
