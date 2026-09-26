import re

# The reference host resolves copy by the `en` slot for this locale, so the
# Chinese text is placed in that slot. The `zh` slot keeps the same text; the
# English wording of each string is preserved in the surrounding comments of
# page.card where it still reads naturally.
p = r"C:/gosim_agentic/05_app/shiyi/bundle/page.card"
s = open(p, encoding="utf-8").read()
pat = re.compile(r'en: "([^"]*)", zh: "([^"]*)"')


def swap(m):
    z = m.group(2)
    return 'en: "%s", zh: "%s"' % (z, z)


s2, n = pat.subn(swap, s)
open(p, "w", encoding="utf-8").write(s2)
print("替换行数:", n)
