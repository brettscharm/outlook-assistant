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
    return link_companies([domain], company)


def link_companies(domains, company):
    if not isinstance(domains,list) or not 1 <= len(domains) <= 100:
        raise ValueError('Enter between 1 and 100 domains.')
    domains=list(dict.fromkeys(normalize_domain(d) for d in domains))
    if not isinstance(company,str) or len(company.strip())>200:
        raise ValueError('Use a company name of up to 200 characters.')
    company=company.strip()
    with _LOCK:
        links=dict(read_config().get('domain_companies',{}))
        # Reuse existing capitalization so one company stays one company.
        company=next((v for v in links.values() if v.casefold()==company.casefold()),company)
        for domain in domains:
            if company: links[domain]=company
            else: links.pop(domain,None)
        if len(links)>1000: raise ValueError('Company link limit reached.')
        update_config({'domain_companies':links})
    return links


SHARED_DOMAINS={'gmail.com','googlemail.com','outlook.com','hotmail.com','live.com','yahoo.com','icloud.com','me.com','aol.com','proton.me','protonmail.com'}


def suggest_company(domain, companies, links):
    if domain in SHARED_DOMAINS: return None
    for parent,company in sorted(links.items(), key=lambda item:len(item[0]), reverse=True):
        if parent not in SHARED_DOMAINS and domain.endswith('.'+parent):
            return {'company':company,'reason':'Related to linked domain '+parent}
    labels=domain.split('.')
    stem=labels[-3] if len(labels)>2 and labels[-2] in {'co','com','org','net'} else labels[-2]
    normalize=lambda name: re.sub(r'[^a-z0-9]','',name.casefold())
    for company in companies:
        name=re.sub(r'\b(incorporated|corporation|company|limited|inc|corp|ltd|llc)\b\.?','',company,flags=re.I)
        if normalize(name)==normalize(stem):
            return {'company':company,'reason':'Matches your account list or a linked company'}
    return {'company':stem.replace('-',' ').title(),'reason':'Suggested from the email domain; please verify'}


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
    for domain,company in links.items():
        groups.setdefault(domain,dict(domain=domain,company=company,contacts=[]))
    for group in groups.values():group['contacts'].sort(key=lambda p:(p['name'].casefold(),p['email']))
    return sorted(groups.values(),key=lambda g:(g['company'].casefold() or g['domain'],g['domain']))
