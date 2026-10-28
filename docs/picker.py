# Draws docs/picker.svg: the repo-tab picker with made-up open source repos, in
# the style of cockpit's screenshots (Vesper colours, macOS window, embedded
# FiraCode Nerd Font Mono subset so it renders the same everywhere).
#
#   uv run --with fonttools docs/picker.py [path/to/FiraCodeNerdFontMono-Regular.ttf]
import base64
import io
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

TEXT, DIM, MUTED, BRIGHT = "#d2d2d2", "#707070", "#9A9AA2", "#F2F2F2"
ORANGE, TEAL, RED, LINE, BG = "#ffc799", "#99ffe4", "#ff8080", "#2c2c30", "#101010"

COLS, ROWS, LEFT = 100, 18, 50
CW, LH, PAD, TOP = 8.4, 20.3, 34.8, 70.0

QUERY = "vim"
TOTAL = 42
# Best match last: fzf's default layout lists from the prompt upwards.
MATCHES = [
    "echasnovski/mini.nvim",
    "nvim-treesitter/nvim-treesitter",
    "nvim-lua/plenary.nvim",
    "junegunn/fzf.vim",
    "tpope/vim-fugitive",
    "LazyVim/LazyVim",
    "folke/lazy.nvim",
    "vim/vim",
    "neovim/neovim",
]
LOG = [
    ("e41a9c2", "(HEAD -> master)", "fix(lsp): empty hover"),
    ("7bd03f5", "", "feat(treesitter): async parsing"),
    ("c2f8e19", "", "docs: clarify 'winborder' default"),
    ("19ab6d0", "", "refactor(api): drop deprecated fns"),
    ("a5e7c34", "", "test: flaky terminal resize spec"),
    ("3f0d2b8", "", "fix(ui): redraw after :colorscheme"),
    ("8c61e4a", "", "build(deps): bump luajit"),
    ("d94b07f", "", "feat(diagnostic): virtual lines"),
    ("2e7fa51", "", "vim-patch:9.1.0812: completion"),
    ("b03c8d6", "", "ci: cache dependencies on macOS"),
]


def fuzzy_positions(text, query):
    """Indexes fzf would highlight: the first left-to-right match of each query char."""
    out, i = set(), 0
    for ch in query:
        i = text.lower().find(ch, i)
        if i < 0:
            return set()
        out.add(i)
        i += 1
    # Prefer a contiguous match when there is one, as fzf's scoring does.
    j = text.lower().rfind(query)
    return set(range(j, j + len(query))) if j >= 0 else out


def build():
    rows = [[] for _ in range(ROWS)]  # runs of (col, text, fill, bold)
    bars = []  # (row, col, width) highlighted cells

    def put(r, c, text, fill=TEXT, bold=False):
        rows[r].append((c, text, fill, bold))

    # Left pane, bottom up: prompt, info, header, then the matches.
    put(ROWS - 1, 0, "repo › ", ORANGE)
    put(ROWS - 1, 7, QUERY, BRIGHT)
    bars.append((ROWS - 1, 7 + len(QUERY), 1, TEXT))
    count = f"  {len(MATCHES)}/{TOTAL} "
    put(ROWS - 2, 0, count, MUTED)
    put(ROWS - 2, len(count), "─" * (LEFT - len(count) - 1), LINE)
    put(ROWS - 3, 2, "Enter: open as a tab in the terminal workspace", DIM)
    for k, repo in enumerate(reversed(MATCHES)):
        r = ROWS - 4 - k
        current = k == 0
        if current:
            bars.append((r, 0, LEFT - 1, LINE))
            put(r, 0, "▌", ORANGE)
        hits = fuzzy_positions(repo, QUERY)
        for i, ch in enumerate(repo):
            fill = TEAL if i in hits else (BRIGHT if current else TEXT)
            put(r, 2 + i, ch, fill, bold=current)

    # Right pane: a rounded preview box with git status and the log.
    x, w = LEFT, COLS - LEFT
    put(0, x, "╭" + "─" * (w - 2) + "╮", LINE)
    put(ROWS - 1, x, "╰" + "─" * (w - 2) + "╯", LINE)
    for r in range(1, ROWS - 1):
        put(r, x, "│", LINE)
        put(r, x + w - 1, "│", LINE)
    c = x + 2
    put(1, c, "## ", TEXT)
    put(1, c + 3, "master", TEAL)
    put(1, c + 9, "...", TEXT)
    put(1, c + 12, "origin/master", RED)
    for k, (sha, refs, msg) in enumerate(LOG):
        r = 3 + k
        put(r, c, sha, ORANGE)
        room = w - 4 - len(sha) - 1
        if refs:
            put(r, c + 8, refs, TEAL)
            put(r, c + 9 + len(refs), msg[: room - len(refs) - 1], TEXT)
        else:
            put(r, c + 8, msg[:room], TEXT)
    return rows, bars


