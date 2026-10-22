//! Groove's persistent activity rail. Commands are resolved through GPUI so
//! workspace does not depend on the individual panel implementation crates.
use crate::Workspace;
use gpui::{Context, Div, Focusable, ParentElement, Stateful, Styled, Window, px, rems};
use ui::{IconButton, IconName, IconSize, Tooltip, prelude::*};

impl Workspace {
    pub(crate) fn render_activity_bar(&self, cx: &mut Context<Self>) -> Stateful<Div> {
        let colors = cx.theme().colors();
        let active_panels = [
            (&self.left_dock, "workspace::ToggleLeftDock"),
            (&self.right_dock, "workspace::ToggleRightDock"),
            (&self.bottom_dock, "workspace::ToggleBottomDock"),
        ]
        .into_iter()
        .filter_map(|(dock, toggle)| {
            let dock = dock.read(cx);
            dock.is_open()
                .then(|| {
                    dock.active_panel()
                        .map(|panel| (panel.persistent_name(), toggle))
                })
                .flatten()
        })
        .collect::<Vec<_>>();
        let focus = self.active_pane.read(cx).focus_handle(cx);
        let entries = [
            (
                "explorer",
                "Explorer",
                IconName::FileTree,
                "project_panel::ToggleFocus",
                "Project Panel",
            ),
            (
                "search",
                "Search Project",
                IconName::MagnifyingGlass,
                "pane::DeploySearch",
                "",
            ),
            (
                "git",
                "Source Control",
                IconName::GitBranch,
                "git_panel::ToggleFocus",
                "GitPanel",
            ),
            (
                "debug",
                "Run and Debug",
                IconName::Debug,
                "debug_panel::ToggleFocus",
                "DebugPanel",
            ),
            (
                "outline",
                "Outline",
                IconName::ListTree,
                "outline_panel::ToggleFocus",
                "Outline Panel",
            ),
            (
                "extensions",
                "Extensions",
                IconName::Blocks,
                "zed::Extensions",
                "",
            ),
            (
                "agent",
                "AI Assistant",
                IconName::ZedAssistant,
                "agent::ToggleFocus",
                "AgentPanel",
            ),
            (
                "terminal",
                "Terminal",
                IconName::Terminal,
                "terminal_panel::Toggle",
                "TerminalPanel",
            ),
        ];
        let buttons = entries
            .into_iter()
            .filter_map(|(id, label, icon, command, panel)| {
                let active_toggle = active_panels
                    .iter()
                    .find(|(name, _)| !panel.is_empty() && *name == panel)
                    .map(|(_, toggle)| *toggle);
                let action = cx
                    .build_action(active_toggle.unwrap_or(command), None)
                    .ok()?;
                let tooltip_action = action.boxed_clone();
                let focus = focus.clone();
                let selected = active_toggle.is_some();
                Some(
                    div()
                        .w(px(48.))
                        .h(px(46.))
                        .flex()
                        .items_center()
                        .justify_center()
                        .border_l_2()
                        .border_color(if selected {
                            colors.border_focused
                        } else {
                            colors.border_transparent
                        })
                        .child(
                            IconButton::new(id, icon)
                                .icon_size(IconSize::Custom(rems(1.5)))
                                .toggle_state(selected)
                                .aria_label(label)
                                .tooltip(move |_, cx| {
                                    Tooltip::for_action(label, &*tooltip_action, cx)
                                })
                                .on_click(move |_, window, cx| {
                                    window.focus(&focus, cx);
                                    window.dispatch_action(action.boxed_clone(), cx);
                                }),
                        ),
                )
            })
            .collect::<Vec<_>>();
        v_flex()
            .id("groove-activity-bar")
            .w(px(48.))
            .h_full()
            .flex_shrink_0()
            .bg(colors.surface_background)
            .border_r_1()
            .border_color(colors.border)
            .tab_group()
            .role(gpui::Role::Toolbar)
            .aria_label("Activity bar")
            .children(buttons)
            .child(div().flex_1())
            .child(
                div()
                    .w_full()
                    .h(px(46.))
                    .flex()
                    .items_center()
                    .justify_center()
                    .child(
                        IconButton::new("activity-settings", IconName::Settings)
                            .icon_size(IconSize::Custom(rems(1.5)))
                            .aria_label("Settings")
                            .tooltip(Tooltip::text("Settings"))
                            .on_click(|_, window: &mut Window, cx| {
                                if let Ok(action) = cx.build_action("zed::OpenSettings", None) {
                                    window.dispatch_action(action, cx);
                                }
                            }),
                    ),
            )
    }
}
