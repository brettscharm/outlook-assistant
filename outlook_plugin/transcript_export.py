"""Explicit transcript export through the macOS save dialog."""
import re
import subprocess
from pathlib import Path
from .storage import _replace


def filename(title):
    return (re.sub(r'[\x00-\x1f/\\:*?"<>|]', '-', title).strip(' .')[:100] or 'Meeting') + '-transcript.txt'


def export(data):
    title=data.get('title','Meeting');content=data.get('transcript')
    if not isinstance(title,str) or len(title)>300:raise ValueError('Invalid meeting title.')
    if not isinstance(content,str) or not content.strip() or len(content)>500000:raise ValueError('Add a transcript of up to 500,000 characters first.')
    script='''on run argv
try
activate
set destination to choose file name with prompt "Export transcript" default name (item 1 of argv)
return POSIX path of destination
on error number -128
return ""
end try
end run'''
    result=subprocess.run(['/usr/bin/osascript','-e',script,filename(title)],capture_output=True,text=True,timeout=180)
    if result.returncode:raise ValueError('Could not open the save dialog. Please try again.')
    target=result.stdout.rstrip('\n')
    if not target:return {'saved':False}
    path=Path(target)
    if not path.is_absolute():raise ValueError('Choose a local destination.')
    _replace(path,content.encode('utf-8'))
    return {'saved':True}
