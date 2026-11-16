THEMES = {
    "greenit": ("#7BD88F", "#C9E4CE", "#9BEDAF", "#63C9A8", "#78997F"),
    "mono": ("#E6E6E6", "#F0F0F0", "#A0A0A0", "#BDBDBD", "#737373"),
    "ocean": ("#00B4FF", "#BCEBFF", "#51E0FF", "#0096FE", "#4E6B7B"),
    "ember": ("#FF7B28", "#FFB18A", "#F55A3C", "#FF9C58", "#7A3A1C"),
    "sakura": ("#FFB4DC", "#FFDCEF", "#FDA4CD", "#DD62A5", "#8E5A6C"),
    "midnight": ("#96B4FF", "#C7D3FF", "#B09BFF", "#6A78FF", "#454A63"),
    "nord": ("#88C0D0", "#ECEFF4", "#81A1C1", "#8FBCBB", "#4C566A"),
    "catppuccin": ("#89B4FA", "#CDD6F4", "#CBA6F7", "#74C7EC", "#585B70"),
    "tokyonight": ("#7AA2F7", "#C0CAF5", "#BB9AF7", "#7DCFFF", "#565F89"),
    "dracula": ("#BD93F9", "#F8F8F2", "#FF79C6", "#8BE9FD", "#6272A4"),
    "gruvbox": ("#FABD2F", "#EBDBB2", "#83A598", "#B8BB26", "#665C54"),
    "solarized": ("#268BD2", "#839496", "#2AA198", "#B58900", "#586E75"),
    "cyberpunk": ("#00FFFF", "#FFE066", "#FF2BD6", "#00FFFF", "#46305F"),
    "matrix": ("#00FF43", "#B4FFB4", "#00C853", "#69FF8A", "#003510"),
    "sunset": ("#FF9A4D", "#FFDFC2", "#FFD166", "#EF476F", "#623B3B"),
    "aurora": ("#B48CFF", "#E8DFF8", "#9E7DF2", "#64D2FF", "#48345F"),
    "neon": ("#00FFFF", "#E6FFFF", "#FF00FF", "#FFFF00", "#3E2063"),
    "retro": ("#FFBF00", "#FFE89A", "#FFB000", "#FF7B00", "#594400"),
}

def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

def get_theme(name):
    return THEMES.get(name, THEMES["greenit"])

def theme_names():
    return list(THEMES)

def color(value, text, bold=False):
    r, g, b = rgb(value)
    prefix = "\033[1;38;2" if bold else "\033[38;2"
    return f"{prefix};{r};{g};{b}m{text}\033[0m"
