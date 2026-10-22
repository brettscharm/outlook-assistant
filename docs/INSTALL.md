# Get Outlook Assistant

For **Apple silicon Macs (M1 or newer)** with macOS 13 or later. No Windows version.

## 1. Download

**[Download Outlook Assistant for Mac](https://github.com/brettscharm/outlook-assistant/releases/download/v2.19.0/Outlook-Assistant-2.19.0-Apple-Silicon-Mac.zip)**

## 2. Install

Double-click the downloaded ZIP. Drag **Outlook Assistant.app** into **Applications**.

## 3. Open

Open **Outlook** and let it sync. Then open **Outlook Assistant** from Applications.

## 4. Finish setup

In **Settings → Setup**, follow the setup walkthrough. For automatic task suggestions:

- Click **Install / update Bob** if Bob is missing.
- Create and add your Bob API key using the steps below.
- Add your name and email in **Settings → Profile & writing → My profile**.

### Get your Bob API key

1. Open **[bob.ibm.com](https://bob.ibm.com)** and sign in with your work account.
2. Open your **subscription instance**, then **API key management**.
3. Create a new key and choose **Inference**. If asked, choose the team you use for work.
4. **Copy the key before closing the dialog.** Bob only shows the full key once.
5. Back in Outlook Assistant, open **Settings → Bob connection**. Set **Key name** to something like `Work Bob`, then paste the key into **Bob API key**.
6. Click **Test Bob connection**. Wait for **Connected to IBM Bob. Test request succeeded.**

No Terminal commands are needed. Keep your key private; each person should use their own. If your subscription or key-management page is unavailable, ask your Bob administrator for access.

Already have a **General** key? Enter its team ID under **Bob team ID** in the same settings panel, or create an Inference key instead. [IBM’s API key guide, with screenshots](https://bob.ibm.com/docs/shell/account/api-keys).

That’s it. Keep the app open; updates install automatically when it’s idle. Your work saves on your Mac.

**Sharing it?** Choose **Settings → Setup → Share app** to copy this page’s link. Your emails, tasks, settings, and API key are not included.

**Mac won’t open it?** This is a development build and is not Apple-notarized. If macOS or your company blocks it, contact your IT support. A fully signed installer is not available yet.

<details>
<summary>More help and technical details</summary>

Download: **2.19.0 prerelease**. Application updates: **2.26.0**. Verified October 22, 2026. The direct download above avoids GitHub’s older “Latest” release and its source-code ZIPs. Installation on a clean Mac is not yet fully verified.

### Outlook

Open **New Outlook**, sign in to your account, and wait for mail to sync. Then open Outlook Assistant and use **Settings → Setup**.

- One supported profile: detected automatically.
- Several profiles: choose the one you want in **Settings → Mail**.
- No profile or unreadable cache: open and sync Outlook, then check setup again. A different Outlook version or permissions restriction may require support.

Keep Outlook running for new mail. Older cached mail can remain readable when Outlook is closed. This app cannot fetch messages or attachments that Outlook has not downloaded, and Teams calendar coverage depends on what Teams has cached.

### Bob setup details

You can use accessible cached mail and saved tasks without Bob. To enable generated replies and automatic task discovery:

1. Open **Settings → Setup → Install / update Bob**. The app installs a private Node 24 runtime if needed, then Bob. You can also follow **[IBM’s official installation guide](https://bob.ibm.com/docs/shell/getting-started/install-and-setup)**.
2. Return to **Settings → Setup → Check setup again**. This app currently supports **Bob Shell 2.x**.
3. Follow **[Get your Bob API key](#get-your-bob-api-key)** above. Choose an **Inference** key; a General key also needs your team ID.
4. In **Settings → Bob connection**, give the key a recognizable name, enter it, and choose **Test Bob connection**. Never put your key in a GitHub issue or screenshot.
5. Open **Settings → Profile & writing → My profile** and add your full name and email addresses or aliases. Add your role and account list to improve relevance.

**Settings → Setup → Install or update Bob** downloads Node 24 when needed and runs IBM’s installer in the background into an app-private folder. Click **Install / update Bob** to start. The app checks compatibility before AI requests and checks IBM’s supported release daily while open. Corporate restrictions may still block installation. This installer flow has been tested with mocked processes, not a clean Mac.

After successful setup, a fresh configuration checks for tasks every 15 minutes, starting with the past seven days. This sends cached message excerpts and saved context to IBM Bob and uses your Bob allowance. Review the suggestions in **Tasks to review**. Pause or change the scan range under **Email task options**. Existing users retain their saved settings.

### Updates

- Always open the same app from Applications. Do not run a second copy from Downloads.
- Application code updates automatically when the app is open and idle; active Bob requests finish first. No manual refresh is normally needed.
- A newer desktop download should **replace** the old app at the same location after quitting it. Bundle changes, such as runtime and Dock icon updates, require a newer desktop download.
- To start the service when you sign in to your Mac, enable **Settings → Startup & storage → Start at login** after putting the app in its permanent location.
- Closing the window may leave the service running. Quit stops a service launched by that app; an independently started service may remain running.

### Your saved work

Tasks, projects, subtasks, notes, drafts, identity, company links, and preferences save outside the application. Updating or restarting the laptop does not delete completed saves. An interrupted AI request may need to run again.

Find storage details and **Export a backup** in **Settings → Startup & storage**. Local recovery copies are automatic, but they share your laptop’s disk. Use your normal Mac backup too. Do not delete `.outlook_assistant_*.json` files when updating or moving the app.

### Troubleshooting

| What you see | What to do |
|---|---|
| macOS or company policy blocks opening | Request an approved distribution from your administrator. The current release is not notarized. |
| No Outlook profile | Open New Outlook, sign in, let mail download, and check Setup again. |
| Several Outlook profiles | Choose the intended profile in Settings → Mail. |
| Bob missing, unsupported, or unable to start | Use IBM’s installation guide; check for Bob 2.x and Node 24+, then recheck Setup. |
| Key rejected, expired, or revoked | Replace it in Settings → Bob connection and test the connection. |
| A task’s source email is unavailable | Open Outlook and sync. If the email remains cached with the same stable identity, its link can recover after an ID change. Otherwise use Search conversation in the task preview. Deleted or uncached content cannot be restored; the task remains saved. |
| New emails are missing | Let Outlook sync first, then click Sync now in this app. |
| Update is waiting | Let active Bob work finish, save/close editors and Settings, and leave the app idle. |
| Tasks are not being suggested | Check your identity, Bob connection, scan date range, and whether discovery is paused. |
| Calendar is empty | Open Teams Calendar to refresh cached events. Meeting-email discovery also searches Deleted Items. Missing cached events do not establish availability. |

For help, use Settings → Feedback or [open a repository issue](https://github.com/brettscharm/outlook-assistant/issues). Describe your app, macOS, and Outlook versions. Do not attach private emails, account details, or API keys.



### Connect another AI app

Click **MCP connection** in the left sidebar, then **Copy connection settings**. This is also available under **Settings → Connect AI apps**. Merge the server entry into the local MCP configuration of a compatible desktop client, then restart that client. Keep Outlook Assistant running. The bundled bridge requires macOS 13+ and supports Apple silicon; it needs no Bob or separate language runtime. It can read mail/calendar and create or edit local tasks/projects, including checklist steps and progress notes. ChatGPT cloud connections require a supported remote endpoint or Secure MCP Tunnel and are not automatically configured by this app.

</details>

[Back to the README](../README.md)
