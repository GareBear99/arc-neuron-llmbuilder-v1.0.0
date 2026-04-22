#[derive(Debug, Clone)]
pub struct LinuxSurface {
    pub status: &'static str,
    pub initial_scope: Vec<&'static str>,
}

pub fn surface() -> LinuxSurface {
    LinuxSurface {
        status: "planning",
        initial_scope: vec![
            "argv/env layout",
            "cwd and file descriptors",
            "clock/time helpers",
            "minimal errno mapping",
        ],
    }
}
