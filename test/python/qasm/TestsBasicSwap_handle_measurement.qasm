OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
cx q[0],q[1];
measure q[2] -> c[2];
h q[3];
swap q[3],q[2];
cx q[2],q[1];
measure q[1] -> c[1];
swap q[2],q[1];
cx q[1],q[0];
measure q[0] -> c[0];
measure q[1] -> c[3];
