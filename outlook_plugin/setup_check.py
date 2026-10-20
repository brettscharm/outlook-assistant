"""Read-only first-run checks; never run AppleScript or send mail to Bob."""
import os
import platform
from pathlib import Path
from . import local_store,bob_status
from .ai_agent import bob_executable, get_bob_api_key, node_executable
from .config import read_config

def check():
    machine=platform.machine()
    version=platform.mac_ver()[0]
    major=int(version.split('.')[0]) if version and version.split('.')[0].isdigit() else 0
    supported=platform.system()=='Darwin' and major>=13 and machine in ('arm64','x86_64')
    arch='arm64' if machine=='arm64' else 'amd64'
    helper=Path(__file__).parent/'bin'/'hxmail-darwin'
    cfg=read_config()
    try:
        available=local_store.profiles()
        selected=cfg.get('outlook_profile','')
        profile_ok=any(str(p.resolve())==str(Path(selected).expanduser().resolve()) for p in available) if selected else len(available)==1
        detail=('Local profile found.' if profile_ok else 'Choose your Outlook profile in Settings.' if available else 'Open New Outlook, sign in, and let your mail download. A supported local cache is required.')
    except PermissionError:
        profile_ok=False;detail='macOS has blocked access to Outlook data. Check app permissions or contact your administrator.'
    identity=cfg.get('user_context',{})
    connection=bob_status.current(get_bob_api_key())
    checks=[
        dict(id='mac',label='Supported Mac',ready=supported,detail=f'macOS {version or "unknown"} · {machine}. Requires macOS 13 or later, Apple silicon or Intel.'),
        dict(id='reader',label='Bundled mail reader',ready=helper.is_file() and os.access(helper,os.X_OK),detail='Included with the Mac app; no Python, Git, or Homebrew installation is required.'),
        dict(id='outlook',label='Outlook local profile',ready=profile_ok,detail=detail),
        dict(id='bob',label='IBM Bob Shell',ready=bool(bob_executable()),detail='Install Bob Shell 2.x through IBM’s official distribution. It is a separate prerequisite.'),
        dict(id='node',label='Node.js for Bob',ready=bool(node_executable(bob_executable())),detail='IBM Bob Shell requires Node.js 24 or later. The app detects common Homebrew, npm, nvm, fnm, mise, and Volta locations.'),
        dict(id='key',label='Your Bob API key',ready=bool(get_bob_api_key()) and connection['state'] not in ('revoked','expired','invalid','permission'),detail=connection['message']),
        dict(id='identity',label='Your name and email',ready=bool(identity.get('full_name','').strip() and '@' in identity.get('email_addresses','')),detail='Add your identity in My context to enable personalized task discovery.')]
    return {'ready':all(c['ready'] for c in checks),'checks':checks}
