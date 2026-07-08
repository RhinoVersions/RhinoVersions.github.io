## 2026-07-07 - [Visual Affordance for Active State on Interactive Toggles]
**Learning:** Found that non-traditional interactive elements (like `.version-card-toggle`) lacked an `:active` CSS state. Missing `:active` reduces interaction affordance for mouse/touch users, making the component feel less like a button.
**Action:** Include `:active` styles (like a subtle scale transform using `transform: scale(0.95)`) for interactive elements to mimic native controls and provide satisfying tactile feedback upon click.
