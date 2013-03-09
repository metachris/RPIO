all: pwm py

pwm:
	gcc -Wall -g -O2 -o pwm pwm.c

py2.6:
	mkdir -p build
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.6 -c pwm.c -o build/pwm.o
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.6 -c pwm_py.c -o build/pwm_py.o
	gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-z,relro build/pwm.o build/pwm_py.o -o _PWM.so
	rm -rf build

py2.7:
	mkdir -p build
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.7 -c pwm.c -o build/pwm.o
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.7 -c pwm_py.c -o build/pwm_py.o
	gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-z,relro build/pwm.o build/pwm_py.o -o _PWM.so
	rm -rf build

py3.2:
	mkdir -p build
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python3.2mu -c pwm.c -o build/pwm.o
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python3.2mu -c pwm_py.c -o build/pwm_py.o
	gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-z,relro build/pwm.o build/pwm_py.o -o _PWM.so
	rm -rf build
