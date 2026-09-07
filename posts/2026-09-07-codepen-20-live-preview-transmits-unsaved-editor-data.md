---
title: "CodePen 2.0 Live Preview Transmits Unsaved Editor Data"
date: "2026-09-07"
tags: ["codepen", "security", "webdev", "privacy"]
summary: "A recent community test reveals CodePen 2.0 streams unsaved editor text to preview servers within seconds, raising privacy concerns for developers."
source_url: "https://news.ycombinator.com/item?id=49596976"
source_title: "Apparently CodePen 2.0 sends data to their servers as you type"
---
CodePen 2.0 users should be mindful when editing sensitive information. Community testing shows that the updated editor automatically transmits typed input to background servers almost immediately, well before you click save.

In a recent test, un-saved text entered into index.html triggered a background build with a save false flag. The typed text then surfaced verbatim inside the generated preview served from codepen.dev.

Important security details:
- Text sends to preview servers in just one to two seconds.
- Preview builds generate live without explicit saving.
- Accidental API keys or secrets entered in the editor should be considered compromised.

Read the full report on [Hacker News](https://news.ycombinator.com/item?id=49596976).
