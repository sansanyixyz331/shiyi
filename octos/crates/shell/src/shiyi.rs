//! 拾意's own host service: its agent's `shiyi.*` tools (ADR 0004 §4, §7).
//!
//! | method | args | answer |
//! |---|---|---|
//! | `shiyi.repin` | `{card_id, title, when?, where?, as_of?, notify?}` | `{card_id, replaced, expires_at}` once the card is on the glance screen ([`repin`]) |
//!
//! **What it is for.** 拾意's card is where the person reads a sentence they
//! asked 拾意 to keep; the card's own chat (card_chat.rs) is where they talk
//! back. Without a tool the assistant can only talk. `shiyi.repin` gives it
//! one arm: the newest text becomes the card. The card is republished under
//! the **same `card_id`**, and cards are keyed by `(app, card_id)`
//! (glance.rs), so the card the person is looking at is **replaced in
//! place**, never duplicated.
//!
//! **Whose card.** The card's exact L0 source is taken from the live card
//! ([`crate::glance::card`]) and only its `rec` data changes: what the model
//! rewrites is text, never card code, and the edited card is byte-for-byte
//! the app's own card. The publication goes out through
//! [`crate::glance::publish_for`] as `os.shiyi`, the same road official
//! Calendar's `calendar.notify` takes — the host checks admission, this
//! service only fills in the values.
//!
//! **Who answers.** 拾意 is a system app, so its own namespace is its own
//! service (script_apps.rs): registering this one means the generic notice
//! service (glance_notice.rs) no longer stands in for `shiyi`, so this
//! service answers `shiyi.notify` too, with the shell's notice card.
use serde_json::{json, Value};

/// 拾意's app id and tool namespace.
pub const APP: &str = "os.shiyi";
const FAMILY: &str = "shiyi";
/// How long a repinned card lives, in seconds (seven days, as the app pins).
const EXPIRES_S: u64 = 604800;

/// `text` cut to `max` characters, an ellipsis last when it was longer.
fn clip(text: &str, max: usize) -> String {
    if text.chars().count() <= max {
        return text.to_string();
    }
    let mut out: String = text.chars().take(max.saturating_sub(1)).collect();
    out.push('\u{2026}');
    out
}

/// One of the card's two labelled lines: the caller's value, or the live
/// card's current line, or the app's own "nothing said" line — never empty,
/// so the card states one thing or another, never a blank field.
fn line(args: &Value, key: &str, prefix: &str, fallback: &str, old: Option<&Value>) -> String {
    let given = args.get(key).and_then(Value::as_str).map(str::trim).unwrap_or("");
    if !given.is_empty() {
        // The caller may repeat the label ("时间 · 下周四") or give the bare
        // value ("下周四"); keep exactly one label.
        let bare = given.strip_prefix(prefix).map(str::trim).unwrap_or(given);
        return format!("{prefix}{bare}");
    }
    if let Some(text) = old.and_then(Value::as_str).map(str::trim).filter(|t| !t.is_empty()) {
        return text.to_string();
    }
    fallback.to_string()
}

fn field<'a>(args: &'a Value, key: &str) -> &'a str {
    args.get(key).and_then(Value::as_str).unwrap_or("").trim()
}

