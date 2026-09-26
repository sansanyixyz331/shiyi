#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the first screen into the bundle, and only the bundle.

Cards live in cards/ (five screens, one directory each, sharing bundle/kit).
The Hub takes one bundle and the bundle carries one page.card, so the screen
the app opens on — READ — is the one that goes in. This script keeps that
copy honest:

  cards/shiyi-01-read/page.card      -> bundle/page.card
  cards/shiyi-01-read/page.data.json -> bundle/page.data.json
  cards/*/screenshots/01.png         -> bundle/screenshots/<n>-<name>.png

It also refreshes the listing's screenshot list and the release version, so
the published metadata always matches the screens that were actually
rendered. Run render_cards.py first: a screen with no capture is a failure,
not something to paper over.

Usage:
    python build/sync_bundle.py [--version 0.2.0]
"""

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "bundle")
CARDS = os.path.join(ROOT, "cards")

MAIN = "shiyi-01-read"
SCREENS = [
    ("shiyi-01-read", "01-read"),
    ("shiyi-02-ask", "02-ask"),
    ("shiyi-03-plan", "03-plan"),
    ("shiyi-04-memo", "04-memo"),
    ("shiyi-05-done", "05-done"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="0.2.0")
    args = ap.parse_args()

    # 1. The opening screen is the bundle's card.
    for name in ("page.card", "page.data.json"):
        src = os.path.join(CARDS, MAIN, name)
        if not os.path.isfile(src):
            sys.exit("missing %s" % src)
        shutil.copy2(src, os.path.join(BUNDLE, name))
        print("card   ", name)

    # 2. Every screen's real capture, in listing order.
    shots = os.path.join(BUNDLE, "screenshots")
    if os.path.isdir(shots):
        shutil.rmtree(shots)
    os.makedirs(shots)
    names = []
    for screen, label in SCREENS:
        src = os.path.join(CARDS, screen, "screenshots", "01.png")
        if not os.path.isfile(src):
            sys.exit("no capture for %s — run render_cards.py first" % screen)
        dst = os.path.join(shots, label + ".png")
        shutil.copy2(src, dst)
        names.append("screenshots/" + label + ".png")
        print("shot   ", label + ".png")

    # 3. Metadata follows the screens, never the other way round.
    lp = os.path.join(BUNDLE, "listing.json")
    listing = json.load(open(lp, encoding="utf-8"))
    listing["screenshots"] = names
    listing["release_notes"] = (
        "%s — five screens (read, ask, plan, remember, done), each one a "
        "hand-written L0 card rendered through the reference host." % args.version
    )
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(listing, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("listing", "screenshots=%d" % len(names))

    mp = os.path.join(BUNDLE, "manifest.json")
    manifest = json.load(open(mp, encoding="utf-8"))
    manifest["version"] = args.version
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print("manifest", "version=%s" % args.version)
    print("\nbundle is current. Now: hub stamp, hub check, hub scan.")


if __name__ == "__main__":
    main()
