OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[1];
swap q[1],q[0];
cx q[0],q[2];
measure q[1] -> c[0];
measure q[0] -> c[1];
measure q[2] -> c[2];
