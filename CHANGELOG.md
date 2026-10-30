# Changelog

## 0.1.0 (2026-10-30)

First release.

- One list of every Claude Code session (VSCode, CLI, Claude Desktop) and Codex thread (app, CLI, IDE, Chrome, every model provider), with status, latest step and last activity.
- `catchup` and the portal's Needs you view: sessions blocked on a decision first, then new replies, with read marks.
- Local web portal: session tables, a detail panel, and links that open each session in VSCode, Claude Desktop, Codex or a terminal.
- Insights: sessions, prompts, tokens, tool calls, files edited and linked PRs over 7, 30 or 90 days or all time, by runtime, model and project. Usage history is kept when agents delete old transcripts.
- Briefings: daily, weekly and monthly reports written by an LLM, with an overview, next steps, highlights, risks and the full record by category, project and task.
- Runs on Python 3.9 and newer with the standard library only. A session that cannot be parsed is listed with its error instead of breaking the other commands.
- Demo data generator and an end-to-end smoke test.
