#!/usr/bin/env python3
"""Install a successfully built Groove binary and wire the desktop launcher."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

p=argparse.ArgumentParser();p.add_argument('binary',type=Path);a=p.parse_args()
binary=a.binary.resolve()
if not binary.is_file(): raise SystemExit('Build the zed binary first')
subprocess.run([str(binary),'--version'],check=True)
home=Path.home();backup=home/'.local/state/zed-groove/backups'/str(time.time_ns());backup.mkdir(parents=True)
app=home/'.local/lib/zed-groove';app.mkdir(parents=True,exist_ok=True)
subprocess.run(['cp','--reflink=auto',str(binary),str(app/'.zed-editor.new')],check=True)
os.replace(app/'.zed-editor.new',app/'zed-editor')
launcher=home/'.local/bin/zed-groove'
launcher.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
from urllib.parse import urlparse,unquote
home=Path.home()
args=sys.argv[1:]
# When Thunar opens one code file, include its folder in the explorer.
if len(args)==1:
    value=args[0]
    if value.startswith('file://'):
        value=unquote(urlparse(value).path)
    file=Path(value)
    if file.is_file():
        args=[str(file.resolve().parent),str(file.resolve())]
os.environ['ZED_RELEASE_CHANNEL']='stable'
cli=home/'.local/zed.app/bin/zed'
os.execv(str(cli),[str(cli),'--zed',str(home/'.local/lib/zed-groove/zed-editor'),*args])
''');launcher.chmod(0o755)
zed=home/'.local/bin/zed'
if zed.exists() or zed.is_symlink():
    shutil.copy2(zed,backup/'zed-launcher',follow_symlinks=False)
    zed.unlink()
zed.symlink_to(launcher)
desktop=home/'.local/share/applications/dev.zed.Zed.desktop'
shutil.copy2(desktop,backup/desktop.name)
text=desktop.read_text()
text=text.replace(str(home/'.local/zed.app/bin/zed'),str(launcher))
desktop.write_text(text)
settings=home/'.config/zed/settings.json';shutil.copy2(settings,backup/settings.name)
data=json.loads(settings.read_text());data['auto_update']=False
settings.write_text(json.dumps(data,indent=2)+'\n')
subprocess.run(['update-desktop-database',str(desktop.parent)],check=True)
print('Custom build installed; previous launchers saved in',backup)
