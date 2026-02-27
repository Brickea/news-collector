# Skill: Generate Knowledge Graph Document & Visualization

## Overview

This skill documents the **standard process** for generating a personal daily reading knowledge graph from the user's reading notes.

The output is a **pair of linked files** placed in the archive for the corresponding date:

| File | Type | Purpose |
|------|------|---------|
| `YYYY-MM-DD-reading-notes.md` | Markdown (Jekyll) | Structured text: what/why/next per topic |
| `YYYY-MM-DD-knowledge-graph.html` | Self-contained HTML | Interactive D3.js force-directed graph |

Both files are placed in `docs/archive/YYYY/MM/` and cross-linked. The period index (`docs/archive/YYYY/MM/index.md`) is updated to list them.

---

## Trigger

The user will say something like:

> "我今天的知识图谱写好了" / "I've finished today's reading notes"

At that point you should:
1. Ask for (or locate) the user-provided reading notes source.
2. Execute the steps below to generate the two output files.
3. Update the period index.
4. Commit and push via `report_progress`.

---

## Input

The user provides their daily reading notes in one of two forms:

- **Raw dump** – a list of URLs / tab titles they read, possibly with brief personal annotations.
- **Pre-structured markdown** – already in the reading-notes format (see [Contribution Guide](../../docs/guides/contributing-knowledge-graph.md)).

---

## Step-by-Step Process

### Step 1 — Determine date and paths

```
DATE        = YYYY-MM-DD   (today or as specified by user)
YEAR        = YYYY
MONTH       = MM
ARCHIVE_DIR = docs/archive/YYYY/MM
NOTES_FILE  = docs/archive/YYYY/MM/YYYY-MM-DD-reading-notes.md
GRAPH_FILE  = docs/archive/YYYY/MM/YYYY-MM-DD-knowledge-graph.html
INDEX_FILE  = docs/archive/YYYY/MM/index.md
```

### Step 2 — Understand the content

Read the user's notes and extract three structural elements:

#### 2a. CATEGORIES (topic clusters)

Each category is a **theme or domain** that groups several articles.
Choose 4–8 categories from the user's reading session.

```
id     : short snake_case identifier (e.g. "cat-ai")
label  : display label, can include emoji and a newline for sub-title
         e.g. "🤖 Agentic AI\n技术生态"
color  : hex color for this group (see palette below)
size   : 22  (fixed for categories; root node uses 28)
group  : integer index starting at 1
```

**Recommended color palette** (vary freely):

| Concept area | Suggested color |
|-------------|----------------|
| AI / ML | `#667eea` |
| Security | `#f5a623` |
| Engineering / DevOps | `#43e97b` |
| Business / Industry | `#fa709a` |
| Personal Projects | `#4facfe` |
| Science / Academia | `#a29bfe` |
| Other / Misc | `#fd79a8` |

Always include a **root node** as the first element:

```js
{ id: "root", label: "YYYY-MM-DD\n阅读会话", color: "#ffffff", size: 28, group: 0 }
```

#### 2b. ARTICLES (resources)

Each article is a single **URL / resource** the user found interesting.

```
id    : short unique snake_case (e.g. "cowork")
cat   : id of the parent CATEGORY
label : display label; use \n to split into two short lines
url   : full URL of the resource
desc  : 1–3 sentence description (Chinese preferred for personal notes)
```

Aim for **3–6 articles per category**.

#### 2c. CROSS_EDGES (cross-cutting connections)

Identify 5–12 **thematically interesting links** between articles that span different categories.

```
source : article id
target : article id
label  : short Chinese/English description of the connection
```

### Step 3 — Generate the reading notes Markdown file

Template:

