# Feature status

This tracks earlier requests against implemented behavior. A local cache is not a substitute for authorization, a complete server history, or a writable Outlook integration.

## Implemented in 2.16

- Unified work hierarchy: project boards with names/descriptions/counts, project-aware task creation, and one saved-task panel for task details, subtasks, dependencies and updates. Project context persists across page reloads; cards use a single Open task action.

- Task progress: dated notes, checklist steps, waiting-on and next-step fields. Notes and steps require explicit Add; their drafts stay locally recoverable. Waiting/next-step fields autosave. Board cards show progress and the latest note.
- Assistant proposals can add task notes/checklist steps and change waiting/next-step fields, with Apply and stale-task checks.
- Task handoff: export/import one task as JSON, including description, source link and checklist. No email contents or update history included. Import is explicit and idempotent. This is manual transfer, not cross-device delivery.
- Teams calendar: calendar-only read-only snapshot reader, universal helper, upcoming cached instances with local times and join links. Cancellation/deduplication/date tests pass. Real-cache validation found 3,174 calendar records but no upcoming meetings in the next 30 days; opening Teams Calendar may refresh its coverage. No free/busy guarantees or recurrence expansion.
- Meeting-email evidence: all cached mail folders, including Deleted Items, are searched for invitation/response subjects or .ics attachments. Downloaded .ics times/status are shown as evidence, separately from confirmed events. Folder location does not establish acceptance/cancellation. Up to 500 recent matching emails are shown with an explicit truncation notice.
- Explicit mail archive: standard .eml snapshots, including downloaded attachments, under the app’s Application Support archive directory. Existing snapshots are retained. 5 GB archive bound; 50 MB individual and 100 MB per-message attachment bounds. Missing/skipped content is counted. Excluded domains are omitted. Not a full server archive or an automatic retention bypass.
- Private Node setup: when absent, the Bob installer obtains Node 24 from nodejs.org, verifies its published SHA-256 checksum, validates archive paths, and installs without sudo. Tested with synthetic archives/mocks; not run on a clean physical Mac.
- Native floating Assistant: app menu → Float Assistant Above Other Apps (Cmd+J); return with the same command. Requires the 2.16 desktop bundle, not just a code update.
- Draft team: writer and independent grounding reviewer run separate Bob sessions concurrently (maximum two), followed by an editor session. No shell tools/subagents enabled inside those sessions; all outputs remain drafts. Three inference calls per draft; actual usage recorded. Tested with synthetic responses, not private mailbox inference.

## Implemented in 2.15

- Projects: create/rename, description, task membership, board project filter, completion counts. Tasks remain in the existing status lanes. Project metadata and membership save locally and are included in exports.
- AI assistants: editable per-purpose instructions and examples, autosave, restore defaults, and explicit sample tests through Bob. This is prompt customization, not model training or persistent autonomous subagents.
- Real activity: current/recent Bob request states and timestamps for this service session. No invented agent conversations or hidden reasoning. Ordinary requests serialize; the bounded draft team in 2.16 runs two sessions concurrently.
- Assistant task changes support priority, project, and source links as reviewable proposals.
- Evidence-backed completion suggestions during new-mail scans, with explicit acceptance and stale-task protection. Real Bob completion quality has not been validated against a live mailbox.
- Dismissal Undo, plus the existing Dismissed → Restore workflow.
- Navigation: Tasks, Tasks to review, Mail, Drafts, Contacts & companies, Projects. Profile/writing/usage are accessible from Settings; incomplete Calendar and standalone Briefing are removed from primary navigation.
- User-triggered Bob install/update through IBM’s installer, using an app-private npm prefix. Requires an existing Node 24+ installation including npm. Does not bypass IT policy. The installer waits for Bob to be idle, suppresses raw installer logs in the UI, and never receives the app's API key.
- Daily IBM release check while the interface is running, with latest/installed version comparison in Setup. No automatic installation. Installer execution was tested with mocked processes/downloads, not on a clean Mac.

## Already implemented

Task review and local persistence, custom lanes, task details and email previews, optional priority, due-date indicators and sorting, hidden completed cards, owner/contact selection, contacts pagination and domain linking, formatted drafts, floating in-app Assistant, usage reporting, named-key status, dismissible errors, app code updates, universal desktop shell, automatic local recovery copies, excluded mail domains, and a mail-robot app identity.

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
| Universally installable signed release | No Developer ID credentials available. Signing/notarization tooling exists, but clean-Mac and physical Intel acceptance tests remain outstanding. |
| Signed code updates | Updates use HTTPS/repository commits, not an independently signed update manifest. |
| Broad desktop distribution | A 2.15 development desktop build includes current code and icon. A signed/notarized, clean-Mac-tested release is still required for broad distribution. |

Do not turn any unchecked item into a working-feature claim in the README or UI.

True model fine-tuning is not implemented; Bob profile instructions/examples are prompt customization. Automatic progress updates from email are not yet generated; users or reviewed Assistant proposals can add updates. Slack local-cache monitoring, automated Outlook Reply All insertion, automatic shared assignments, Focused/Other classification, signed updates and Apple signing/notarization remain unfinished.
