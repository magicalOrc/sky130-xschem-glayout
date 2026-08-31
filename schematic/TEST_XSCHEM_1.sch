v {xschem version=3.4.6RC file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 1860 -1240 1860 -1210 {
lab=GND}
N 1780 -1200 1780 -1180 {
lab=GND}
N 1860 -1360 1860 -1300 {
lab=VOUT}
N 1860 -1460 1860 -1420 {
lab=VDD}
N 1710 -1440 1710 -1410 {
lab=VDD}
N 1710 -1350 1710 -1320 {
lab=GND}
N 1860 -1270 1890 -1270 {
lab=GND}
N 1890 -1270 1890 -1230 {
lab=GND}
N 1860 -1230 1890 -1230 {
lab=GND}
N 1780 -1390 1820 -1390 {
lab=#net1}
N 1860 -1390 1890 -1390 {
lab=VDD}
N 1890 -1440 1890 -1390 {
lab=VDD}
N 1860 -1440 1890 -1440 {
lab=VDD}
N 1780 -1280 1780 -1260 {
lab=VIN}
N 1800 -1270 1820 -1270 {
lab=#net2}
C {sky130_fd_pr/nfet_01v8.sym} 1840 -1270 0 0 {name=M1
W=1
L=0.15
nf=1 
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {vdd.sym} 1860 -1460 0 0 {name=l1 lab=VDD}
C {vsource.sym} 1780 -1230 0 0 {name=V1 value=0.8 savecurrent=false}
C {gnd.sym} 1860 -1210 0 0 {name=l2 lab=GND}
C {gnd.sym} 1780 -1180 0 0 {name=l3 lab=GND}
C {vdd.sym} 1710 -1440 0 0 {name=l4 lab=VDD}
C {vsource.sym} 1710 -1380 0 0 {name=V2 value=1.8 savecurrent=false}
C {gnd.sym} 1710 -1320 0 0 {name=l5 lab=GND}
C {code.sym} 1940 -1390 0 0 {name=s1 only_toplevel=false value=".dc V1 0 1.8 0.01"

}
C {sky130_fd_pr/corner.sym} 1940 -1550 0 0 {name=CORNER1 only_toplevel=true corner=tt}
C {lab_wire.sym} 1860 -1330 0 0 {name=p1 sig_type=std_logic lab=VOUT
}
C {lab_wire.sym} 1780 -1270 0 0 {name=p2 sig_type=std_logic lab=VIN
}
C {sky130_fd_pr/pfet_01v8.sym} 1840 -1390 0 0 {name=M2
W=2
L=0.15
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {lab_wire.sym} 1790 -1390 0 0 {name=p3 sig_type=std_logic lab=VIN
}
C {lab_wire.sym} 1810 -1270 0 0 {name=p4 sig_type=std_logic lab=VIN
}
