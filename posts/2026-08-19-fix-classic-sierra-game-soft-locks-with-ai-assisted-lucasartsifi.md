---
title: "Fix Classic Sierra Game Soft-Locks with AI-Assisted Lucasartsifier"
date: "2026-08-19"
tags: ["ai", "gaming", "opensource", "retro"]
summary: "Replay retro adventure games without fear of unwinnable states. Lucasartsifier uses AI-assisted static analysis to automatically patch classic Sierra titles."
source_url: "https://github.com/katiahayati/lucasartsifier/"
source_title: "Show HN: Automatically detect and patch walking-dead states in Sierra games"
---
Classic Sierra adventure games are infamous for soft-locking players who forget a key item hours prior. To solve this retro gaming headache, an indie developer created Lucasartsifier, a static analysis tool that automatically fixes these walking-dead scenarios.

The project decompiles original Sierra resource files to locate unwinnable states. It then generates code patches that stop players from advancing until necessary requirements are met, turning brutal Sierra logic into a fairer LucasArts-style experience.

Key features include:
- Support for titles like Leisure Suit Larry 2 and King's Quest 6
- Generic logic engine that patches games without custom hardcoding
- Built using Claude for code generation alongside human playtesting

Explore the source code on [GitHub](https://github.com/katiahayati/lucasartsifier/).
