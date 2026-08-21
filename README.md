# Sumdle

## Word engine

The Python word engine lives in `backend/`. It persists a deliberately small,
curated solution list and previously checked dictionary words in SQLite at
`backend/data/sumdle.db`. The database is created and seeded automatically and
is intentionally not committed.

Run the API with `uvicorn backend.app:app --reload` and the tests with
`python -m pytest`. Daily puzzles are selected using the backend server's date,
SHA-256 of that ISO date, and alphabetically ordered active solutions. The
current React evaluator runs in the browser, so the puzzle APIs return the
solution for gameplay; this is not a security boundary and should be replaced
with server-side guess evaluation before answers need to be secret.

### Optional MCP dictionary enrichment

Sumdle validates its checked-in word bank first. It can optionally ask the
[Word of the Day MCP server](https://github.com/Traves-Theberge/Word_of_the_day)
about unknown five-letter words and retrieve definitions. Clone, install, and
build that server separately, then configure its stdio command before starting
the API:

```sh
export SUMDLE_MCP_COMMAND=node
export SUMDLE_MCP_ARGS='["dist/index.js"]'
export SUMDLE_MCP_CWD=/path/to/Word_of_the_day
# Optional; defaults to 3 seconds.
export SUMDLE_MCP_TIMEOUT_SECONDS=3
```

If `SUMDLE_MCP_COMMAND` is unset or the server is unavailable, local gameplay
continues normally. `GET /api/words/{word}/lookup` reports the validation
source, while `GET /api/words/{word}/definition` returns normalized dictionary
data when available.

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