```markdown
---
layout: default
title: 📖 Reading Notes · YYYY-MM-DD
---

<div style="margin-bottom: 1rem;">
  <a href="/news-collector/" style="display: inline-block; padding: 0.5rem 1rem; background: #667eea; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem;">← Back to Home</a>
  <a href="index.html" style="display: inline-block; padding: 0.5rem 1rem; background: #764ba2; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem; margin-left: 0.5rem;">← Back to [Month] [Year]</a>
  <a href="YYYY-MM-DD-knowledge-graph.html" style="display: inline-block; padding: 0.5rem 1rem; background: #43e97b; color: #1a1a2e; text-decoration: none; border-radius: 4px; font-size: 0.9rem; margin-left: 0.5rem;">🕸 交互式知识图谱 →</a>
</div>

# 📖 今日新闻阅读 — 深度知识图谱 · YYYY-MM-DD

> 🗓️ 结构化摘要与原始链接 · 按主题节点组织

[brief 1-line description of the reading session]

---

## 📑 目录

- [概览节点](#overview)
- [CATEGORY_EMOJI CATEGORY_TITLE](#anchor-id)
...
- [🎯 快速可执行结论](#actionable-conclusions)

---

## 概览节点 {#overview}

[Brief description of the starting point / digest that was read]

🔗 <a href="URL" target="_blank">URL</a>

---

## CATEGORY_EMOJI CATEGORY_TITLE {#anchor-id}

### ARTICLE_TITLE

**要点（what）**：...

**意义（why）**：...

**可行动线索（how / next）**：...

🔗 <a href="URL" target="_blank">SOURCE · ARTICLE_TITLE</a>

---

[... repeat for all articles in all categories ...]

## 🎯 快速可执行结论 {#actionable-conclusions}

### 1. [Conclusion title]

[2-3 sentence summary of the most important action item]

### 2. [Conclusion title]

...

---

<div style="text-align: center; padding: 2rem 0; color: #666;">
  <p>📖 Personal reading notes · <a href="https://github.com/Brickea/news-collector">news-collector</a></p>
</div>
```

**Rules for reading notes:**
- Links use `<a href="..." target="_blank">` HTML tags (NOT markdown links inside the content body) so they render correctly on GitHub Pages.
- Section anchors use kramdown syntax `{#anchor-id}` where the id is lowercase-kebab-case.
- Each article entry must have all three sub-sections: 要点 / 意义 / 可行动线索.
- The 🎯 conclusions section distills 2–5 concrete next actions.

### Step 4 — Generate the knowledge graph HTML file

