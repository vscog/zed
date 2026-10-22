# Groove Zed

Personal Zed fork for Valentin's Hyprland desktop: Ink Black surfaces, restrained blue focus, Inter UI and GeistMono code, and a Neovim-inspired workflow.

## Assessment and implemented changes

Zed draws its own interface, so GTK/Thunar styles do not skin the editor. The correct integration is a complete Zed theme generated from `~/.config/theme/theme.toml`. The theme covers chrome, editor, gutters, selections, syntax, diagnostics, Git states, and terminal ANSI colors. Opaque editor surfaces keep code readable; Hyprland retains responsibility for window borders, shadows and rounding. Server decorations avoid a second set of client window decorations.

The fork includes `assets/themes/groove/groove.json`, changes the default dark theme, fonts, Vim mode, relative numbers, decorations and title-bar visibility in `assets/settings/default.json`, and extends `assets/keymaps/vim.json`. It keeps upstream functionality and the upstream remote for rebasing.

The installed custom build uses `~/.config/zed/settings.json`, `keymap.json`, and `themes/groove.json`. The activity bar is implemented in Rust; the theme, editor preferences and agent configuration remain editable without a rebuild. The official installation is retained as the CLI transport and as a fallback.

IDE setup includes a left project/Git panel, bottom terminal, breadcrumbs, sticky scopes, indentation guides, language-server completion and diagnostics, and format on save. Language-server and formatter availability depends on each project/language. Inlay hints remain off to keep the interface quiet. Title-bar sign-in prompts are hidden; account and agent features remain available.

## Keys

Space is the leader in normal-mode editors. Ordinary Vim motions, operators, visual mode, `gd`, `gr`, and `K` use Zed's built-in Vim implementation.

| Keys | Action |
| --- | --- |
| Space w / q | Save / close current item |
| Space f f | Find files |
| Space f g or Space / | Search project |
| Space f b or Space Space | Switch tabs |
| Space f s / f d / f c | Symbols / diagnostics / command palette |
| Space e | Project tree |
| Space g g or g s | Git panel |
| Space c r / c a / c f | Rename / code action / format |
| Space b d | Close current item |
| Shift H / L | Previous / next tab |
| Ctrl h/j/k/l | Navigate panes in normal mode and project tree |
| Space v / s | Split right / down |
| Space z z or z h, Ctrl backslash | Toggle terminal |

These are Vim emulation bindings, not embedded Neovim: Lua plugins, Snacks, Telescope and tmux edge handoff do not run inside Zed. Terminal Ctrl combinations remain available to shell applications. Zed's which-key popup is enabled for discovering leader chords.

## Reapply and theme integration

```sh
python3 groove/configure.py --install
python3 groove/integrate.py
```

`configure.py` reads the desktop TOML, generates the versioned theme and configuration, and optionally installs them. Existing Zed files are backed up under `~/.local/state/zed-groove/backups` before replacement. Reapplying replaces those config files; merge personal edits first.

`integrate.py` adds the theme to the existing renderer's templates and adds an idempotent Thunar custom action, backing up Thunar's XML first. It does not change directory MIME defaults. New Thunar windows may be needed to reload the action.

Future desktop theme applications update Zed's theme through the shared renderer. Font changes can be applied by rerunning the configuration generator. The generated theme has a stable display name even if palette values change.

Launch with `~/.local/bin/zed` or the standard desktop entry. `/usr/bin/zed` is the ZFS event daemon and is untouched.

## Validation

Theme checked against Zed's official v0.2.0 JSON schema; modified upstream JSONC assets parsed successfully; shared renderer output compared against the installed theme. Launched Zed 1.25.2 on the live Wayland desktop and visually checked theme, Vim normal mode, relative line numbers, and the Space f f file picker. Logs showed no configuration/keymap/theme parse errors. The full custom binary was subsequently compiled successfully. The live Wayland UI was checked after fixing the activity-row height. Actual mouse clicks verified Explorer collapse/reopen, Source Control, Extensions and Search. Opening `configure.py` through GIO from `/tmp` launched the installed custom executable with its containing folder in the explorer. HTML still resolves to Firefox.

