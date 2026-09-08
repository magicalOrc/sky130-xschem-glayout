#!/usr/bin/env python3
"""
gm/ID sweep runner for sky130_fd_pr__pfet_01v8.

Why this script exists instead of a pure ngspice .control sweep:
  1. `alter @XM1[l] = ...` on this binned PDK device is unreliable
     (produces "no such device or model name" errors).
  2. ngspice's $variable substitution inside nested foreach loops
     is unreliable for building dynamic wrdata filenames.

Fix: generate one fully-static netlist per (L, VD) pair -- with L and VD
hardcoded directly as plain numbers, no alter, no nested loop string
substitution -- then run `ngspice -b` on each file separately.

Also runs ngspice with cwd = the PDK's ngspice folder, since that's the
setup we confirmed actually resolves the PDK's internal includes correctly.

Just edit the CONFIG section below, then run:
    python3 run_gmid_sweep.py
"""

import os
import subprocess

# ------------------ CONFIG: edit these ------------------
PDK_DIR  = "/media/mohussein/Ubuntu_Nvme/pdks/share/pdk/sky130B/libs.tech/ngspice"
LIB_FILE = "sky130.lib.spice"   # relative to PDK_DIR -- confirmed working this way
CORNER   = "tt"

L_VALS  = ["0.15", "0.3", "0.5", "1", "2"]      # microns, matches your original values
VD_VALS = ["0.3", "0.6", "0.9", "1.2"]

W  = "0.42"
NF = 1

VG_START = "1.8"
VG_STOP  = "0"
VG_STEP  = "-0.005"

# Where results land -- absolute path, so it doesn't matter that we chdir into PDK_DIR
OUT_DIR = "/home/mohussein/gmid_sweep_output"
# ----------------------------------------------------------

NETLIST_TEMPLATE = """* Auto-generated gm/ID sweep netlist -- L={l_val}u, VD={vd_val}V
.lib {lib_file} {corner}

XM1 drain gate VDD VDD sky130_fd_pr__pfet_01v8 L={l_val} W={w} nf={nf} m=1

VDD VDD 0 DC 1.8
VD drain 0 DC {vd_val}
VG gate 0 DC 1.8

.control
dc VG {vg_start} {vg_stop} {vg_step}
wrdata {out_file} v(gate) i(VD)
echo "Done: L={l_val}, VD={vd_val}"
.endc

.GLOBAL GND
.end
"""


def main():
    if not os.path.isdir(PDK_DIR):
        print(f"ERROR: PDK_DIR not found:\n  {PDK_DIR}")
        print("Fix PDK_DIR at the top of this script and re-run.")
        return

    lib_full_path = os.path.join(PDK_DIR, LIB_FILE)
    if not os.path.isfile(lib_full_path):
        print(f"ERROR: lib file not found:\n  {lib_full_path}")
        print("Fix PDK_DIR/LIB_FILE at the top of this script and re-run.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    total = len(L_VALS) * len(VD_VALS)
    count = 0

    for l_val in L_VALS:
        for vd_val in VD_VALS:
            count += 1
            safe_l = l_val.replace(".", "p")
            safe_vd = vd_val.replace(".", "p")
            out_filename = f"pfet_L{safe_l}_VD{safe_vd}.txt"
            out_file_abs = os.path.join(OUT_DIR, out_filename)

            netlist_text = NETLIST_TEMPLATE.format(
                l_val=l_val,
                lib_file=LIB_FILE,
                corner=CORNER,
                w=W,
                nf=NF,
                vd_val=vd_val,
                vg_start=VG_START,
                vg_stop=VG_STOP,
                vg_step=VG_STEP,
                out_file=out_file_abs,
            )

            spice_filename_abs = os.path.join(
                OUT_DIR, f"netlist_L{safe_l}_VD{safe_vd}.spice"
            )
            with open(spice_filename_abs, "w") as f:
                f.write(netlist_text)

            print(f"[{count}/{total}] Running L={l_val}u, VD={vd_val}V ...")

            # Run with cwd = PDK_DIR, since that's the confirmed-working setup
            # for resolving sky130.lib.spice's own internal includes.
            result = subprocess.run(
                ["ngspice", "-b", spice_filename_abs],
                capture_output=True,
                text=True,
                cwd=PDK_DIR,
            )

            if result.returncode != 0 or "Error" in result.stdout or "error" in result.stderr.lower():
                print(f"  !! Possible issue for {spice_filename_abs}")
                print("  ---- stdout tail ----")
                print("\n".join(result.stdout.strip().splitlines()[-10:]))
                if result.stderr.strip():
                    print("  ---- stderr ----")
                    print(result.stderr.strip())
            else:
                print(f"  OK -> {out_filename}")

    print("\nAll sweeps complete.")
    print(f"Output files are in: {OUT_DIR}")
    print("Each pfet_L..._VD....txt has two columns: v(gate), i(VD)")


if __name__ == "__main__":
    main()
