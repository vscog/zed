use std::{process::Command, sync::Arc};

use editor::{
    Editor, EditorEvent,
    display_map::{BlockPlacement, BlockProperties, BlockStyle, CustomBlockId},
};
use gpui::{
    App, Context, Entity, EventEmitter, FocusHandle, Focusable, Subscription, WeakEntity, Window,
    actions,
};
use language::Point;
use serde::Deserialize;
use ui::{Button, IconName, prelude::*};
use workspace::{
    Workspace,
    dock::{DockPosition, Panel, PanelEvent},
};

const READER: &str = include_str!("gitea_comments.py");
actions!(gitea_comments, [ToggleHistory, ToggleInlineComments]);

#[derive(Clone, Deserialize)]
struct Comment {
    id: u64,
    author: String,
    commit_sha: String,
    path: String,
    start_line: u32,
    end_line: u32,
    body: String,
    inline: bool,
    url: String,
}

#[derive(Deserialize)]
struct History {
    comments: Vec<Comment>,
    content: String,
    path: String,
}

pub struct CommentPanel {
    workspace: WeakEntity<Workspace>,
    focus: FocusHandle,
    search: Entity<Editor>,
    comments: Vec<Comment>,
    status: String,
    all_files: bool,
    inline: bool,
    loading: bool,
    blocks: Vec<CustomBlockId>,
    editor: Option<WeakEntity<Editor>>,
    editor_subscription: Option<Subscription>,
    _subscriptions: Vec<Subscription>,
    position: DockPosition,
}

pub fn register(workspace: &mut Workspace) {
    workspace.register_action(|workspace, _: &ToggleHistory, window, cx| {
        let panel = ensure_panel(workspace, window, cx);
        window.defer(cx, move |window, cx| {
            panel.update(cx, |panel, cx| panel.refresh(window, cx));
        });
        workspace.toggle_panel_focus::<CommentPanel>(window, cx);
    });
    workspace.register_action(|workspace, _: &ToggleInlineComments, window, cx| {
        let panel = ensure_panel(workspace, window, cx);
        window.defer(cx, move |window, cx| {
            panel.update(cx, |panel, cx| {
                panel.inline = !panel.inline;
                if panel.inline {
                    panel.refresh(window, cx);
                } else {
                    panel.clear_blocks(cx);
                }
                cx.notify();
            });
        });
        workspace.open_panel::<CommentPanel>(window, cx);
    });
}

fn ensure_panel(
    workspace: &mut Workspace,
    window: &mut Window,
    cx: &mut Context<Workspace>,
) -> Entity<CommentPanel> {
    if let Some(panel) = workspace.panel::<CommentPanel>(cx) {
        return panel;
    }
    let workspace_handle = workspace.weak_handle();
    let panel = cx.new(|cx| {
        let search = cx.new(|cx| Editor::single_line(window, cx));
        search.update(cx, |editor, cx| {
            editor.set_placeholder_text("Search comments, paths, authors…", window, cx)
        });
        let subscription = cx.subscribe(&search, |_, _, _: &EditorEvent, cx| cx.notify());
        CommentPanel {
            workspace: workspace_handle,
            focus: cx.focus_handle(),
            search,
            comments: vec![],
            status: "Open a tracked file, then Refresh.".into(),
            all_files: false,
            inline: false,
            loading: false,
            blocks: vec![],
            editor: None,
            editor_subscription: None,
            _subscriptions: vec![subscription],
            position: DockPosition::Right,
        }
    });
    workspace.add_panel(panel.clone(), window, cx);
    panel
}

impl CommentPanel {
    fn clear_blocks(&mut self, cx: &mut Context<Self>) {
        if let Some(editor) = self.editor.as_ref().and_then(WeakEntity::upgrade) {
            let blocks = self.blocks.drain(..).collect();
            editor.update(cx, |editor, cx| editor.remove_blocks(blocks, None, cx));
        }
        self.blocks.clear();
        self.editor_subscription = None;
    }

