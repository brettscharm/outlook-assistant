# Mac distribution release gate

Current status: development release. No Developer ID identity is available on the development Mac. Notarization and fresh-machine acceptance are not complete. Do not label the download as working on every Mac.

## Dependencies and setup

- App supports macOS 13+, Apple silicon and Intel; bundles Python and the mail reader.
- Bob Shell must be version 2.x; Node must be 24+. Setup and every inference request validate Bob's version. Unknown, broken, timed-out and unsupported versions fail with actionable messages. Version probes send no prompts or API keys.
- Use IBM's supported installer: https://bob.ibm.com/docs/shell/getting-started/install-and-setup . Bob and Node are not silently downloaded or redistributed. Corporate installation policy still applies.
- Mail and saved tasks must remain usable without Bob. A supported Outlook cache is required for mail. New mail depends on Outlook downloading it.
- A future Outlook cache change cannot be guaranteed compatible. Missing, inaccessible and unreadable caches must show an error, never erase saved tasks.

## Signed release

1. Obtain an Apple Developer ID Application certificate with its private key on the build Mac. Store notarization credentials in a named `notarytool` Keychain profile. Never commit credentials.
2. Run `scripts/build_mac.sh` with universal Python and the packaging dependencies.
3. Set `SIGNING_IDENTITY` to the Developer ID Application identity and `NOTARY_PROFILE` to the stored profile. Run `bash scripts/notarize_mac.sh`.
4. The release script checks both architectures, signs nested code with hardened runtime and timestamps, submits to Apple, staples the ticket, validates Gatekeeper and creates the final ZIP only after success.
5. Test the ZIP downloaded through a browser on clean machines before publishing. Do not remove quarantine or bypass Gatekeeper to pass the test.

## Acceptance matrix — not yet completed

Test a fresh macOS user on Apple silicon and physical Intel, minimum supported macOS and current supported macOS. Record OS, architecture, Outlook version, Bob version and result without mail contents.

- No Python, Git, Homebrew, Node or Bob: native window opens; setup explains missing prerequisites; manual tasks save/reopen.
- Install Bob using IBM's installer, reopen app: discovers runtime without terminal PATH setup. Invalid/old/future Bob versions and Node 22 show setup errors; supported Bob 2.x and Node 24+ pass.
- Missing Outlook, no profile, multiple profiles, permission denied, corrupt/incompatible cache: clear recovery message; no data loss.
- With a test mailbox: mail sync, new-message discovery, task accept/edit/move, links and contacts work. Use synthetic data for AI testing until transmission is authorized.
- Quit, reboot, relaunch and update: tasks, preferences and history survive; one canonical app is launched; no terminal window is required.
- Downloaded signed app passes Gatekeeper online and after stapling offline. Company policy may still block installation.
- Automatic code updates currently use HTTPS and a repository commit, not signed update manifests. Installer notarization does not authenticate later downloaded code. Signed updates remain a separate production-release requirement.
