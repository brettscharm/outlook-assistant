# Outlook Assistant for Mac

Read the mail **already cached by New Outlook on your Mac**, search it, keep tasks and personal work context, and generate drafts and briefings through **IBM Bob Shell** using your own Bob API key.

## Open the Mac app

Download the Mac app from [Releases](https://github.com/brettscharm/outlook-assistant/releases), unzip it, and open **Outlook Assistant.app**. Python and the local mail reader are included. The app opens your browser at `http://localhost:8484`.

The initial packaged release is built and tested on Apple silicon. Both Apple silicon and Intel cache readers are included; the source launcher works with Python 3.9+ on either architecture. An Intel app bundle must be built on an Intel Mac or with a compatible universal Python distribution. This is not a signed/notarized enterprise deployment: managed Macs may require IT approval. Do not disable macOS security controls to run it.

For source users, double-click **Launch Outlook Assistant.command**, or run `./run.sh`. No administrator access, launch agent, shell-profile edit, or background installer is required.

## Connect Bob

Install [IBM Bob Shell 2.x](https://bob.ibm.com/docs/shell/getting-started/install-and-setup) through IBM's official distribution. In Settings, enter your Bob API key, and a team ID if you use a general key. Click **Test Bob connection**.

The app invokes `bob run --format json`, passes prompts on stdin and the key through `BOB_API_KEY`, and reads `last_message` plus session usage. Requests use your Bob subscription; the app does not use an invented Bob HTTP API or substitute canned replies. Each request has a 120-second timeout, three-turn limit, and one-Bobcoin cost limit. Only one Bob request runs at a time. File, command, MCP, skill, subagent, and mode tools are disabled for these sessions.

Bob runs **only when you request a test, draft, or briefing**. Mail refresh does not consume Bob usage. Email text is untrusted context, not an instruction to execute commands. Generated drafts stay in the browser until you copy them; the app cannot send mail.

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

Tasks is the default screen. **Find tasks in my emails** sends up to 30 recent messages matching the Mail folder, search, and unread filter to IBM Bob, using up to 6,000 cached characters per message plus your saved context. Suggestions include a verified supporting quote and a link to the source email. Edit the title or owner, then Add task or Dismiss. Saved tasks retain the email link; duplicate titles from the same source are not added twice. This is a limited AI review, not a complete mailbox audit.

## Contacts and companies

Contacts groups unique senders from the local cache by exact email domain. It is not a full Outlook address-book sync. Expand a domain, choose a company suggested from your saved account list (first spreadsheet column), or type a new name, then Save company. Multiple domains can use the same company name; subdomains remain separate groups. Company links are private local settings, can be unlinked, and are included as context only when you request a Bob action. Shared domains such as gmail.com are not reliable company identifiers. Search contacts by person, address, domain, or linked company; Search mail opens a mailbox search for that address.
