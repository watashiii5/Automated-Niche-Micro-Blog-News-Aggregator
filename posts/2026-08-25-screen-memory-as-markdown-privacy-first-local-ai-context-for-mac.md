---
title: "Screen Memory as Markdown: Privacy-First Local AI Context for macOS"
date: "2026-08-25"
tags: ["macos", "productivity", "ai", "privacy", "markdown"]
summary: "Track your daily Mac activity without heavy OCR or screenshots. Ambient Context saves window text into plain Markdown so AI assistants can instantly query your work history."
source_url: "https://github.com/dragthelake/ambient-context"
source_title: "Show HN: Screen memory without screenshots, just text to Markdown"
---
Keeping track of what you worked on throughout the week often means relying on resource-heavy screenshot recorders or invasive OCR tools. A new open-source macOS menu bar app offers a much lighter alternative by grabbing plain text directly from your focused windows.

By pulling text via the native Accessibility API every few seconds, it quietly logs your activity into daily Markdown files inside a local folder of your choice. It even auto-generates an AGENTS.md file so local AI assistants and tools like Claude Code can immediately parse your context.

Here is why this approach stands out:
- Zero screenshots, video recording, or OCR processing
- Entirely local Markdown output saved per day
- Native compatibility with file-reading LLM workflows

It is a simple, privacy-minded way to build a searchable knowledge base of your digital workflow for your favorite AI tools.

Source: https://github.com/dragthelake/ambient-context
