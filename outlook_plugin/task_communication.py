"""Prepare user-requested email drafts; never send mail."""
import re
import subprocess
from urllib.parse import quote, urlencode


def draft_url(data):
    recipients=data.get('recipients',[])
    if not isinstance(recipients,list) or not 1<=len(recipients)<=21:
        raise ValueError('Choose at least one owner with an email address.')
    if any(not isinstance(address,str) or len(address)>254 or not re.fullmatch(r'[^\s@<>?,;]+@[^\s@<>?,;]+\.[^\s@<>?,;]+',address) for address in recipients):
        raise ValueError('Use valid email addresses for the owners.')
    subject=str(data.get('subject','')).replace('\r',' ').replace('\n',' ')[:2000]
    body=str(data.get('body',''))[:10000]
    return 'mailto:'+','.join(quote(address,safe='@') for address in dict.fromkeys(recipients))+'?'+urlencode({'subject':subject,'body':body},quote_via=quote)


def open_draft(data):
    url=draft_url(data)
    try:subprocess.run(['/usr/bin/open',url],check=True,capture_output=True,timeout=15)
    except (OSError,subprocess.SubprocessError):raise ValueError('Could not open your email app. Check your default mail app in macOS.') from None
    return {'opened':True}


def open_feedback(kind):
    from . import __version__
    templates = {
        'feature': ('Feature suggestion', 'What would you like to add or improve?\n\n'),
        'problem': ('Problem report', 'What happened?\n\nWhat did you expect?\n\nSteps to reproduce:\n\n'),
    }
    if kind not in templates:
        raise ValueError('Choose a feature suggestion or problem report.')
    subject, body = templates[kind]
    url = draft_url({'recipients': ['brett.scharmett@ibm.com'],
                     'subject': 'Outlook Assistant — ' + subject,
                     'body': body + 'App version: ' + __version__})
    try:
        subprocess.run(['/usr/bin/open', '-a', 'Microsoft Outlook', url],
                       check=True, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        raise ValueError('Could not open Outlook. Open Microsoft Outlook and try again, or email brett.scharmett@ibm.com.') from None
    return {'opened': True}
