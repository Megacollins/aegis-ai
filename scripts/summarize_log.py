"""Quick pandas summary of a trades.csv log: regime distribution, stance
distribution, win rate per regime, and the equity curve's max drawdown.

Run: python scripts/summarize_log.py --log logs/trades.csv
"""

import argparse

import pandas as pd


def summarize(log_path: str) -> None:
    df = pd.read_csv(log_path)

    print(f"Total rows: {len(df)}\n")

    print("Regime distribution:")
    print(df["regime"].value_counts().to_string(), "\n")

    print("Stance distribution:")
    print(df["stance"].value_counts().to_string(), "\n")

    traded = df[df["realized_pnl"].notna()]
    if len(traded):
        print("Trades executed:", len(traded))
        print("Win rate:", round((traded["realized_pnl"] > 0).mean() * 100, 1), "%")
        print()
        print("Win rate by regime:")
        win_rate_by_regime = traded.groupby("regime")["realized_pnl"].apply(lambda s: round((s > 0).mean() * 100, 1))
        print(win_rate_by_regime.to_string(), "\n")

        balances = traded["running_balance"]
        peak = balances.cummax()
        drawdown_pct = (peak - balances) / peak * 100
        print(f"Max drawdown observed: {drawdown_pct.max():.2f}%")
        print(f"Final balance: {balances.iloc[-1]:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="logs/trades.csv")
    args = parser.parse_args()
    summarize(args.log)
