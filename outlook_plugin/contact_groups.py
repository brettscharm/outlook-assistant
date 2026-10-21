"""Persistent local contact groups, anchored to a company domain."""
import re
from .config import read_config, update_config, _LOCK
from .contacts import normalize_domain


def listing():
    return read_config().get('contact_groups', [])


def save(data):
    identifier=data.get('id','')
    if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',identifier):raise ValueError('Invalid group ID.')
    with _LOCK:
        rows=listing();current=next((r for r in rows if r['id']==identifier),None)
        revision=current.get('revision',0) if current else 0
        if type(data.get('revision')) is not int or data['revision']!=revision:raise ValueError('This group changed. Close and reopen it before editing.')
        if data.get('remove') is True:
            update_config({'contact_groups':[r for r in rows if r['id']!=identifier]});return {'removed':True}
        name=data.get('name','')
        if not isinstance(name,str) or not name.strip() or len(name.strip())>100:raise ValueError('Name the group using up to 100 characters.')
        domain=normalize_domain(data.get('domain',''))
        emails=data.get('emails',[])
        if not isinstance(emails,list) or len(emails)>1000:raise ValueError('Use up to 1,000 email addresses per group.')
        clean=[]
        for email in emails:
            if not isinstance(email,str) or len(email)>254 or not re.fullmatch(r'[^\s@<>?,;]+@[^\s@<>?,;]+\.[^\s@<>?,;]+',email.strip()):raise ValueError('Use valid email addresses.')
            email=email.strip().lower()
            if email not in clean:clean.append(email)
        item={'id':identifier,'domain':domain,'name':name.strip(),'emails':clean,'revision':revision+1}
        if not current and len(rows)>=1000:raise ValueError('Group limit reached.')
        update_config({'contact_groups':[r for r in rows if r['id']!=identifier]+[item]})
        return item
