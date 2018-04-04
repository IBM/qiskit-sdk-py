//@author Raymond Harry Rudy rudyhar@jp.ibm.com
//Bernstein-Vazirani with 15 qubits.
//Hidden string is 11111111111111
OPENQASM 2.0;
include "qelib1.inc";
qreg qr[15];
creg cr[14];
h qr[0];
h qr[1];
h qr[2];
h qr[3];
h qr[4];
h qr[5];
h qr[6];
h qr[7];
h qr[8];
h qr[9];
h qr[10];
h qr[11];
h qr[12];
h qr[13];
x qr[14];
h qr[14];
barrier qr[0],qr[1],qr[2],qr[3],qr[4],qr[5],qr[6],qr[7],qr[8],qr[9],qr[10],qr[11],qr[12],qr[13],qr[14];
cx qr[0],qr[14];
cx qr[1],qr[14];
cx qr[2],qr[14];
cx qr[3],qr[14];
cx qr[4],qr[14];
cx qr[5],qr[14];
cx qr[6],qr[14];
cx qr[7],qr[14];
cx qr[8],qr[14];
cx qr[9],qr[14];
cx qr[10],qr[14];
cx qr[11],qr[14];
cx qr[12],qr[14];
cx qr[13],qr[14];
barrier qr[0],qr[1],qr[2],qr[3],qr[4],qr[5],qr[6],qr[7],qr[8],qr[9],qr[10],qr[11],qr[12],qr[13],qr[14];
h qr[0];
h qr[1];
h qr[2];
h qr[3];
h qr[4];
h qr[5];
h qr[6];
h qr[7];
h qr[8];
h qr[9];
h qr[10];
h qr[11];
h qr[12];
h qr[13];
measure qr[0] -> cr[0];
measure qr[1] -> cr[1];
measure qr[2] -> cr[2];
measure qr[3] -> cr[3];
measure qr[4] -> cr[4];
measure qr[5] -> cr[5];
measure qr[6] -> cr[6];
measure qr[7] -> cr[7];
measure qr[8] -> cr[8];
measure qr[9] -> cr[9];
measure qr[10] -> cr[10];
measure qr[11] -> cr[11];
measure qr[12] -> cr[12];
measure qr[13] -> cr[13];
