OPENQASM 2.0;
include "standard_gates.inc";

qreg q[4];
creg c[4];
cx q[0],q[1];
h q[3];
measure q[2] -> c[2];
swap q[2],q[3];
cx q[2],q[1];
measure q[1] -> c[1];
swap q[1],q[2];
cx q[1],q[0];
measure q[0] -> c[0];
measure q[1] -> c[3];
