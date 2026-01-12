
# Underlying App (Tkinter + pandas)

Modular Tkinter dashboard for large pandas DataFrames (Python 3.12, numpy/pandas/tkinter only).

## Run
```bash
python app.py
```

## Highlights
- **Copy cells**: double-click a cell to copy; **Ctrl+C** copies the last clicked cell (or selected rows as TSV fallback).
- **Sorting**: click headers to sort; arrow ▲/▼ is kept.
- **Auto-fit columns**: columns expand to show full content (horizontal scroll is fine).
- **Raptor big-data mode**:
  - shows only first **500** rows
  - global **Search** uses **Apply** (manual) to avoid lag
  - other filters remain usable

## Actions
This build ships with **7 actions**:
- Actions 1–5: table outputs
- **Spread Matrix**: matrix of mean `abs(Bid-Ask)` with its own filters (product, callput)
- **Issuer Plot**: table + plot; selecting an issuer plots the (downsampled) subset and highlights the mean point

## Plugging in real data
Replace fake loaders in `app.py`:
- `make_fake_underlyings(...)`
- `make_fake_raptor_from_underlyings(...)`

## Adding actions
Edit `underlying_app/data/actions_registry.py` and add an `ActionSpec`.
Supported `view_type`:
- `"table"`
- `"spread_matrix"`
- `"table_plot"`
