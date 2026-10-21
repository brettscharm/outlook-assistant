# Outlook Assistant for Mac

A desktop workspace for mail cached by Outlook, tasks, contacts, projects, and optional IBM Bob task discovery and email drafting. Opens in its own Mac window—no browser or Terminal needed for everyday use.

## Install on a Mac

1. **[Open the latest release](https://github.com/brettscharm/outlook-assistant/releases/latest)** and download the **Desktop-Mac.zip** file under **Assets**. Do not choose GitHub’s “Source code” ZIP.
2. Unzip it and move **Outlook Assistant.app** into **Applications**. Keep one installed copy.
3. Open **Microsoft Outlook**, sign in, and let your mail finish downloading.
4. Open **Outlook Assistant**. Use **Settings → Setup** to see any missing requirements.
5. For AI features, install **[IBM Bob Shell](https://bob.ibm.com/docs/shell/getting-started/install-and-setup)**, then add your Bob API key in **Settings → Bob connection** and test the connection. Add your name and email in **Settings → Profile & writing → My profile**.

**[Step-by-step installation and troubleshooting →](docs/INSTALL.md)**

The Mac app includes Python and the mail reader. You do not need Git, Xcode, Python, or Homebrew to open it. AI features additionally require **Bob Shell 2.x and Node.js 24+**; Settings → Setup → Install or update Bob installs a private Node 24 runtime if needed, then runs IBM’s installer. Installation starts with an explicit click.

**Requirements:** macOS 13 or later, Apple silicon or Intel, and New Outlook with a supported local cache. Compatibility with every Mac, Outlook version, and company-managed device is not guaranteed. The current downloadable app is ad-hoc signed, **not Developer ID signed or notarized**. macOS or company policy may block it; do not disable security controls.

**Download versus app version:** the latest packaged desktop release is currently **2.17.0**. Newer application features are delivered by the in-app updater. See the [feature status](docs/FEATURE_STATUS.md) for implemented features and remaining integrations. Keep the app open and connected to the internet; installation waits for a safe idle period and for active Bob work to finish. The displayed version changes after the update restarts the service. A package update does not replace the bundled runtime or Finder/Dock icon; those require a newer desktop download.

## Everyday use

- **Tasks:** create and edit tasks, customize lanes, and drag cards between them. Optional priorities and due dates support sorting. Upcoming deadlines stand out; completed cards turn gray and can be hidden without deleting them.
- **Tasks to review:** review suggested actions before adding them. Accepting one keeps you on the review page. Unclear suggestions default to you; choosing My task uses your saved name. You can assign a different owner or dismiss a suggestion with a reason and undo it. New-mail checks can also suggest completing existing tasks with a supporting quote; acceptance is required.
- **Mail:** browse cached mail and folders, search, preview source emails, and draft replies. Outlook must download new mail before this app can read it.
- **Drafts:** drafts save locally. Copy a draft into Outlook, review it, and send it there. The app does not send mail or insert Reply All drafts into Outlook.
- **Contacts:** browse cached senders by domain and link multiple domains to one company. This is not an Outlook address-book sync.
- **Projects:** group related tasks, filter the board, and see completion counts.
- **Settings → AI assistants:** edit instructions and examples, restore defaults, and test sample content. **AI activity** shows real request status.
- **Settings → Profile & writing:** your identity, role, writing style, and usage details. Calendar reads cached Teams meetings.

Your name, role, account list, and writing preferences help personalize Bob’s results. Writing style uses examples and instructions; it does not train a new model. Usage reports this app’s recorded Bobcoins and available token counts, not an account-wide balance or dollar bill.

## Automatic task discovery and sync

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

Build the universal reader with `scripts/build_readers.sh` and the Mac app with `scripts/build_mac.sh` using universal Python and PyInstaller. Signing and notarization require your own Apple Developer credentials; see [release instructions](docs/MAC_RELEASE_CHECKLIST.md).

For isolated tests, set `OUTLOOK_ASSISTANT_DATA_DIR` and `OUTLOOK_ASSISTANT_PROFILE_ROOT`. Never use real mail or credentials as fixtures. Legacy Outlook tests require explicit `OUTLOOK_LEGACY_E2E=1`.

See `vendor/hxmail/UPSTREAM.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md` for provenance and licenses.

## Tasks and calendar in 2.16

Open a project to work on its board. New tasks inherit that project. Choose **Open task** for details, subtasks, updates, waiting-on and next steps in one panel. Project progress counts completed tasks; subtasks track the steps inside each task. Use **Export task** / **Import task** for an explicit coworker handoff. Files contain task descriptions and source links; review them before sharing.

**Calendar** shows upcoming cached Teams instances. Open Teams Calendar to refresh coverage. **Meeting emails** also checks Deleted Items for invitations and responses; these are evidence, not a confirmed calendar. Missing events never establish availability.

**Settings → Startup & storage → Archive downloaded mail** saves EML files and available attachments, with size limits and missing-content counts. It cannot recover cloud-only content.

The desktop app menu offers **Float Assistant Above Other Apps** (Cmd+J). This requires the new desktop bundle. Reply drafting now runs a bounded writer/reviewer/editor workflow and uses three Bob requests per draft.

### Files on tasks and projects
Open a saved task or edit a saved project, then choose **Attach files**. Word, Excel,
PowerPoint, PDF, text, and image files are supported, up to 25 MB each. **Open** uses
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
on Apple Silicon and Intel. Cache formats and organization permissions can vary;
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

Drag files from Finder into the **Files** drop area on a saved task or project, or use the file picker. Multiple files are supported, up to 25 MB each. Supported types: Word, Excel, PowerPoint, PDF, text/CSV/RTF, PNG and JPEG. Unsupported files are reported without preventing other valid files from being saved.

## Connect another AI app with MCP

The general in-app chat has been removed. Task discovery and email drafting remain. Existing chat history is retained in local backups.

Open **Settings → Connect AI apps → Copy connection settings**. Add the `outlook-assistant` entry to your desktop AI client’s local MCP configuration (merge with existing servers rather than replacing them). Keep Outlook Assistant running. Claude Desktop supports local MCP configuration; restart it after adding the server. This uses a bundled universal Mac executable, so no separate Python, Node, or Bob installation is required for MCP.

The connection exposes read-only tools for searching mail, reading an email, listing tasks and projects, contacts/companies, and cached Teams meetings. Results are paginated, mail exclusions are respected, and no API keys are returned. It does not send emails, change tasks, run Bob, or expose attachment contents. Your chosen AI client may send requested content to its provider under that client’s settings.

This is a local stdio connection, not a public link. ChatGPT’s custom MCP setup requires a supported remote endpoint or Secure MCP Tunnel; a localhost URL pasted into chat does not grant access. This app does not publish your mailbox or configure a tunnel.

For source installations, `python3 -m outlook_plugin.mcp_server` runs the same read-only tools over stdio. The bundled bridge forwards stdio to the running app’s local API; `/api/mcp` is an internal bridge endpoint, not a Streamable HTTP transport URL. If using a nondefault app port, set `OUTLOOK_ASSISTANT_PORT` in the MCP client’s server environment.
