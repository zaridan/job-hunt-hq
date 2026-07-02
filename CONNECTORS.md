# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. The skills describe workflows in terms of
categories rather than specific products — use whichever you have connected.

## Connectors for this plugin

| Category   | Placeholder    | Options                              | Used by        |
|------------|----------------|--------------------------------------|----------------|
| Email      | `~~email`      | Gmail, Outlook                       | reply-monitor  |
| Job boards | `~~job boards` | Indeed, ZipRecruiter, Dice, LinkedIn | job-scrub      |

Neither connector is strictly required: job-scrub also covers public job
boards via web search, and reply-monitor simply can't run without an email
connector (everything else still works).
