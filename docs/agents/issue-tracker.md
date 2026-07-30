# Issue tracker: GitHub

Issues and PRDs for this repository live in GitHub Issues at
`SlanyCukr/stream-sniper`. Use the `gh` CLI for operations.

## Conventions

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."`
- Close: `gh issue close <number> --comment "..."`

Commands should run inside this checkout so `gh` infers the repository from the
configured GitHub remote.

When a skill says to publish to the issue tracker, create a GitHub issue. When a
skill says to fetch a ticket, use `gh issue view <number> --comments`.
