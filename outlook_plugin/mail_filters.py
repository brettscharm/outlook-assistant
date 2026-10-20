"""User-controlled sender exclusions, applied before pagination and AI retrieval."""
import re
from email.utils import parseaddr
from .config import read_config

def normalize_domains(value):
    if isinstance(value,str):value=re.split(r'[\s,;]+',value)
    if not isinstance(value,list) or len(value)>200:raise ValueError('Enter up to 200 domains, one per line.')
    result=set()
    for raw in value:
        if not isinstance(raw,str):raise ValueError('Enter domain names such as example.com.')
        domain=raw.strip().lower().lstrip('@').rstrip('.')
        if not domain:continue
        try:domain=domain.encode('idna').decode('ascii')
        except UnicodeError:raise ValueError('Invalid domain name.') from None
        if len(domain)>253 or '.' not in domain or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in domain.split('.')):
            raise ValueError('Use domains such as example.com, without URLs or email addresses.')
        result.add(domain)
    return sorted(result)

def visible_messages(rows):
    excluded=read_config().get('excluded_domains',[])
    if not excluded:return rows
    def allowed(message):
        sender=message.get('from') or {}
        address=sender.get('address','') if isinstance(sender,dict) else ''
        address=address or parseaddr(message.get('sender',''))[1]
        domain=address.rsplit('@',1)[-1].lower().rstrip('.') if '@' in address else ''
        try:domain=domain.encode('idna').decode('ascii')
        except UnicodeError:pass
        return not any(domain==rule or domain.endswith('.'+rule) for rule in excluded)
    return [message for message in rows if allowed(message)]
