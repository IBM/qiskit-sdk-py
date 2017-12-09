include "qelib1.inc";
qreg q[5];
creg c[5];

h q[1];
h q[2];
s q[1];
s q[2];
h q[2];
cx q[1],q[2];
h q[2];
s q[1];
s q[2];
h q[1];
h q[2];
x q[1];
x q[2];
h q[2];
cx q[1],q[2];
h q[2];
x q[1];
x q[2];
h q[1];
h q[2];
measure q[1] -> c[1];
measure q[2] -> c[2];
