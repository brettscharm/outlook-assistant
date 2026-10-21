# Core email-to-task audit — 2026-10-21

Version: 2.22.0. Scope: local cached email → extraction → persistent review → acceptance and resumption. This is a core workflow audit, not a clean-Mac certification or an exhaustive visual audit of every screen.

## Findings fixed

- Long emails previously stopped at 6,000 characters. The app now scans all available text in overlapping 6,000-character sections, retaining the original email link and opening context. Existing short-message checkpoints remain valid; previously unscanned tails become eligible automatically. Long emails can therefore consume more Bob usage.
- Local scans repeatedly searched the cache to obtain each body. They now obtain visible cached bodies in one pass, preserving domain exclusions.
- Recipient information was omitted. Extraction now includes To/CC and distinguishes awareness from assignment in its instructions.
- Duplicate copies could create repeated suggestions. Matching provider message IDs plus matching evidence now suppress new duplicates; similar subjects or titles alone are not enough. Existing saved tasks are not deleted or merged.
- Rejected, unsupported AI suggestions previously still marked their emails processed. Valid results are saved, affected emails remain pending, and an error explains that the next scan will retry them.

## Verification

A live Bob evaluation used ten synthetic emails, not the user's mail. Baseline: 9/10 cases passed; after fixes: 10/10. Cases covered explicit ownership, another person's assignment, relative dates, no deadline, a sent commitment, newsletters, completed work, a completed quoted request, malicious instructions inside email, and an action beyond the old cutoff. This small single-run sample establishes specific behavior, not an accuracy percentage for real mail.

Regression suite: 192 Python tests run, 191 passed and one skipped; 33 JavaScript tests passed. Added regression cases cover long-message boundaries, source links, resume checkpoints, provider-copy deduplication, invalid-evidence retries, and single-pass cache reading. Existing tests cover first-run/date filtering, exclusion rules, review/accept/dismiss/restore, stop/resume, new-arrival scheduling, persistence, and completion review. No real user tasks were created by the audit.

## Remaining limits

- Only locally readable cached mail is available. Missing bodies, attachments containing requests, uncached folders, and Outlook cache-format changes can reduce coverage. A preview is explicitly labeled as incomplete context for extraction.
- AI output is not guaranteed complete or semantically correct. Quotes and dates are validated structurally, but a literal quote can still be interpreted incorrectly. Review remains necessary.
- Long threads are read in sections with opening context, not as unlimited single conversations. Cross-section dependencies or superseding statements can remain ambiguous.
- Ownership that remains ambiguous defaults to the user, as requested. This is a review convenience, not proof of assignment.
- Completion detection currently supplies up to 200 unfinished tasks per extraction batch. Older tasks outside that context may not receive completion suggestions. Completion requires review and is not applied automatically.
- Exact-copy suppression requires a provider message ID and matching evidence. Reworded follow-ups can still need manual duplicate dismissal.
- The preserved checkpoint format ignores recipient-only changes; changing message content or the user's context makes the message eligible again.
- This audit did not test a clean Mac, every Outlook version, or every UI flow. Automated checks do not establish that the app is bug-free.
