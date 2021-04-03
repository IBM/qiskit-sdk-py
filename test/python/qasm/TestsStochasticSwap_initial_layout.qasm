OPENQASM 2.0;
include "standard_gates.inc";

qreg q[4];
creg c[4];
h q[1];
measure q[0] -> c[0];
swap q[0],q[1];
cx q[0],q[2];
measure q[0] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
