# Scrollbar Hiding Rule

**Description:** Always hide default browser scrollbars for clean UI aesthetics.

**Context:**
- The project has a `.no-scrollbar` CSS utility class defined in `index.css` that cross-browser hides scrollbars (hides webkit scrollbar, uses `scrollbar-width: none` for Firefox and `-ms-overflow-style: none` for IE/Edge).

**Instructions:**
- When creating any scrollable containers (e.g., `overflow-y-auto`, `overflow-x-auto`, `overflow-scroll`), you MUST append the `no-scrollbar` class to the container's className to hide the ugly native scrollbar.
- Exception: Unless explicitly requested by the user to keep the scrollbar visible.
