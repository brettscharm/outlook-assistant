"""Fail packaging if a Mach-O component cannot run natively on both Mac architectures."""
import subprocess
import sys
from pathlib import Path

root=Path(sys.argv[1])
checked=0
failures=[]
for path in root.rglob('*'):
    if path.is_symlink() or not path.is_file():continue
    with path.open('rb') as stream:magic=stream.read(4)
    if magic not in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'):continue
    result=subprocess.run(['lipo','-archs',str(path)],capture_output=True,text=True,check=True)
    checked+=1
    if not {'arm64','x86_64'}.issubset(result.stdout.split()):failures.append(str(path.relative_to(root)))
if not checked:raise SystemExit('No Mach-O components found to verify.')
if failures:raise SystemExit('Non-universal components:\n'+'\n'.join(failures))
print(f'All {checked} Mach-O components support Apple silicon and Intel natively.')
