Derived from https://github.com/pA1nD/hxmail at 75b1432069166d2f3da642ee6bb81860271b076e (MIT). Original attribution and underlying m365crawl notices are retained in LICENSE and THIRD_PARTY_NOTICES.md.

Outlook Assistant changes:
- Accept Outlook 16.112 header tag 0x428; trailing string word offsets are eight bytes earlier and the string base is the actual tag plus lead.
- Accept body tag 0x740 and scan its actual fixed region.
- Accept folder tag 0x4c2, name at 1076, kind at 1148, well-known identifier at 1172.
- Optional all-account-root collection; enabled in the embedded CLI. Expose stable message detail keys and folder keys in JSON.
- Preserve paragraph boundaries in the CLI's plain-text body output, without fetching images or executing HTML.
- Synthetic regression tests for the three older record layouts. Existing upstream tests retained.

Local validation on Outlook 16.112.1: 2,063 message records, current-day mail, 227 matching InternetMessageId records with matching read status. Personal data and diagnostic snapshots are not included in this repository. Internal cache layouts may change; no universal version support is claimed.
