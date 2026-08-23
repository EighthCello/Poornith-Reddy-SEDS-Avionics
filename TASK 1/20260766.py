import argparse
import csv
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# This function loads the csv in which data is seperated using delimiters like "," or "." and ";".
# [Asked Ai for help when I got an error while loading the csv.] 
def _to_numeric_robust(series):
    primary = pd.to_numeric(series, errors="coerce")
    if primary.isna().any():
        alt = pd.to_numeric(
            series.astype(str).str.strip().str.replace(",", ".", regex=False),
            errors="coerce",
        )
        if alt.notna().sum() > primary.notna().sum():
            return alt
    return primary

#Loading the data
# [Asked Claude to improve my code.]
def load_data(csv_path, point_col="Point", depth_col="Depth (m)"):
    try:
        with open(csv_path, "r", newline="") as f:
            header_line = f.readline()
    except FileNotFoundError:
        sys.exit(f"Error: could not find file '{csv_path}'")

    if not header_line.strip():
        sys.exit(f"Error: '{csv_path}' is empty")

    # Sniff the delimiter from the header line only. Sniffing the whole
    # file gets confused by decimal commas in the data rows (e.g. a
    # European-locale export with '-263,7'); the header has no numbers
    # to create that ambiguity, so it's a reliable place to detect ';'
    # vs ',' vs tab, etc.
    try:
        sep = csv.Sniffer().sniff(header_line, delimiters=";,\t|").delimiter
    except csv.Error:
        sep = ","  # fall back to the standard default

    try:
        df = pd.read_csv(csv_path, sep=sep)
    except pd.errors.EmptyDataError:
        sys.exit(f"Error: '{csv_path}' is empty")
    except Exception as e:
        sys.exit(f"Error: could not parse '{csv_path}' as CSV ({e})")

    if df.empty:
        sys.exit(f"Error: '{csv_path}' has no rows")

    df.columns = [c.strip() for c in df.columns]

    if point_col not in df.columns or depth_col not in df.columns:
        sys.exit(
            f"Error: expected columns '{point_col}' and '{depth_col}', "
            f"but found {list(df.columns)}."
        )

    df[depth_col] = _to_numeric_robust(df[depth_col])
    df[point_col] = pd.to_numeric(df[point_col], errors="coerce")

    if df[point_col].isna().any():
        sys.exit(f"Error: '{point_col}' column contains non-numeric values")

    df = df.sort_values(point_col).reset_index(drop=True)
    return df

# Anomaly detection & repair 
#(Here, I've called "anomalies" in the data either the non-numeric values or values which are extremely away from the other points, i.e their standard deviation w.r.t median is high.)

def hampel_anomaly_mask(values, window=5, n_sigmas=4.0):
    # Flag anomalies with a rolling-median / MAD Hampel filter.
    # A point is flagged if it is more than `n_sigmas` robust standard
    # deviations away from the median of its local window, or if it is
    # NaN (i.e. was non-numeric in the source data).
    n = len(values)
    mask = np.zeros(n, dtype=bool)
    k = 1.4826  # scales MAD to approximate a standard deviation. (The statistical scaling constant)

    for i in range(n):
        if np.isnan(values[i]):
            mask[i] = True
            continue

        lo, hi = max(0, i - window), min(n, i + window + 1)
        local = values[lo:hi]
        local = local[~np.isnan(local)]
        if local.size == 0:
            continue

        med = np.median(local)
        mad = np.median(np.abs(local - med)) * k
        if mad == 0:
            mad = 1e-9  # avoid divide-by-zero

        if abs(values[i] - med) > n_sigmas * mad:
            mask[i] = True

    return mask

# Repairing of anomalies 
# So basically, repairing is just the mean of the values before and after the anomaly. The number of neighbours chosen can be customized using the window arguement below.
# If there's an anomaly at the end of the interval, it just uses a neighbor.
def repair_anomalies(values, mask):
    repaired = values.copy()
    valid_idx = np.where(~mask)[0]

    if valid_idx.size == 0:
        return np.zeros_like(repaired)  # entire series is invalid

    for i in np.where(mask)[0]:
        before = valid_idx[valid_idx < i]
        after = valid_idx[valid_idx > i]

        if before.size and after.size:
            repaired[i] = (values[before[-1]] + values[after[0]]) / 2
        elif before.size:
            repaired[i] = values[before[-1]]
        else:
            repaired[i] = values[after[0]]

    return repaired


