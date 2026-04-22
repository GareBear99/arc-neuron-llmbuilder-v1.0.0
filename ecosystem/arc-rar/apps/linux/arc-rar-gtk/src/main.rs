use gtk::prelude::*;
use gtk::{Application, ApplicationWindow, Box as GtkBox, Button, Label, Orientation, ScrolledWindow, TextView};
use std::process::Command;

fn run_arc_rar(args: &[&str]) -> String {
    match Command::new("arc-rar").args(args).output() {
        Ok(output) => {
            let mut text = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr);
            if !stderr.trim().is_empty() {
                text.push_str("\n");
                text.push_str(&stderr);
            }
            text
        }
        Err(err) => format!("{{\"ok\":false,\"error\":\"{}\"}}", err),
    }
}

fn main() {
    let app = Application::builder().application_id("com.arcrar.gtk").build();
    app.connect_activate(|app| {
        let window = ApplicationWindow::builder()
            .application(app)
            .title("Arc-RAR")
            .default_width(800)
            .default_height(520)
            .build();

        let root = GtkBox::new(Orientation::Vertical, 8);
        root.set_margin_top(12);
        root.set_margin_bottom(12);
        root.set_margin_start(12);
        root.set_margin_end(12);

        let title = Label::new(Some("Arc-RAR"));
        title.add_css_class("title-1");
        root.append(&title);

        let buttons = GtkBox::new(Orientation::Horizontal, 8);
        let open = Button::with_label("Open Sample");
        let status = Button::with_label("Refresh Status");
        buttons.append(&open);
        buttons.append(&status);
        root.append(&buttons);

        let text = TextView::new();
        text.set_editable(false);
        let scroller = ScrolledWindow::builder().child(&text).vexpand(true).hexpand(true).build();
        root.append(&scroller);

        let text_clone = text.clone();
        open.connect_clicked(move |_| {
            let buf = text_clone.buffer();
            buf.set_text(&run_arc_rar(&["gui", "open", "/tmp/demo.rar", "--json"]));
        });

        let text_clone = text.clone();
        status.connect_clicked(move |_| {
            let buf = text_clone.buffer();
            buf.set_text(&run_arc_rar(&["gui", "status", "--json"]));
        });

        window.set_child(Some(&root));
        window.present();
    });
    app.run();
}
