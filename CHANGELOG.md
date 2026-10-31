# Changelog

## Unreleased

- Portal: the Needs you view is now the Workbench (`#workbench`; old `#inbox`, `#catchup`, `#week` and `#all` links still work). It opens with a strip of apps that have active sessions, then Waiting on a decision, a new Running zone with each session's latest step and your last prompt, and New replies.
- New replies has sub tabs per app plus Project and Topic selects. Counts match the list, and the mark-as-read button acts on exactly the replies shown.
- The This week view is gone. All sessions has a When select (today, this week, started this week, picked up again this week, last 3, 7 or 30 days, any time) and Project and Topic selects beside the app select.
- A session's topic is the category of the newest cached briefing that mentions it. `/api/list` and `/api/catchup` return it as `topic`, and `/api/catchup` also returns the `running` sessions.
- New look: a floating glass top bar replaces the sidebar, on a dark frosted-glass theme with a light variant (toggle in the bar, saved in the browser). It follows reduced-motion and reduced-transparency settings.

## 0.1.0 (2026-10-30)

First release.

- One list of every Claude Code session (VSCode, CLI, Claude Desktop) and Codex thread (app, CLI, IDE, Chrome, every model provider), with status, latest step and last activity.
- `catchup` and the portal's Needs you view: sessions blocked on a decision first, then new replies, with read marks.
- Local web portal: session tables, a detail panel, and links that open each session in VSCode, Claude Desktop, Codex or a terminal.
- Insights: sessions, prompts, tokens, tool calls, files edited and linked PRs over 7, 30 or 90 days or all time, by runtime, model and project. Usage history is kept when agents delete old transcripts.
- Briefings: daily, weekly and monthly reports written by an LLM, with an overview, next steps, highlights, risks and the full record by category, project and task.
- Runs on Python 3.9 and newer with the standard library only. A session that cannot be parsed is listed with its error instead of breaking the other commands.
- Demo data generator and an end-to-end smoke test.
