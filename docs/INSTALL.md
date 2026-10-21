# Install Outlook Assistant on your Mac

## 1. Download and open the desktop app

1. Go to **[Latest release](https://github.com/brettscharm/outlook-assistant/releases/latest)**.
2. Under **Assets**, download the ZIP whose name ends in **Desktop-Mac.zip**. GitHub’s source-code downloads are for developers.
3. Double-click the ZIP in Finder.
4. Move **Outlook Assistant.app** into **Applications**. If you do not have permission to use the shared Applications folder, use your own `~/Applications` folder if your organization permits it.
5. Open the app from Applications. You should get a dedicated Mac window; no Terminal or browser window is needed for normal use.

The current packaged download is **Outlook-Assistant-2.16.0-Desktop-Mac.zip**. It installs the desktop shell; newer app code arrives through the automatic updater. Leave the app open with internet access. Updates wait while Bob is busy or the interface has unsaved work. The version is shown near the bottom of the sidebar. Some controls described below appear after that update.

The download supports macOS 13+ and contains Apple silicon and Intel code. Physical Intel hardware, all macOS releases, and clean installations have not all been tested. The app is not yet Developer ID signed or notarized. If macOS or your organization blocks it, follow your organization’s approved software process; do not disable Gatekeeper or remove quarantine to bypass the block.

## 2. Let Outlook download your mail

Open **New Outlook**, sign in to your account, and wait for mail to sync. Then open Outlook Assistant and use **Settings → Setup**.

- One supported profile: detected automatically.
- Several profiles: choose the one you want in **Settings → Mail**.
- No profile or unreadable cache: open and sync Outlook, then check setup again. A different Outlook version or permissions restriction may require support.

Keep Outlook running for new mail. Older cached mail can remain readable when Outlook is closed. This app cannot fetch messages or attachments that Outlook has not downloaded, and Teams calendar coverage depends on what Teams has cached.

## 3. Connect IBM Bob for AI features

You can use accessible cached mail and saved tasks without Bob. To enable the Assistant, generated replies, and task discovery:

1. Open **Settings → Setup → Install / update Bob**. The app installs a private Node 24 runtime if needed, then Bob. You can also follow **[IBM’s official installation guide](https://bob.ibm.com/docs/shell/getting-started/install-and-setup)**.
2. Return to **Settings → Setup → Check setup again**. This app currently supports **Bob Shell 2.x**.
3. Create your own Bob API key through IBM’s Bob portal. Prefer an **Inference** key; a general key also needs your team ID.
4. In **Settings → Bob connection**, give the key a recognizable name, enter it, and choose **Test Bob connection**. Never put your key in a GitHub issue or screenshot.
5. Open **Settings → Profile & writing → My profile** and add your full name and email addresses or aliases. Add your role and account list to improve relevance.

**Settings → Setup → Install or update Bob** downloads Node 24 when needed and runs IBM’s installer in the background into an app-private folder. Click **Install / update Bob** to start. The app checks compatibility before AI requests and checks IBM’s supported release daily while open. Corporate restrictions may still block installation. This installer flow has been tested with mocked processes, not a clean Mac.

After successful setup, a fresh configuration checks for tasks every 15 minutes, starting with the past seven days. This sends cached message excerpts and saved context to IBM Bob and uses your Bob allowance. Review the suggestions in **Tasks to review**. Pause or change the scan range under **Email task options**. Existing users retain their saved settings.

## 4. Keep one copy and let it update

- Always open the same app from Applications. Do not run a second copy from Downloads.
- Application code updates automatically when the app is open and idle; active Bob requests finish first. No manual refresh is normally needed.
- A newer desktop download should **replace** the old app at the same location after quitting it. Bundle changes, such as runtime and Dock icon updates, require a newer desktop download.
- To start the service when you sign in to your Mac, enable **Settings → Startup & storage → Start at login** after putting the app in its permanent location.
- Closing the window may leave the service running. Quit stops a service launched by that app; an independently started service may remain running.

## Saved work survives restarts

Tasks, drafts, chat, identity, company links, and preferences save outside the application. Updating or restarting the laptop does not delete completed saves. An interrupted AI request may need to run again.

Find storage details and **Export a backup** in **Settings → Startup & storage**. Local recovery copies are automatic, but they share your laptop’s disk. Use your normal Mac backup too. Do not delete `.outlook_assistant_*.json` files when updating or moving the app.

## Quick troubleshooting

| What you see | What to do |
|---|---|
| macOS or company policy blocks opening | Request an approved distribution from your administrator. The current release is not notarized. |
| No Outlook profile | Open New Outlook, sign in, let mail download, and check Setup again. |
| Several Outlook profiles | Choose the intended profile in Settings → Mail. |
| Bob missing, unsupported, or unable to start | Use IBM’s installation guide; check for Bob 2.x and Node 24+, then recheck Setup. |
| Key rejected, expired, or revoked | Replace it in Settings → Bob connection and test the connection. |
| New emails are missing | Let Outlook sync first, then click Sync now in this app. |
| Update is waiting | Let active Bob work finish, save/close editors and Settings, and leave the app idle. |
| Tasks are not being suggested | Check your identity, Bob connection, scan date range, and whether discovery is paused. |
| Calendar is empty | Open Teams Calendar to refresh cached events. Meeting-email discovery also searches Deleted Items. Missing cached events do not establish availability. |

For help, use Settings → Feedback or [open a repository issue](https://github.com/brettscharm/outlook-assistant/issues). Describe your app, macOS, and Outlook versions. Do not attach private emails, account details, or API keys.

[Back to the README](../README.md)

When Node is missing, **Install / update Bob** now downloads a private Node 24 runtime from nodejs.org and checks its published checksum. No sudo is used. Company installation restrictions still apply.
