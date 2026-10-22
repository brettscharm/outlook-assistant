# Feature status

This tracks earlier requests against implemented behavior. A local cache is not a substitute for authorization, a complete server history, or a writable Outlook integration.

## Current distribution (verified October 22, 2026)

- Desktop download: **2.19.0 Apple silicon prerelease**, linked directly from the [installation guide](INSTALL.md). GitHub’s Latest badge still belongs to 2.15.0; it is not the newest desktop package.
- Application code: **2.27.2**, installed through the in-app updater. Package/runtime updates still require a new desktop download.
- Main navigation includes Tasks, Projects, Tasks to review, Calendar, Mail, Drafts, Contacts & companies, and MCP connection. The general in-app chat has been removed.
- Subsequent features include project emails, meetings/recording attachments, custom project colors, visible subtask creation, meeting-scheduling task guidance, stronger review-history matching, owner contact details, and stable email-link recovery. Cached calendar and mail coverage remain incomplete; unavailable messages cannot be restored from the server.
- The sections below describe when earlier features were introduced, not the current installation requirements. Use the installation guide for current setup steps.

## Implemented in 2.16

- Unified work hierarchy: project boards with names/descriptions/counts, project-aware task creation, and one saved-task panel for task details, subtasks, dependencies and updates. Project context persists across page reloads; cards use a single Open task action.

- Task progress: dated notes, checklist steps, waiting-on and next-step fields. Notes and steps require explicit Add; their drafts stay locally recoverable. Waiting/next-step fields autosave. Board cards show progress and the latest note.
- Task handoff: export/import one task as JSON, including description, source link and checklist. No email contents or update history included. Import is explicit and idempotent. This is manual transfer, not cross-device delivery.
- Teams calendar: calendar-only read-only snapshot reader, Apple silicon helper, upcoming cached instances with local times and join links. Cancellation/deduplication/date tests pass. Reads both legacy Teams and the embedded Outlook calendar in partitioned WebStorage. Read-only validation on October 21 found 372 embedded calendar events and 92 upcoming meetings; the legacy store alone ended September 16. No free/busy guarantees or recurrence expansion.
- Meeting-email evidence: all cached mail folders, including Deleted Items, are searched for invitation/response subjects or .ics attachments. Downloaded .ics times/status are shown as evidence, separately from confirmed events. Folder location does not establish acceptance/cancellation. Up to 500 recent matching emails are shown with an explicit truncation notice.
- Explicit mail archive: standard .eml snapshots, including downloaded attachments, under the app’s Application Support archive directory. Existing snapshots are retained. 5 GB archive bound; 50 MB individual and 100 MB per-message attachment bounds. Missing/skipped content is counted. Excluded domains are omitted. Not a full server archive or an automatic retention bypass.
- Private Node setup: when absent, the Bob installer obtains Node 24 from nodejs.org, verifies its published SHA-256 checksum, validates archive paths, and installs without sudo. Tested with synthetic archives/mocks; not run on a clean physical Mac.
- Draft team: writer and independent grounding reviewer run separate Bob sessions concurrently (maximum two), followed by an editor session. No shell tools/subagents enabled inside those sessions; all outputs remain drafts. Three inference calls per draft; actual usage recorded. Tested with synthetic responses, not private mailbox inference.

## Implemented in 2.15

- Projects: create/rename, description, task membership, board project filter, completion counts. Tasks remain in the existing status lanes. Project metadata and membership save locally and are included in exports.
- AI assistants: editable per-purpose instructions and examples, autosave, restore defaults, and explicit sample tests through Bob. This is prompt customization, not model training or persistent autonomous subagents.
- Real activity: current/recent Bob request states and timestamps for this service session. No invented agent conversations or hidden reasoning. Ordinary requests serialize; the bounded draft team in 2.16 runs two sessions concurrently.
- Evidence-backed completion suggestions during new-mail scans, with explicit acceptance and stale-task protection. Real Bob completion quality has not been validated against a live mailbox.
- Dismissal Undo, plus the existing Dismissed → Restore workflow.
- Navigation: Tasks, Tasks to review, Mail, Drafts, Contacts & companies, Projects. Profile/writing/usage are accessible from Settings; incomplete Calendar and standalone Briefing are removed from primary navigation.
- User-triggered Bob install/update through IBM’s installer, using an app-private npm prefix. Requires an existing Node 24+ installation including npm. Does not bypass IT policy. The installer waits for Bob to be idle, suppresses raw installer logs in the UI, and never receives the app's API key.
- Daily IBM release check while the interface is running, with latest/installed version comparison in Setup. No automatic installation. Installer execution was tested with mocked processes/downloads, not on a clean Mac.

## Already implemented

Task review and local persistence, custom lanes, task details and email previews, optional priority, due-date indicators and sorting, hidden completed cards, owner/contact selection, contacts pagination and domain linking, formatted drafts, usage reporting, named-key status, dismissible errors, app code updates, Apple silicon desktop shell, automatic local recovery copies, excluded mail domains, and a mail-robot app identity.

## Not implemented / requires additional verification

