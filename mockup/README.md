# Mockup

The final design of the demo screen, decided in [What the demo screen shows](https://github.com/dangth1101/IS6002/issues/6). Build the real app to match this.

```sh
uv run --with streamlit streamlit run mockup/demo_screen.py
```

No LLM and no database. Every result is canned. The "Mock outcome" picker in the sidebar switches between the six verdicts. It's not part of the design.

## What's on the screen

- Sidebar: the active model, read-only.
- Two input tabs. The active tab decides the run type:
  - "Pick a BIRD dev Question" is a Scored run.
  - "Type your own" is an Unscored run.
- "Use Evidence" toggle. Disabled on "Type your own".
- Scored run, top to bottom:
  1. Verdict banner: Match, Mismatch, SQL error, Timeout, Match on empty result (warning colour), No SQL in reply
  2. Row-diff counts: rows only in Predicted, rows only in Ground-truth
  3. "Prompt sent to the LLM", collapsed
  4. Predicted SQL and rows, next to Ground-truth SQL and rows
- Unscored run: an info line, the prompt expander, then the Predicted SQL and rows. No banner, no diff counts, no Ground-truth column.

## Still open

- The verdict labels depend on [How the demo scores a run](https://github.com/dangth1101/IS6002/issues/8).
- Typed Evidence for Unscored runs: [Can a typed Question carry typed Evidence](https://github.com/dangth1101/IS6002/issues/10).
- Failure categories next to the banner: [Does the demo label why a run failed](https://github.com/dangth1101/IS6002/issues/11).
