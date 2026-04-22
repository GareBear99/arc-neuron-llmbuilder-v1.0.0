#[derive(Debug, Clone)]
pub struct ManagedPlan {
    pub status: &'static str,
    pub next_step: &'static str,
    pub candidate_formats: Vec<&'static str>,
}

pub fn plan() -> ManagedPlan {
    ManagedPlan {
        status: "stub",
        next_step: "prefer WASM first, then consider JVM and .NET adapters behind explicit runtime dependencies",
        candidate_formats: vec!["wasm", "jar", ".net"],
    }
}
