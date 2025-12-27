from __future__ import annotations

import time
import random

class HintRegistry:
    """The did-you-know style hint shown in the CLI widget."""
    
    def __init__(self, primary: str):
        self._primary = primary
        self._other_hints: list[str] = []
        self._time_last_given = -1
        self._last_hint = primary
    
    def add_hint(self, hint: str):
        """Add a hint to the registry."""
        self._other_hints.append(hint)
        
    def get_primary_hint(self) -> str:
        """Get the primary hint to show."""
        return self._primary
    
    def get_random_hint(self) -> str:
        if not self._other_hints:
            return self._primary
        t0 = time.time()
        if t0 - self._time_last_given < 2:
            return self._last_hint
        self._time_last_given = t0
        if random.random() < 0.25:
            # should often show the primary hint
            self._last_hint = self._primary
        else:
            self._last_hint = "Tip | " + random.choice(self._other_hints)
        return self._last_hint

HINTS = HintRegistry("Run command here. Type '>' to enter action search mode. Type '/' to enter recent file mode.")
HINTS.add_hint("Run `some_command?` to see the documentation for the command e.g. `open?`.")
HINTS.add_hint("Type '>' to enter action search mode. All the menu and toolbar actions will be listed.")
HINTS.add_hint("Type '/' to enter recent file mode. You can quickly open and view recent files from there.")
HINTS.add_hint("Click the `...` button on the right to see and search command history.")
HINTS.add_hint("`alias` command is useful to create custom commands. Run `alias?` for the details.")
HINTS.add_hint("`name` command is useful to define custom object selectors. Run `name?` for the details.")
HINTS.add_hint("`mousemode` command allows you to customize mouse modes with keyboard modifiers.")
HINTS.add_hint("`buttonpanel` command creates panel of buttons in the GUI.")
HINTS.add_hint("`functionkey` command assigns function keys F1-F12 to commands.")
