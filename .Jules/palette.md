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

## 2026-05-25 - Skip Link Focus Ring Clipping
**Learning:** When using a visually hidden `.skip-link` accessibility pattern that drops down into the viewport on focus, placing the element exactly at `left: 0` causes the left edge of the browser's focus ring (`outline`) to clip against the viewport boundary, reducing visibility and failing WCAG focus indicator requirements.
**Action:** Always provide a positive horizontal viewport offset (e.g., `left: 8px`) alongside the vertical offset when styling absolutely positioned skip links to ensure their focus indicators are fully visible on screen.

## 2026-05-26 - Invisible Feedback on Clipboard Actions
**Learning:** When executing inline visual changes within an interactive element (e.g., momentarily updating a link's text to "Copied!"), screen readers often ignore the update because the element isn't marked as a live region. Users relying on assistive technology receive absolutely no confirmation that their clipboard action was successful.
**Action:** Always pair visual, temporary text changes (like copy-to-clipboard success states) with an `aria-live="polite"` visually hidden announcer (`sr-only`) to ensure screen readers explicitly narrate the success to the user.

## 2026-03-26 - Visual Affordance for Hidden Actions
**Learning:** Invisible clipboard actions (like copying a deep link when clicking on a version number) are completely undiscoverable to new users unless there is a visual affordance. Simply changing the text on click to "Copied!" only rewards accidental discovery. Adding a subtle link icon that appears on card hover and fully highlights on link hover/focus clearly communicates the copy functionality before the user interacts.
**Action:** For UI elements that trigger hidden clipboard operations, always pair the action with a contextual icon (like a link or copy icon). Ensure the icon fades in or changes state on hover/focus to provide clear visual affordance.

## 2026-03-27 - Visually Distinct Empty States
**Learning:** Filter-heavy interfaces often result in states with zero matching items. Presenting this as plain, unstyled text feels incomplete and looks identical to loading/error fallbacks. By wrapping the empty state in a dashed container (using existing `.glass-card` classes) and pairing it with a contextual icon (like a magnifying glass) and clearer typography, users immediately recognize it as an expected state rather than an error. It also elevates the discoverability of recovery actions like the "Clear Filters" button.
**Action:** Whenever implementing a search or filter result list, never use plain text for the "no results" state. Always design a visually distinct empty state container that includes a descriptive icon, clear headings, and a prominently placed recovery call-to-action to help the user proceed.

## 2026-03-28 - Sticky Sidebar for Context Retention
**Learning:** When a user scrolls down a long list of items (like a version history dashboard), a statically positioned filter sidebar disappears from view. This forces the user to manually scroll all the way back to the top of the page just to change a single filter or perform a new search, resulting in significant friction.
**Action:** Always apply `position: sticky; align-self: flex-start;` to sidebars that control long adjacent content lists, ensuring the controls remain immediately accessible within the viewport at all times.

## 2026-03-30 - Reduced Motion Accessibility
**Learning:** The application uses several smooth transitions, staggered fadeInUp animations on cards, and continuous spinning loaders. While these add visual polish, they can trigger nausea, dizziness, or headaches for users with vestibular motion disorders. Relying solely on standard styles without checking system-level motion preferences excludes these users and violates WCAG guidelines for animation.
**Action:** Always include a `@media (prefers-reduced-motion: reduce)` block in the global CSS to neutralize animations, transitions, and smooth scrolling for users who have explicitly requested reduced motion at the OS level.

## 2026-03-31 - External Link Accessibility
**Learning:** Links that open in a new tab (`target="_blank"`) without warning are disorienting for screen reader users and those with cognitive disabilities. Relying solely on color to indicate a link (e.g., in a footer) fails WCAG contrast requirements if the contrast ratio between the link and surrounding text is low.
**Action:** Always warn users when a link opens in a new tab. For visual links within text, append a visually hidden warning: `<span class="sr-only"> (opens in a new tab)</span>`. For icon buttons or complex interactive elements, append ` (opens in a new tab)` to the `aria-label`. To ensure links are distinguishable from surrounding text without relying on color alone, style inline links with `text-decoration: underline` by default.

## 2026-05-27 - Preventing Layout Shifts During Inline Feedback
**Learning:** Swapping text of variable lengths (like a long version number "8.25.12345..." to "Copied!") during inline feedback causes jarring layout shifts, especially in densely packed lists or flex layouts. This breaks visual stability and degrades the UX.
**Action:** Instead of changing text content, provide feedback by swapping fixed-width affordances (like changing a copy/link icon to a checkmark) and updating colors. This maintains the physical dimensions of the element while still clearly communicating success.

## 2026-06-01 - Comprehensive Native UI Theming
**Learning:** Modern dark modes can't just stop at CSS variables for the page background. If `color-scheme` isn't declared, native browser UI components (like scrollbars, default `<select>` dropdowns, and form controls) remain stubbornly light, creating jarring visual inconsistencies. Additionally, on mobile browsers, the address bar's color is governed by the `<meta name="theme-color">` tag. If this tag isn't dynamically updated via JS when the theme toggles, users get a blinding white address bar floating above a dark-themed website.
**Action:** When implementing dark mode, always pair CSS `color-scheme` properties (`light` on `:root`, `dark` on the dark-theme selector) with a JavaScript function that dynamically updates the `content` attribute of `<meta name="theme-color">` to ensure 100% cohesion across the browser's native UI.

## 2026-06-02 - Form Input Focus Contrast
**Learning:** Using a low-opacity box-shadow (like `rgba(59, 130, 246, 0.15)`) for form input focus states fails WCAG 2.1 Non-text Contrast requirements. Users with low vision or varying monitor calibrations may not see the focus ring, resulting in poor keyboard navigation.
**Action:** Always use a solid `outline` (e.g., `outline: 2px solid var(--color-accent)`) with an offset rather than relying on subtle box-shadows to ensure focus states are clearly visible and accessible to all users.

## 2026-06-03 - Text Color Contrast Across Themes
**Learning:** Colors that are legible in dark mode may fail WCAG AA text contrast requirements (4.5:1) when inverted against a light background. For example, standard bright blues (`#3b82f6`) often fail on white backgrounds, while slightly darker shades (`#2563eb`) pass. Additionally, status colors like `--color-success` must be explicitly defined in dark mode; otherwise, they may inherit an overly dark value (like `#059669`) that is invisible against a dark background.
**Action:** Always verify contrast ratios for both light and dark themes independently. When defining utility colors in CSS, ensure they are explicitly overridden in the `[data-theme="dark"]` block if the light mode equivalent is too dark to be readable on a dark surface.

## 2026-06-03 - Label in Name Accessibility
**Learning:** Providing an `aria-label` that is completely different from a button's visible text (e.g., a button displaying "Clear Filters" with an `aria-label` of "Clear all filters to show all versions") violates the WCAG "Label in Name" criterion. This prevents voice dictation users from targeting the button by speaking its visible text, as assistive technologies only register the `aria-label`.
**Action:** For buttons with clear, visible text, avoid using an `aria-label`. If an `aria-label` is strictly necessary to provide extra context, the visible text must be fully included within it (e.g., "Clear Filters to show all versions"), though simply omitting the `aria-label` is almost always better for dictation users.

## 2026-04-06 - Accordion Escape Key Navigation
**Learning:** When designing expandable components like accordion cards, power users navigating via keyboard often expect the `Escape` key to act as a quick collapse mechanism, especially when focus is within the expanded content or on the container itself. If `Escape` isn't handled, the user must manually navigate back to the toggle button or use other means to close the section.
**Action:** Always add an `Escape` key listener to the container of expandable content. When triggered, it should collapse the section and explicitly return keyboard focus back to the primary trigger (e.g., the `headerButton`) to maintain a smooth navigation loop.

## 2026-06-03 - Text Color Contrast Across Themes
**Learning:** Colors that are legible in dark mode may fail WCAG AA text contrast requirements (4.5:1) when inverted against a light background. For example, standard bright blues (`#3b82f6`) often fail on white backgrounds, while slightly darker shades (`#1d4ed8`) pass. Additionally, status colors like `--color-success` must be explicitly defined in dark mode; otherwise, they may inherit an overly dark value (like `#047857`) that is invisible against a dark background.
**Action:** Always verify contrast ratios for both light and dark themes independently. When defining utility colors in CSS, ensure they are explicitly overridden in the `[data-theme="dark"]` block if the light mode equivalent is too dark to be readable on a dark surface.

## 2026-04-09 - Focus Management on Deep Links
**Learning:** When deep linking to a specific item in a long list, automatically scrolling the item into view is visually sufficient for sighted mouse users. However, for keyboard-only or screen reader users, visual scrolling doesn't change their logical location. Without programmatic focus management, they remain at the top of the document (or wherever focus last was) and must manually tab through the entire preceding page content to reach the element they just linked to.
**Action:** When automatically scrolling an item into view (like a deep-linked row), always shift programmatic focus to a logical, interactive element within that item (e.g., `.focus({ preventScroll: true })` on the item's header or title). This ensures all users start their interaction at the intended destination.

## 2026-06-03 - Predictive Tooltips for Toggle Buttons
**Learning:** For multi-state buttons like a 3-way theme toggle (system → light → dark), indicating the current state is not always enough for clear interaction feedback. Sighted users hovering over the button can benefit from knowing what will happen when they click. While the visible label states the *current* condition, a `title` tooltip predicting the *next* state (e.g., "Switch to Light theme") sets clear expectations.
**Action:** When implementing multi-state interactive elements, use the `title` attribute to provide a predictive tooltip that explicitly describes the next state in the sequence, improving clarity and confidence in the interaction.

## 2026-06-04 - Actionable Error States
**Learning:** Presenting error states as plain text simply describing the issue (e.g. "Check your connection and refresh") is poor UX because it requires the user to figure out the UI controls (finding the browser refresh button). Error states styled consistently with empty states (e.g. `.glass-card` with an icon) help users recognize them quickly. More importantly, including a direct, actionable button (e.g. "Refresh Page") right in the error box reduces friction and guides users to the immediate recovery step.
**Action:** When implementing an error state, never rely purely on text instructions. Always embed the primary recovery action directly into the error container as an interactive `<button>` (like a refresh trigger) to ensure an intuitive and actionable fallback experience.

## 2026-06-05 - Retaining aria-live Announcements on Mobile
**Learning:** Using `display: none;` on a container removes its contents entirely from the accessibility tree. In responsive designs, if an `aria-live` region (such as a search result count like `#version-count`) is placed inside a sidebar that gets hidden on mobile with `display: none;`, screen reader users will no longer receive dynamic announcements, degrading the experience on small viewports.
**Action:** When a UI element containing an active `aria-live` region needs to be hidden on mobile viewports to save space, never use `display: none;`. Instead, apply visually hidden CSS patterns (e.g., the `.sr-only` class) to the container to hide it visually while preserving its presence in the accessibility tree so dynamic announcements still trigger correctly.

## 2026-06-06 - Input Hover Affordance
**Learning:** Form elements like `.search-input` and `.filter-select` can feel unclickable or inactive to sighted users if they don't provide a visual `:hover` state prior to receiving focus. Additionally, drop-down style inputs like `<select>` are often more intuitive when they use a `cursor: pointer`, signaling that interacting with them will trigger an immediate menu rather than just text entry.
**Action:** Always provide a subtle `:hover` state (e.g., slightly darkening the border color) for form inputs to indicate interactivity. For inputs that function as menus or toggles (like `<select>`), apply `cursor: pointer` to match the expected interaction model of a button.

## 2026-06-07 - Accessible Custom Search Clear Buttons
**Learning:** Native browser search clear buttons (like WebKit's `::-webkit-search-cancel-button`) are notoriously difficult to style consistently across browsers, and they often lack proper keyboard navigability or accessibility states. Additionally, providing an empty state action without proper sizing and contrast violates WCAG guidelines.
**Action:** Always replace the native search clear button with a custom, accessible `<button type="button">` containing an SVG icon. Ensure this button has an `aria-label` or `title`. Furthermore, its visibility can be efficiently managed purely in CSS by positioning it as a sibling to the input and using `.input:not(:placeholder-shown) ~ .clear-btn`, keeping the DOM state logic clean while ensuring full cross-browser keyboard accessibility and styling control.

## 2026-06-08 - Hiding Interactive Elements Completely
**Learning:** Using `opacity: 0` and `pointer-events: none` on interactive elements (like a "Clear Search" button) is insufficient because the element remains in the accessibility tree and the DOM tab order. This creates a confusing "ghost" tab stop for keyboard-only users who might tab into an invisible button.
**Action:** When hiding interactive elements that should not receive keyboard focus, always pair `opacity: 0` with `visibility: hidden`. Use CSS transitions to animate `opacity` and toggle `visibility` simultaneously, ensuring the element is removed from the accessibility tree and tab order when hidden.

## 2026-06-09 - Distinct Containers for Empty States
**Learning:** Presenting an empty state (e.g., "No versions found") using plain text often gets lost in the application layout, making it harder for users to realize what happened or what they need to do.
**Action:** When implementing an empty state or error state, use visually distinct containers (such as adding a `.glass-card` class with a dashed border) to explicitly demarcate the section and draw attention to recovery actions (like "Clear Filters").

## 2026-06-10 - Input Field Visual Affordance
**Learning:** Text input fields, especially search inputs, lack immediate visual affordance when they are empty. While placeholder text helps, adding a decorative icon (like a magnifying glass) directly inside the input container instantly communicates the field's purpose without requiring the user to read the text. Furthermore, using a general sibling combinator (`.input:focus ~ .icon`) to highlight the icon when the input is focused provides excellent interactive feedback and connects the icon visually to the user's action.
**Action:** When designing primary search or filter inputs, always embed a decorative contextual icon within the input wrapper. Ensure the icon is positioned over the input (using padding to prevent text overlap), has `pointer-events: none;`, and changes color during the input's `:focus` state to reinforce interactivity. Always use general sibling combinators (`~`) instead of adjacent (`+`) for dynamic states to prevent DOM insertion order from breaking CSS rules.
## 2026-06-11 - Consistent Keyboard Focus Underline
**Learning:** Keyboard users tabbing to interactive elements like `.version-link` often see a focus ring but may miss text-level hover changes (like underlining `.version-number`), causing a visual disconnect between mouse and keyboard states.
**Action:** Ensure CSS selectors providing `:hover` text enhancements (like `text-decoration: underline`) are paired with `:focus-visible` states to offer consistent visual feedback regardless of the input method.

## 2026-06-12 - Inline Success Feedback with Tooltips
**Learning:** When providing inline success feedback for a click action (like copying to clipboard), visual changes like swapping icons or changing colors are effective, but mouse users often keep their cursor hovering over the element after clicking. The native browser tooltip (`title` attribute) remains visible and continues to show the original, now outdated, action (e.g., "Copy link to version..."). This creates a disconnect between the visual state ("Copied!") and the tooltip state.
**Action:** When providing inline success feedback for a click action, temporarily update the element's native tooltip (`title` attribute) to a success message (e.g., "Copied!") alongside the visual changes, and seamlessly restore the original `title` after a brief timeout to reinforce the interaction for mouse users.

## 2026-06-13 - Semantic Time Elements for Dates
**Learning:** Using generic `<span>` elements to render dates, even if visually formatted properly, strips away semantic meaning for assistive technologies and machine readers. Screen readers may misinterpret ambiguous date formats, and search engines lose valuable structured data.
**Action:** When rendering dates or times in the UI, always use the semantic HTML `<time>` element and include a valid, machine-readable `datetime` attribute (e.g., `YYYY-MM-DD`). This ensures dates are correctly parsed by assistive technologies, improves SEO, and provides a clear separation between the human-readable visual presentation and the machine-readable data.

## 2026-06-14 - Contextual Empty States
**Learning:** When users search for a specific term and get zero results, presenting a generic "No versions found matching your filters" empty state feels unresponsive. Providing contextual feedback by directly referencing their search term (e.g., "We couldn't find any versions matching '8.24.123'") reassures the user that the system processed their specific request and makes the empty state much more helpful and personalized.
**Action:** Always inject the user's current search query directly into empty state messaging to provide clear, contextual feedback. Ensure the injected string is safely HTML-escaped to prevent XSS and wrapped in `word-break: break-word;` to prevent layout breakage from extremely long continuous strings.
