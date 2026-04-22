use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationRecipe {
    pub name: String,
    pub from: String,
    pub to: String,
    pub autowrap_required: bool,
    pub intent_audit_required: bool,
}

pub fn render_recipe(name: &str, from: &str, to: &str) -> String {
    match name {
        "batch-extract" => format!(
            "watch {} and extract archives into {} with autowrap + intent validation receipts",
            from, to
        ),
        "dropbox" => format!(
            "consume incoming folder {} and emit processed files to {} with autowrap + intent validation receipts",
            from, to
        ),
        _ => format!("unknown recipe: {} (from {} to {})", name, from, to),
    }
}

pub fn recipe_contract(name: &str, from: &str, to: &str) -> AutomationRecipe {
    AutomationRecipe {
        name: name.into(),
        from: from.into(),
        to: to.into(),
        autowrap_required: true,
        intent_audit_required: true,
    }
}
