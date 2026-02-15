# Beta Testing Guide

Thank you for testing Notetime. This guide covers everything you need to get started, what to focus on, and how to send feedback.

---

## Accessing the App

The app runs in your browser — no installation required.

**URL:** provided separately by the team

**To create an account:** click **Register** on the login page. Use any email and a password of at least 8 characters.

---

## What Notetime Does

Notetime is a notebook-style weekly planner combined with a time tracker. The idea:

- You plan tasks at the start of the week
- You log actual time spent as you work
- At the end of the week you get a summary grouped by project

There is no backlog. Every task is either **active**, **delegated**, **completed**, or **canceled**. Active and delegated tasks automatically carry forward to the next week if not finished.

---

## Core Workflow

### 1. Plan your week

Open the app and you land on the current week. Add tasks using **+ New Task** or the quick-add bar at the top (natural language entry — see below).

### 2. Log time as you work

Click **+ Log Time** to record minutes spent on a task. You can log multiple entries per task per day. Enter actual minutes — the weekly summary rounds up to the nearest 15 minutes automatically.

### 3. Manage tasks inline

Select a task to reveal actions:

| Action | What it does |
|--------|-------------|
| Complete | Marks the task done. It stays in this week's record. |
| Delegate | Marks it handed off (you can still log time against it). |
| Defer | Moves the task to next week. |
| Delete | Removes the task and all its time entries permanently. |

### 4. Review your week

The summary panel shows hours per project and task, rounded to the nearest quarter-hour. Export to CSV from the week menu if you need to copy numbers elsewhere.

### 5. Navigate weeks

Use the week navigation arrows to move between weeks. Active tasks that weren't finished will appear in the next week.

---

## Quick-Add (Natural Language Entry)

The quick-add bar accepts plain-text entries:

| You type | What gets created |
|----------|------------------|
| `P1 Review client proposal` | Priority-1 task |
| `@API update auth endpoints` | Task tagged to project "API" |
| `9-11 client meeting` | 2-hour time log (120 min) |
| `2h fixed bug @Backend` | 2-hour log tagged to "Backend" project |
| `45m standup` | 45-minute time log |

---

## Projects

Create projects at the **Projects** page (Ctrl+P). Assign tasks to projects when creating them. The weekly summary groups time by project.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New task |
| Ctrl+T | Log time |
| Ctrl+P | Open projects |
| Ctrl+X | Complete selected task |
| Ctrl+D | Delegate selected task |
| ↑ / ↓ | Navigate task list |
| Enter | Edit selected task title |

---

## Submitting Feedback

Use the **Feedback** link in the footer (or go to `/feedback`). No login required.

Please tell us:
- **What you were trying to do**
- **What happened instead** (or what felt clunky)
- **How often it happens** (always / sometimes / once)

The form has categories for bugs, feature requests, UX issues, and general thoughts. A rating (1–5) is optional but helpful.

---

## Known Limitations

See [KNOWN-ISSUES.md](KNOWN-ISSUES.md) for the current list of known gaps and workarounds.

---

## What We Are Specifically Testing

1. **Does the weekly planning flow feel natural?** Creating tasks, ordering them, moving between weeks.
2. **Is time logging friction-free?** Minutes entry, quick-add, editing entries.
3. **Are the summaries useful?** Does the project grouping and quarter-hour rounding match how you bill or report time?
4. **Does task deferral work as expected?** Tasks moved to next week, carry-forward behavior.
5. **Mobile usability.** The app should work on phone browsers — please test if you can.

---

## Things Not in Scope for This Beta

- Shared / team access (all data is per account)
- Calendar integrations
- Time budget / estimates
- Notifications or reminders
- Mobile native app

---

## Support

If you find a bug that blocks you entirely, reach out directly rather than waiting for the feedback form. Contact details provided separately.
