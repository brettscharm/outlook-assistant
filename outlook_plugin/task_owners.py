"""Resolve owners only against addresses actually present in message headers."""
from email.utils import getaddresses


def full_name(value):
    value=str(value or '').strip().strip('"')
    parts=value.split(',')
    return (parts[1].strip()+' '+parts[0].strip()) if len(parts)==2 and all(p.strip() for p in parts) else value


def resolve_owner(owner, message):
    headers=[message.get('sender','')]
    for key in ('to','cc'):
        values=message.get(key,[]) or []
        if isinstance(values,str):values=[values]
        for value in values:
            if isinstance(value,dict):headers.append(f'{value.get("name","")} <{value.get("address",value.get("email",""))}>')
            elif isinstance(value,str):headers.append(value)
    people={address.casefold():full_name(name) for name,address in getaddresses(headers) if '@' in address}
    supplied=getaddresses([owner])[0] if owner else ('','')
    query=full_name(supplied[0] or owner).casefold()
    if supplied[1].casefold() in people:
        address=supplied[1].casefold();name=people[address]
        return f'{name} <{address}>' if name else address
    matches=[(address,name) for address,name in people.items() if name and (name.casefold()==query or (len(query.split())==1 and name.split()[0].casefold()==query))]
    if len(matches)==1:
        address,name=matches[0];return f'{name} <{address}>'
    return full_name(owner)
