
# Underlying App (Tkinter + pandas)

A modular Tkinter dashboard designed for large pandas DataFrames:
- Load *Underlyings* (small/medium DF)
- Load *Raptor* (very large DF, UI shows only the first 500 rows)
- Run multiple **Actions** (plugin-like calculations) that produce new result tables

## Requirements
- Python 3.12
- Standard stack only: `tkinter`, `pandas`, `numpy`

## Run
```bash
python app.py
```

## Project layout
```
app.py
underlying_app/
  theme.py                     # your provided theme file
  data/
    fake_data.py               # fake underlyings generator
    raptor_data.py             # fake "raptor" (scheine) generator derived from underlyings
    model.py                   # generic filtering model
    actions.py                 # example calculations (Action 1/2/3)
    actions_registry.py        # ActionSpec + action registry (plugin system)
    state.py                   # pipeline state + stale detection
  ui/
    main_window.py             # layout, navigation, status bar, buttons
    data_view.py               # reusable view (filters + quick stats + table)
    data_table.py              # Treeview table (sorting ▲/▼, autofit columns)
    styles.py                  # light "pyqt-ish" styling (ttk only)
    logger.py                  # bottom log helper
```

## Key UX features
- **Sorting**: click column headers to sort; arrows ▲/▼ remain visible.
- **Auto-fit columns**: columns expand to show full content (horizontal scroll is fine).
- **Large DF support**: Raptor shows first 500 rows and displays `total … | showing 500`.
- **Debounced filters**: prevents lag by applying filters after short pause while typing.
- **Pipeline status bar**:
  - Underlyings / Raptor loaded state
  - Action readiness state
  - **Stale detection**: action marked ⚠ if computed on an older Raptor.

## Plugging in your real data
Replace the fake loaders in `app.py`:
- `make_fake_underlyings(...)`  → your real underlyings loader
- `make_fake_raptor_from_underlyings(...)` → your real raptor merge/pipeline

Keep the API the same:
- Underlyings: `win.set_underlyings_df(df_under)`
- Raptor: `win.set_raptor_df(df_raptor)`

## Adding new actions (plugin system)
1. Implement a function in `underlying_app/data/actions.py`:
   ```python
   def action_4(raptor: pd.DataFrame) -> pd.DataFrame:
       ...
       return df_out
   ```
2. Register it in `underlying_app/data/actions_registry.py`:
   ```python
   ActionSpec(
       key="action4",
       name="Acción 4",
       button_text="Calculate 4",
       view_title="Acción 4",
       run=action_4,
       enable_filters=False,
       row_limit=2000,
   )
   ```

No other UI code needs to change.

## Debugging tips
- The **bottom log** is your first line of defense (pipeline steps + errors).
- Errors are also displayed with a popup (`messagebox.showerror`).
- Stale warning ⚠ helps detect “I loaded new Raptor but forgot to rerun actions”.