Use the template below, filling in the `DATA` section with the CATEGORIES, ARTICLES, and CROSS_EDGES extracted in Step 2.

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>📖 知识图谱 · YYYY-MM-DD</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f1117; color: #e6e6ef;
      height: 100vh; display: flex; flex-direction: column; overflow: hidden;
    }
    header {
      padding: 0.7rem 1.2rem; background: #1a1d2e;
      border-bottom: 1px solid #2d3154;
      display: flex; align-items: center; gap: 1rem;
      flex-shrink: 0; flex-wrap: wrap;
    }
    header h1 { font-size: 1.05rem; font-weight: 600; color: #a8b4ff; }
    header p  { font-size: 0.78rem; color: #8890b0; }
    .header-links { display: flex; gap: 0.6rem; margin-left: auto; flex-wrap: wrap; }
    .header-links a {
      font-size: 0.75rem; padding: 0.3rem 0.8rem; border-radius: 4px;
      text-decoration: none; color: #fff; white-space: nowrap;
    }
    .btn-home  { background: #667eea; }
    .btn-notes { background: #764ba2; }
    main { display: flex; flex: 1; overflow: hidden; }
    #graph-container { flex: 1; position: relative; overflow: hidden; }
    svg { width: 100%; height: 100%; display: block; }
    #legend {
      width: 200px; flex-shrink: 0; background: #1a1d2e;
      border-left: 1px solid #2d3154; padding: 1rem; overflow-y: auto;
      display: flex; flex-direction: column; gap: 0.5rem;
    }
    #legend h3 { font-size: 0.8rem; color: #8890b0; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem; }
    .legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem; color: #c0c8e0; cursor: pointer; padding: 0.2rem 0; border-radius: 3px; transition: background 0.15s; }
    .legend-item:hover { background: #252840; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
    #legend hr { border: none; border-top: 1px solid #2d3154; margin: 0.4rem 0; }
    #legend .hint { font-size: 0.7rem; color: #606880; line-height: 1.5; }
    #tooltip {
      position: fixed; pointer-events: none; background: #1e2236;
      border: 1px solid #3a4070; border-radius: 8px; padding: 0.75rem 1rem;
      max-width: 280px; font-size: 0.78rem; line-height: 1.55; color: #d0d8f0;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5); display: none; z-index: 100;
    }
    #tooltip .tt-title { font-weight: 600; color: #a8b4ff; margin-bottom: 0.35rem; font-size: 0.82rem; }
    #tooltip .tt-type  { font-size: 0.7rem; color: #6070a0; margin-bottom: 0.4rem; }
    #tooltip .tt-desc  { color: #b0bcd0; }
    #tooltip .tt-link  { margin-top: 0.4rem; font-size: 0.7rem; color: #667eea; }
    .node circle { stroke: #0f1117; stroke-width: 2px; cursor: pointer; transition: filter 0.15s; }
    .node circle:hover { filter: brightness(1.35) drop-shadow(0 0 6px currentColor); }
    .node text { pointer-events: none; fill: #d8e0f8; text-anchor: middle; dominant-baseline: central; }
    .link { stroke: #3a4070; stroke-opacity: 0.55; fill: none; }
    .link.cross { stroke: #8890b0; stroke-opacity: 0.35; stroke-dasharray: 4 3; }
    #controls { position: absolute; bottom: 1rem; left: 1rem; display: flex; gap: 0.4rem; }
    #controls button {
      background: #1e2236; border: 1px solid #3a4070; color: #a8b4ff;
      border-radius: 4px; padding: 0.3rem 0.7rem; font-size: 0.78rem;
      cursor: pointer; transition: background 0.15s;
    }
    #controls button:hover { background: #2d3154; }
    @media (max-width: 600px) {
      header { padding: 0.45rem 0.75rem; gap: 0.5rem; }
      header h1 { font-size: 0.9rem; }
      header p  { display: none; }
      .header-links a { font-size: 0.7rem; padding: 0.25rem 0.55rem; }
      main { flex-direction: column-reverse; }
      #legend { width: 100%; max-height: 28vh; border-left: none; border-top: 1px solid #2d3154; flex-direction: row; flex-wrap: wrap; gap: 0.3rem; padding: 0.5rem 0.75rem; }
      #legend h3 { width: 100%; margin-bottom: 0.1rem; }
      #legend hr { display: none; }
      #legend .hint { display: none; }
      .legend-item { font-size: 0.72rem; padding: 0.15rem 0.4rem; }
      #controls { bottom: 0.5rem; left: 0.5rem; }
      #controls button { padding: 0.25rem 0.55rem; font-size: 0.72rem; }
      #tooltip { max-width: min(260px, 85vw); font-size: 0.74rem; }
    }
  </style>
</head>
<body>

<header>
  <div>
    <h1>📖 知识图谱 · YYYY-MM-DD</h1>
    <p>今日新闻阅读 — 深度知识图谱（交互式网络视图）</p>
  </div>
  <div class="header-links">
    <a class="btn-home"  href="/news-collector/">← 首页</a>
    <a class="btn-notes" href="YYYY-MM-DD-reading-notes.html">📄 文字版</a>
  </div>
</header>

<main>
  <div id="graph-container">
    <svg id="graph"></svg>
    <div id="tooltip"></div>
    <div id="controls">
      <button id="btn-reset">重置视图</button>
      <button id="btn-freeze">暂停布局</button>
    </div>
  </div>
  <nav id="legend">
    <h3>主题节点</h3>
    <!-- populated by JS -->
    <hr/>
    <p class="hint">
      🖱 拖动节点<br/>
      🔍 滚轮缩放<br/>
      👆 点击打开链接<br/>
      🏷 悬停查看描述
    </p>
    <hr/>
    <h3>连线类型</h3>
    <div class="legend-item"><svg width="28" height="10"><line x1="0" y1="5" x2="28" y2="5" stroke="#3a4070" stroke-width="2"/></svg> 从属关系</div>
    <div class="legend-item"><svg width="28" height="10"><line x1="0" y1="5" x2="28" y2="5" stroke="#8890b0" stroke-width="1.5" stroke-dasharray="4 3"/></svg> 横切关联</div>
  </nav>
</main>

<script>
// ── DATA ──────────────────────────────────────────────────────────────────────
const CATEGORIES = [
  { id: "root", label: "YYYY-MM-DD\n阅读会话", color: "#ffffff", size: 28, group: 0 },
  // ADD CATEGORIES HERE
  // { id: "cat-ai", label: "🤖 Agentic AI\n技术生态", color: "#667eea", size: 22, group: 1 },
];

const ARTICLES = [
  // ADD ARTICLES HERE
  // { id: "example", cat: "cat-ai", label: "Example\nArticle", url: "https://example.com", desc: "Description of this article." },
];

const CROSS_EDGES = [
  // ADD CROSS-CUTTING EDGES HERE
  // { source: "article-a", target: "article-b", label: "Connection description" },
];

// ── GRAPH SETUP ───────────────────────────────────────────────────────────────
const nodes = [
  ...CATEGORIES.map(c => ({ ...c, type: c.id === "root" ? "root" : "category" })),
  ...ARTICLES.map(a  => ({ ...a, type: "article", color: null })),
];
const catColorMap = Object.fromEntries(CATEGORIES.map(c => [c.id, c.color]));
nodes.forEach(n => {
  if (n.type === "article") { n.color = catColorMap[n.cat] + "bb"; n.size = 12; }
});
const links = [];
CATEGORIES.slice(1).forEach(c => links.push({ source: "root", target: c.id, type: "hierarchy" }));
ARTICLES.forEach(a => links.push({ source: a.cat, target: a.id, type: "hierarchy" }));
CROSS_EDGES.forEach(e => links.push({ ...e, type: "cross" }));

const svg = d3.select("#graph");
const container = document.getElementById("graph-container");
const tooltip   = document.getElementById("tooltip");
let width  = container.clientWidth;
let height = container.clientHeight;
const g = svg.append("g").attr("class", "scene");
const zoom = d3.zoom().scaleExtent([0.15, 4]).on("zoom", e => g.attr("transform", e.transform));
svg.call(zoom);

const simulation = d3.forceSimulation(nodes)
  .force("link",    d3.forceLink(links).id(d => d.id).distance(d =>
    d.source.type === "root" ? 170 : d.source.type === "category" ? 110 : 90
  ).strength(0.6))
  .force("charge",  d3.forceManyBody().strength(d =>
    d.type === "root" ? -900 : d.type === "category" ? -500 : -180
  ))
  .force("center",  d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide().radius(d => d.size + 16).strength(0.7));

const link = g.append("g").attr("class", "links")
  .selectAll("line").data(links).join("line")
  .attr("class", d => "link" + (d.type === "cross" ? " cross" : ""))
  .attr("stroke-width", d => d.type === "cross" ? 1.2 : 1.5);

const node = g.append("g").attr("class", "nodes")
  .selectAll("g").data(nodes).join("g").attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end",   (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
  )
  .on("click", (e, d) => { if (d.url) window.open(d.url, "_blank", "noopener"); })
  .on("mouseover", (e, d) => {
    tooltip.innerHTML = `
      <div class="tt-title">${d.label.replace(/\n/g, " ")}</div>
      <div class="tt-type">${d.type === "category" ? "主题节点" : d.type === "root" ? "根节点" : "文章 / 资源"}</div>
      ${d.desc ? `<div class="tt-desc">${d.desc}</div>` : ""}
      ${d.url  ? `<div class="tt-link">🔗 点击打开链接</div>` : ""}
    `;
    tooltip.style.display = "block"; moveTooltip(e);
  })
  .on("mousemove", moveTooltip)
  .on("mouseout",  () => { tooltip.style.display = "none"; });

node.append("circle")
  .attr("r", d => d.size).attr("fill", d => d.color)
  .attr("stroke", d => d.type === "root" ? "#fff" : "transparent")
  .attr("stroke-width", d => d.type === "root" ? 3 : 0);

node.append("text")
  .attr("dy", d => d.size + 12)
  .attr("font-size", d => d.type === "root" ? "10px" : d.type === "category" ? "9px" : "8px")
  .attr("font-weight", d => d.type !== "article" ? "600" : "400")
  .attr("fill", "#c8d0e8")
  .each(function(d) {
    const parts = d.label.split("\n");
    const el = d3.select(this);
    el.text(null);
    parts.forEach((p, i) => el.append("tspan").attr("x", 0).attr("dy", i === 0 ? 0 : "1.2em").text(p));
  });

simulation.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${d.x},${d.y})`);
});

const legendEl = document.getElementById("legend");
const legendHr = legendEl.querySelector("hr");
CATEGORIES.slice(1).forEach(c => {
  const div = document.createElement("div");
  div.className = "legend-item";
  div.innerHTML = `<span class="legend-dot" style="background:${c.color}"></span>${c.label.replace(/\n/g," ")}`;
  div.addEventListener("click", () => highlightCategory(c.id));
  legendEl.insertBefore(div, legendHr);
});

function highlightCategory(catId) {
  node.select("circle").transition().duration(300)
    .attr("opacity", d => (d.id === catId || d.cat === catId || d.id === "root") ? 1 : 0.18);
  link.transition().duration(300)
    .attr("opacity", d => (d.source.id === catId || d.target.id === catId || d.source.cat === catId) ? 1 : 0.08);
}
svg.on("click.bg", () => {
  node.select("circle").transition().duration(300).attr("opacity", 1);
  link.transition().duration(300).attr("opacity", 1);
});

document.getElementById("btn-reset").addEventListener("click", () => {
  svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(1));
});
let frozen = false;
document.getElementById("btn-freeze").addEventListener("click", function() {
  frozen = !frozen;
  frozen ? simulation.stop() : simulation.restart();
  this.textContent = frozen ? "▶ 恢复布局" : "暂停布局";
});

new ResizeObserver(() => {
  width  = container.clientWidth;
  height = container.clientHeight;
  simulation.force("center", d3.forceCenter(width / 2, height / 2)).alpha(0.1).restart();
}).observe(container);

function moveTooltip(e) {
  const pad = 16;
  let x = e.clientX + pad, y = e.clientY + pad;
  if (x + 290 > window.innerWidth)  x = e.clientX - 290 - pad;
  if (y + 180 > window.innerHeight) y = e.clientY - 180 - pad;
  tooltip.style.left = x + "px";
  tooltip.style.top  = y + "px";
}
</script>
</body>
</html>
```

### Step 5 — Update the period archive index

Open `docs/archive/YYYY/MM/index.md`. Find or add a `## 📖 Reading Notes` section and add entries for both new files:

```markdown
## 📖 Reading Notes

- [YYYY-MM-DD · 深度知识图谱（文字版）](YYYY-MM-DD-reading-notes.html) - Structured knowledge graph from personal reading session
- [YYYY-MM-DD · 知识图谱（交互式网络视图）](YYYY-MM-DD-knowledge-graph.html) - Interactive D3.js force-directed knowledge graph
```

### Step 6 — Verify file structure

After creating all files, verify:

```
docs/archive/YYYY/MM/
├── index.md                          ← updated with new Reading Notes entries
├── YYYY-MM-DD.md                     ← auto-generated daily digest (exists)
├── YYYY-MM-DD-reading-notes.md       ← NEW: structured text notes (Jekyll)
└── YYYY-MM-DD-knowledge-graph.html   ← NEW: interactive D3.js visualization
```

### Step 7 — Commit and push

Use `report_progress` to commit all changed files with a message like:

```
📖 Add knowledge graph for YYYY-MM-DD
```

---

## Output Quality Checklist

Before committing, verify:

- [ ] `YYYY-MM-DD-reading-notes.md` has valid Jekyll front matter (`layout: default`, `title`)
- [ ] All links in reading notes use `<a href="..." target="_blank">` HTML (not markdown `[text](url)`)
- [ ] Section anchors use `{#anchor-id}` kramdown syntax and match the TOC links
- [ ] `YYYY-MM-DD-knowledge-graph.html` is self-contained (no external dependencies except D3 CDN)
- [ ] Navigation links in both files point to the correct relative paths
- [ ] `index.md` for the period has been updated with links to both new files
- [ ] `YYYY-MM-DD-knowledge-graph.html` header links point correctly:
  - `href="/news-collector/"` for home
  - `href="YYYY-MM-DD-reading-notes.html"` for text version

---

## Reference: Existing Example

See `docs/archive/2026/02/2026-02-26-reading-notes.md` and  
`docs/archive/2026/02/2026-02-26-knowledge-graph.html` for a complete, production-quality example.
