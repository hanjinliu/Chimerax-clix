from __future__ import annotations

import re
from .._utils import bold_colored

def color_text_by_match(input_text: str, command_text: str, color: str) -> str:
    """Color text based on the input text."""
    if input_text == "":
        return command_text
    words = input_text.split(" ")
    pattern = re.compile("|".join(words), re.IGNORECASE)

    output_texts: list[str] = []
    last_end = 0
    for match_obj in pattern.finditer(command_text):
        output_texts.append(command_text[last_end : match_obj.start()])
        word = match_obj.group()
        colored_word = bold_colored(word, color)
        output_texts.append(colored_word)
        last_end = match_obj.end()

    if last_end == 0 and len(input_text) < 4:  # no match word-wise
        replace_table: dict[int, str] = {}
        for char in input_text:
            idx = command_text.lower().find(char.lower())
            if idx >= 0:
                replace_table[idx] = bold_colored(command_text[idx], color)
        for i, value in sorted(
            replace_table.items(), key=lambda x: x[0], reverse=True
        ):
            command_text = command_text[:i] + value + command_text[i + 1 :]
        return command_text

    output_texts.append(command_text[last_end:])
    output_text = "".join(output_texts)
    return output_text
