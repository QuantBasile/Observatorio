
from __future__ import annotations

from underlying_app.data.fake_data import make_fake_underlyings
from underlying_app.data.raptor_data import make_fake_raptor_from_underlyings
from underlying_app.ui.main_window import MainWindow


def main():
    win = MainWindow(on_load_underlying=lambda: None, on_load_raptor=lambda: None)

    def load_underlying():
        df = make_fake_underlyings(n_rows=700, seed=42)
        win.set_underlyings_df(df)
        win.show_underlyings()

    def load_raptor():
        under = win.get_underlyings_df()
        if under is None:
            return
        df_raptor = make_fake_raptor_from_underlyings(under, n_rows=1_000_000, seed=123)
        win.set_raptor_df(df_raptor)
        win.show_raptor()

    win.load_under_btn.configure(command=load_underlying)
    win.load_raptor_btn.configure(command=load_raptor)

    win.mainloop()


if __name__ == "__main__":
    main()
