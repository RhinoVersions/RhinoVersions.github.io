## 2024-03-17 - Responsive Text Truncation Pattern
**Learning:** In narrow mobile views (under 480px), full textual labels (like long dates or platform names) can cause layout breakage or awkward wrapping inside version cards. Using CSS classes `.date-full`/`.date-short` (and similar `.label-full`/`.label-short`) to conditionally display different lengths of text based on screen size is a very clean and reusable pattern in this repository's design system. It maintains clarity without sacrificing layout integrity.
**Action:** When adding new dates, labels, or badges to the UI, remember to leverage these `*-full` and `*-short` utility classes so the design scales gracefully down to mobile.

## 2024-03-18 - Tactile Feedback and Screen Reader Noise Reduction
**Learning:** Adding subtle `:active` pseudo-class states (like `transform: scale(0.95)` or `translateY(0)`) to buttons and cards provides essential tactile feedback on click/tap, making the UI feel responsive. Additionally, images inside links that already contain descriptive text or `aria-label`s should explicitly have `alt=""` and `aria-hidden="true"` to prevent screen readers from reading redundant information.
**Action:** Always include `:active` states alongside `:hover` for interactive elements. Ensure decorative or redundant images inside labeled interactive elements are explicitly hidden from assistive technologies.
## 2026-03-19 - Focus State Border Radius
**Learning:** When applying a global `:focus-visible` style to links and buttons, overriding the `border-radius` (e.g., `border-radius: var(--radius-sm);`) distorts the shape of already rounded elements (like circular avatar buttons or pill-shaped toggles) when they receive keyboard focus.
**Action:** Use `border-radius: inherit;` or simply omit it and let the browser's default focus ring wrap the element's actual shape.

## 2026-04-12 - Nested Interactive Elements Keyboard Accessibility
**Learning:** When a nested interactive element (like a link inside an accordion button) handles a `click` event with `stopPropagation()`, keyboard events (`Enter` or `Space`) can still bubble up to the parent interactive element if not explicitly stopped. This causes the parent's `keydown` handler to execute instead of or alongside the child's default behavior, breaking keyboard accessibility for the nested element.
**Action:** Always ensure that nested interactive elements explicitly stop propagation for relevant `keydown` events (`Enter` and `Space`) in addition to `click` events to prevent parent handlers from intercepting the interaction.

## 2024-04-15 - Keyboard Navigation Loop: Focus and Release
**Learning:** Providing a keyboard shortcut (like `/`) to focus an input is excellent for power users, but it creates a "focus trap" if there's no equally fast way to release that focus and return to standard document navigation. Users expect `Escape` to act as a universal "cancel" or "release" action. If `Escape` only clears the input but leaves it focused, the user is still stuck in the input field.
**Action:** Always pair focus-shortcuts with an `Escape` fallback. When implementing an input, ensure `Escape` clears the input's content first. If the input is already empty, a second `Escape` press (or the first if it was empty) should explicitly call `.blur()` on the element to release focus and complete the keyboard navigation loop.

## 2026-05-20 - Seamless Deep Link Interactions
**Learning:** Using deep link URLs in `href` attributes inside a heavily stateful single-page application dashboard causes jarring full-page reloads when clicked by a user intending to "copy" the link. This behavior unexpectedly clears their current filter and search states.
**Action:** For shareable deep links within a dashboard, intercept the `click` and `keydown` (`Enter`/`Space`) events. Instead of allowing standard navigation, use `navigator.clipboard.writeText()` to copy the link, provide immediate inline visual feedback (e.g., changing text to "Copied!"), and update the address bar silently using `window.history.replaceState()`. Always update the `aria-label` and `title` to clarify that the link will "Copy link to version..." to set correct user expectations.
