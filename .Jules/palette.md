## 2024-05-15 - Dynamic aria-labels on stateful buttons
**Learning:** Static `aria-label`s on stateful buttons completely override internal text content, masking the current state from screen readers.
**Action:** When creating a stateful button, either use visually hidden text that dynamically changes with the state, or dynamically update the `aria-label` attribute itself via JavaScript.
