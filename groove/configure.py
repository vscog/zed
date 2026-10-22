#!/usr/bin/env python3
"""Generate Groove's Zed theme/config from the shared desktop palette."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

def generate(palette):
    c = palette['colors']
    t = palette['typography']
    theme = copy.deepcopy(json.loads((ROOT/'assets/themes/one/one.json').read_text())['themes'][0])
    theme['name'] = 'Groove Ink Black'
    s = theme['style']
    # Replace every inherited color, preserving alpha and semantic contrast.
    for key, value in list(s.items()):
        if not isinstance(value, str) or not value.startswith('#'):
            continue
        if key.endswith('background'):
            s[key] = c['BG1']
        elif 'border' in key:
            s[key] = c['BORDER_SUBTLE']
        elif 'muted' in key or 'placeholder' in key or 'disabled' in key:
            s[key] = c['GREY_DIM']
        else:
            s[key] = c['FOREGROUND']
    groups = {
        'BG0': ['background','editor.background','editor.gutter.background','tab.active_background','terminal.background'],
        'BG1': ['surface.background','elevated_surface.background','panel.background','status_bar.background','title_bar.background','title_bar.inactive_background','toolbar.background','tab_bar.background','tab.inactive_background','editor.subheader.background'],
        'BG2': ['element.hover','element.active','element.selected','ghost_element.hover','ghost_element.active','ghost_element.selected','editor.active_line.background','editor.highlighted_line.background'],
        'BORDER_SUBTLE': ['border','border.variant','editor.indent_guide','scrollbar.track.border'],
        'BORDER_VISIBLE': ['editor.indent_guide_active','scrollbar.thumb.background','scrollbar.thumb.hover_background'],
        'ACCENT': ['text.accent','icon.accent','border.focused','border.selected','panel.focused_border','pane.focused_border','editor.line_number_active'],
        'FOREGROUND': ['text','editor.foreground','terminal.foreground'],
        'SILVER': ['icon','text.muted','icon.muted'],
        'GREY_DIM': ['editor.line_number','text.placeholder','text.disabled','icon.disabled','icon.placeholder','editor.invisible'],
    }
    for color, keys in groups.items():
        for key in keys:
            s[key] = c[color]
    for key in ['border.transparent','ghost_element.background','scrollbar.track.background']:
        s[key] = '#00000000'
    s['search.match_background'] = c['ACCENT']+'33'
    s['search.active_match_background'] = c['YELLOW']+'44'
    s['drop_target.background'] = c['ACCENT']+'33'
    roles = {'error':'RED','warning':'YELLOW','info':'CYAN','hint':'PURPLE','success':'GREEN','created':'GREEN','modified':'YELLOW','deleted':'RED','conflict':'YELLOW','renamed':'CYAN','ignored':'GREY_DIM','hidden':'GREY_DIM','unreachable':'GREY_DIM','predictive':'GREY_DIM'}
    for role, color in roles.items():
        for suffix, alpha in [('', ''),('.background','18'),('.border','55')]:
            s[role+suffix] = c[color]+alpha
    ansi = {'black':'BG2','red':'RED','green':'GREEN','yellow':'YELLOW','blue':'BLUE','magenta':'PURPLE','cyan':'CYAN','white':'FOREGROUND'}
    for name, color in ansi.items():
        for variant in ['', 'bright_', 'dim_']:
            s['terminal.ansi.'+variant+name] = c[color]
    s['players'] = [{'cursor':c['ACCENT'],'background':c['ACCENT'],'selection':c['ACCENT']+'33'}]
    for token, style in s['syntax'].items():
        color = 'FOREGROUND'
        if 'comment' in token: color = 'GREY_DIM'
        elif any(k in token for k in ['keyword','operator']): color = 'PURPLE'
        elif any(k in token for k in ['string','added']): color = 'GREEN'
        elif any(k in token for k in ['number','boolean','constant']): color = 'YELLOW'
        elif any(k in token for k in ['function','title','link']): color = 'BLUE'
        elif any(k in token for k in ['type','constructor','tag']): color = 'CYAN'
        elif 'deleted' in token: color = 'RED'
        elif 'punctuation' in token: color = 'SILVER'
        style['color'] = c[color]
    family = {'$schema':'https://zed.dev/schema/themes/v0.2.0.json','name':'Groove','author':'vscog','themes':[theme]}
    settings = {
        'theme': {'mode':'dark','dark':'Groove Ink Black','light':'One Light'},
        'vim_mode': True,
        'vim': {'use_system_clipboard':'always','toggle_relative_line_numbers':True,'use_smartcase_find':True},
        'ui_font_family': t['ui_family'], 'ui_font_size':16,
        'buffer_font_family':t['mono_family'], 'buffer_font_size':14,
        'buffer_line_height':'comfortable', 'relative_line_numbers':'enabled',
        'window_decorations':'server',
        'title_bar':{'show_branch_name':True,'show_branch_status_icon':True,'show_onboarding_banner':False,'show_user_picture':False,'show_sign_in':False},
        'toolbar':{'breadcrumbs':True,'quick_actions':False,'selections_menu':False},
        'project_panel':{'dock':'left','default_width':250,'auto_reveal_entries':True},
        'git_panel':{'dock':'left'},
        'terminal':{'dock':'bottom','default_height':260,'font_family':t['mono_family'],'font_size':14,'working_directory':'current_project_directory'},
        'indent_guides':{'enabled':True},'inlay_hints':{'enabled':False},
        'sticky_scroll':{'enabled':True},'use_smartcase_search':True,
        'format_on_save':'on','which_key':{'enabled':True},
    }
    settings.update({
        'agent_ui_font_size':14, 'agent_buffer_font_size':14,
        'agent':{'enabled':True,'button':True,'dock':'right','default_width':640,'flexible':False},
        'agent_servers':{
            'codex-acp':{'type':'registry','env':{'CODEX_HOME':str(Path.home()/'.codex')}},
            'claude-acp':{'type':'registry','env':{'CLAUDE_CONFIG_DIR':str(Path.home()/'.claude')}},
        },
        'auto_install_extensions':{name:True for name in ['html','toml','dockerfile','docker-compose','lua','nix','glsl','wgsl']},
    })
    nav = dict(zip(['ctrl-h','ctrl-j','ctrl-k','ctrl-l'], ['workspace::ActivatePaneLeft','workspace::ActivatePaneDown','workspace::ActivatePaneUp','workspace::ActivatePaneRight']))
    bindings = {
        'space w':'workspace::Save','space q':'pane::CloseActiveItem',
        'space f f':'file_finder::Toggle','space f g':'pane::DeploySearch',
        'space /':'pane::DeploySearch','space f b':'tab_switcher::Toggle','space space':'tab_switcher::Toggle',
        'space f s':'outline::Toggle','space f d':'diagnostics::Deploy','space f c':'command_palette::Toggle',
        'space e':'project_panel::ToggleFocus','space g g':'git_panel::ToggleFocus','space g s':'git_panel::ToggleFocus',
        'space c r':'editor::Rename','space c a':'editor::ToggleCodeActions','space c f':'editor::Format',
        'space b d':'pane::CloseActiveItem','shift-h':'pane::ActivatePreviousItem','shift-l':'pane::ActivateNextItem',
        'space z z':'terminal_panel::Toggle','space z h':'terminal_panel::Toggle',
        'space v':'pane::SplitRight','space s':'pane::SplitDown',
        'space a a':'agent::ToggleFocus',
        'space a c':['agent::NewExternalAgentThread',{'agent':'claude-acp'}],
        'space a d':['agent::NewExternalAgentThread',{'agent':'codex-acp'}],
        **nav,
    }
    keymap = [
        {'context':'Workspace','bindings':{'ctrl-\\':'terminal_panel::Toggle',
            'ctrl-alt-shift-c':['agent::NewExternalAgentThread',{'agent':'claude-acp'}],
            'ctrl-alt-shift-d':['agent::NewExternalAgentThread',{'agent':'codex-acp'}]}},
        {'context':'Editor && vim_mode == normal && !menu','bindings':bindings},
        {'context':'ProjectPanel','bindings':nav},
    ]
    return family, settings, keymap

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--palette',type=Path,default=Path.home()/'.config/theme/theme.toml')
    p.add_argument('--install',action='store_true')
    args=p.parse_args()
    family,settings,keymap=generate(tomllib.loads(args.palette.read_text()))
    write(ROOT/'assets/themes/groove/groove.json',family)
    for name,data in [('settings.json',settings),('keymap.json',keymap)]:
        write(ROOT/'groove'/name,data)
    if args.install:
        dest=Path.home()/'.config/zed'
        backup=Path.home()/'.local/state/zed-groove/backups'/str(time.time_ns())
        for name in ['settings.json','keymap.json','themes/groove.json']:
            target=dest/name
            if target.exists():
                (backup/name).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,backup/name)
        write(dest/'themes/groove.json',family)
        write(dest/'settings.json',settings)
        write(dest/'keymap.json',keymap)
        print('Installed Groove configuration. Existing files backed up to',backup)

if __name__=='__main__': main()
