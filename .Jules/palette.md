## 2023-10-24 - [Add Relative Time Tooltips to Dates]
**Learning:** Added relative time tooltips to `<time>` elements. Using native `Intl.RelativeTimeFormat` provides a lightweight, zero-dependency way to add this helpful context on hover without cluttering the main UI. It improves usability for quick scanning.
**Action:** When working with static dates, consider adding relative time tooltips (e.g., via `title` attribute) to provide immediate context without taking up extra screen real estate. Always test fallback behavior if `Intl` is unsupported.
