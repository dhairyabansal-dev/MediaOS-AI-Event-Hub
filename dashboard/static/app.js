// Polls the live event API so the dashboard updates without a manual
// refresh. The 2-min backend cycle is the source of truth; we poll more
// often (30s) just so the UI catches the update promptly, not to trigger
// extra fetch cycles ourselves.

const POLL_INTERVAL_MS = 30_000;

function sourceChip(stype, count) {
  return `<span class="chip"><span class="dot"></span>${stype} · ${count}</span>`;
}

function renderCard(e) {
  const thumb = e.thumbnail
    ? `<img class="card-thumb" src="${e.thumbnail}" alt="" loading="lazy">`
    : `<div class="card-thumb placeholder">No image</div>`;

  const chips = Object.entries(e.source_counts || {})
    .map(([stype, count]) => sourceChip(stype, count))
    .join("");

  const tag = e.is_priority ? `<span class="priority-tag">Flagged topic</span>` : "";
  const priorityClass = e.is_priority ? "priority" : "";

  return `
    <a class="event-card ${priorityClass}" href="/event/${e.id}">
      ${thumb}
      <div class="card-body">
        ${tag}
        <h2 class="card-title">${e.title}</h2>
        <div class="card-meta">
          <div class="source-chips">${chips}</div>
        </div>
      </div>
    </a>`;
}

async function refresh() {
  try {
    const res = await fetch("/api/events");
    if (!res.ok) return;
    const data = await res.json();

    const grid = document.getElementById("event-grid");
    if (grid && data.events.length) {
      grid.innerHTML = data.events.map(renderCard).join("");
    }

    const note = document.getElementById("refresh-note");
    if (note && data.last_updated) {
      const t = new Date(data.last_updated);
      note.textContent = `updated ${t.toISOString().slice(11, 19)} UTC`;
    }
  } catch (err) {
    console.error("refresh failed:", err);
  }
}

setInterval(refresh, POLL_INTERVAL_MS);
