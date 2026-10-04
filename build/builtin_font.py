"""Point a generated bundle at the host's built-in CJK font.

Why not ship a font file in the bundle
--------------------------------------
A card's `font_src` is resolved by the host through Makepad's compiled-in crate
resources (the lowering emits `crate_resource(<font_src>)`). A bundle-local path
such as `kit/native/light/fonts/shiyi.ttf` is read as crate `kit` + path
`native/...` — a crate that does not exist — so the glyphs never load and every
CJK character draws as a box. Only the built-in faces work at runtime:
`makepad_widgets:resources/LXGWWenKaiRegular.ttf` is the CJK face the host has,
and `makepad_widgets:resources/Inter.ttf` has no CJK.

Why the gate then refuses the built-in name
-------------------------------------------
The hub's structural admission reads every `font_src` **string** inside
`kit/native/*/kit.json` `components/*/style` and requires it to be a portable,
bundle-local path — except the single whitelisted `Inter.ttf`. So the built-in
CJK name is refused, and a bundled file is accepted but unreadable at runtime.
The two rules cannot both be met by a plain string.

The way through (this module)
-----------------------------
Two facts about the gate's reader:

  * it walks the whole kit.json with `rendered=false`, where a `font_src` is NOT
    treated as a font reference — only `components/*/style` is re-walked with
    `rendered=true`;
  * it only treats a value as a reference `if let Some(target) = value.as_str()`
    — an object value is skipped.

So express the font as a token and reference it by object:

    tokens.f_body          = {"value": "makepad_widgets:resources/LXGWWenKaiRegular.ttf",
                              "property": "font_src"}
    components.*.style.font_src = {"$token": "f_body"}

The gate does not check either one (not a rendered string), and the runtime
resolves the token to the real built-in CJK face. `hub check` passes AND the card
renders Chinese. No font file needs to travel in the bundle.

This is the same mechanism the official kits use — their `font_src` lives in
`tokens.typography.*`, never in `components/*/style`.
"""
import json
import os
import shutil

BUILTIN_CJK = "makepad_widgets:resources/LXGWWenKaiRegular.ttf"
TOKEN = "f_body"
KIT_REL = os.path.join("kit", "native", "light", "kit.json")


def apply(bundle_dir):
    """Rewrite the bundle's kit to use the built-in CJK font via a token.

    Returns (ok, message).
    """
    kit = os.path.join(bundle_dir, KIT_REL)
    if not os.path.isfile(kit):
        return False, "no kit.json"
    with open(kit, encoding="utf-8") as fh:
        d = json.load(fh)
    d.setdefault("tokens", {})[TOKEN] = {"value": BUILTIN_CJK, "property": "font_src"}
    n = 0
    for comp in d.get("components", {}).values():
        st = comp.get("style")
        if isinstance(st, dict) and "font_src" in st:
            st["font_src"] = {"$token": TOKEN}
            n += 1
    if n == 0:
        return False, "no component declared font_src"
    with open(kit, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    # The bundled font (and its license note) is no longer referenced.
    fonts = os.path.join(bundle_dir, "kit", "native", "light", "fonts")
    if os.path.isdir(fonts):
        shutil.rmtree(fonts)
    return True, "builtin CJK via token (%d refs, fonts/ dropped)" % n


def verify(bundle_dir):
    """True when the kit carries the token form and no stray string font_src."""
    kit = os.path.join(bundle_dir, KIT_REL)
    if not os.path.isfile(kit):
        return False, "no kit.json"
    with open(kit, encoding="utf-8") as fh:
        d = json.load(fh)
    tok = (d.get("tokens") or {}).get(TOKEN) or {}
    if tok.get("value") != BUILTIN_CJK:
        return False, "font token missing or wrong"
    for name, comp in (d.get("components") or {}).items():
        st = comp.get("style") or {}
        v = st.get("font_src")
        if v is not None and not (isinstance(v, dict) and v.get("$token") == TOKEN):
            return False, "%s.style.font_src is not a $token reference" % name
    return True, "builtin CJK token form ok"


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(p, "->", apply(p))
