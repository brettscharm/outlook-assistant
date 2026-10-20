"""Contacts inferred locally from cached senders, grouped by exact email domain."""
from email.utils import parseaddr
import re
from .config import read_config, update_config, _LOCK


def normalize_domain(value):
    value=str(value).strip().lower().rstrip('.')
    try: value=value.encode('idna').decode('ascii')
    except UnicodeError: raise ValueError('Enter a valid email domain.') from None
    if len(value)>253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',value) or '.' not in value or any(not part or len(part)>63 or part.startswith('-') or part.endswith('-') for part in value.split('.')):
        raise ValueError('Enter a valid email domain.')
    return value


def link_company(domain,company):
    domain=normalize_domain(domain)
    if not isinstance(company,str) or len(company.strip())>200: raise ValueError('Use a company name of up to 200 characters.')
    with _LOCK:
        links=dict(read_config().get('domain_companies',{}))
        if company.strip():
            if domain not in links and len(links)>=1000: raise ValueError('Company link limit reached.')
            links[domain]=company.strip()
        else: links.pop(domain,None)
        update_config({'domain_companies':links})
    return links


def group_contacts(rows,links):
    people={}
    for row in rows:
        sender=row.get('from') or {}
        name,address=sender.get('name',''),sender.get('address','')
        if not address: name,address=parseaddr(row.get('sender',''))
        address=address.strip().lower()
        if address.count('@')!=1 or any(c.isspace() for c in address): continue
        local,domain=address.rsplit('@',1)
        if not local: continue
        try: domain=normalize_domain(domain)
        except ValueError: continue
        address=local+'@'+domain
        person=people.setdefault(address,dict(email=address,name=name or address,domain=domain,message_count=0))
        person['message_count']+=1
        if person['name']==address and name: person['name']=name
    groups={}
    for person in people.values():
        domain=person.pop('domain')
        group=groups.setdefault(domain,dict(domain=domain,company=links.get(domain,''),contacts=[]))
        group['contacts'].append(person)
    for group in groups.values():group['contacts'].sort(key=lambda p:(p['name'].casefold(),p['email']))
    return sorted(groups.values(),key=lambda g:(g['company'].casefold() or g['domain'],g['domain']))