| Request | Constraint / next required step |
|---|---|
| Direct Outlook calendar from cache | Calendar objects exist locally, but the available parser expects different field offsets from this Outlook cache. Recurrence, cancellations, timezone conversion and current-record selection must be validated before displaying events. Apple Calendar is an alternative only if the work calendar is already available there and local calendar permission is granted. |
| Slack DMs and selected channels | Slack cache directories exist, but no validated reader for complete, current message/thread content is available in this app. Local Storage/cookies must not be mined for tokens. Do not claim monitoring until a reader is verified against synthetic fixtures and a supported cache format. |
| Open Outlook Reply All with inserted draft | The read-only cache cannot create an Outlook draft. Supported routes require an add-in/Graph access; UI automation needs Accessibility permission and tests for exact message matching, recipients and formatting. No automatic sending. |
| Shared assignments to coworkers | Separate laptops require a shared, authenticated service or explicit file handoff. A local cache cannot deliver tasks to another user. Company authorization would be needed for a shared service. |
| Silent automatic task completion | Completion is suggested with evidence, then accepted by the user. It does not silently mark tasks done. |
| Complete server mail/attachment archive | 2.16 archives downloaded visible content only. Cloud-only bodies and attachments cannot be recovered from a local cache. |
| Focused/Other | No verified classification field in the current reader. Do not infer Outlook's actual classification from sender or subject. |
| Native floating Assistant validation | Implemented in the desktop shell; cross-app/full-screen behavior still needs interactive native acceptance testing. |
| Clean-Mac Node/Bob setup acceptance | Private Node installation is implemented; live end-to-end installation on a clean Mac remains unverified. |
| General collaborating Bob agents | A bounded writer/reviewer/editor team now drafts replies. General task agent debate, persistent agents, and user cancellation of active sessions remain unimplemented. |
| Universally installable signed release | No Developer ID credentials available. Signing/notarization tooling exists, but clean-Mac acceptance tests remain outstanding. |
| Signed code updates | Updates use HTTPS/repository commits, not an independently signed update manifest. |
| Broad desktop distribution | A 2.15 development desktop build includes current code and icon. A signed/notarized, clean-Mac-tested release is still required for broad distribution. |

Do not turn any unchecked item into a working-feature claim in the README or UI.

True model fine-tuning is not implemented; Bob profile instructions/examples are prompt customization. Automatic progress updates from email are not yet generated; users or reviewed Assistant proposals can add updates. Slack local-cache monitoring, automated Outlook Reply All insertion, automatic shared assignments, Focused/Other classification, signed updates and Apple signing/notarization remain unfinished.


## External AI clients

The general in-app chat is removed as of 2.19.0. Local MCP tools expose mail, tasks, projects, contacts, and cached calendar data. Since 2.18.1, mutation tools create/edit tasks and projects and manage task progress and checklist steps with retry deduplication and stale-edit checks. MCP connection in the main sidebar (also Settings → Connect AI apps) provides a configuration for desktop clients. No cloud endpoint or tunnel is enabled. Bob task discovery and reply drafting remain.

## Slack investigation — October 22, 2026

Local Slack IndexedDB, browser cache, and service-worker storage are present on the development Mac. Only directory structure and sizes were checked; no tokens, cookies, or credentials were extracted. These files do not establish complete or durable DM/channel coverage. No automatic Slack reader is implemented or verified.

- A supported message-context shortcut requires a Slack app with the `commands` scope: [Slack shortcuts](https://docs.slack.dev/interactivity/implementing-shortcuts/).
- Workspace/organization policy determines whether app installation requires approval: [Slack app approval](https://slack.com/help/articles/222386767-Manage-app-approval-for-your-workspace-Manage-app-installation-settings-for-your-workspace). Private distribution avoids Marketplace listing review, not workspace policy.
- Reading message history requires an authorized token and the relevant conversation scopes/access: [conversations.history](https://docs.slack.dev/reference/methods/conversations.history/). It does not grant blanket access to all DMs.
- Current local workflow: manually copy a message's text and permalink into a task, set Source to Slack, and paste the permalink in Source link. This does not install a Slack app, retrieve the message automatically, or monitor a channel. Follow the organization's rules for copying work content.

## Project transcript tasks (2.28.0)

Saved meetings support transcripts and an attached recording reference. Bob can extract evidence-backed tasks into the review queue, retaining project membership and recording links. Owner and deadline quotes are validated; unknown owners are unassigned. Re-analysis respects prior suggestions and dismissals. Imported text transcripts are limited to 60,000 characters; audio/video transcription and native capture remain unfinished.

## Project search (2.29.0)

Ask project retrieves across associated email content, saved meeting transcripts/notes, project details, tasks, subtasks and updates. Up to 24 relevant excerpts are provided to Bob. Answers validate literal source quotes and include source navigation, coverage counts and unavailable-email counts. History persists locally and exports with workspace backups. It does not transcribe recordings, parse file attachments, or open linked websites.

## Workspace search (2.30.0)

Sidebar Search spans available cached mail, saved call transcripts/notes, calendar, tasks/subtasks/updates, review suggestions, project context, contacts/companies/groups, and drafts. Timezone-aware month/week/custom/all-time filters; persistent results and backup export. Retrieval selects up to 24 excerpts per source family (four families), with three parallel evidence reviewers and a synthesis step. Source quote validation, progress polling, partial-failure and coverage notices are implemented. Audio/video transcription, attachment parsing, and external-link content retrieval remain unsupported. Concurrency and UI tests use synthetic inputs and mocked Bob responses; live multi-shell provider performance remains unverified.