    fn refresh(&mut self, _window: &mut Window, cx: &mut Context<Self>) {
        if self.loading {
            return;
        }
        let editor = self
            .workspace
            .upgrade()
            .and_then(|workspace| workspace.read(cx).active_item_as::<Editor>(cx));
        let Some(editor) = editor else {
            self.status = "Open a tracked source file first.".into();
            cx.notify();
            return;
        };
        let Some(path) = editor.update(cx, |editor, cx| editor.target_file_abs_path(cx)) else {
            self.status = "Comments require a local file.".into();
            cx.notify();
            return;
        };
        self.clear_blocks(cx);
        self.editor = Some(editor.downgrade());
        self.loading = true;
        self.status = "Loading Gitea comment history…".into();
        let all_files = self.all_files;
        let task = cx.background_spawn(async move {
            let output = Command::new("python3")
                .arg("-c")
                .arg(READER)
                .arg(path)
                .arg(if all_files { "all" } else { "file" })
                .output()?;
            if !output.status.success() {
                let value: serde_json::Value = serde_json::from_slice(&output.stdout)?;
                anyhow::bail!(
                    "{}",
                    value["error"].as_str().unwrap_or("Comment reader failed")
                );
            }
            Ok::<History, anyhow::Error>(serde_json::from_slice(&output.stdout)?)
        });
        cx.spawn(async move |panel, cx| {
            let result = task.await;
            panel.update(cx, |panel, cx| {
                panel.loading = false;
                match result {
                    Err(error) => { panel.status = format!("{error}. Configure ~/.config/zed/gitea-comments.json."); panel.comments.clear(); }
                    Ok(history) => {
                        panel.status = format!("{} comments · {} · all revisions", history.comments.len(), if panel.all_files { "repository" } else { &history.path });
                        panel.comments = history.comments;
                        let matches_disk = editor.read(cx).buffer().read(cx).snapshot(cx).text() == history.content;
                        if panel.inline && matches_disk {
                            let comments: Vec<_> = panel.comments.iter().filter(|c| c.inline && c.start_line > 0).cloned().collect();
                            panel.blocks = editor.update(cx, |editor, cx| {
                                let snapshot = editor.buffer().read(cx).snapshot(cx);
                                let blocks = comments.into_iter().map(|comment| {
                                    let anchor = snapshot.anchor_before(Point::new(comment.end_line.saturating_sub(1), 0));
                                    let preview: String = comment.body.chars().take(1000).collect();
                                    let text = format!("{} · {}\n{}{}", comment.author, &comment.commit_sha[..10.min(comment.commit_sha.len())], preview, if comment.body.chars().count() > 1000 { "\nFull comment in history panel." } else { "" });
                                    let height = 2 + text.lines().map(|line| line.chars().count().div_ceil(40).max(1) as u32).sum::<u32>();
                                    BlockProperties {
                                        placement: BlockPlacement::Below(anchor), height: Some(height), style: BlockStyle::Flex, priority: 0,
                                        render: Arc::new(move |_| div().w(px(640.)).max_w_full().p_2().child(text.clone()).into_any_element()),
                                    }
                                });
                                editor.insert_blocks(blocks, None, cx)
                            });
                            panel.editor_subscription = Some(cx.subscribe(&editor, |panel, _, event, cx| {
                                if matches!(event, EditorEvent::BufferEdited) {
                                    panel.clear_blocks(cx);
                                    panel.status = "Code edited — inline comments hidden. Refresh to compare again.".into();
                                    cx.notify();
                                }
                            }));
                        } else if panel.inline && !matches_disk {
                            panel.status.push_str(" · unsaved edits: inline comments hidden");
                        }
                    }
                }
                cx.notify();
            }).ok();
        }).detach();
        cx.notify();
    }
}

