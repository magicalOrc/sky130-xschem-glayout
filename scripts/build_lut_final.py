#!/usr/bin/env python3
"""
Build the gm/ID lookup table from the DC VGS-sweep data (run_gmid_sweep.py output).

Fixes vs build_lut_step1.py:
  1. wrdata with two signals (v(gate) i(VD)) writes 4 columns, not 2:
        col0 = sweep var (== v(gate))
        col1 = v(gate)          <- duplicate of col0, NOT the current
        col2 = sweep var again  <- duplicate of col0
        col3 = i(VD)            <- the actual drain current, use this one
     The old script read col1 (a duplicate of VG) instead of col3 -- that's
     why every L curve looked identical and gm/ID hit nonsense values like -200.
  2. Axes flipped: gm/ID is now the x-axis, matching your reference plot.
  3. gds is now estimated via finite differences across your existing VD_VALS
     grid (0.3/0.6/0.9/1.2V) -- reuses data you already have, no new sims.
     This is coarse (only 4 VD points) but good enough for a first sizing pass.

Run from the folder containing your pfet_L..._VD....txt files:
    cd ~/gmid_sweep_output
    python3 build_lut_final.py
"""

import numpy as np
import pandas as pd
import glob
import re
import matplotlib.pyplot as plt

# ------------------ CONFIG ------------------
W = 0.42e-6
VDD = 1.8
DATA_GLOB = "pfet_L*_VD*.txt"
LUT_OUT = "pfet_01v8_gmid_lut.csv"
ID_FLOOR = 1e-10  # drop points below this current -- gm/ID and log(ID/W) blow up near 0
# ---------------------------------------------

FNAME_RE = re.compile(r"pfet_L([\dp]+)_VD([\dp]+)\.txt")


def decode_num(token):
    """'0p15' -> 0.15, '2' -> 2.0"""
    return float(token.replace("p", "."))


def load_iv(fname):
    """Load one pfet_L..._VD....txt file, return (vg, id) with the column bug fixed."""
    data = np.loadtxt(fname)
    if data.shape[1] != 4:
        raise ValueError(
            f"{fname}: expected 4 columns from wrdata's x,y-pair format, got "
            f"{data.shape[1]}. If you changed the wrdata line in the netlist "
            f"template, update the column indices in load_iv() to match."
        )
    vg = data[:, 0]
    id_ = np.abs(data[:, 3])  # <-- the fix: real current is column 3, not column 1
    return vg, id_


def main():
    files = sorted(glob.glob(DATA_GLOB))
    if not files:
        print(f"No files matched '{DATA_GLOB}' in the current directory.")
        print("cd into the folder with your pfet_L..._VD....txt files and re-run.")
        return

    # Group files by L so we can build the VD grid per L for the gds finite-difference.
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
    for L, vd_map in sorted(by_L.items()):
        vd_vals = sorted(vd_map.keys())

        # The VG sweep parameters are identical across every VD file for a given L,
        # so the VSG grid should line up point-for-point across all of them.
        vsg_ref = None
        id_cols = []
        ok = True
        for vd in vd_vals:
            vg, id_ = load_iv(vd_map[vd])
            vsg = VDD - vg
            order = np.argsort(vsg)
            vsg, id_ = vsg[order], id_[order]
            if vsg_ref is None:
                vsg_ref = vsg
            elif len(vsg) != len(vsg_ref):
                print(f"  WARNING: L={L*1e6:.2f}u VD={vd} has {len(vsg)} points, "
                      f"expected {len(vsg_ref)} -- skipping gds calc for this L.")
                ok = False
                break
            id_cols.append(id_)

        gds_2d = None
        if ok and len(id_cols) >= 2:
            id_2d = np.column_stack(id_cols)              # shape (n_vsg, n_vd)
            gds_2d = np.gradient(id_2d, vd_vals, axis=1)   # d(ID)/d(VD) at each vsg row

        for vd_idx, vd in enumerate(vd_vals):
            vg, id_ = load_iv(vd_map[vd])
            vsg = VDD - vg
            order = np.argsort(vsg)
            vsg, id_ = vsg[order], id_[order]

            gm = np.gradient(id_, vsg)
            gds = gds_2d[:, vd_idx] if gds_2d is not None else np.full_like(id_, np.nan)

            for i in range(len(vsg)):
                if id_[i] < ID_FLOOR:
                    continue
                g = gds[i]
                gm_gds = gm[i] / g if (g and not np.isnan(g)) else np.nan
                rows.append({
                    "L": L, "VDS": vd, "VSG": vsg[i], "ID": id_[i],
                    "gm": gm[i], "gds": g,
                    "gm_id": gm[i] / id_[i],
                    "id_w": id_[i] / W,
                    "gm_w": gm[i] / W,
                    "gm_gds": gm_gds,
                })

    if not rows:
        print("No usable data rows extracted -- check your .txt files have real sweep data.")
        return

    lut = pd.DataFrame(rows)
    lut.to_csv(LUT_OUT, index=False)
    print(f"Saved LUT with {len(lut)} rows to {LUT_OUT}")
    print(f"L values: {sorted(lut.L.unique())}")
    print(f"VDS values: {sorted(lut.VDS.unique())}")
    print(f"gm/ID range: {lut.gm_id.min():.2f} to {lut.gm_id.max():.2f} /V "
          f"(sane range is roughly 2-25 /V for this process -- if you still see huge "
          f"numbers here, something upstream is still off)")

    vds_for_plot = lut.VDS.max()

    # ---- Plot 1: ID/W vs gm/ID, x=gm/ID (matches your reference image), log y ----
    plt.figure(figsize=(7, 5))
    for L in sorted(lut.L.unique()):
        sub = lut[(lut.L == L) & (lut.VDS == vds_for_plot)].sort_values("gm_id")
        plt.plot(sub.gm_id, sub.id_w, label=f"L={L*1e6:.2f}u")
    plt.yscale("log")
    plt.xlabel("gm/ID (1/V)")
    plt.ylabel("ID/W (A/m)")
    plt.title(f"ID/W vs gm/ID  (VDS={vds_for_plot} V)")
    plt.legend()
    plt.grid(True, which="both")
    plt.tight_layout()
    plt.savefig("idw_vs_gmid.png", dpi=150)
    print("Saved plot: idw_vs_gmid.png")

    # ---- Plot 2: gm/gds (intrinsic gain proxy) vs gm/ID ----
    plt.figure(figsize=(7, 5))
    for L in sorted(lut.L.unique()):
        sub = lut[(lut.L == L) & (lut.VDS == vds_for_plot)].sort_values("gm_id")
        plt.plot(sub.gm_id, sub.gm_gds, label=f"L={L*1e6:.2f}u")
    plt.yscale("log")
    plt.xlabel("gm/ID (1/V)")
    plt.ylabel("gm/gds")
    plt.title(f"gm/gds vs gm/ID  (VDS={vds_for_plot} V, gds from 4-pt VD finite diff)")
    plt.legend()
    plt.grid(True, which="both")
    plt.tight_layout()
    plt.savefig("gmgds_vs_gmid.png", dpi=150)
    print("Saved plot: gmgds_vs_gmid.png")
    print("\nNote: gds here comes from only 4 VD points (0.3/0.6/0.9/1.2V) -- coarse but")
    print("usable for a first sizing pass. Add more VD_VALS entries in run_gmid_sweep.py")
    print("and re-run later if you need a smoother gm/gds curve for final decisions.")


if __name__ == "__main__":
    main()