Backups and screenshots remain local and are not included in the public fork.

## Account-backed agents and extensions

The interface now uses 16 px UI text and 14 px editor, terminal and agent text. These are fixed readability overrides to the shared desktop typography; the palette remains synchronized.

Codex and Claude Agent are configured through Zed's ACP Registry, using the existing `~/.codex` ChatGPT login and `~/.claude` Claude Code subscription login. No credentials are copied into the repository. The external agents own authentication; Zed's native model-provider settings are separate. The AI panel is docked on the right.

- Space a a: focus the AI panel.
- Space a d: new Codex thread.
- Space a c: new Claude thread.
- Ctrl Alt Shift D/C: corresponding new threads from the workspace (editor-local bindings can take precedence).

Automatically installed extensions: HTML, TOML, Dockerfile, Docker Compose, Lua, Nix, GLSL and WGSL. Python, Rust, JS/TS, JSON, YAML and Markdown support are provided by Zed itself; language servers may be installed on first use.

## VS Code-style activity bar

The fork adds a persistent 48 px activity rail to the left of the workspace. Explorer, Search, Source Control, Debug, Outline, Extensions, AI and Terminal use Zed's registered native actions. Settings stays at the bottom. Open dock panels have a blue indicator; clicking an active panel closes its dock. Search and Extensions open Zed's native center views. The former left-dock status-bar buttons are replaced by the rail.

The file tree starts open on the left at 300 px, with file icons, folder chevrons, Git status and indentation guides. The outline shares the left dock. AI stays on the right and the terminal below.

Build and install from this checkout:

```sh
CARGO_TARGET_DIR=/data/cache/zed-groove-target cargo build -p zed --bin zed -j 6
python3 groove/install-build.py /data/cache/zed-groove-target/debug/zed
```

The installer copies the binary to `target/groove/zed-editor` in this checkout and links it from `~/.local/lib/zed-groove/zed-editor`. This development build reads assets from the checkout at runtime: keep the checkout in place. It backs up the current launcher and desktop entry, then points them at the custom build using the official CLI's `--zed` option. It disables official automatic updates so they cannot replace the custom UI. Rebuild this branch to update it. The official installation is retained at `~/.local/zed.app`.

The `zed-groove` launcher includes the parent folder when opening a single existing file, so Thunar launches show a useful explorer tree. Existing HTML/browser associations remain unchanged.

## Gitea commit comment history

The native **Gitea Comment History** dock displays the same commit comments as the custom Gitea server. Open a tracked local file and run `gitea comments: toggle history` from the command palette. The panel can search the current file or the entire repository, refresh its contents, and open a comment's original source in Gitea. `gitea comments: toggle inline comments`, or the panel's **Inline** button, displays comments below their original code section.

Configure the server in `~/.config/zed/gitea-comments.json`:

```json
{
  "base_url": "http://100.126.2.20:3131",
  "remote": "origin",
  "token_command": ["/home/valentin/.local/bin/secret-store", "get", "gitea", "token"]
}
```

The credential command is an argument array from user configuration, never a repository-provided shell command. Its token is kept in memory, sent only to the exact configured HTTP(S) origin/base path, and never forwarded through redirects. Python 3 supplies the background API reader; it has no third-party dependencies. The native Rust panel/editor blocks handle display and filtering. Missing configuration or API failures appear in the panel.

Inline placement requires an identical Git blob and an unmodified editor buffer. Editing hides blocks; refresh compares again. Older comments remain searchable with original-source links, and renamed paths are not automatically remapped. Long comments have a bounded inline preview; the history panel retains the complete text. Fetching is explicitly initiated, with a maximum of 10,000 comments per refresh.

Reader trust-boundary tests:

```sh
python3 crates/git_ui/src/gitea_comments_test.py
```

Build/install uses the existing instructions above. Restart Zed after installing a new binary. The new panel supplements the existing activity bar and Git UI.
