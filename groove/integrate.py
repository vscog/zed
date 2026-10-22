#!/usr/bin/env python3
"""Install desktop integration while preserving existing Thunar actions."""
import json
from pathlib import Path
import shutil
import time
import tomllib
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
home=Path.home()
config=home/'.config'
theme_root=(config/'theme/render.py').resolve().parent
palette=tomllib.loads((config/'theme/theme.toml').read_text())
value=(root/'assets/themes/groove/groove.json').read_text()
# Exact base colors also replace the prefix of alpha-bearing colors.
for key,color in palette['colors'].items():
    value=value.replace(color, '@@colors.'+key+'@@')
target=theme_root/'templates/.config/zed/themes/groove.json'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(value)
uca=config/'Thunar/uca.xml'
if uca.exists():
    tree=ET.parse(uca)
    if not any(a.findtext('unique-id')=='groove-zed-open' for a in tree.getroot()):
        backup=home/'.local/state/zed-groove/backups'/str(time.time_ns())
        backup.mkdir(parents=True)
        shutil.copy2(uca,backup/'thunar-uca.xml')
        action=ET.SubElement(tree.getroot(),'action')
        for key,val in {'icon':'zed','name':'Open in Zed','unique-id':'groove-zed-open','command':str(home/'.local/bin/zed')+' %F','description':'Edit selected files or folders in Groove Zed','patterns':'*'}.items():
            ET.SubElement(action,key).text=val
        for key in ['startup-notify','directories','text-files','other-files']:
            ET.SubElement(action,key)
        ET.indent(tree,space='  ')
        tree.write(uca,encoding='UTF-8',xml_declaration=True)
print('Installed shared-palette template and Thunar Open in Zed action')
