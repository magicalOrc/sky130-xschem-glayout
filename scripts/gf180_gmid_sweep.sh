#!/usr/bin/env bash
#
# GF180 gm/ID raw-data sweep generator (nfet_03v3 / pfet_03v3)
#
# Run this INSIDE the container, with GF180 selected:
#   sak-pdk gf180mcuD
#   mkdir -p /foss/designs/gf180_gmid_sweep_output
#   cd /foss/designs/gf180_gmid_sweep_output
#   bash gf180_gmid_sweep.sh nfet     # or: bash gf180_gmid_sweep.sh pfet
#
# Produces files: {device}_L{L}_VD{VD}.txt  (decimals written as "0p5" etc,
# matching the FNAME_RE pattern the analysis script expects), each holding
# a full VG sweep (0 -> VDD) at one fixed absolute drain-node voltage VD.
#
# NOTE on convention (matches your original sky130 pfet script):
#   - VG/VD in these files are ABSOLUTE node voltages (0..VDD), not VGS/VDS.
#   - For nfet (source grounded): VGS = VG directly, VDS = VD directly.
#     No transform needed downstream -- but the analysis script still
#     expects the same file layout, so we generate it the same way.
#   - For pfet (source tied to VDD): the analysis script converts
#     VSG = VDD - VG and derives VSD from the VD sweep. Keep VD sweeping
#     0 -> VDD here exactly like before.

set -euo pipefail

DEVICE="${1:?Usage: $0 nfet|pfet}"
if [[ "$DEVICE" != "nfet" && "$DEVICE" != "pfet" ]]; then
    echo "DEVICE must be 'nfet' or 'pfet'"; exit 1
fi

MODEL="${DEVICE}_03v3"
VDD=3.3
W=1.0          # um -- pick a width you're comfortable normalizing by; keep it
               # the same for nfet and pfet so the two LUTs are comparable
L_LIST=(0.28 0.5 1 2 4)          # um
VD_LIST=(0.3 0.6 0.9 1.2 1.5 1.8 2.1 2.4 2.7 3.0 3.3)  # absolute node volts

PDKPATH="${PDKPATH:-/foss/pdks/gf180mcuD}"
MODELFILE="$PDKPATH/libs.tech/ngspice/sm141064.spice"
DESIGNFILE="$PDKPATH/libs.tech/ngspice/design.spice"

decode_fname() {
    # 0.5 -> 0p5 , 1 -> 1 , 0.28 -> 0p28
    python3 -c "import sys; v=sys.argv[1]; print(v.replace('.','p'))" "$1"
}

for L in "${L_LIST[@]}"; do
  Lf=$(decode_fname "$L")
  for VD in "${VD_LIST[@]}"; do
    VDf=$(decode_fname "$VD")
    OUT="${DEVICE}_L${Lf}_VD${VDf}.txt"
    NET="/tmp/_${DEVICE}_${Lf}_${VDf}.spice"

    if [[ "$DEVICE" == "nfet" ]]; then
      cat > "$NET" <<EOF
* GF180 nfet_03v3 gm/ID sweep -- L=${L}u VD=${VD}
.include ${DESIGNFILE}
.lib ${MODELFILE} typical

VD d 0 ${VD}
VG g 0 0
VS s 0 0
VB b 0 0

XM1 d g s b ${MODEL} L=${L}u W=${W}u nf=1 m=1

.control
dc VG 0 ${VDD} 0.01
wrdata ${OUT} v(g) i(vd)
.endc
.end
EOF
    else
      cat > "$NET" <<EOF
* GF180 pfet_03v3 gm/ID sweep -- L=${L}u VD=${VD} (VD is absolute node volts)
.include ${DESIGNFILE}
.lib ${MODELFILE} typical

VDDN vdd 0 ${VDD}
VD d 0 ${VD}
VG g 0 0

XM1 d g vdd vdd ${MODEL} L=${L}u W=${W}u nf=1 m=1

.control
dc VG 0 ${VDD} 0.01
wrdata ${OUT} v(g) i(vd)
.endc
.end
EOF
    fi

    echo "Running L=${L}u VD=${VD} -> ${OUT}"
    ngspice -b "$NET" > /tmp/_${DEVICE}_${Lf}_${VDf}.log 2>&1 \
      || { echo "FAILED: L=${L} VD=${VD}, see /tmp/_${DEVICE}_${Lf}_${VDf}.log"; }
  done
done

echo "Done. Files written to $(pwd)/${DEVICE}_L*_VD*.txt"
