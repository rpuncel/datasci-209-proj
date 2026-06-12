# IDE setup

Two supported editors. Pick whichever you'll actually open every day.

## Positron (recommended)

[Positron](https://positron.posit.co/) is Posit's data science IDE. It's a VS Code fork with native Quarto support, a Python/R interpreter picker, and a layout that should feel familiar if you're coming from RStudio.

1. **Install** — download from <https://positron.posit.co/> and install for your platform.
2. **Open the repo** — `File → Open Folder…` → select `datasci-209-proj/`.
3. **Select the Python interpreter** — click the interpreter picker in the status bar (bottom-right) and choose `.venv/bin/python`. If it's not listed, restart Positron after running `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` once in the integrated terminal.
4. **Preview the dashboard** — in the integrated terminal: `quarto preview`. Positron will open the rendered dashboard in a side pane and hot-reload on save.

That's it — Quarto support is bundled, no extensions needed.

## VS Code (alternative)

If you'd rather stay in [VS Code](https://code.visualstudio.com/), install these extensions:

| Extension | ID | Why |
| --- | --- | --- |
| Quarto | `quarto.quarto` | Syntax, preview, render commands |
| Python | `ms-python.python` | Interpreter selection, debugging |
| Jupyter | `ms-toolsai.jupyter` | Runs the Python chunks in `.qmd` files |
| Pylance *(optional)* | `ms-python.vscode-pylance` | Type hints / autocomplete |

Install them all in one go from the terminal:

```bash
code --install-extension quarto.quarto \
     --install-extension ms-python.python \
     --install-extension ms-toolsai.jupyter \
     --install-extension ms-python.vscode-pylance
```

Then:

1. **Open the folder** — `code .` from the repo root.
2. **Select interpreter** — `Cmd/Ctrl+Shift+P → Python: Select Interpreter → .venv/bin/python`.
3. **Preview** — `Cmd/Ctrl+Shift+K` (Quarto extension's preview shortcut), or run `quarto preview` in the integrated terminal.

## Common prerequisites (both editors)

- The **Quarto CLI** must be installed system-wide (not just as an extension). Verify with `quarto --version`. Install from <https://quarto.org/docs/get-started/>.
- The `.venv/` virtualenv must exist with `requirements.txt` installed. See the [README quick start](../README.md#quick-start).

## Troubleshooting

- **"Jupyter kernel not found"** — your editor isn't pointed at `.venv`. Re-select the interpreter.
- **`quarto preview` opens but charts don't render** — usually a stale `.quarto/` cache. Delete it (`rm -rf .quarto`) and try again.
- **Port already in use** — `quarto preview --port 4848` (or any free port).
