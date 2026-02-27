---
layout: default
title: 📖 Knowledge Graph Contribution Guide
---

# 📖 Knowledge Graph Contribution Guide

> **System Prompt** — How to contribute a daily personal reading knowledge graph to this repository.

<div style="margin-bottom: 1rem;">
  <a href="/news-collector/" style="display: inline-block; padding: 0.5rem 1rem; background: #667eea; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem;">← Back to Home</a>
</div>

---

## 🧭 Overview

This repository uses a **two-file system** for personal daily reading notes:

| File | Role |
|------|------|
| `YYYY-MM-DD-reading-notes.md` | Structured Markdown — your annotated notes, organized by topic, each with *what / why / next* |
| `YYYY-MM-DD-knowledge-graph.html` | Interactive HTML visualization — a D3.js force-directed graph linking the same concepts |

You write the **reading notes**. The agent generates **both files** and updates the archive index.

---

## 🔄 Collaboration Workflow

```
Daily workflow
──────────────
1. GitHub Actions auto-generates the daily news digest
   (runs at 08:00 UTC, committed to docs/YYYY-MM-DD.md)

2. You read the digest (and other sources), pick the stories
   that interest you, and write your reading notes
   following the format below.

3. You tell the agent:
   "我今天的知识图谱写好了" (or paste your draft)

4. The agent:
   • Validates / polishes your reading notes markdown
   • Generates the interactive knowledge-graph HTML
   • Updates docs/archive/YYYY/MM/index.md
   • Commits and pushes everything
```

---

## 📁 File Naming & Placement

Place all personal knowledge graph files in:

```
docs/archive/YYYY/MM/
```

| File | Naming rule | Example |
|------|-------------|---------|
| Reading notes | `YYYY-MM-DD-reading-notes.md` | `2026-02-26-reading-notes.md` |
| Knowledge graph | `YYYY-MM-DD-knowledge-graph.html` | `2026-02-26-knowledge-graph.html` |

> **Rule:** Always use the **date you did the reading**, not the date of the articles.

---

## 📝 Reading Notes Format

### Required front matter

Every reading-notes file **must** start with:

```yaml
---
layout: default
title: 📖 Reading Notes · YYYY-MM-DD
---
```

### Navigation header

Copy and adapt this block at the top of the file body (after front matter):

```html
<div style="margin-bottom: 1rem;">
  <a href="/news-collector/" style="...">← Back to Home</a>
  <a href="index.html" style="...">← Back to [Month] [Year]</a>
  <a href="YYYY-MM-DD-knowledge-graph.html" style="...">🕸 交互式知识图谱 →</a>
</div>
```

### Document structure

```
# 📖 今日新闻阅读 — 深度知识图谱 · YYYY-MM-DD

> 🗓️ 结构化摘要与原始链接 · 按主题节点组织

[one-line session summary]

---

## 📑 目录
- [概览节点](#overview)
- [CATEGORY entries ...]
- [🎯 快速可执行结论](#actionable-conclusions)

---

## 概览节点 {#overview}
[What you started from — usually the daily digest link]

---

## [CATEGORY SECTIONS]

---

## 🎯 快速可执行结论 {#actionable-conclusions}
```

### Category section structure

Each category section contains one or more **article entries**. A category is a theme or domain (e.g., "Agentic AI 技术生态", "软件工程 CI/CD").

```markdown
## 🤖 Agentic AI 技术生态（中心节点） {#agentic-ai}

### [Article or Concept Title]

**要点（what）**：One or two sentences describing the key fact or finding.

**意义（why）**：Why this matters to you or the field.

**可行动线索（how / next）**：A concrete action you could take based on this.

🔗 <a href="https://..." target="_blank">Source Name · Article Title</a>

---
```

**Required fields per article entry:**
- `**要点（what）**` — the key finding
- `**意义（why）**` — why it matters
- `**可行动线索（how / next）**` — concrete next step
- At least one `<a href="..." target="_blank">` link

### Actionable Conclusions section

