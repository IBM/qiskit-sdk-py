OPENQASM 2.0;
include "qelib1.inc";
qreg q[25];
creg c[25];
h q[0];
cu1(1.570796326794897) q[1],q[0];
h q[1];
cu1(0.785398163397448) q[2],q[0];
cu1(1.570796326794897) q[2],q[1];
h q[2];
cu1(0.392699081698724) q[3],q[0];
cu1(0.785398163397448) q[3],q[1];
cu1(1.570796326794897) q[3],q[2];
h q[3];
cu1(0.196349540849362) q[4],q[0];
cu1(0.392699081698724) q[4],q[1];
cu1(0.785398163397448) q[4],q[2];
cu1(1.570796326794897) q[4],q[3];
h q[4];
cu1(0.098174770424681) q[5],q[0];
cu1(0.196349540849362) q[5],q[1];
cu1(0.392699081698724) q[5],q[2];
cu1(0.785398163397448) q[5],q[3];
cu1(1.570796326794897) q[5],q[4];
h q[5];
cu1(0.049087385212341) q[6],q[0];
cu1(0.098174770424681) q[6],q[1];
cu1(0.196349540849362) q[6],q[2];
cu1(0.392699081698724) q[6],q[3];
cu1(0.785398163397448) q[6],q[4];
cu1(1.570796326794897) q[6],q[5];
h q[6];
cu1(0.024543692606170) q[7],q[0];
cu1(0.049087385212341) q[7],q[1];
cu1(0.098174770424681) q[7],q[2];
cu1(0.196349540849362) q[7],q[3];
cu1(0.392699081698724) q[7],q[4];
cu1(0.785398163397448) q[7],q[5];
cu1(1.570796326794897) q[7],q[6];
h q[7];
cu1(0.012271846303085) q[8],q[0];
cu1(0.024543692606170) q[8],q[1];
cu1(0.049087385212341) q[8],q[2];
cu1(0.098174770424681) q[8],q[3];
cu1(0.196349540849362) q[8],q[4];
cu1(0.392699081698724) q[8],q[5];
cu1(0.785398163397448) q[8],q[6];
cu1(1.570796326794897) q[8],q[7];
h q[8];
cu1(0.006135923151543) q[9],q[0];
cu1(0.012271846303085) q[9],q[1];
cu1(0.024543692606170) q[9],q[2];
cu1(0.049087385212341) q[9],q[3];
cu1(0.098174770424681) q[9],q[4];
cu1(0.196349540849362) q[9],q[5];
cu1(0.392699081698724) q[9],q[6];
cu1(0.785398163397448) q[9],q[7];
cu1(1.570796326794897) q[9],q[8];
h q[9];
cu1(0.003067961575771) q[10],q[0];
cu1(0.006135923151543) q[10],q[1];
cu1(0.012271846303085) q[10],q[2];
cu1(0.024543692606170) q[10],q[3];
cu1(0.049087385212341) q[10],q[4];
cu1(0.098174770424681) q[10],q[5];
cu1(0.196349540849362) q[10],q[6];
cu1(0.392699081698724) q[10],q[7];
cu1(0.785398163397448) q[10],q[8];
cu1(1.570796326794897) q[10],q[9];
h q[10];
cu1(0.001533980787886) q[11],q[0];
cu1(0.003067961575771) q[11],q[1];
cu1(0.006135923151543) q[11],q[2];
cu1(0.012271846303085) q[11],q[3];
cu1(0.024543692606170) q[11],q[4];
cu1(0.049087385212341) q[11],q[5];
cu1(0.098174770424681) q[11],q[6];
cu1(0.196349540849362) q[11],q[7];
cu1(0.392699081698724) q[11],q[8];
cu1(0.785398163397448) q[11],q[9];
cu1(1.570796326794897) q[11],q[10];
h q[11];
cu1(0.000766990393943) q[12],q[0];
cu1(0.001533980787886) q[12],q[1];
cu1(0.003067961575771) q[12],q[2];
cu1(0.006135923151543) q[12],q[3];
cu1(0.012271846303085) q[12],q[4];
cu1(0.024543692606170) q[12],q[5];
cu1(0.049087385212341) q[12],q[6];
cu1(0.098174770424681) q[12],q[7];
cu1(0.196349540849362) q[12],q[8];
cu1(0.392699081698724) q[12],q[9];
cu1(0.785398163397448) q[12],q[10];
cu1(1.570796326794897) q[12],q[11];
h q[12];
cu1(0.000383495196971) q[13],q[0];
cu1(0.000766990393943) q[13],q[1];
cu1(0.001533980787886) q[13],q[2];
cu1(0.003067961575771) q[13],q[3];
cu1(0.006135923151543) q[13],q[4];
cu1(0.012271846303085) q[13],q[5];
cu1(0.024543692606170) q[13],q[6];
cu1(0.049087385212341) q[13],q[7];
cu1(0.098174770424681) q[13],q[8];
cu1(0.196349540849362) q[13],q[9];
cu1(0.392699081698724) q[13],q[10];
cu1(0.785398163397448) q[13],q[11];
cu1(1.570796326794897) q[13],q[12];
h q[13];
cu1(0.000191747598486) q[14],q[0];
cu1(0.000383495196971) q[14],q[1];
cu1(0.000766990393943) q[14],q[2];
cu1(0.001533980787886) q[14],q[3];
cu1(0.003067961575771) q[14],q[4];
cu1(0.006135923151543) q[14],q[5];
cu1(0.012271846303085) q[14],q[6];
cu1(0.024543692606170) q[14],q[7];
cu1(0.049087385212341) q[14],q[8];
cu1(0.098174770424681) q[14],q[9];
cu1(0.196349540849362) q[14],q[10];
cu1(0.392699081698724) q[14],q[11];
cu1(0.785398163397448) q[14],q[12];
cu1(1.570796326794897) q[14],q[13];
h q[14];
cu1(0.000095873799243) q[15],q[0];
cu1(0.000191747598486) q[15],q[1];
cu1(0.000383495196971) q[15],q[2];
cu1(0.000766990393943) q[15],q[3];
cu1(0.001533980787886) q[15],q[4];
cu1(0.003067961575771) q[15],q[5];
cu1(0.006135923151543) q[15],q[6];
cu1(0.012271846303085) q[15],q[7];
cu1(0.024543692606170) q[15],q[8];
cu1(0.049087385212341) q[15],q[9];
cu1(0.098174770424681) q[15],q[10];
cu1(0.196349540849362) q[15],q[11];
cu1(0.392699081698724) q[15],q[12];
cu1(0.785398163397448) q[15],q[13];
cu1(1.570796326794897) q[15],q[14];
h q[15];
cu1(0.000047936899621) q[16],q[0];
cu1(0.000095873799243) q[16],q[1];
cu1(0.000191747598486) q[16],q[2];
cu1(0.000383495196971) q[16],q[3];
cu1(0.000766990393943) q[16],q[4];
cu1(0.001533980787886) q[16],q[5];
cu1(0.003067961575771) q[16],q[6];
cu1(0.006135923151543) q[16],q[7];
cu1(0.012271846303085) q[16],q[8];
cu1(0.024543692606170) q[16],q[9];
cu1(0.049087385212341) q[16],q[10];
cu1(0.098174770424681) q[16],q[11];
cu1(0.196349540849362) q[16],q[12];
cu1(0.392699081698724) q[16],q[13];
cu1(0.785398163397448) q[16],q[14];
cu1(1.570796326794897) q[16],q[15];
h q[16];
cu1(0.000023968449811) q[17],q[0];
cu1(0.000047936899621) q[17],q[1];
cu1(0.000095873799243) q[17],q[2];
cu1(0.000191747598486) q[17],q[3];
cu1(0.000383495196971) q[17],q[4];
cu1(0.000766990393943) q[17],q[5];
cu1(0.001533980787886) q[17],q[6];
cu1(0.003067961575771) q[17],q[7];
cu1(0.006135923151543) q[17],q[8];
cu1(0.012271846303085) q[17],q[9];
cu1(0.024543692606170) q[17],q[10];
cu1(0.049087385212341) q[17],q[11];
cu1(0.098174770424681) q[17],q[12];
cu1(0.196349540849362) q[17],q[13];
cu1(0.392699081698724) q[17],q[14];
cu1(0.785398163397448) q[17],q[15];
cu1(1.570796326794897) q[17],q[16];
h q[17];
cu1(0.000011984224905) q[18],q[0];
cu1(0.000023968449811) q[18],q[1];
cu1(0.000047936899621) q[18],q[2];
cu1(0.000095873799243) q[18],q[3];
cu1(0.000191747598486) q[18],q[4];
cu1(0.000383495196971) q[18],q[5];
cu1(0.000766990393943) q[18],q[6];
cu1(0.001533980787886) q[18],q[7];
cu1(0.003067961575771) q[18],q[8];
cu1(0.006135923151543) q[18],q[9];
cu1(0.012271846303085) q[18],q[10];
cu1(0.024543692606170) q[18],q[11];
cu1(0.049087385212341) q[18],q[12];
cu1(0.098174770424681) q[18],q[13];
cu1(0.196349540849362) q[18],q[14];
cu1(0.392699081698724) q[18],q[15];
cu1(0.785398163397448) q[18],q[16];
cu1(1.570796326794897) q[18],q[17];
h q[18];
cu1(0.000005992112453) q[19],q[0];
cu1(0.000011984224905) q[19],q[1];
cu1(0.000023968449811) q[19],q[2];
cu1(0.000047936899621) q[19],q[3];
cu1(0.000095873799243) q[19],q[4];
cu1(0.000191747598486) q[19],q[5];
cu1(0.000383495196971) q[19],q[6];
cu1(0.000766990393943) q[19],q[7];
cu1(0.001533980787886) q[19],q[8];
cu1(0.003067961575771) q[19],q[9];
cu1(0.006135923151543) q[19],q[10];
cu1(0.012271846303085) q[19],q[11];
cu1(0.024543692606170) q[19],q[12];
cu1(0.049087385212341) q[19],q[13];
cu1(0.098174770424681) q[19],q[14];
cu1(0.196349540849362) q[19],q[15];
cu1(0.392699081698724) q[19],q[16];
cu1(0.785398163397448) q[19],q[17];
cu1(1.570796326794897) q[19],q[18];
h q[19];
cu1(0.000002996056226) q[20],q[0];
cu1(0.000005992112453) q[20],q[1];
cu1(0.000011984224905) q[20],q[2];
cu1(0.000023968449811) q[20],q[3];
cu1(0.000047936899621) q[20],q[4];
cu1(0.000095873799243) q[20],q[5];
cu1(0.000191747598486) q[20],q[6];
cu1(0.000383495196971) q[20],q[7];
cu1(0.000766990393943) q[20],q[8];
cu1(0.001533980787886) q[20],q[9];
cu1(0.003067961575771) q[20],q[10];
cu1(0.006135923151543) q[20],q[11];
cu1(0.012271846303085) q[20],q[12];
cu1(0.024543692606170) q[20],q[13];
cu1(0.049087385212341) q[20],q[14];
cu1(0.098174770424681) q[20],q[15];
cu1(0.196349540849362) q[20],q[16];
cu1(0.392699081698724) q[20],q[17];
cu1(0.785398163397448) q[20],q[18];
cu1(1.570796326794897) q[20],q[19];
h q[20];
cu1(0.000001498028113) q[21],q[0];
cu1(0.000002996056226) q[21],q[1];
cu1(0.000005992112453) q[21],q[2];
cu1(0.000011984224905) q[21],q[3];
cu1(0.000023968449811) q[21],q[4];
cu1(0.000047936899621) q[21],q[5];
cu1(0.000095873799243) q[21],q[6];
cu1(0.000191747598486) q[21],q[7];
cu1(0.000383495196971) q[21],q[8];
cu1(0.000766990393943) q[21],q[9];
cu1(0.001533980787886) q[21],q[10];
cu1(0.003067961575771) q[21],q[11];
cu1(0.006135923151543) q[21],q[12];
cu1(0.012271846303085) q[21],q[13];
cu1(0.024543692606170) q[21],q[14];
cu1(0.049087385212341) q[21],q[15];
cu1(0.098174770424681) q[21],q[16];
cu1(0.196349540849362) q[21],q[17];
cu1(0.392699081698724) q[21],q[18];
cu1(0.785398163397448) q[21],q[19];
cu1(1.570796326794897) q[21],q[20];
h q[21];
cu1(0.000000749014057) q[22],q[0];
cu1(0.000001498028113) q[22],q[1];
cu1(0.000002996056226) q[22],q[2];
cu1(0.000005992112453) q[22],q[3];
cu1(0.000011984224905) q[22],q[4];
cu1(0.000023968449811) q[22],q[5];
cu1(0.000047936899621) q[22],q[6];
cu1(0.000095873799243) q[22],q[7];
cu1(0.000191747598486) q[22],q[8];
cu1(0.000383495196971) q[22],q[9];
cu1(0.000766990393943) q[22],q[10];
cu1(0.001533980787886) q[22],q[11];
cu1(0.003067961575771) q[22],q[12];
cu1(0.006135923151543) q[22],q[13];
cu1(0.012271846303085) q[22],q[14];
cu1(0.024543692606170) q[22],q[15];
cu1(0.049087385212341) q[22],q[16];
cu1(0.098174770424681) q[22],q[17];
cu1(0.196349540849362) q[22],q[18];
cu1(0.392699081698724) q[22],q[19];
cu1(0.785398163397448) q[22],q[20];
cu1(1.570796326794897) q[22],q[21];
h q[22];
cu1(0.000000374507028) q[23],q[0];
cu1(0.000000749014057) q[23],q[1];
cu1(0.000001498028113) q[23],q[2];
cu1(0.000002996056226) q[23],q[3];
cu1(0.000005992112453) q[23],q[4];
cu1(0.000011984224905) q[23],q[5];
cu1(0.000023968449811) q[23],q[6];
cu1(0.000047936899621) q[23],q[7];
cu1(0.000095873799243) q[23],q[8];
cu1(0.000191747598486) q[23],q[9];
cu1(0.000383495196971) q[23],q[10];
cu1(0.000766990393943) q[23],q[11];
cu1(0.001533980787886) q[23],q[12];
cu1(0.003067961575771) q[23],q[13];
cu1(0.006135923151543) q[23],q[14];
cu1(0.012271846303085) q[23],q[15];
cu1(0.024543692606170) q[23],q[16];
cu1(0.049087385212341) q[23],q[17];
cu1(0.098174770424681) q[23],q[18];
cu1(0.196349540849362) q[23],q[19];
cu1(0.392699081698724) q[23],q[20];
cu1(0.785398163397448) q[23],q[21];
cu1(1.570796326794897) q[23],q[22];
h q[23];
cu1(0.000000187253514) q[24],q[0];
cu1(0.000000374507028) q[24],q[1];
cu1(0.000000749014057) q[24],q[2];
cu1(0.000001498028113) q[24],q[3];
cu1(0.000002996056226) q[24],q[4];
cu1(0.000005992112453) q[24],q[5];
cu1(0.000011984224905) q[24],q[6];
cu1(0.000023968449811) q[24],q[7];
cu1(0.000047936899621) q[24],q[8];
cu1(0.000095873799243) q[24],q[9];
cu1(0.000191747598486) q[24],q[10];
cu1(0.000383495196971) q[24],q[11];
cu1(0.000766990393943) q[24],q[12];
cu1(0.001533980787886) q[24],q[13];
cu1(0.003067961575771) q[24],q[14];
cu1(0.006135923151543) q[24],q[15];
cu1(0.012271846303085) q[24],q[16];
cu1(0.024543692606170) q[24],q[17];
cu1(0.049087385212341) q[24],q[18];
cu1(0.098174770424681) q[24],q[19];
cu1(0.196349540849362) q[24],q[20];
cu1(0.392699081698724) q[24],q[21];
cu1(0.785398163397448) q[24],q[22];
cu1(1.570796326794897) q[24],q[23];
h q[24];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
cx q[0],q[3];
cx q[0],q[4];
cx q[0],q[5];
cx q[0],q[6];
cx q[0],q[7];
cx q[0],q[8];
cx q[0],q[9];
cx q[0],q[10];
cx q[0],q[11];
cx q[0],q[12];
cx q[0],q[13];
cx q[0],q[14];
cx q[0],q[15];
cx q[0],q[16];
cx q[0],q[17];
cx q[0],q[18];
cx q[0],q[19];
cx q[0],q[20];
cx q[0],q[21];
cx q[0],q[22];
cx q[0],q[23];
cx q[0],q[24];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];
measure q[8] -> c[8];
measure q[9] -> c[9];
measure q[10] -> c[10];
measure q[11] -> c[11];
measure q[12] -> c[12];
measure q[13] -> c[13];
measure q[14] -> c[14];
measure q[15] -> c[15];
measure q[16] -> c[16];
measure q[17] -> c[17];
measure q[18] -> c[18];
measure q[19] -> c[19];
measure q[20] -> c[20];
measure q[21] -> c[21];
measure q[22] -> c[22];
measure q[23] -> c[23];
measure q[24] -> c[24];
