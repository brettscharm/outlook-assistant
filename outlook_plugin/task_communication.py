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
