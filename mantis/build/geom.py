import re
TOK = re.compile(r"[MLHVCZmlhvcz]|-?\d*\.?\d+(?:e-?\d+)?")
def mat(t):
    m = re.search(r"matrix\(([^)]*)\)", t or "")
    if not m: return (1, 0, 0, 1, 0, 0)
    return tuple(float(x) for x in re.split(r"[ ,]+", m.group(1).strip()))
def points(d, m):
    toks = TOK.findall(d); pts = []; cmd = None; i = 0; cx = cy = 0.0; curve = False
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t; i += 1
            if cmd in "Cc": curve = True
            continue
        if cmd in ("M", "L"):
            cx, cy = float(toks[i]), float(toks[i+1]); i += 2
        elif cmd == "H": cx = float(toks[i]); i += 1
        elif cmd == "V": cy = float(toks[i]); i += 1
        elif cmd == "C":
            cx, cy = float(toks[i+4]), float(toks[i+5]); i += 6
        else:
            i += 1; continue
        pts.append((m[0]*cx + m[2]*cy + m[4], m[1]*cx + m[3]*cy + m[5]))
    return pts, curve
def attr(el, name):
    m = re.search(r'\s' + name + r'="([^"]*)"', el)
    return m.group(1) if m else None
