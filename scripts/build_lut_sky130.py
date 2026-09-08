#!/usr/bin/env python3
"""
SKY130 gm/ID lookup table + plots. Mirrors build_lut_gf180.py exactly --
same logic, just VDD=1.8V and the sky130 file-naming convention.

Usage:
    cd ~/sky130_gmid_sweep_output
    python3 build_lut_sky130.py nfet
    python3 build_lut_sky130.py pfet
"""

import sys
import numpy as np
import pandas as pd
import glob
import re
import matplotlib.pyplot as plt

if len(sys.argv) != 2 or sys.argv[1] not in ("nfet", "pfet"):
    print("Usage: python3 build_lut_sky130.py nfet|pfet")
    sys.exit(1)

DEVICE = sys.argv[1]
W = 0.42e-6                    # matches your original sky130 pfet script
VDD = 1.8
DATA_GLOB = f"{DEVICE}_01v8_L*_VD*.txt"
LUT_OUT = f"{DEVICE}_01v8_gmid_lut.csv"
ID_FLOOR = 1e-9
SMOOTH_WINDOW = 7

FNAME_RE = re.compile(rf"{DEVICE}_01v8_L([\dp]+)_VD([\dp]+)\.txt")


def decode_num(token):
    return float(token.replace("p", "."))


def smooth(y, window):
    if window < 3:
        return y
    pad = window // 2
    y_padded = np.pad(y, pad, mode="reflect")
    kernel = np.ones(window) / window
    return np.convolve(y_padded, kernel, mode="valid")


def load_iv(fname):
    data = np.loadtxt(fname)
    if data.shape[1] != 4:
        raise ValueError(
            f"{fname}: expected 4 columns from wrdata's x,y-pair format, got "
            f"{data.shape[1]}. If you changed the wrdata line, update load_iv()."
        )
    vg = data[:, 0]
    id_ = np.abs(data[:, 3])
    return vg, id_


def gate_to_x(vg, device):
    if device == "nfet":
        return vg
    else:
        return VDD - vg


def main():
    files = sorted(glob.glob(DATA_GLOB))
    if not files:
        print(f"No files matched '{DATA_GLOB}' in the current directory.")
        return

    by_L = {}
    for fname in files:
        m = FNAME_RE.search(fname)
        if not m:
            print(f"  (skipping, doesn't match naming pattern: {fname})")
            continue
        L = decode_num(m.group(1)) * 1e-6
        VD = decode_num(m.group(2))
        by_L.setdefault(L, {})[VD] = fname

    rows = []
    xlabel = "VGS" if DEVICE == "nfet" else "VSG"

    for L, vd_map in sorted(by_L.items()):
        vd_vals = sorted(vd_map.keys())

        x_ref = None
        id_cols = []
        ok = True
        for vd in vd_vals:
            vg, id_ = load_iv(vd_map[vd])
            x = gate_to_x(vg, DEVICE)
            order = np.argsort(x)
            x, id_ = x[order], id_[order]
            id_smooth = smooth(id_, SMOOTH_WINDOW)
            if x_ref is None:
                x_ref = x
            elif len(x) != len(x_ref):
                print(f"  WARNING: L={L*1e6:.2f}u VD={vd} has {len(x)} points, "
                      f"expected {len(x_ref)} -- skipping gds calc for this L.")
                ok = False
                break
            id_cols.append(id_smooth)

        gds_2d = None
        if ok and len(id_cols) >= 2:
            id_2d = np.column_stack(id_cols)
            if DEVICE == "nfet":
                gds_2d = np.gradient(id_2d, vd_vals, axis=1)
            else:
                gds_2d = -np.gradient(id_2d, vd_vals, axis=1)

        for vd_idx, vd in enumerate(vd_vals):
            vg, id_raw = load_iv(vd_map[vd])
            x = gate_to_x(vg, DEVICE)
            order = np.argsort(x)
            x, id_raw = x[order], id_raw[order]
            id_ = smooth(id_raw, SMOOTH_WINDOW)

            gm = np.gradient(id_, x)
            gds = gds_2d[:, vd_idx] if gds_2d is not None else np.full_like(id_, np.nan)

            for i in range(len(x)):
                if id_[i] < ID_FLOOR:
                    continue
                g = gds[i]
                gm_gds = gm[i] / g if (g and not np.isnan(g)) else np.nan
                rows.append({
                    "L": L, "VD_abs": vd, "X": x[i], "ID": id_[i],
                    "gm": gm[i], "gds": g,
                    "gm_id": gm[i] / id_[i],
                    "id_w": id_[i] / W,
                    "gm_w": gm[i] / W,
                    "gm_gds": gm_gds,
                })

    if not rows:
        print("No usable data rows extracted.")
        return

    lut = pd.DataFrame(rows)
    lut.to_csv(LUT_OUT, index=False)
    print(f"Saved LUT with {len(lut)} rows to {LUT_OUT}")
    print(f"L values: {sorted(lut.L.unique())}")
    print(f"gm/ID range: {lut.gm_id.min():.2f} to {lut.gm_id.max():.2f} /V")

    vd_for_plot = lut.VD_abs.max()
    Ls = sorted(lut.L.unique())

    def get_curve(L):
        return lut[(lut.L == L) & (lut.VD_abs == vd_for_plot)].sort_values("X")

    fig, axes = plt.subplots(3, 1, figsize=(7, 13), sharex=True)

    ax = axes[0]
    for L in Ls:
        sub = get_curve(L)
        ax.plot(sub.gm_id, sub.X, label=f"L={L*1e6:.2f}u")
    ax.set_ylabel(f"{xlabel} (V)")
    ax.set_title(f"{DEVICE}_01v8: {xlabel}, ID/W, gm/gds vs gm/ID (VD_abs={vd_for_plot} V)")
    ax.grid(True)
    ax.legend()

    ax = axes[1]
    for L in Ls:
        sub = get_curve(L)
        ax.plot(sub.gm_id, sub.id_w, label=f"L={L*1e6:.2f}u")
    ax.set_yscale("log")
    ax.set_ylabel("ID/W (A/m)")
    ax.grid(True, which="both")

    ax = axes[2]
    for L in Ls:
        sub = get_curve(L)
        ax.plot(sub.gm_id, sub.gm_gds, label=f"L={L*1e6:.2f}u")
    ax.set_yscale("log")
    ax.set_ylabel("gm/gds")
    ax.set_xlabel("gm/ID (1/V)")
    ax.grid(True, which="both")

    plt.tight_layout()
    outpng = f"{DEVICE}_gmid_lut_combined.png"
    plt.savefig(outpng, dpi=150)
    print(f"Saved combined plot: {outpng}")


if __name__ == "__main__":
    main()