End with a numbered list of 2–5 concrete takeaways:

```markdown
## 🎯 快速可执行结论 {#actionable-conclusions}

### 1. [Action title]

2–3 sentences synthesizing multiple articles into one concrete step.

### 2. [Action title]

...
```

### Links rule

> ⚠️ **Important:** Always use HTML `<a>` tags for links, NOT Markdown `[text](url)` syntax.
> Markdown links inside the content body do not render correctly on GitHub Pages (Jekyll/kramdown).

✅ Correct:
```html
🔗 <a href="https://example.com" target="_blank">Example.com · Article Title</a>
```

❌ Wrong:
```markdown
🔗 [Example.com · Article Title](https://example.com)
```

---

## 🗺️ Knowledge Graph Data Structure

When you write your reading notes, the agent will also generate the interactive knowledge graph. You can optionally pre-specify the graph data in your notes to give the agent better guidance.

### CATEGORIES

Each category is a colored **hub node** in the graph:

```
Fields:
  id     — short snake_case, prefixed with "cat-"    e.g. "cat-ai"
  label  — display label, \n separates title/subtitle e.g. "🤖 AI\n技术生态"
  color  — hex color (see palette)                   e.g. "#667eea"
  size   — node size (use 22 for categories)
  group  — integer index starting at 1
```

Recommended color palette:

| Theme | Color |
|-------|-------|
| AI / ML / LLM | `#667eea` |
| Security / Privacy | `#f5a623` |
| Engineering / DevOps | `#43e97b` |
| Business / Industry | `#fa709a` |
| Personal Projects | `#4facfe` |
| Science / Academia | `#a29bfe` |
| Culture / Misc | `#fd79a8` |

### ARTICLES

Each article is a smaller **leaf node** connected to its category:

```
Fields:
  id    — short unique snake_case                e.g. "cowork"
  cat   — parent category id                    e.g. "cat-ai"
  label — display label, \n for line break       e.g. "Anthropic\nCowork"
  url   — full URL                               e.g. "https://venturebeat.com/..."
  desc  — 1–3 sentences (Chinese preferred)      e.g. "桌面级 Agent..."
```

### CROSS_EDGES

Cross-cutting **connections between articles** in different categories:

```
Fields:
  source — article id
  target — article id
  label  — short description of the connection
```

Aim for 5–12 cross edges to keep the graph interesting without being overwhelming.

---

## ✅ Contribution Checklist

Before telling the agent your notes are ready, confirm:

- [ ] File is named `YYYY-MM-DD-reading-notes.md` with the correct date
- [ ] Front matter has `layout: default` and `title`
- [ ] All URL links use `<a href="..." target="_blank">` HTML tags
- [ ] Each article entry has 要点 / 意义 / 可行动线索
- [ ] Section anchors `{#id}` match the TOC links
- [ ] At least one 🎯 快速可执行结论 entry
- [ ] You've told the agent which date the notes are for

---

## 💬 How to Tell the Agent You're Done

You can say any of the following:

> "我今天的知识图谱写好了，日期是 YYYY-MM-DD"

> "I've finished my reading notes for YYYY-MM-DD, please generate the knowledge graph"

> "帮我把下面的阅读笔记整理成知识图谱：[paste your draft]"

The agent will:
1. Validate and optionally polish your reading notes
2. Generate the interactive knowledge graph HTML
3. Update `docs/archive/YYYY/MM/index.md`
4. Commit and push all files

---

## 📂 Example

See the complete example for 2026-02-26:

- 📄 [Reading Notes (text)](../archive/2026/02/2026-02-26-reading-notes.html) — structured markdown notes
- 🕸 [Knowledge Graph (interactive)](../archive/2026/02/2026-02-26-knowledge-graph.html) — D3.js visualization

---

<div style="text-align: center; padding: 2rem 0; color: #666;">
  <p>📖 Part of <a href="https://github.com/Brickea/news-collector">news-collector</a> · Personal knowledge management workflow</p>
</div>