def merge(runs):
    """Join adjacent single-cell runs of the same style so the SVG stays small."""
    out = []
    for col, text, fill, bold in sorted(runs, key=lambda t: t[0]):
        if out and out[-1][2] == fill and out[-1][3] == bold and out[-1][0] + len(out[-1][1]) == col:
            out[-1] = (out[-1][0], out[-1][1] + text, fill, bold)
        else:
            out.append((col, text, fill, bold))
    return out


def font_face(path, chars, weight):
    opts = subset.Options()
    opts.layout_features = []
    opts.name_IDs = ["*"]
    font = TTFont(path)
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(chars))))
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'Cockpit Mono';src:url(data:font/ttf;base64,{data}) format('truetype');font-weight:{weight}}}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    regular = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Library/Fonts/FiraCodeNerdFontMono-Regular.ttf")
    bold = regular.with_name(regular.name.replace("Regular", "Bold"))
    rows, bars = build()
    width = round(PAD * 2 + COLS * CW)
    height = round(TOP - 15 + ROWS * LH + 28)

    body = []
    for r, c, n, fill in bars:
        y = TOP + r * LH - 15
        body.append(f'<rect x="{PAD + c * CW:.1f}" y="{y:.1f}" width="{n * CW:.1f}" height="{LH + 0.6:.1f}" fill="{fill}"/>')
    chars = {False: "", True: ""}
    for r, runs in enumerate(rows):
        y = TOP + r * LH
        for col, text, fill, b in merge(runs):
            chars[b] += text
            weight = ' font-weight="bold"' if b else ""
            body.append(
                f'<text x="{PAD + col * CW:.1f}" y="{y:.1f}" fill="{fill}"{weight} '
                f'textLength="{len(text) * CW:.1f}" lengthAdjust="spacingAndGlyphs">{esc(text)}</text>'
            )

    style = (
        font_face(regular, chars[False] + "herdr · repo-tab", "normal")
        + font_face(bold, chars[True] or "a", "bold")
        + " text{font-family:'Cockpit Mono',monospace;font-size:14px;white-space:pre}"
    )
    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<style>{style}</style>",
        f'<rect width="100%" height="100%" rx="12" fill="{BG}" stroke="#2C2C30"/>'
        '<circle cx="24" cy="21.0" r="6" fill="#FF5F57"/><circle cx="44" cy="21.0" r="6" fill="#FEBC2E"/>'
        '<circle cx="64" cy="21.0" r="6" fill="#28C840"/>',
        f'<text x="{width / 2:.0f}" y="25" text-anchor="middle" fill="{DIM}" font-size="12">herdr · repo-tab</text>',
        *body,
        "</svg>",
    ])
    out = Path(__file__).with_name("picker.svg")
    out.write_text(svg + "\n")
    print(f"wrote {out} ({len(svg) // 1024} KB, {width}x{height})")


if __name__ == "__main__":
    main()
