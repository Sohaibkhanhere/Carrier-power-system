"""Quick analysis of real data patterns for synthetic generator calibration."""
import pandas as pd
from pathlib import Path

xl = pd.ExcelFile(Path(r"..\One Month data.xlsx"))
df_a = xl.parse("Tower_A")
df_a["dt"] = pd.to_datetime(df_a["Date"]) + pd.to_timedelta(df_a["Time"].astype(str) + ":00")
df_a["hour"] = df_a["dt"].dt.hour
df_a["dow"] = df_a["dt"].dt.dayofweek

for label, mask in [("Weekday", df_a["dow"] < 5), ("Weekend", df_a["dow"] >= 5)]:
    print(f"\n=== {label} - Carrier 1_A ===")
    sub = df_a[mask & (df_a["Tower_Sector"] == "1_A")]
    for h in range(24):
        s = sub[sub["hour"] == h]
        if len(s) > 0:
            prb_m = s["DL_PRB_Utilization(%)"].mean()
            prb_s = s["DL_PRB_Utilization(%)"].std()
            trf_m = s["L.Traffic.User.Avg"].mean()
            print(f"  {h:02d}:00  PRB={prb_m:.1f}+/-{prb_s:.1f}  Traffic={trf_m:.1f}")

# Also show per-carrier averages
print("\n=== Per-carrier mean PRB ===")
for sec in ["1_A", "1_B", "1_C", "2_A", "2_B", "2_C"]:
    sub = df_a[df_a["Tower_Sector"] == sec] if sec.startswith("1") else xl.parse("Tower_B")
    if not sec.startswith("1"):
        sub = sub[sub["Tower_Sector"] == sec]
    print(f"  {sec}: mean={sub['DL_PRB_Utilization(%)'].mean():.1f}  std={sub['DL_PRB_Utilization(%)'].std():.1f}")
