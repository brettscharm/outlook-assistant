# Outlook Assistant for Mac

Read the mail **already cached by New Outlook on your Mac**, search it, keep tasks and personal work context, and generate drafts and briefings through **IBM Bob Shell** using your own Bob API key.

## Open the Mac app

Download the Mac app from [Releases](https://github.com/brettscharm/outlook-assistant/releases), unzip it, move **Outlook Assistant.app** into Applications, and open it. Python and the local mail reader are included. Version 2.7 opens its own native Mac window with a Dock icon and menus. Its bundled local service starts automatically without a Terminal window. The browser interface remains available for migration and troubleshooting, but is no longer the main entry point.

The release provides one **Universal Mac** download for Apple silicon and Intel, requiring **macOS 13 or later**. Python and architecture-specific cache readers are bundled; recipients do not need Python, Git, Xcode, or Homebrew to launch the app. IBM Bob Shell 2.x and its Node.js 24+ runtime remain separate prerequisites for AI features. The native Apple silicon and translated Intel app paths were smoke-tested with isolated empty settings. Physical Intel hardware, other macOS versions, and other Outlook cache layouts have not been verified. This is ad-hoc signed, not Developer ID signed or notarized: macOS or company policy may block it. Do not disable security controls to run it.

For source users, double-click **Launch Outlook Assistant.command**, or run `./run.sh`. No administrator access, launch agent, shell-profile edit, or background installer is required.

## Connect Bob

Install [IBM Bob Shell 2.x](https://bob.ibm.com/docs/shell/getting-started/install-and-setup) through IBM's official distribution. In Settings, enter your Bob API key, and a team ID if you use a general key. Click **Test Bob connection**.

The app invokes `bob run --format json`, passes prompts on stdin and the key through `BOB_API_KEY`, and reads `last_message` plus session usage. Requests use your Bob subscription; the app does not use an invented Bob HTTP API or substitute canned replies. Each request has a 120-second timeout, three-turn limit, and one-Bobcoin cost limit. Only one Bob request runs at a time. File, command, MCP, skill, subagent, and mode tools are disabled for these sessions.

Bob runs when you request an AI action or enable scheduled task scans. Mail refresh does not consume Bob usage. Email text is untrusted context, not an instruction to execute commands. Generated drafts autosave locally until you copy them; the app cannot send mail.

## Local Outlook data

New Outlook's active store is normally:

```
~/Library/Group Containers/UBF8T346G9.Office/Outlook/Outlook 15 Profiles/<profile>/HxStore.hxd
```

Large cached bodies can be stored under that profile's `Files/` directory. The older `Data/Outlook.sqlite` can contain stale legacy mail even while New Outlook is running. Finding Outlook installed is not proof of current mailbox access.

The app automatically finds profiles and uses a pinned, locally built **hxmail** reader. It reads a consistent temporary copy, then removes the copy. The original store is never modified. No Microsoft app registration, Graph token, or cloud mailbox login is used for this path. macOS may ask for permission to access Outlook's data. Several profiles require selection in Settings.

This is an **experimental cache reader**, not a Microsoft-supported export API. Supported layouts include Outlook 16.112's header `0x428`, body `0x740`, and folder `0x4c2`, plus upstream 16.114/16.115 layouts. Unknown layouts fail visibly. Deleted/stale records or incomplete folders can exist in caches; the view is not an authoritative server export. Multiple account roots are included; folder identity is preserved, but account labels are not inferred.

A cached body is shown when available; otherwise the app explicitly shows **Preview only**. It cannot download content Outlook has not cached. Keep Outlook running and synced for new mail; the page checks the cache every minute, and **Sync now** re-reads it. This button does not force Outlook to fetch cloud content.

**Calendar support is not implemented for the new cache format.** Meeting invitations are searchable as mail, but do not establish availability. Bob must not invent free time. Legacy AppleScript and explicit Graph bridges remain in source for compatibility, but are not substitutes for a successful current-cache read.

## My context

Use **My context** for your role, accounts/customers, key people, priorities, and writing preferences. Context and the Bob key are saved in `~/.outlook_assistant_config.json` with owner-only permissions; tasks use `~/.outlook_assistant_tasks.json`. These files are not part of the application or GitHub repository. The API never returns the saved Bob key.

Your selected email and saved context go to IBM Bob when generating a draft. Briefings currently use up to 40 unread Inbox previews. IBM Bob's own retention and logging policies still apply. This is not fully offline AI. Mail itself is kept in memory by the app; no app-managed mailbox database or remote telemetry is created.

## Updates

While the page is open, updates are checked automatically after 45 seconds and then every five minutes. Installation waits until the page has been idle for 30 seconds, Bob is not working, Settings is closed, and no task suggestions are awaiting review. The update restarts the local server. The open page detects the new server instance and refreshes automatically. Draft text is retained across that refresh. Source checkouts with local changes are not overwritten. ZIP/app installs stage the new package and validate archive paths before replacing it. Updates use HTTPS and the repository's exact commit; they are not independently cryptographically signed.

The bundled Python runtime stays inside the app; updateable application code lives in `~/Library/Application Support/Outlook Assistant/app`. Runtime changes may require downloading a new app release. Your settings and tasks survive code updates.

## Development and validation

```
python3 -m unittest discover -s tests -v
cd vendor/hxmail && go test ./...
```

Build the reader with Go 1.27+ for `GOOS=darwin`, `GOARCH=arm64` and `amd64` into `outlook_plugin/bin/hxmail-darwin-<arch>`. Build the app with Python and PyInstaller using `scripts/build_mac.sh`. Legacy Outlook integration tests require `OUTLOOK_LEGACY_E2E=1` and a populated Legacy Outlook account.

See `vendor/hxmail/UPSTREAM.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md` for provenance and licenses. No real emails or credentials are included in test fixtures.

## Tasks from mail

Tasks opens first. Set your full name, email addresses/aliases, role, and account context in My context. Bob distinguishes explicit requests to you, commitments you made, other named owners, and unclear ownership. Email previews show a task summary above the message after scanning.

Choose a starting date (this month by default) and My tasks / All tasks. Scans review all matching cached messages in batches of ten, with up to 6,000 characters per message. Completed batches are remembered using message content, scan mode, and your context; restarting resumes unprocessed or changed messages. A configurable per-scan Bob reported-usage cap pauses work, and Stop finishes the current batch. Missing cloud mail is not fetched. AI extraction remains limited to the cached text supplied.

Automatic checks are opt-in at 15, 30, or 60 minutes. They run while the local server is running even if the browser is closed, use the saved Bob key and allowance, and review only unprocessed/changed messages within the chosen range. The timer restarts when the app restarts. Updates defer during an active scan.

Review suggestions before adding them. Each has an owner, source quote, company when linked, and a due date only when supported by a literal deadline quote. Bob interprets relative dates using the source message's received timestamp; ambiguous dates remain undated or flagged for review. Edit owners and dates before or after saving. My tasks, others/unclear, completed, and due-date filters keep the lists separate.

Dismissal reasons (not mine, not relevant to role, already done, duplicate, not an action) persist, can be restored, and provide limited feedback for future extraction. Stable source/evidence IDs suppress repeated suggestions; this is not a guarantee of semantic deduplication across different emails.

Private local data: `~/.outlook_assistant_config.json` stores identity, context, key, company links, and scan settings; `~/.outlook_assistant_tasks.json` stores accepted tasks; `~/.outlook_assistant_task_review.json` stores suggestions, supporting quotes, dismissals, and scan checkpoints. Files use owner-only permissions, not encryption. Keys are never included in browser configuration responses or releases.

## Contacts and companies

Contacts groups unique senders from the local cache by exact email domain. It is not a full Outlook address-book sync. Expand a domain, choose a company suggested from your saved account list (first spreadsheet column), or type a new name, then Save company. Multiple domains can use the same company name; subdomains remain separate groups. Company links are private local settings, can be unlinked, and are included as context only when you request a Bob action. Shared domains such as gmail.com are not reliable company identifiers. Search contacts by person, address, domain, or linked company; Search mail opens a mailbox search for that address.

### Ask your email

The **Ask your email** tab searches downloaded mail locally, then asks IBM Bob to answer with supporting email links. Follow-up questions include recent conversation context. Retrieval ranks word matches in subjects, senders, and cached bodies; it is not a complete semantic mailbox search. Each answer receives at most 12 matching message excerpts of 6,000 characters each, with a Bob reported usage cap of 1. Missing cache data is not evidence that a message or commitment does not exist.

Chat history is saved in `~/.outlook_assistant_chat.json` with owner-only permissions, survives app/laptop restarts, and can be cleared independently of tasks and mail. Draft questions are retained in browser local storage. Nothing is sent or edited in Outlook.

### Everyday workspace features

- **Writing style:** paste examples you wrote, ask Bob to produce a guide, and refine it. Samples and guide changes autosave. The guide is included in future reply requests. This is prompt personalization, not fine-tuning. Raw samples stay in your private local settings and are sent to Bob only when you request learning.
- **Drafts:** typed and generated replies autosave to a private data file, with a browser recovery copy for pending edits. Continue, copy, discard, or undo the latest discard. They are shared by app windows on this Mac, not synced to Outlook.
- **Settings → Start at login:** creates a per-user macOS LaunchAgent for the current app location, effective at the next login. Leave the app at that location. It starts the local server without opening a browser; scheduled task checks remain separately configurable. Turning this off removes the login configuration, without interrupting the current app. Actual login behavior depends on macOS permissions and device policy.
- **Settings → Download a backup:** exports tasks, review state, chat, selected preferences, saved drafts, and pending browser drafts as JSON. Bob API keys, team settings, Outlook profile paths, and the mailbox are excluded. Keep this file private. There is no in-app restore workflow yet.
- **Data integrity:** unreadable task files are preserved rather than reset. Updates defer while Bob requests are active.

### Fresh Mac requirements and setup

1. macOS 13+ on Apple silicon or Intel; download the Universal Mac ZIP. Move the app to Applications before enabling Start at login.
2. New Outlook must be signed in and have a supported local HxStore cache. Open Outlook and allow mail to download. Cache formats differ across Outlook versions; support is not guaranteed just because Outlook is installed.
3. Install IBM Bob Shell 2.x through IBM’s official distribution, then provide your own Bob key in Settings. Use Test Bob connection to verify the subscription.
4. Use **Finish setup** / Settings for the first-run checklist. Add your name and work email in My context before task extraction.

The desktop app does not automatically fall back to AppleScript if the cache is missing. It reports what setup is needed without prompting to automate Outlook. These checks identify prerequisites; they cannot override company policy or prove a cache format is supported until it is read.

Builds default to `--target-arch universal2` and require universal Python and compatible libraries. The build declares macOS 13 as its minimum, stamps the app version, and verifies its signature. `SIGNING_IDENTITY` can select an available developer identity; notarization still requires a separate Apple-authorized release step.

For isolated testing, `OUTLOOK_ASSISTANT_DATA_DIR` puts settings and runtime code in a separate directory, and `OUTLOOK_ASSISTANT_PROFILE_ROOT` selects a separate cache search location. Defaults preserve existing users’ files and profile discovery.

### Desktop app and durable storage (2.7)

- Open **Outlook Assistant.app** normally. Closing its window leaves the app/background checks running; reopen it from the Dock. Quit stops the service when that window launched it. An existing independently launched service is left intact. No Terminal or browser tab is required.
- Existing tasks, chat, identity, account list, company links, style, and scan progress remain in the same private user files, outside the app bundle and update directory. Updates do not replace those files.
- Reply drafts now autosave to `~/.outlook_assistant_drafts.json`. Existing browser drafts migrate when that browser page first loads 2.7. The native app reads the same disk file. Wait for **Saved on this Mac** before clearing old browser data. Offline edits retain a browser recovery copy and retry. Conflicting edits are preserved for review rather than silently overwritten.
- Context, writing samples/style, company links, valid scan settings, and edits to saved tasks autosave. Credential fields save on change/blur. Creating/accepting a new task and invoking AI remain explicit actions.
- JSON saves flush file contents, replace the primary atomically, and flush the directory. Private recovery copies live in `~/.outlook_assistant_backups`: three previous saves and up to seven daily versions per file. Existing files receive an initial copy on startup. If a file is missing or invalid JSON, the reader restores an available valid copy and preserves a damaged original. Settings shows recovery notices. A recovered copy can be older than the last edit.
- Local recovery copies may contain the saved API key and private work content; directory permissions are owner-only and files are owner-readable/writable. Downloaded exports still exclude the configured API key. These copies share the laptop’s disk, so they do not protect against disk failure or loss of the laptop; use an external Mac backup for that.
- A stopped process or restart does not remove completed saves. An interrupted AI request or unfinished scan batch may need another run. No actual OS reboot was performed in QA; a forced native-app/service termination and reopen was tested.