impl Focusable for CommentPanel {
    fn focus_handle(&self, _: &App) -> FocusHandle {
        self.focus.clone()
    }
}
impl EventEmitter<PanelEvent> for CommentPanel {}
impl Panel for CommentPanel {
    fn persistent_name() -> &'static str {
        "GiteaCommentHistory"
    }
    fn panel_key() -> &'static str {
        "GiteaCommentHistory"
    }
    fn position(&self, _: &Window, _: &App) -> DockPosition {
        self.position
    }
    fn position_is_valid(&self, position: DockPosition) -> bool {
        matches!(position, DockPosition::Left | DockPosition::Right)
    }
    fn set_position(&mut self, position: DockPosition, _: &mut Window, cx: &mut Context<Self>) {
        self.position = position;
        cx.notify();
    }
    fn default_size(&self, _: &Window, _: &App) -> Pixels {
        px(400.)
    }
    fn icon(&self, _: &Window, _: &App) -> Option<IconName> {
        Some(IconName::Chat)
    }
    fn icon_tooltip(&self, _: &Window, _: &App) -> Option<&'static str> {
        Some("Gitea Comment History")
    }
    fn toggle_action(&self) -> Box<dyn gpui::Action> {
        Box::new(ToggleHistory)
    }
    fn activation_priority(&self) -> u32 {
        20
    }
}
impl Render for CommentPanel {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let query = self.search.read(cx).text(cx).to_lowercase();
        v_flex()
            .id("gitea-comment-history")
            .track_focus(&self.focus)
            .size_full()
            .p_2()
            .gap_2()
            .child(Label::new("Gitea Comment History"))
            .child(
                h_flex()
                    .gap_1()
                    .child(
                        Button::new("refresh-comments", "Refresh")
                            .disabled(self.loading)
                            .on_click(
                                cx.listener(|panel, _, window, cx| panel.refresh(window, cx)),
                            ),
                    )
                    .child(
                        Button::new(
                            "comments-scope",
                            if self.all_files {
                                "Repository"
                            } else {
                                "Current file"
                            },
                        )
                        .disabled(self.loading)
                        .on_click(cx.listener(|panel, _, window, cx| {
                            panel.all_files = !panel.all_files;
                            panel.refresh(window, cx);
                        })),
                    )
                    .child(
                        Button::new(
                            "inline-comments",
                            if self.inline {
                                "Inline: on"
                            } else {
                                "Inline: off"
                            },
                        )
                        .on_click(cx.listener(|panel, _, window, cx| {
                            panel.inline = !panel.inline;
                            if panel.inline {
                                panel.refresh(window, cx);
                            } else {
                                panel.clear_blocks(cx);
                            }
                            cx.notify();
                        })),
                    ),
            )
            .child(self.search.clone())
            .child(Label::new(self.status.clone()).size(LabelSize::Small))
            .child(
                v_flex()
                    .id("comment-history-list")
                    .overflow_y_scroll()
                    .gap_2()
                    .children(
                        self.comments
                            .iter()
                            .filter(|comment| {
                                format!("{} {} {}", comment.author, comment.path, comment.body)
                                    .to_lowercase()
                                    .contains(&query)
                            })
                            .map(|comment| {
                                let url = comment.url.clone();
                                v_flex()
                                    .p_2()
                                    .gap_1()
                                    .border_1()
                                    .border_color(cx.theme().colors().border)
                                    .child(
                                        Button::new(
                                            ("comment", comment.id),
                                            format!(
                                                "{} · {}:{}–{}",
                                                comment.author,
                                                comment.path,
                                                comment.start_line,
                                                comment.end_line
                                            ),
                                        )
                                        .on_click(move |_, _, cx| cx.open_url(&url)),
                                    )
                                    .child(
                                        Label::new(if comment.inline {
                                            "Matches current file"
                                        } else {
                                            "Historical source — open original"
                                        })
                                        .size(LabelSize::Small),
                                    )
                                    .child(div().child(comment.body.clone()))
                            }),
                    ),
            )
    }
}
