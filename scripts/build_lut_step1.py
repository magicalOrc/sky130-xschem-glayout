#!/usr/bin/env python3
"""
Step 1: Build the gm/ID lookup table from your existing DC VGS-sweep data,
and plot the two classic curves you can get from that data alone:
    - gm/ID vs VSG
    - gm/ID vs ID/W

Run this from the folder containing your pfet_L..._VD....txt files, e.g.:
    cd ~/gmid_sweep_output
    python3 build_lut_step1.py
"""

import numpy as np
import pandas as pd
import glob
import re
import matplotlib.pyplot as plt

# ------------------ CONFIG ------------------
W = 0.42e-6   # the actual W used in your sims (0.42 micron) -- must match your netlists
VDD = 1.8
DATA_GLOB = "pfet_L*_VD*.txt"
LUT_OUT = "pfet_01v8_gmid_lut.csv"
# ---------------------------------------------

# Your filenames look like: pfet_L0p15_VD0p3.txt  (and pfet_L2_VD1p2.txt -- no 'p' if whole number)
FNAME_RE = re.compile(r"pfet_L([\dp]+)_VD([\dp]+)\.txt")


def decode_num(token):
    """'0p15' -> 0.15, '2' -> 2.0"""
    return float(token.replace("p", "."))


def main():
    files = sorted(glob.glob(DATA_GLOB))
    if not files:
        print(f"No files matched '{DATA_GLOB}' in the current directory.")
        print("cd into the folder with your pfet_L..._VD....txt files and re-run.")
        return

    rows = []
    for fname in files:
        m = FNAME_RE.search(fname)
        if not m:
            print(f"  (skipping, doesn't match naming pattern: {fname})")
            continue
        L = decode_num(m.group(1)) * 1e-6   # stored as microns in filename -> meters
        VD = decode_num(m.group(2))

        data = np.loadtxt(fname)
        vg = data[:, 0]
        id_ = np.abs(data[:, 1])   # PMOS drain current sign flip -> take magnitude

        vsg = VDD - vg   # source-gate voltage (source tied to VDD for this PMOS)

        # Sort by vsg ascending so gradient is well-behaved (dc sweep went VG: 1.8->0,
        # so vsg naturally goes 0->1.8 already, but sort defensively anyway)
        order = np.argsort(vsg)
        vsg = vsg[order]
        id_ = id_[order]

        gm = np.gradient(id_, vsg)

        for i in range(len(vsg)):
            if id_[i] < 1e-10:   # skip near-zero current, gm/ID blows up / meaningless
                continue
            rows.append({
                "L": L,
                "VDS": VD,
                "VSG": vsg[i],
                "ID": id_[i],
                "gm": gm[i],
                "gm_id": gm[i] / id_[i],
                "id_w": id_[i] / W,
                "gm_w": gm[i] / W,
            })

    if not rows:
        print("No usable data rows extracted -- check that your .txt files have real sweep data.")
        return

    lut = pd.DataFrame(rows)
    lut.to_csv(LUT_OUT, index=False)
    print(f"Saved LUT with {len(lut)} rows to {LUT_OUT}")
    print(f"L values found: {sorted(lut.L.unique())}")
    print(f"VDS values found: {sorted(lut.VDS.unique())}")

    # ---------------- Plot 1: gm/ID vs VSG, one curve per L, at your highest VDS ----------------
    vds_for_plot = lut.VDS.max()
    plt.figure(figsize=(7, 5))
    for L in sorted(lut.L.unique()):
        sub = lut[(lut.L == L) & (lut.VDS == vds_for_plot)].sort_values("VSG")
        plt.plot(sub.VSG, sub.gm_id, label=f"L={L*1e6:.2f}u")
    plt.xlabel("VSG (V)")
    plt.ylabel("gm/ID (1/V)")
    plt.title(f"gm/ID vs VSG  (VDS={vds_for_plot} V)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("gmid_vs_vsg.png", dpi=150)
    print("Saved plot: gmid_vs_vsg.png")

    # ---------------- Plot 2: gm/ID vs ID/W (the classic sizing curve), same VDS ----------------
    plt.figure(figsize=(7, 5))
    for L in sorted(lut.L.unique()):
        sub = lut[(lut.L == L) & (lut.VDS == vds_for_plot)].sort_values("id_w")
        plt.plot(sub.id_w, sub.gm_id, label=f"L={L*1e6:.2f}u")
    plt.xscale("log")
    plt.xlabel("ID/W (A/m)")
    plt.ylabel("gm/ID (1/V)")
    plt.title(f"gm/ID vs ID/W  (VDS={vds_for_plot} V)")
    plt.legend()
    plt.grid(True, which="both")
    plt.tight_layout()
    plt.savefig("gmid_vs_idw.png", dpi=150)
    print("Saved plot: gmid_vs_idw.png")

    print("\nStep 1 done. You now have gm/ID vs VSG and gm/ID vs ID/W for all 5 L values.")
    print("Next: run extract_gds_cgg.py to get gm/gds and gm/Cgg (needs separate sweeps).")


if __name__ == "__main__":
    main()
