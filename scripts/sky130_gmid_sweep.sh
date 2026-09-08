#!/usr/bin/env bash
#
# SKY130 gm/ID raw-data sweep generator (nfet_01v8 / pfet_01v8)
# Mirrors gf180_gmid_sweep.sh exactly -- same file-naming convention, same
# wrdata column layout, so build_lut_sky130.py can reuse the same logic.
#
# NOTE: uses the "combined" (continuous) sky130 models at
# libs.tech/combined/sky130.lib.spice -- confirmed via Xschem's own
# generated netlist, NOT libs.tech/ngspice/sky130.lib.spice (the old
# binned models, whose auto bin-matching failed in this ngspice build).
# L/W are plain numbers (no 'u' suffix), matching Xschem's convention,
# relying on the global SCALE=1e-6 already set by this PDK's ngspice init.
#
# Run inside the container:
#   sak-pdk sky130A
#   mkdir -p /foss/designs/sky130_gmid_sweep_output
#   cd /foss/designs/sky130_gmid_sweep_output
#   bash sky130_gmid_sweep.sh nfet     # or: bash sky130_gmid_sweep.sh pfet

set -euo pipefail

DEVICE="${1:?Usage: $0 nfet|pfet}"
if [[ "$DEVICE" != "nfet" && "$DEVICE" != "pfet" ]]; then
    echo "DEVICE must be 'nfet' or 'pfet'"; exit 1
fi

MODEL="sky130_fd_pr__${DEVICE}_01v8"
CORNER="tt"
VDD=1.8
W=0.42          # um -- matches your original sky130 pfet script's W
L_LIST=(0.15 0.3 0.5 1 2)        # um -- adjust if you want a different sweep set
VD_LIST=(0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8)  # absolute node volts

PDKPATH="${PDKPATH:-/foss/pdks/sky130A}"
MODELFILE="$PDKPATH/libs.tech/combined/sky130.lib.spice"

decode_fname() {
    python3 -c "import sys; v=sys.argv[1]; print(v.replace('.','p'))" "$1"
}

for L in "${L_LIST[@]}"; do
  Lf=$(decode_fname "$L")
  for VD in "${VD_LIST[@]}"; do
    VDf=$(decode_fname "$VD")
    OUT="${DEVICE}_01v8_L${Lf}_VD${VDf}.txt"
    NET="/tmp/_sky130_${DEVICE}_${Lf}_${VDf}.spice"

    if [[ "$DEVICE" == "nfet" ]]; then
      cat > "$NET" <<EOF
* sky130 nfet_01v8 gm/ID sweep -- L=${L}u VD=${VD}
.lib ${MODELFILE} ${CORNER}

VD d 0 ${VD}
VG g 0 0
VS s 0 0
VB b 0 0

XM1 d g s b ${MODEL} L=${L} W=${W} nf=1 ad=0 as=0 pd=0 ps=0 nrd=0 nrs=0 sa=0 sb=0 sd=0 mult=1

.control
dc VG 0 ${VDD} 0.01
wrdata ${OUT} v(g) i(vd)
.endc
.end
EOF
    else
      cat > "$NET" <<EOF
* sky130 pfet_01v8 gm/ID sweep -- L=${L}u VD=${VD} (VD is absolute node volts)
.lib ${MODELFILE} ${CORNER}

VDDN vdd 0 ${VDD}
VD d 0 ${VD}
VG g 0 0

XM1 d g vdd vdd ${MODEL} L=${L} W=${W} nf=1 ad=0 as=0 pd=0 ps=0 nrd=0 nrs=0 sa=0 sb=0 sd=0 mult=1

.control
dc VG 0 ${VDD} 0.01
wrdata ${OUT} v(g) i(vd)
.endc
.end
EOF
    fi

    echo "Running L=${L}u VD=${VD} -> ${OUT}"
    if ! ngspice -b "$NET" > /tmp/_sky130_${DEVICE}_${Lf}_${VDf}.log 2>&1; then
      echo "FAILED: L=${L} VD=${VD}, see /tmp/_sky130_${DEVICE}_${Lf}_${VDf}.log"
    fi
  done
done

echo "Done. Files written to $(pwd)/${DEVICE}_01v8_L*_VD*.txt"
echo "Check for any FAILED lines above before running the analysis script."
