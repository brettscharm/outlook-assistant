# Feature status

This tracks earlier requests against implemented behavior. A local cache is not a substitute for authorization, a complete server history, or a writable Outlook integration.

## Implemented in 2.15

- Projects: create/rename, description, task membership, board project filter, completion counts. Tasks remain in the existing status lanes. Project metadata and membership save locally and are included in exports.
- AI assistants: editable per-purpose instructions and examples, autosave, restore defaults, and explicit sample tests through Bob. This is prompt customization, not model training or persistent autonomous subagents.
- Real activity: current/recent Bob request states and timestamps for this service session. No invented agent conversations or hidden reasoning. Only one Bob request runs at a time.
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
| Outlook/Teams calendar from cache | Calendar objects exist locally, but the available parser expects different field offsets from this Outlook cache. Recurrence, cancellations, timezone conversion and current-record selection must be validated before displaying events. Apple Calendar is an alternative only if the work calendar is already available there and local calendar permission is granted. |
| Slack DMs and selected channels | Slack cache directories exist, but no validated reader for complete, current message/thread content is available in this app. Local Storage/cookies must not be mined for tokens. Do not claim monitoring until a reader is verified against synthetic fixtures and a supported cache format. |
| Open Outlook Reply All with inserted draft | The read-only cache cannot create an Outlook draft. Supported routes require an add-in/Graph access; UI automation needs Accessibility permission and tests for exact message matching, recipients and formatting. No automatic sending. |
| Shared assignments to coworkers | Separate laptops require a shared, authenticated service or explicit file handoff. A local cache cannot deliver tasks to another user. Company authorization would be needed for a shared service. |
| Silent automatic task completion | Completion is suggested with evidence, then accepted by the user. It does not silently mark tasks done. |
| Full mail/attachment archive | Not implemented. Cache coverage and retention policy must be understood; backup exports do not include mail or attachments. |
| Focused/Other | No verified classification field in the current reader. Do not infer Outlook's actual classification from sender or subject. |
| Assistant overlay on Outlook itself | Assistant floats only inside this app. A separate native panel and window/lifecycle testing are still required. |
| Automatic Node installation | Not implemented. Node installation remains with IBM’s official setup instructions. |
| Multiple collaborating Bob shells | Intentionally not enabled: current sessions disable subagents and tools. Needs bounded orchestration, evidence validation, usage visibility, and cancellation/recovery tests before replacing the serial workflow. |
| Universally installable signed release | No Developer ID credentials available. Signing/notarization tooling exists, but clean-Mac and physical Intel acceptance tests remain outstanding. |
| Signed code updates | Updates use HTTPS/repository commits, not an independently signed update manifest. |
| Broad desktop distribution | A 2.15 development desktop build includes current code and icon. A signed/notarized, clean-Mac-tested release is still required for broad distribution. |

Do not turn any unchecked item into a working-feature claim in the README or UI.
