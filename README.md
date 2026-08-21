# Sumdle

## Word engine

The Python word engine lives in `backend/`. Its checked-in word banks are built
from the local `web2` dictionary using:

```bash
python -m backend.word_bank_builder /usr/share/dict/web2
```

Replace that input with a reviewed, trustworthy open dictionary when updating
the production bank. `solutions.json` comes from the deliberately curated
answer candidates; `valid_guesses.json` is the larger normalized dictionary and
always includes every solution.

Run the API with `uvicorn backend.app:app --reload` and the tests with
`python -m pytest`. The puzzle endpoints intentionally return only puzzle
metadata, never a solution. The existing React game still evaluates guesses
against its local word array, so it cannot use this non-revealing API for a
complete game until answer evaluation moves server-side.

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