def smooth_series(values, window):
    if window <= 1:
        return values
    return pd.Series(values).rolling(window=window, center=True, min_periods=1).mean().to_numpy()

# Plotting / animation
# Inspired (copied) from a youtube tutorial. 
def animate_depth(points, depths, anomaly_mask, point_col, depth_col, interval=15):
    fig, ax = plt.subplots(figsize=(11, 6))

    ax.set_xlim(points.min(), points.max())
    span = depths.max() - depths.min()
    pad = span * 0.1 if span > 0 else 1.0
    ax.set_ylim(depths.min() - pad, depths.max() + pad)

    ax.set_xlabel(point_col)
    ax.set_ylabel(depth_col)
    ax.set_title("Depth Profile")
    ax.grid(alpha=0.3)

    line, = ax.plot([], [], color="#2b6cb0", lw=1.6, label="Depth")
    marker, = ax.plot([], [], "o", color="#2b6cb0", ms=5)
# Plots the anamoly points in red color.
    if anomaly_mask.any():
        ax.scatter(points[anomaly_mask], depths[anomaly_mask],
                   color="crimson", zorder=5, s=45, label="Repaired anomaly")

    ax.legend(loc="lower right")

    def init():
        line.set_data([], [])
        marker.set_data([], [])
        return line, marker

    def update(frame):
        line.set_data(points[:frame + 1], depths[:frame + 1])
        marker.set_data([points[frame]], [depths[frame]])
        return line, marker

    anim = animation.FuncAnimation(
        fig, update, frames=len(points), init_func=init,
        interval=interval, blit=True, repeat=False,
    )

    plt.show()

    return anim

#There's a   reduction argument as well which smooths the curve by taking the mean (yes, again, ik) of the neighbors and assigning values near it.

def main():
    parser = argparse.ArgumentParser(
        description="Plot a depth-profiling CSV."
    )
    parser.add_argument("csv_path", help="Path to the input CSV file")
    parser.add_argument("--window", type=int, default=5,
                        help="Rolling window size (points on each side) used "
                             "for anomaly detection (default is 5)")
    parser.add_argument("--sigmas", type=float, default=4.0,
                        help="Detection sensitivity in robust standard "
                             "deviations; lower = stricter (default: 4.0)")
    parser.add_argument("--interval", type=int, default=15,
                        help="Milliseconds between animation frames (default: 15)")
    parser.add_argument("--noisered", type=int, default=0, metavar="WINDOW",
                        help="Reduce noise by smoothing the "
                             "depth profile with a moving-average filter over "
                             "WINDOW points."
                             "(default: 0)")
    args = parser.parse_args()

    point_col, depth_col = "Point", "Depth (m)"
    df = load_data(args.csv_path, point_col, depth_col)
    points = df[point_col].to_numpy()
    raw_depths = df[depth_col].to_numpy(dtype=float)

    mask = hampel_anomaly_mask(raw_depths, window=args.window, n_sigmas=args.sigmas)
    clean_depths = repair_anomalies(raw_depths, mask)

    if mask.any():
        flagged_points = points[mask].tolist()
        print(f"Detected and repaired {mask.sum()} anomal{'y' if mask.sum() == 1 else 'ies'} "
              f"at {point_col}(s): {flagged_points}")
        for p, old, new in zip(points[mask], raw_depths[mask], clean_depths[mask]):
            old_str = "NaN/non-numeric" if np.isnan(old) else f"{old:.1f}"
            print(f"  Point {p}: {old_str}  ->  {new:.1f}")
    else:
        print("No anomalies detected.")

    if args.noisered > 0:
        clean_depths = smooth_series(clean_depths, args.noisered)
        print(f"Applied noise reduction (moving average, window={args.noisered})")

    animate_depth(points, clean_depths, mask, point_col, depth_col,
                  interval=args.interval)


if __name__ == "__main__":
    main()
