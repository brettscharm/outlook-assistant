"""Remember sanitized connection outcomes for the current credential, never raw errors."""
import hashlib
import json
import os
import re
from datetime import datetime,timezone
from .config import read_config,update_config
MESSAGES={
 'missing':('No Bob key','Add your Bob API key in Settings.'),
 'unchecked':('Key not verified','A key is saved, but this key and team have not been verified. Use Test Bob connection.'),
 'connected':('Bob connected','The last Bob request succeeded.'),
 'revoked':('Bob key revoked','IBM reported that the Bob credential was revoked. Add a new API key in Settings, then test the connection.'),
 'expired':('Bob key expired','IBM reported that the Bob credential expired. Add a new API key in Settings, then test the connection.'),
 'invalid':('Bob key rejected','IBM rejected authentication. The key may be invalid, expired, or revoked. Replace it in Settings and test again.'),
 'permission':('Bob access denied','IBM denied access. Check your team ID and the key’s permissions. This does not prove the key was revoked.'),
 'quota':('Bob usage limit reached','IBM reported a budget or quota limit. Check your Bob allowance or ask your subscription administrator.'),
 'rate_limit':('Bob rate limited','Too many requests. Wait briefly and try again.'),
 'network':('Bob connection failed','Bob could not connect or timed out. Check your network and retry; the key has not been confirmed invalid.'),
 'error':('Bob request failed','Bob did not complete the request. Test the connection in Settings. The cause is not confirmed.')}

def identity(key,team):return hashlib.sha256((key+'\0'+str(team or '')).encode()).hexdigest()

def remember(key,team,state):
    if state not in MESSAGES:return
    try:update_config({'bob_connection':{'credential':identity(key,team),'state':state,'checked_at':datetime.now(timezone.utc).isoformat()}})
    except (OSError,ValueError):pass

def current(key):
    cfg=read_config();saved=cfg.get('bob_connection',{})
    team=os.environ.get('BOB_TEAM_ID') or cfg.get('bob_team_id')
    state='missing' if not key else 'unchecked'
    checked=None
    if key and saved.get('credential')==identity(key,team) and saved.get('state') in MESSAGES:
        state=saved['state'];checked=saved.get('checked_at')
    title,message=MESSAGES[state]
    return dict(state=state,title=title,message=message,checked_at=checked)

def classify(error):
    raw=json.dumps(error) if not isinstance(error,str) else error
    raw=raw.lower()[:40000]
    if re.search(r'(key|credential|token).{0,70}revoked|revoked.{0,70}(key|credential|token)',raw):return 'revoked'
    if re.search(r'(key|credential|token).{0,70}expired|expired.{0,70}(key|credential|token)',raw):return 'expired'
    if any(term in raw for term in ('invalid_api_key','invalid api key','unauthorized','authentication failed','authentication_error','invalid token')) or re.search(r'(status|code|http)[^\d]{0,15}401\b',raw):return 'invalid'
    if any(term in raw for term in ('insufficient_quota','budget exceeded','budget_exceeded','quota exceeded','insufficient credits','cost limit reached')):return 'quota'
    if 'rate limit' in raw or re.search(r'(status|code|http)[^\d]{0,15}429\b',raw):return 'rate_limit'
    if 'forbidden' in raw or 'permission denied' in raw or re.search(r'(status|code|http)[^\d]{0,15}403\b',raw):return 'permission'
    if any(term in raw for term in ('timeout','timed out','econnrefused','enotfound','econnreset','network error','fetch failed','unable to connect')):return 'network'
    return 'error'

def failure(key,team,error):
    state=classify(error);remember(key,team,state)
    return RuntimeError(MESSAGES[state][1])
