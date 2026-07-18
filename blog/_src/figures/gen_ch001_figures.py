#!/usr/bin/env python3
"""Hand-converted SVG renderings of the two TikZ figures in math
chapter 001 (division block, 756 factor trees). Coordinates mirror the
TikZ sources; colors follow the math repo palette."""

from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "posts" / "integers-divisibility-and-proof" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#244A73"
TEAL = "#1C6B65"
GOLD = "#9A6B16"
INK = "#333333"
SERIF = "Georgia, 'Times New Roman', serif"

# ------------------------------------------------------------------
# Figure 1: division block  (fig:ch001-division-block)
# ------------------------------------------------------------------

def fig_division_block():
    UX, UY = 95.0, 65.0            # px per tikz unit
    def X(x): return (x + 0.6) * UX
    def Y(y): return (1.6 - y) * UY

    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -16 850 176" '
             'width="850" height="176" font-family="%s" font-size="15">' % SERIF)

    # axis
    ax_y = Y(0)
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
             % (X(-0.4), ax_y, X(6.4) - 10, ax_y, INK))
    p.append('<path d="M %.1f %.1f l -11 -4.5 v 9 z" fill="%s"/>' % (X(6.4), ax_y, INK))

    labels = ["5q", "5q+1", "5q+2", "5q+3", "5q+4", "5(q+1)"]
    for i, lab in enumerate(labels):
        x = X(i)
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (x, ax_y - 7, x, ax_y + 7, INK))
        p.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-style="italic" fill="%s">%s</text>'
                 % (x, ax_y + 26, INK, lab))

    # block line
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
             % (X(0), Y(0.85), X(5), Y(0.85), BLUE))

    # highlighted point a = 5q+3
    p.append('<circle cx="%.1f" cy="%.1f" r="4.2" fill="%s"/>' % (X(3), ax_y, GOLD))
    p.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-style="italic" fill="%s">a = 5q+3</text>'
             % (X(3), Y(0.28), GOLD))

    # brace for r = 3
    x0, x1, yb = X(0), X(3), Y(1.15)
    yt, tip = yb - 8, yb - 15
    xm = (x0 + x1) / 2
    p.append('<path d="M %.1f %.1f Q %.1f %.1f %.1f %.1f L %.1f %.1f Q %.1f %.1f %.1f %.1f '
             'Q %.1f %.1f %.1f %.1f L %.1f %.1f Q %.1f %.1f %.1f %.1f" '
             'fill="none" stroke="%s" stroke-width="1.6"/>'
             % (x0, yb, x0, yt, x0 + 9, yt,
                xm - 9, yt, xm, yt, xm, tip,
                xm, yt, xm + 9, yt,
                x1 - 9, yt, x1, yt, x1, yb, TEAL))
    p.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-style="italic" fill="%s">r = 3</text>'
             % (xm, tip - 8, TEAL))

    # side note
    p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="14.5">'
             '<tspan font-style="italic">0 ≤ r &lt; 5</tspan> selects</text>'
             % (X(5.45), Y(1.12), INK))
    p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="14.5">one point in the block</text>'
             % (X(5.45), Y(0.8), INK))

    p.append("</svg>")
    (OUT / "ch001-division-block.svg").write_text("\n".join(p))


# ------------------------------------------------------------------
# Figure 2: factor trees for 756  (fig:ch001-756-factor-trees)
# ------------------------------------------------------------------

def fig_factor_trees():
    U = 55.0
    def X(x): return (x + 6.25) * U
    def Y(y): return (0.95 - y) * U

    def box_w(text):
        return {1: 26, 2: 34, 3: 44}[len(text)]

    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 290" '
             'width="720" height="290" font-family="%s" font-size="14.5">' % SERIF)

    def tree(shift, title, nodes, edges, note, note_pos):
        # edges first so node boxes cover the line ends
        for a, b in edges:
            xa, ya = nodes[a][1] + shift, nodes[a][2]
            xb, yb = nodes[b][1] + shift, nodes[b][2]
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.1"/>'
                     % (X(xa), Y(ya), X(xb), Y(yb), BLUE))
        for label, x, y, kind in nodes.values():
            cx, cy = X(x + shift), Y(y)
            w, h = box_w(label), 26
            stroke, fill = (TEAL, "#ebf3f2") if kind == "p" else (BLUE, "#f7f9fc")
            weight = ' font-weight="bold"' if kind == "p" else ""
            p.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="3" '
                     'fill="%s" stroke="%s" stroke-width="1.2"/>'
                     % (cx - w / 2, cy - h / 2, w, h, fill, stroke))
            p.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="%s"%s>%s</text>'
                     % (cx, cy + 5, INK, weight, label))
        p.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-weight="bold" '
                 'fill="%s" font-size="14">%s</text>'
                 % (X(shift), Y(0.62), BLUE, title))
        p.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="%s" font-size="12.5" '
                 'font-style="italic">%s</text>'
                 % (X(note_pos[0] + shift), Y(note_pos[1]), TEAL, note))

    left_nodes = {
        "l756": ("756", 0, 0, "c"), "l27": ("27", -1.4, -0.8, "c"),
        "l28": ("28", 1.4, -0.8, "c"), "l3a": ("3", -2.0, -1.6, "p"),
        "l9": ("9", -0.8, -1.6, "c"), "l4": ("4", 0.8, -1.6, "c"),
        "l7": ("7", 2.0, -1.6, "p"), "l3b": ("3", -1.15, -2.4, "p"),
        "l3c": ("3", -0.45, -2.4, "p"), "l2a": ("2", 0.45, -2.4, "p"),
        "l2b": ("2", 1.15, -2.4, "p"),
    }
    left_edges = [("l756", "l27"), ("l756", "l28"), ("l27", "l3a"), ("l27", "l9"),
                  ("l9", "l3b"), ("l9", "l3c"), ("l28", "l4"), ("l28", "l7"),
                  ("l4", "l2a"), ("l4", "l2b")]
    tree(-3.8, "first split 27·28", left_nodes, left_edges,
         "prime leaves: 2, 2, 3, 3, 3, 7", (0, -3.05))

    right_nodes = {
        "r756": ("756", 0, 0, "c"), "r3a": ("3", -1.8, -0.8, "p"),
        "r252": ("252", 0.8, -0.8, "c"), "r7": ("7", 0.1, -1.6, "p"),
        "r36": ("36", 1.5, -1.6, "c"), "r4": ("4", 0.9, -2.4, "c"),
        "r9": ("9", 2.1, -2.4, "c"), "r2a": ("2", 0.55, -3.2, "p"),
        "r2b": ("2", 1.25, -3.2, "p"), "r3b": ("3", 1.75, -3.2, "p"),
        "r3c": ("3", 2.45, -3.2, "p"),
    }
    right_edges = [("r756", "r3a"), ("r756", "r252"), ("r252", "r7"), ("r252", "r36"),
                   ("r36", "r4"), ("r36", "r9"), ("r4", "r2a"), ("r4", "r2b"),
                   ("r9", "r3b"), ("r9", "r3c")]
    tree(3.8, "first split 3·252", right_nodes, right_edges,
         "prime leaves: 2, 2, 3, 3, 3, 7", (0.35, -3.85))

    p.append("</svg>")
    (OUT / "ch001-756-factor-trees.svg").write_text("\n".join(p))


fig_division_block()
fig_factor_trees()
print("wrote SVGs to", OUT)
