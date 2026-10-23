# Outlook Assistant for Mac

A desktop workspace for mail cached by Outlook, tasks, contacts, projects, and optional IBM Bob task discovery and email drafting. Opens in its own Mac window—no browser or Terminal needed for everyday use.

## Install on a Mac

1. **[Download Outlook Assistant for Mac](https://github.com/brettscharm/outlook-assistant/releases/download/v2.19.0/Outlook-Assistant-2.19.0-Apple-Silicon-Mac.zip)**.
2. Open the ZIP and drag **Outlook Assistant.app** into **Applications**.
3. Open **Outlook**, then **Outlook Assistant**.
4. Follow **Settings → Setup**. Follow **[Get your Bob API key](docs/INSTALL.md#get-your-bob-api-key)**, then add your name/email to enable task suggestions.

**[Step-by-step installation and troubleshooting →](docs/INSTALL.md)**

The Mac app includes Python and the mail reader. You do not need Git, Xcode, Python, or Homebrew to open it. AI features additionally require **Bob Shell 2.x and Node.js 24+**; Settings → Setup → Install or update Bob installs a private Node 24 runtime if needed, then runs IBM’s installer. Installation starts with an explicit click.

**Requirements:** macOS 13 or later, Apple silicon (M1 or later), and New Outlook with a supported local cache. Compatibility with every Mac, Outlook version, and company-managed device is not guaranteed. The current downloadable app is ad-hoc signed, **not Developer ID signed or notarized**. macOS or company policy may block it; do not disable security controls.

**Download versus app version:** the newest packaged desktop download is the **2.19.0 prerelease**. GitHub’s generic Latest link points to the older 2.15 build; use the explicit download link above. Newer application features are delivered by the in-app updater. See the [feature status](docs/FEATURE_STATUS.md) for implemented features and remaining integrations. Keep the app open and connected to the internet; installation waits for a safe idle period and for active Bob work to finish. The displayed version changes after the update restarts the service. A package update does not replace the bundled runtime or Finder/Dock icon; those require a newer desktop download.

## Everyday use

- **Tasks:** create and edit tasks, customize lanes, and drag cards between them. Priority is always shown, including No priority; due dates and priority support sorting. Each task has an optional local-time reminder and repeat interval in days. Reminders autosave, skip completed tasks, and check missed times after wake or restart while the app service is running. No Bob usage is involved. macOS notification/Focus settings control visibility; the current AppleScript delivery may be listed under Script Editor. Upcoming deadlines stand out; completed cards turn gray and can be hidden without deleting them.
- **Tasks to review:** review suggested actions before adding them. Accepting one keeps you on the review page. Unclear suggestions default to you; choosing My task uses your saved name. You can assign a different owner or dismiss a suggestion with a reason and undo it. New-mail checks can also suggest completing existing tasks with a supporting quote; acceptance is required.
- **Mail:** browse cached mail and folders, search, preview source emails, and draft replies. Stable message identities recover links when Outlook changes local row IDs; unavailable task previews offer conversation search. Deleted or uncached mail cannot be restored by this app. Outlook must download new mail before this app can read it.
- **Drafts:** drafts save locally. Copy a draft into Outlook, review it, and send it there. The app does not send mail or insert Reply All drafts into Outlook.
- **Contacts:** browse cached senders by domain and link multiple domains to one company. This is not an Outlook address-book sync.
- **Projects:** group related tasks, filter the board, and see completion counts. Open a Calendar event to add it to a project’s Meetings list; filter month, week, or day views by project or No project. Links apply to the selected occurrence and do not change Outlook or Teams.
- **Settings → AI assistants:** edit instructions and examples, restore defaults, and test sample content. **AI activity** shows real request status.
- **Settings → Profile & writing:** your identity, role, writing style, and usage details. Calendar reads cached Teams meetings.

Your name, role, account list, and writing preferences help personalize Bob’s results. Writing style uses examples and instructions; it does not train a new model. Usage reports this app’s recorded Bobcoins and available token counts, not an account-wide balance or dollar bill.

## Automatic task discovery and sync

Long emails are checked in overlapping sections, so requests after the first 6,000 characters are included. Each suggestion links to its original email. Dismissed and accepted suggestions remain remembered across rescans and updates. Matching uses stable message identifiers when available, normalized titles and evidence, and relevant review history supplied to Bob. Cross-email checks also compare concrete deadlines, owners, subjects, and sufficiently specific titles or evidence. Pending suggestions are included in Bob’s review context. Matching saved tasks offer a comparison view; they are not automatically merged or deleted. Distinct new requests can still appear; semantic matching is not perfect. Scans resume from saved checkpoints, and invalid evidence is retried instead of silently counted as finished. Only mail actually available in Outlook’s local cache can be checked; previews may omit work. See [the core workflow audit](docs/core-workflow-audit.md) for test results and remaining limits.

After identity and Bob connection setup, a fresh configuration defaults to checking every **15 minutes**, initially looking back **seven days**. Existing saved scan settings are preserved. Change the date range or pause discovery in **Tasks to review → Email task options**.

Checks run while the app’s local service is running and process unprocessed or changed cached messages in batches. Relevant message excerpts and saved context go to IBM Bob using your allowance. The app imposes no spending cap; IBM account limits still apply. Mail-only reads do not use Bob.

**Sync now** refreshes cached mail and requests a task check when setup is complete and Bob is available. It cannot force Outlook to download cloud mail. Keep Outlook open and synced for fresh data. Bob receives limited cached excerpts, so review task ownership, dates, and generated answers.

## Your data and updates

Saved tasks, drafts, chat, and preferences live outside the app bundle and survive normal restarts and updates. Changes autosave; adding a new task and accepting a suggestion remain explicit actions.

- User data: `~/.outlook_assistant_*.json` in your Mac user folder.
- Local recovery copies: `~/.outlook_assistant_backups`.
- Updated app code: `~/Library/Application Support/Outlook Assistant/app`.
- **Settings → Startup & storage → Export a backup** creates an extra copy excluding your Bob key and mailbox. In-app backup import is not implemented.

Private files have owner-only permissions, not encryption. Local recovery copies may contain credentials and private work content; use your normal Mac backup for protection against laptop or disk loss. The app does not send usage registrations to the repository owner.

Keep one app at `~/Applications/Outlook Assistant.app` or `/Applications/Outlook Assistant.app`. Code updates use the same Application Support directory and do not create duplicate apps. To replace the desktop bundle, quit the app and replace that same copy. Do not delete your user-data files to update.

Updates use HTTPS and an exact repository commit; they do not yet have independently signed update manifests. Developer ID signing, notarization, and fresh-machine testing remain production-release requirements. See the [Mac release checklist](docs/MAC_RELEASE_CHECKLIST.md).

## Outlook cache access

The reader discovers profiles under:

```text
~/Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles/<profile>/HxStore.hxd
```

It reads a temporary copy and does not modify Outlook’s store. Select a profile in Settings if several are found. No Microsoft app registration or Graph sign-in is used for this local-cache path. macOS permissions and organization policy still apply.

Outlook’s private cache format can change. This is an experimental reader, not a Microsoft-supported mailbox export. A missing body displays as Preview only. Cloud-only mail, cloud-only attachments, Slack ingestion, and automatic shared task delivery are not supported. Calendar reads cached Teams instances; it is not a complete calendar sync.

## Developers

For source development, Python is required. Double-click **Launch Outlook Assistant.command** or run `./run.sh` from a checkout. The similarly named **Install Outlook Assistant.command** is a source launcher, not the packaged desktop installer. Most users should use the release ZIP above.

```sh
python3 -m unittest discover -s tests -v
node tests/task_sort.test.cjs
cd vendor/hxmail && go test ./...
```

Build the Apple silicon readers with `scripts/build_readers.sh` and the Mac app with `scripts/build_mac.sh` using Apple silicon Python and PyInstaller. Signing and notarization require your own Apple Developer credentials; see [release instructions](docs/MAC_RELEASE_CHECKLIST.md).

For isolated tests, set `OUTLOOK_ASSISTANT_DATA_DIR` and `OUTLOOK_ASSISTANT_PROFILE_ROOT`. Never use real mail or credentials as fixtures. Legacy Outlook tests require explicit `OUTLOOK_LEGACY_E2E=1`.

See `vendor/hxmail/UPSTREAM.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md` for provenance and licenses.

## Tasks and calendar in 2.16

Open a project to work on its board. New tasks inherit that project. Choose **Open task** for details, subtasks, updates, waiting-on and next steps in one panel. Project progress counts completed tasks; subtasks track the steps inside each task. Use **Export task** / **Import task** for an explicit coworker handoff. Files contain task descriptions and source links; review them before sharing.

**Calendar** shows upcoming cached Teams instances. Open Teams Calendar to refresh coverage. **Meeting emails** also checks Deleted Items for invitations and responses; these are evidence, not a confirmed calendar. Missing events never establish availability.

**Settings → Startup & storage → Archive downloaded mail** saves EML files and available attachments, with size limits and missing-content counts. It cannot recover cloud-only content.

The desktop app menu offers **Float Assistant Above Other Apps** (Cmd+J). This requires the new desktop bundle. Reply drafting now runs a bounded writer/reviewer/editor workflow and uses three Bob requests per draft.

### Files on tasks and projects
Open a saved task or edit a saved project, then choose **Attach files**. Word, Excel,
PowerPoint, PDF, text, images, video, and audio recordings are supported, up to 2 GB each. **Open** uses
your Mac's default app for that document. The assistant keeps its own copy; edits
made after opening that copy are retained. Removing an attachment deletes that
copy only, leaving the original unchanged.

Files live in `~/Library/Application Support/Outlook Assistant/attachments`, outside
the application and update folders. They survive app updates and restarts. Include
that folder in your Mac backup; downloadable JSON workspace backups and task
exports do not include attachment files. Attachments are not sent to Bob.


### Task cards and meeting deadlines
Task cards show due time, priority, owner, project, and next step. Choose an optional
color edge in the task editor. Under **Due**, choose **Before a meeting**, select a
cached meeting, and choose when the task must be ready. Sync checks for rescheduling;
unavailable meetings retain their last deadline with a notice. Meeting deadlines
use the Mac's current time zone, including daylight saving changes. Date-only tasks
remain due on the selected local calendar day.

Version 2.17.0 adds the native macOS file picker. Older desktop windows need the new
Mac application download even after their page updates. **Mail & calendar** shows
local source availability and buttons to open Outlook and Teams. Both apps must be
signed in and have downloaded their data. Supported desktop builds target macOS 13+
on Apple silicon. Cache formats and organization permissions can vary;
installation alone does not guarantee readable or complete mail/calendar data.

### Calendar views
Calendar offers Month, Week, and Day views, with Today, previous/next, and date
selection controls. Click a meeting for details and its join link. Week and Day
place overlapping meetings side by side and keep all-day events above the hourly
grid. Times use the Mac's current timezone. Navigation reads the selected date
range from the local cache; it cannot download uncached dates from Microsoft.

### Task ownership and review

Tasks have an owner and optional co-owners (one name or email per line). These are local labels, not shared assignments. **Draft email to owners** opens a draft in the Mac’s default email app when owner email addresses are available; review and send it yourself. Task notes are private to this Mac.

Use **×** to dismiss a suggestion without providing feedback, or **Dismiss with feedback** to give a reason that guides later task checks. This is prompt context, not model training. Restore a dismissed suggestion to withdraw that feedback. Under **Email task options**, exclude sender domains from future task checks while keeping those messages in Mail. Existing tasks and suggestions are kept.

Drag files from Finder into the **Files** drop area on a saved task or project, or use the file picker. Multiple files are supported, up to 2 GB each. Supported types: Word, Excel, PowerPoint, PDF, text/CSV/RTF, PNG, JPEG, MP4, MOV, M4V, WebM, MP3, M4A, and WAV. Unsupported files are reported without preventing other valid files from being saved.

## Connect another AI app with MCP

The general in-app chat has been removed. Task discovery and email drafting remain. Existing chat history is retained in local backups.

Open **Settings → Connect AI apps → Copy connection settings**. Add the `outlook-assistant` entry to your desktop AI client’s local MCP configuration (merge with existing servers rather than replacing them). Keep Outlook Assistant running. Claude Desktop supports local MCP configuration; restart it after adding the server. This uses a bundled Apple silicon executable, so no separate Python, Node, or Bob installation is required for MCP.

The connection exposes tools for searching mail, reading an email, listing tasks and projects, contacts/companies, and cached Teams meetings. It also creates and edits tasks/projects, moves tasks between lanes, and manages progress notes, waiting-on/next-step fields, and checklist steps. Results are paginated, mail exclusions are respected, and no API keys are returned. Changes save directly to the same local workspace and appear in the app. It can also manage review suggestions, company links and pins, board lanes, local drafts, attachments, profile preferences, exclusions, specialist instructions, and scan settings. Only `start_task_scan` calls Bob and consumes its allowance. Mail and calendar remain read-only. It cannot send emails, reveal API keys, or access arbitrary files. Your chosen AI client may send requested content to its provider under that client’s settings.

This is a local stdio connection, not a public link. ChatGPT’s custom MCP setup requires a supported remote endpoint or Secure MCP Tunnel; a localhost URL pasted into chat does not grant access. This app does not publish your mailbox or configure a tunnel.

For source installations, `python3 -m outlook_plugin.mcp_server` runs the same tools over stdio. The bundled bridge forwards stdio to the running app’s local API; `/api/mcp` is an internal bridge endpoint, not a Streamable HTTP transport URL. If using a nondefault app port, set `OUTLOOK_ASSISTANT_PORT` in the MCP client’s server environment.

### MCP write tools

- Tasks: `get_task`, `create_task`, `edit_task`, `list_task_lanes`, `move_task`. Fields include owner/co-owners, priority, dates or meeting deadlines, color, source links, and project assignment.
- Projects: `get_project`, `create_project`, `edit_project`, `delete_project` (empty projects only). Includes colors and ISC/Gainsight/deployment links.
- Progress: `add_task_update`, `add_subtask`, `set_subtask_completed`, `set_task_next_step`.

Write tools are marked as mutations for the AI client. Task/project creation and progress append calls require a stable `request_id` to prevent duplicates on retry. Partial task/project edits require the latest `revision` from `get_task`/`get_project` as `expected_revision`; stale edits return an error instead of overwriting newer data. Reconnect or refresh tools in your AI client after updating.

Tasks in a project display its shared color. Edit the project to change the color for every task in it; existing projects receive an automatic color. Tasks moved out of a project return to their personal color. Completed tasks retain their muted appearance. MCP project creation/editing also accepts a `color`.

## Regression checks

Every push and pull request runs the Python workflow/storage suite, JavaScript UI regressions, syntax checks, and an Apple silicon architecture check in GitHub Actions. Run these locally before a release:

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.cjs
```

Tests use synthetic data. The save tests cover overlapping edits, failed saves, retries, quit protection, interrupted writes, damaged-file recovery, and persistence across processes. A passing suite does not replace the clean-Mac and signed-release checks in the release checklist.

Version 2.19 and later target Apple silicon only. Intel Macs should keep their last compatible release; do not install the Apple silicon package on Intel.

### First-run walkthrough and Bob usage

The first launch opens a six-step walkthrough covering setup, your profile, projects/tasks/subtasks, AI instructions, and usage. Progress saves on this Mac. Use **Settings → Setup → Setup walkthrough** to resume or replay it. Opening the walkthrough does not make AI requests.

The footer opens aggregate Bobcoins and token usage for this app on this Mac: today, this month, and all time. Unreported usage remains marked unknown; these totals are not an account-wide balance. If Bob reports exhausted usage, the app offers **Open Bob** and explains how to request more allowance. After the allowance is restored, use **Settings → Bob connection → Test Bob connection**.

### Opportunity-linked projects and calendar calls

Projects can contain multiple named ISC opportunity, Gainsight renewal, and deployment links. Add these in the project editor; existing projects autosave changes. Links open the source record but do not synchronize its data. Dashboard imports and change alerts require a verified, accessible data source.

Calendar overflow opens a list of all cached meetings for that date. Meeting details include **Join meeting** when a usable call URL is present in the cached meeting or location.

### Bulk task review

In **Tasks to review**, select individual suggestions or **Select all results** (including later pages). **Add selected…** can assign a project, owner, priority, date, or co-owners. Only checked fields override existing values. Successful additions stay saved; if a request fails, retry processes only the remaining selections. Completion suggestions are reviewed individually.

MCP attachments are restricted to saved task/project copies. Reads use paginated base64 chunks; uploads support files up to 48 KiB per call (use the app for larger files). Draft changes affect the app’s local drafts, not Outlook’s mailbox. Preferences and specialist edits require revisions; drafts use numeric revisions. Delete operations are explicit tools. Calendar range queries require timezone-aware ISO timestamps and are limited to 63 days. Reconnect your AI client to discover newly added tools.

### Troubleshooting and support

**Report a problem** refreshes the local mail cache first, then asks Bob for diagnostic advice if a fix cannot be verified. A missing email that becomes readable can be opened again without a Bob call. Bob receives your typed description and basic diagnostic checks, not email bodies, local paths, or stored API keys. This uses your Bob allowance. Bob does not execute repair commands or change app code. If the issue remains, **Still not working? Contact Brett** opens an Outlook draft to brett.scharmett@ibm.com; nothing sends automatically. Feature suggestions open a draft directly.

### Company contact groups

Under **Contacts & companies**, expand a company and choose **Add group**. Name a team or department, select people across its linked domains, or paste addresses. Changes save automatically on this Mac. **Copy emails** copies a deduplicated semicolon-separated list for Outlook. Groups survive restarts and mail refreshes, and are included in local configuration backups. Deleting a group leaves the contacts untouched. MCP clients can use `list_contact_groups` and `save_contact_group` after reconnecting.

Calendar event details show cached invitees, their required/optional status and responses when available. **Create group** preselects invitees with email addresses (excluding rooms/resources) and lets you choose a company and adjust membership. **Copy emails** is also available directly in the event. Missing cached invitees are reported rather than inferred; the local cache cannot guarantee a complete invitation list.

Use **Contacts & companies → Groups** for a searchable list of all saved groups. Add or edit groups and copy recipients directly from this view; large lists have pagination.

The calendar shows its last saved snapshot immediately while Teams is read in the background. Its update timestamp stays visible, and failed refreshes retain the previous events. A private `.outlook_assistant_calendar_cache.json` beside the app’s other data survives restarts; it is replaced atomically after successful reads. Initial use needs one calendar read before a snapshot is available.

In Mail, type directly into the larger, resizable reply editor and choose **Polish draft** to improve your wording without changing its meaning. Tone defaults to Friendly; Professional, Direct, Firm, and Casual are available. **Draft for me** generates a reply from the email and optional instructions. Changes autosave, **Undo change** restores the previous version, and edits made during a Bob request are preserved for review alongside the suggestion. Review all generated wording before sending.

Task discovery considers all active dismissal feedback when selecting examples. Each scan receives full-history reason counts plus up to 100 relevant, deduplicated examples within a 24,000-character budget, prioritizing the same email and related wording before recency. Quick dismissals are excluded; restoring a suggestion withdraws its feedback. This supplies context to Bob, rather than training its underlying model.


### Project meetings and recordings

Choose **Projects → Meetings** to add past calls, notes, Teams meeting links, and recording links. **From calendar** offers cached meetings from the past 60 days through the next two days; use **Add meeting** for older or uncached calls. Dates display in the Mac's current timezone. Existing projects autosave edits.

Paste a recording's HTTPS link to keep it online, or download a recording you can access and attach it in **Files & recordings**. Links open in your browser and retain the source service's access requirements. The app does not automatically fetch recordings from Teams. Uploaded files are copied locally and do not consume Bob usage.

Uploads support up to **2 GB per file**, show progress, and stream large files directly to disk. Recording copies live under `~/Library/Application Support/Outlook Assistant/attachments/project/<project-id>/recordings/`. They survive restarts and updates; removing a copy does not remove your original. Include the attachments folder in your Mac backup: JSON exports contain project meeting metadata and links, but not video/audio files. Larger recordings can be linked instead of copied.


### Project emails

Choose **View emails** on a project card or its task board. The list combines email sources from all saved tasks in that project (including completed tasks) with emails added directly, without duplicates. **Add emails** searches visible cached mail; associations save immediately. Open a message to read/reply, then use **Back to project emails** to return. Both lists paginate, and project search includes available cached body text.

**Unlink** removes only a direct association. An email remains visible if a project task still links to it; Outlook mail is never moved or deleted. Links survive app updates and restarts but do not archive the email body: missing or excluded mail shows as unavailable without exposing its content. MCP clients can use `list_project_emails` and `link_project_email` after reconnecting.

Project colors support any six-digit hex color. In **Edit project**, use the color picker or enter a code such as `#008080`. Changes autosave and apply to the project and its task cards. Existing named colors remain supported, including through MCP.


### Meeting scheduling tasks

Task discovery recognizes requests to schedule, book, arrange, or reschedule meetings. It keeps the named scheduler as owner, including someone the user is waiting on, and distinguishes a scheduling deadline from the requested meeting date. Status updates should not duplicate an already active scheduling task.

A matching email invitation or explicit booking confirmation can produce a **completion suggestion** in Tasks to review. Promises, tentative holds, cancellation, or a proposed date passing do not establish completion. Scheduling does not complete preparation or attendance tasks. Completion still requires your review. The task finder uses the supplied cached emails for this check; it does not independently query Teams or infer that no meeting exists from missing calendar data. Instructions and examples are included in the Task finder defaults; core scheduling rules also apply when you have customized its instructions. This updates guidance, not Bob's underlying model weights.

### Transcript tasks

In **Projects → Meetings**, choose an uploaded recording or paste its recording link. Paste a speaker-labeled transcript, or import a UTF-8 `.txt`, `.vtt`, or `.srt` file (up to 500,000 characters per meeting). Transcripts autosave with the project. Click **Find tasks** to send the transcript and saved context to Bob. Suggestions appear in **Tasks to review**, with the project, source quote, and named owner. Unknown owners stay unassigned. Review owners and deadlines before adding; assignment does not notify anyone. Previously reviewed suggestions are remembered on subsequent scans.

Native recordings are transcribed automatically after Stop & save. For an existing local project recording, choose **Transcribe** in Recordings. Recording links are not downloaded or transcribed; attach a local copy you can access, or import the provider transcript.

### Ask a project

Choose **Projects → Ask project** to search that project’s linked emails, saved meeting transcripts and notes, tasks, subtasks, and progress updates. Press Enter to ask; Shift+Enter adds a line. Answers and source quotes save on this Mac, and **Open source** takes you to the email, task, or meeting. Project question history is also included in downloadable workspace backups.

Search scans all associated text and sends up to 24 relevant 3,000-character excerpts to Bob, along with recent questions and your saved context. Coverage appears beneath each answer; large-project answers are not exhaustive. Excluded and unavailable emails are omitted. Audio/video, attachments, and the contents of linked web pages are not searched—add a transcript for recordings. Quoted sources are checked against the supplied excerpts, but you should still verify conclusions. This search cannot modify or send anything.

**Export a transcript:** In Projects → Meetings, click **Export transcript** beside the transcript. This saves the current text as a UTF-8 `.txt` file, preserving speaker labels, timestamps, and line breaks. The desktop app offers a save dialog; the browser downloads the file.

Project searches start a separate, isolated Bob Shell request and can run alongside automatic task scans or reply drafting. One project search runs at a time. Both requests count toward your existing Bob allowance; provider rate limits still apply. Bob installation waits until all active and queued requests are finished.

### Search across the workspace

Open **Search** in the sidebar. Choose **This month**, **Past 7 days**, **Last month**, **All time**, or **Custom dates**, then ask a question. The app searches cached emails, saved meeting transcripts and notes, cached calendar events, tasks and updates, subtasks, task-review suggestions, projects, contacts/companies, groups, and saved drafts. Results save locally and are included in workspace backup exports.

Dates use the Mac’s current timezone. Email uses received time; meetings use occurrence time; tasks qualify by creation, update, progress-update, or due date. Meeting transcripts need a meeting date to appear in a date-filtered search. Undated project and contact data is included as background context. Other undated records are excluded from date-filtered searches, with a count in coverage.

Each search ranks excerpts across four source families, selecting up to 24 excerpts per family. Up to six isolated Bob Shell requests review groups concurrently, subject to the shared hardware-aware scheduler, followed by a cited synthesis when needed. Background task scanning can continue. This uses your Bob allowance for multiple requests; it is not a spending cap. Sources and exact quotes are validated, and coverage/partial failures appear in results. This is retrieval across saved content, not an exhaustive model review of every record in large date ranges.

Search does not transcribe audio/video, parse attachment contents, read arbitrary local files, or fetch linked web pages. A calendar entry is evidence of a scheduled meeting, not proof that a call happened or that a person attended. No messages are sent and no tasks are changed by search.

### Responsive parallel processing

Every Bob request uses one shared scheduler. It chooses a limit of 2–8 concurrent requests based on CPU count and installed RAM, reserves one or two slots for interactive work, and prioritizes direct questions/replies, then workspace search, then automatic scanning. Background work waits when CPU load is high. Up to six search groups can be ready at once, but the scheduler’s lower machine limit always wins. Excess requests wait rather than launching more shells; the queue itself is bounded. This is a resource limit, not a Bobcoin budget.

Project search, workspace search, drafts, and task discovery can overlap. Each keeps its own safeguards against duplicate operations. AI activity shows running and waiting requests and the machine’s limit. Bob installation and app updates require an idle scheduler and prevent new work from starting during maintenance. Timeouts and failures release capacity. Provider speed and account limits still apply; no concurrency setting can guarantee that a Mac will never run out of resources.

### Recordings library

Open **Recordings** in the sidebar to browse local audio/video attachments, project meeting recording links, and saved transcripts. Filter by project or search names; larger libraries paginate. **Open recording** uses the default Mac player; **Open web recording** opens the saved HTTPS link. **View transcript** opens the project meeting, where you can edit/export its transcript or find tasks.

Choose **Add existing**, select a saved project, and upload or drop files. Choose **Add link or transcript** to create a project meeting instead. Files remain in their existing project/task attachment folders; this library does not duplicate them. Use **Start recording** for a new call; it saves and transcribes automatically.

### Long-email summaries

Emails over 2,200 characters show **Summarize** above the reply composer and message body. Bob produces a collapsible list of main points, requests and deadlines with expandable supporting quotes. Summaries are cached locally (up to 500 entries) and reused for the same source text. Excluded/unavailable emails cannot be summarized. Preview-only messages and bodies beyond the first 100,000 characters show a partial-content notice. Summarization runs on demand through the shared scheduler and does not create tasks or send mail.

### Updates while you work

The app checks for source updates every five minutes, including while Bob is busy. An available update shows a dismissible banner at most once per local calendar day. **Update when ready** waits for running work, open editors, and unsaved drafts; it never cancels a Bob job. Idle automatic updates continue. Keep the app open to apply a queued update. Native app-shell updates still require the latest Mac download.

### Reading and replying

Mail has a sender header, a full-length reading area, and a **Reply** composer above the message. Use **Expand editor** for more space, choose a tone, write a draft, then **Polish draft**. Formatting is available in the toolbar and **More formatting**; drafts save automatically. **Copy reply** transfers the draft to Outlook for review and sending. The current cache bridge supplies plain text, so this is an Outlook-style layout, not an exact copy of the original message's HTML, images, or attachments.

### Slack imports

Open **Slack → Import messages**. Enter a workspace and conversation name, then paste a conversation or select message JSON files from a Slack export you are allowed to access. Select files from one channel/DM at a time (up to 30 files, 1 MB each). Import `users.json` with the same workspace name to resolve people’s names. You can add an optional original Slack message link.

Imports are saved locally, included in downloadable workspace backups, searchable in **Slack** and **Search**, and can become tasks through **Create task**. Reimporting the same workspace/conversation/timestamp updates the existing message. Pasted text is deduplicated by its content; it has no inferred date and appears only in all-time workspace searches. Export timestamps support date-filtered searches. These are saved imports, not live channel/DM monitoring; attachments are not downloaded and export availability depends on your Slack workspace permissions.

### Start a recording manually

On an Apple silicon Mac with **macOS 14 or later**, open **Recordings → Start recording**. Choose **No project** or a saved project, and optionally give the meeting a title. Call audio and your microphone are enabled by default; turn on **Include screen video** if you also want video. macOS’s picker lets you choose a screen or app. Audio-only mode saves no screen frames. Allow the requested screen/audio and microphone permissions, and let participants know you are recording.

Screen video uses the selected source’s Retina pixel dimensions, preserving its proportions, up to 4K (3,840 pixels on the long edge and 8.3 megapixels) at up to 30 fps. Smaller sources are not enlarged. The recorder shows the capture resolution; exports preserve it. Higher-quality video uses more disk space and can reach the 2 GB recording limit sooner. Text already blurry in a remote screen share cannot be restored by recording.

A visible banner and a Mac menu-bar recorder show that capture is active. Use **Stop & save** in either place. The recorder runs separately, so minimizing the main app does not stop it; closing the laptop or sleeping can interrupt capture. App updates wait until capture is finished. Recordings stop automatically after three hours, 2 GB of intermediate media, or low disk space. Start requires 3 GB free because saving temporarily needs room for the final file too.

Finished audio (`.m4a`) or video (`.mp4`) is attached to the selected project and appears under Recordings. Interrupted or failed exports retain their source files under `~/Library/Application Support/Outlook Assistant/recordings/<session>/`; **Show recovery files** opens that folder. Recording itself uses no Bob allowance. Local transcription follows automatically; task extraction uses your Bob allowance. Possible-call reminders can offer to record when a supported calling app or browser uses the microphone. This capture path still needs a real-call permission/audio test on each supported Mac setup.

Developers: `bash scripts/build_recorder.sh` builds/signs the bundled recorder. Its `--self-test <empty-folder>` and `--self-test-video <empty-folder>` modes exercise the real media writer/export with generated tones/frames only; they do not access capture devices.


### Automatic transcripts and project tasks (2.37)

1. Open **Recordings → Start recording**, choose a project, then choose the audio/screen source in macOS.
2. **Stop & save** attaches the file and queues local transcription. The first run downloads a private Python runtime, speech packages, and models (about 1 GB; allow 3 GB free). No Terminal, Python, or extra API key is required on Apple silicon Macs with macOS 14+. Internet is needed for first-use downloads and Bob task extraction.
3. The recording card shows setup, speaker separation, transcription, and task progress. **Transcript & speakers** lets you name voices and export the transcript. Speaker labels are estimates, including recurring voices within the same recording; overlapping or unmatched speech stays explicitly uncertain. Names heard in introductions appear as suggestions for confirmation. There is no voice identity database across calls.
4. Bob extracts evidence-backed tasks into **Tasks to review**, linked to the project and meeting transcript. Review ownership and due dates before accepting. Confirmed speaker names update pending suggestions on the next pass; accepted/dismissed tasks are preserved. Assigning a name does not message that person.

Only one local speech job runs at a time, with two CPU threads per speech model. Long transcripts are sent to Bob in sections through the shared scheduler. Audio stays local; transcript text and saved context go to Bob for task extraction. No recording, transcription, or speaker identification is perfect, especially with overlapping voices, echo, accents, or poor microphones.

Jobs, timestamped speaker segments, and confirmed names are saved under `~/Library/Application Support/Outlook Assistant/transcription/jobs/`. Downloaded speech tools/models live beside that folder. The project transcript is also saved with project data and included in workspace exports; binary recordings and the separate speech-job files are not included in JSON backup exports. App updates preserve these data folders and wait for queued/active processing. After a normal app restart, unfinished work resumes. **Retry** reuses a saved transcript if only the Bob task step failed. Manual edits made in the project transcript are preserved rather than overwritten by processing.

Existing local project recordings have a **Transcribe** button. Web links and recordings attached only to tasks require a local project attachment first. Uploads do not silently start processing. The transcription limit is three hours per file. Closing the app stops processing until it is reopened; minimizing the window does not. Initial setup errors are visible with Retry; corporate download restrictions still apply.

Speech components: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT), [Whisper models](https://github.com/openai/whisper) (MIT), [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Apache-2.0), [speaker segmentation model](https://huggingface.co/pyannote/segmentation-3.0) (MIT), [WeSpeaker](https://github.com/wenet-e2e/wespeaker) (Apache-2.0), and [Python standalone builds](https://github.com/astral-sh/python-build-standalone). Python and speaker-model archives are checksum-pinned, Whisper uses a pinned model revision, and Python package versions are pinned in `speech-requirements.txt`. Models are downloaded on first use rather than stored in this repository.

Validation: real local transcription and speaker separation on a synthetic two-voice conversation, real Bob extraction against that transcript with isolated project/task storage, restart/retry and deduplication unit tests, and desktop/mobile browser checks. Live Teams/Slack capture, hour-long performance, and a clean Mac installation still require field testing.


### “Record this call?” reminders (2.38)

Recording reminders are enabled by default on Apple silicon Macs with **macOS 14.2+**. A small native popup appears when Teams, Slack, Zoom, Chrome, Safari, Edge, Firefox, or Brave reports sustained microphone input. Choose **No project** or a project and **Record…** to open macOS’s recording picker. This starts the same audio-and-microphone capture and automatic transcription workflow as **Start recording**. Nothing records until you click and select a source. The popup works while the main window is minimized, as long as the app/service remains running.

**Not now** dismisses the current microphone session. Short input pauses do not cause another prompt; after 90 seconds without that app’s input, a new session can qualify. The helper waits at least eight seconds before offering a reminder and ignores our recorder’s own audio. It suppresses reminders while a recording is active. Choose **Don’t ask to record calls** in the popup, or use **Recordings → Ask to record calls** to turn reminders off/on.

Detection reads public Core Audio process activity—not audio samples, camera frames, browser URLs, participants, or call transcripts. Camera use alone does not trigger a reminder. Microphone activity is only a possible-call signal: pre-call checks or dictation in a supported app can trigger it; a fully muted call may be missed. Browser activity is labeled by browser, so a Google Meet call in Chrome appears as Google Chrome, not as a confirmed Meet call. Attribution depends on the app exposing an identifiable audio process. Manual **Start recording** remains available on macOS 14.0+ and whenever a call is missed.

The native reminder is a notification-style window, not a Notification Center notification. It does not request notification permission and is not managed by macOS Focus filters; turn reminders off in Recordings if needed. Session dismissal metadata is kept privately in `.outlook_assistant_call_prompts.json`; the setting is in the app config. The helper polls every five seconds and exits when its app service stops or restarts.

Developers: `bash scripts/build_call_reminder.sh` builds the bundled helper. `--probe` reads current supported-app microphone activity without starting capture; `--self-test` checks app attribution. Native popup controls were tested against a synthetic local endpoint that cannot record. Actual calls across each listed app/browser still need field testing.

Recordings can be saved without a project. They appear in Recordings as **No project**, transcribe automatically, and generate task suggestions without a project. After transcription finishes, use the project selector on the recording card to associate it with a project. This preserves the recording and transcript instead of copying the media. Existing suggested or accepted tasks keep their current project; you can organize those separately. Local file uploads also support **No project**; links and pasted meeting transcripts still belong to a project.