/// `shiyi.repin`: replace 拾意 card `card_id` in place with the caller's
/// text. The live card must exist and be an L0 card: its source is reused
/// exactly, so what changes is only the data. Refused (with a reason the
/// model can act on) when the card is gone, is not 拾意's, or the text is
/// blank or too long.
pub fn repin(app: &str, args: &Value) -> Result<Value, String> {
    if app != APP {
        return Err(format!("{FAMILY}.repin serves {APP} only"));
    }
    let card_id = field(args, "card_id");
    if card_id.is_empty() {
        return Err("shiyi.repin needs the card_id of the card to change".into());
    }
    let key = format!("{APP}/{card_id}");
    let existing = crate::glance::card(&key)
        .ok_or_else(|| format!("There is no live 拾意 card with card_id {card_id} on the glance screen."))?;
    let l0 = existing.l0.as_ref().ok_or("That 拾意 card is not an L0 card, so it cannot be repinned.")?;
    // The model rewrites values, never the card: its exact source comes back
    // out unchanged.
    let source = l0.source.clone();
    let old = l0.data.get("rec");
    let title = field(args, "title");
    if title.is_empty() || title.chars().count() > crate::glance::TITLE_MAX {
        return Err(format!("Provide a title of 1 to {} characters.", crate::glance::TITLE_MAX));
    }
    let subtitle = line(args, "when", "\u{65f6}\u{95f4} \u{00b7} ", "\u{65f6}\u{95f4} \u{00b7} \u{8fd9}\u{53e5}\u{8bdd}\u{91cc}\u{6ca1}\u{63d0}", old.and_then(|r| r.get("subtitle")));
    let summary = line(args, "where", "\u{5730}\u{70b9} \u{00b7} ", "\u{5730}\u{70b9} \u{00b7} \u{8fd9}\u{53e5}\u{8bdd}\u{91cc}\u{6ca1}\u{63d0}", old.and_then(|r| r.get("summary")));
    let as_of = field(args, "as_of");
    let as_of = if as_of.is_empty() {
        old.and_then(|r| r.get("as_of")).and_then(Value::as_str).unwrap_or("").to_string()
    } else {
        as_of.to_string()
    };
    let notify = args.get("notify").and_then(Value::as_bool).unwrap_or(false);
    let publish = json!({
        "card_id": card_id,
        "title": clip(&format!("\u{62fe}\u{610f} \u{00b7} {title}"), crate::glance::TITLE_MAX),
        "source": source,
        "data": {"rec": {"title": title, "subtitle": subtitle, "summary": summary, "as_of": as_of}},
        "priority": existing.priority,
        "open": {"app": APP},
        "notify": notify,
        "expires": EXPIRES_S,
    });
    crate::glance::publish_for(APP, &publish)
}

/// 拾意's own host service: it answers `shiyi.repin` and `shiyi.notify`
/// (the shell's notice card) for 拾意 alone.
pub struct ShiyiService;

impl octosense_appstore::services::HostService for ShiyiService {
    fn family(&self) -> &'static str {
        FAMILY
    }
    fn call(&mut self, call: octosense_appstore::services::ServiceCall, reply: octosense_appstore::services::Replier, _host: &mut dyn octosense_appstore::services::ServiceHost) {
        if call.app_id != APP {
            return reply.send(Err(format!("{FAMILY} serves {APP} only")));
        }
        match call.method() {
            "repin" => reply.send(repin(&call.app_id, &call.args)),
            "notify" => reply.send(crate::glance_notice::notify(&call.app_id, &call.args)),
            other => reply.send(Err(format!("{FAMILY} has no method {other:?}"))),
        }
    }
}

/// Register [`ShiyiService`] for 拾意, before the generic notice service
/// ([`crate::glance_notice::serve_system_apps`]): 拾意's own name is taken,
/// so the notice service never stands in for it.
pub fn register() {
    octosense_appstore::services::register_host_service(Box::new(ShiyiService));
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The caller's values win, a label already in them is not doubled, and
    /// a missing one falls back to the live card's line or the app's own.
    #[test]
    fn a_line_keeps_exactly_one_label() {
        let old = json!("\u{65f6}\u{95f4} \u{00b7} \u{660e}\u{5929}");
        assert_eq!(line(&json!({"when": "\u{4e0b}\u{5468}\u{56db}"}), "when", "\u{65f6}\u{95f4} \u{00b7} ", "fallback", Some(&old)), "\u{65f6}\u{95f4} \u{00b7} \u{4e0b}\u{5468}\u{56db}");
        assert_eq!(line(&json!({"when": "\u{65f6}\u{95f4} \u{00b7} \u{4e0b}\u{5468}\u{56db}"}), "when", "\u{65f6}\u{95f4} \u{00b7} ", "fallback", Some(&old)), "\u{65f6}\u{95f4} \u{00b7} \u{4e0b}\u{5468}\u{56db}");
        assert_eq!(line(&json!({}), "when", "\u{65f6}\u{95f4} \u{00b7} ", "fallback", Some(&old)), "\u{65f6}\u{95f4} \u{00b7} \u{660e}\u{5929}");
        assert_eq!(line(&json!({}), "when", "\u{65f6}\u{95f4} \u{00b7} ", "fallback", None), "fallback");
    }

    /// A repin the person's card cannot satisfy is refused with a reason,
    /// before anything is published.
    #[test]
    fn a_repin_without_a_card_is_refused() {
        assert!(repin("os.mail", &json!({"card_id": "x", "title": "y"})).unwrap_err().contains("serves os.shiyi only"));
        assert!(repin(APP, &json!({"title": "y"})).unwrap_err().contains("card_id"));
        assert!(repin(APP, &json!({"card_id": "shiyi-p9", "title": "y"})).unwrap_err().contains("no live"));
    }
}
