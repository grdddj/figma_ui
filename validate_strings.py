import json
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


@dataclass
class TooLong:
    model: str
    type: str
    key: str
    value: str
    lines: list[str]
    en: str
    lines_en: list[str]

    def __str__(self) -> str:
        return f"{self.key}: {self.value} --- {self.en} ({len(self.lines)} / {len(self.lines_en)})"

    def lines_str(self) -> str:
        return "\n".join(fill_lines_till_end(self.lines, self.type, self.model))

    def lines_en_str(self) -> str:
        return "\n".join(fill_lines_till_end(self.lines_en, self.type, self.model))


altcoins = [
    "binance",
    "cardano",
    # "ethereum",
    "eos",
    "monero",
    "nem",
    "stellar",
    "solana",
    "ripple",
    "tezos",
]


SCREEN_TEXT_WIDTHS = {"TT": 240 - 12, "TS3": 128}
MAX_BUTTON_WIDTH = {"TT": 162, "TS3": 88}

FONT_MAPPING = {
    "TT": {
        "title": "bold",
        "text": "normal",
        "bold": "bold",
        "button": "bold",
    },
    "TS3": {
        "title": "bold",
        "text": "normal",
        "bold": "bold",
        "button": "normal",
    },
}

DEVICES = ["TT", "TS3"]

FONTS_FILE = HERE / "font_widths.json"

FONTS: dict[str, dict[str, dict[str, int]]] = json.loads(FONTS_FILE.read_text())


def will_fit(text: str, type: str, device: str, lines: int) -> bool:
    if type == "button":
        return get_text_width(text, type, device) <= MAX_BUTTON_WIDTH[device]
    else:
        needed_lines = get_needed_lines(text, type, device)
        return needed_lines <= lines


def get_needed_lines(text: str, type: str, device: str) -> int:
    return len(assemble_lines(text, type, device))


def assemble_lines(text: str, type: str, device: str) -> list[str]:
    space_width = get_text_width(" ", type, device)
    words = text.replace("\r", "\n").split(" ")  # Splitting explicitly by space
    current_line_length = 0
    current_line = []
    assembled_lines: list[str] = []

    screen_width = SCREEN_TEXT_WIDTHS[device]

    for word in words:
        segments = word.split("\n")
        for i, segment in enumerate(segments):
            if segment:
                segment_width = get_text_width(segment, type, device)
                if current_line_length + segment_width <= screen_width:
                    current_line.append(segment)
                    current_line_length += segment_width + space_width
                else:
                    assembled_lines.append(" ".join(current_line))
                    current_line = [segment]
                    current_line_length = segment_width + space_width
            # If this is not the last segment, add a newline
            if i < len(segments) - 1:
                assembled_lines.append(" ".join(current_line))
                current_line = []
                current_line_length = 0

    if current_line:  # Append the last line if it's not empty
        assembled_lines.append(" ".join(current_line))

    return assembled_lines


def fill_lines_till_end(lines: list[str], type: str, device: str) -> list[str]:
    filled_lines: list[str] = []
    screen_width = SCREEN_TEXT_WIDTHS[device]

    for line in lines:
        if_first = True
        line_width = get_text_width(line, type, device)
        while line_width < screen_width:
            if if_first:
                if_first = False
                line += " "
            else:
                line += "*"
            line_width = get_text_width(line, type, device)
        filled_lines.append(line[:-1])

    return filled_lines


def get_text_width(text: str, type: str, device: str) -> int:
    font = FONT_MAPPING[device][type]
    widths = FONTS[device][font]
    return sum(widths.get(c, 8) for c in text)


def check_translations(translation_content: dict[str, str]) -> list[TooLong]:
    en_file = HERE / "en.json"
    en_content = json.loads(en_file.read_text())["translations"]

    rules_file = HERE / "rules.json"
    rules_content = json.loads(rules_file.read_text())

    translation_content = {
        k: v.replace(" (TODO)", "") for k, v in translation_content.items()
    }
    translation_content = {
        k: v.replace(" (TOO LONG)", "") for k, v in translation_content.items()
    }

    wrong: dict[str, TooLong] = {}

    for k, v in list(translation_content.items())[:]:
        if k.split("__")[0] in altcoins:
            continue
        if k.split("__")[0] == "plurals":
            continue

        rule = rules_content.get(k)
        if not rule:
            print(f"Missing rule for {k}")
            continue
        type, lines = rule.split(",")
        lines = int(lines)

        for model in DEVICES:
            if model == "TT" and k.startswith("tutorial"):
                continue

            if not will_fit(v, type, model, lines):
                too_long = TooLong(
                    model=model,
                    type=type,
                    key=k,
                    value=v,
                    lines=assemble_lines(v, type, model),
                    en=en_content[k],
                    lines_en=assemble_lines(en_content[k], type, model),
                )
                wrong[k] = too_long

    return list(wrong.values())


if __name__ == "__main__":
    file = HERE / "de.json"
    content = json.loads(file.read_text())["translations"]
    wrong = check_translations(content)
    for w in wrong:
        print(60 * "*")
        print()
        print(w)
        print()
        print(w.lines_str())
        print()
        print(w.lines_en_str())
