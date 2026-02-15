# Known Issues and Limitations

This document lists gaps and rough edges we are aware of in the current beta. If you encounter something not listed here, please submit feedback at `/feedback`.

---

## Known Bugs

### Minor

| # | Description | Workaround |
|---|-------------|------------|
| K-1 | Navigating to a week far in the future (10+ years) via the arrows is slow — every click creates a DB record. | Use the arrow navigation in small steps; avoid holding the button. |
| K-2 | The quick-add bar does not parse relative dates ("tomorrow", "next Monday"). Only clock-style times (`9-11`, `2h`, `45m`) are understood. | Enter tasks without a date component; log time separately. |
| K-3 | If you delete a project that has tasks assigned to it, those tasks lose their project label but are not deleted. The project field shows blank. | Re-assign affected tasks to a different project after deleting. |
| K-4 | The CSV export rounds time to the nearest 15 minutes per entry, not per day. Very short entries (< 8 min) may round to zero in the export. | Log time in meaningful blocks rather than sub-8-minute entries. |

---

## Limitations (by design for this beta)

These are not bugs — they are features we deliberately scoped out for the initial release.

| # | Limitation | Notes |
|---|-----------|-------|
| L-1 | **No undo.** Deleting a task or work entry is permanent. | We plan to add a short-window undo in a future release. |
| L-2 | **No drag-to-reorder.** Tasks can only be reordered with the ↑ / ↓ keyboard shortcuts or the move buttons. | This is the intended UX for now. |
| L-3 | **Delegation is free text only.** The delegate field accepts any string — it does not link to another user account. | Type the person's name manually. |
| L-4 | **No bulk actions.** You cannot complete or delete multiple tasks at once. | Select and act on tasks individually. |
| L-5 | **No task estimates / time budgets.** You can only log actual time spent, not planned duration. | Out of scope for this beta. |
| L-6 | **All data is per account.** There is no sharing, collaboration, or team workspace. | Out of scope for this beta. |
| L-7 | **No notifications or reminders.** The app does not send email or push alerts. | Out of scope for this beta. |
| L-8 | **No calendar integration.** Tasks cannot be synced with Google Calendar, Outlook, etc. | Out of scope for this beta. |
| L-9 | **No recurring tasks.** Each task must be created manually each week. | Carry-forward (active tasks rolling to next week) partially covers this. |
| L-10 | **No mobile native app.** The app runs in a mobile browser only. Some touch interactions may feel limited. | Please report any mobile UX issues — we are testing this. |

---

## Performance Notes

- The app has not been load-tested. If you experience slowness with a large number of tasks or work entries, please note it in your feedback.
- The weekly summary recalculates on every page load. With many entries, this may be noticeable.

---

## Browser Compatibility

Tested in Chrome, Firefox, and Safari (latest versions). Older browsers may have issues with HTMX-driven partial updates. Please note your browser and version when reporting bugs.

---

## Out of Scope for This Beta

The following were explicitly excluded and will not be addressed during the beta period:

- Team / shared workspaces
- Calendar sync (Google Calendar, Outlook, iCal)
- Mobile native apps (iOS / Android)
- Time budgets and estimates
- Notifications and reminders
- Reporting beyond weekly CSV export
- Dark mode

---

## Reporting New Issues

Use the **Feedback** link in the app footer or go to `/feedback`. No login required.

Please include:
1. What you were trying to do
2. What happened instead
3. Your browser and device (especially for mobile issues)
4. How often it happens (always / sometimes / once)
