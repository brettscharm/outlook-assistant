# Outlook Assistant for Mac

A desktop workspace for mail cached by Outlook, tasks, contacts, and an IBM Bob-powered assistant. Opens in its own Mac window—no browser or Terminal needed for everyday use.

## Install on a Mac

1. **[Open the latest release](https://github.com/brettscharm/outlook-assistant/releases/latest)** and download the **Desktop-Mac.zip** file under **Assets**. Do not choose GitHub’s “Source code” ZIP.
2. Unzip it and move **Outlook Assistant.app** into **Applications**. Keep one installed copy.
3. Open **Microsoft Outlook**, sign in, and let your mail finish downloading.
4. Open **Outlook Assistant**. Use **Settings → Setup** to see any missing requirements.
5. For AI features, install **[IBM Bob Shell](https://bob.ibm.com/docs/shell/getting-started/install-and-setup)**, then add your Bob API key in **Settings → Bob connection** and test the connection. Add your name and email in **More → My context**.

**[Step-by-step installation and troubleshooting →](docs/INSTALL.md)**

The Mac app includes Python and the mail reader. You do not need Git, Xcode, Python, or Homebrew to open it. AI features additionally require **Bob Shell 2.x and Node.js 24+**; these are not automatically installed or updated by this app. Use IBM’s official setup instructions.

**Requirements:** macOS 13 or later, Apple silicon or Intel, and New Outlook with a supported local cache. Compatibility with every Mac, Outlook version, and company-managed device is not guaranteed. The current downloadable app is ad-hoc signed, **not Developer ID signed or notarized**. macOS or company policy may block it; do not disable security controls.

**Download versus app version:** the latest packaged desktop release is currently **2.10.0**. Newer application features are delivered by the in-app updater. Keep the app open and connected to the internet; installation waits for a safe idle period and for active Bob work to finish. The displayed version changes after the update restarts the service. A package update does not replace the bundled runtime or Finder/Dock icon; those require a newer desktop download.

## Everyday use

- **Tasks:** create and edit tasks, customize lanes, and drag cards between them. Optional priorities and due dates support sorting. Upcoming deadlines stand out; completed cards turn gray and can be hidden without deleting them.
- **Tasks to review:** review suggested actions before adding them. Accepting one keeps you on the review page. Unclear suggestions default to you; choosing My task uses your saved name. You can assign a different owner or dismiss a suggestion with a reason.
- **Mail:** browse cached mail and folders, search, preview source emails, and draft replies. Outlook must download new mail before this app can read it.
- **Drafts:** drafts save locally. Copy a draft into Outlook, review it, and send it there. The app does not send mail or insert Reply All drafts into Outlook.
- **Contacts:** browse cached senders by domain and link multiple domains to one company. This is not an Outlook address-book sync.
- **Assistant:** open it from the bottom left, or expand it. Ask about mail, tasks, and contacts. Supported changes appear as proposals for you to review and apply.
- **More:** My context, Writing style, Usage, Briefing, and Calendar. Calendar is not connected; Briefing summarizes a limited email snapshot, not your complete day.

Your name, role, account list, and writing preferences help personalize Bob’s results. Writing style uses examples and instructions; it does not train a new model. Usage reports this app’s recorded Bobcoins and available token counts, not an account-wide balance or dollar bill.

## Automatic task discovery and sync

After identity and Bob connection setup, a fresh configuration defaults to checking every **15 minutes**, initially looking back **seven days**. Existing saved scan settings are preserved. Change the date range or pause discovery in **Tasks to review → Task discovery settings**.

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

Outlook’s private cache format can change. This is an experimental reader, not a Microsoft-supported mailbox export. A missing body displays as Preview only. Cloud-only mail, full attachment archiving, Slack ingestion, shared task assignment, and calendar sync are not implemented.

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
