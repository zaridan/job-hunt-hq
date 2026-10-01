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
| Browser    | Claude in Chrome | the Claude in Chrome extension, signed in to LinkedIn | linkedin-job-search, people-finder, referral-outreach |

Neither of the first two is strictly required: job-scrub also covers public
job boards via web search, and reply-monitor simply can't run without an
email connector (everything else still works).

The three LinkedIn skills are optional too. They need Claude in Chrome
because LinkedIn has no connector: they work in your own logged-in browser,
read-only unless you approve an exact list of requests or messages in chat.
Without it, the People tab still works for people you add by hand.
