#[derive(Debug, Clone)]
pub struct LlvmPlan {
    pub status: &'static str,
    pub next_step: &'static str,
}

pub fn plan() -> LlvmPlan {
    LlvmPlan {
        status: "stub",
        next_step: "add heavier optimization and offline object-generation lane after the baseline JIT path exists",
    }
}
