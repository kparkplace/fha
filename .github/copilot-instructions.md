# FHA Workspace Copilot Instructions

## Coding Style
- Prefer inline code over helper functions that are used only once.
- Create code chunks that are easy to read and understand; avoid long, complex functions.
- Extract functions only when logic is reused, materially improves readability, or is needed for testing.
- Keep code explicit and easy to audit; avoid unnecessary abstraction.
- Preserve existing variable names unless a rename clearly improves clarity.

## Data Workflow
- Favor pandas-first transformations with clear, linear steps.
- Keep row-level filters visible near the analysis block that uses them.
- Before merge operations, check join keys for duplicates when row expansion is possible.
- For weighted summaries, keep weight assumptions explicit in code and labels.

## Plotting
- Use plotnine for charts unless asked otherwise.
- Keep axis labels and titles descriptive, including metric definitions and units.
- Use fixed y-axis scales across facets unless explicitly requested to use free scales.
- Use stable x-axis breaks for quarter-based charts (for example every 4 quarters) when readable.
- Use theme_classic() as default for plotnine charts unless a different theme is requested.

## Safety and Validation
- Do not silently change analysis definitions; call out behavioral changes.
- After meaningful edits, run a quick syntax check or lightweight validation when feasible.
- When adding derived fields, preserve existing output contracts unless asked to change schema.

## Collaboration Preferences
- Ask before introducing new dependencies.
- For one-off requests, implement directly in the current script section instead of creating new modules.
- Keep responses concise and implementation-focused.
 - Make scripts and loaders runnable in the VS Code Interactive window/IPython: prefer resolving data paths relative to the script location, include `if __name__ == "__main__"` entrypoints, and avoid assumptions about the current working directory.
