all: gpio

gpio:
	mkdir -p build
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.7 -c py_gpio.c -o build/py_gpio.o
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.7 -c c_gpio.c -o build/c_gpio.o
	gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.7 -c cpuinfo.c -o build/cpuinfo.o
	gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions -Wl,-z,relro build/py_gpio.o build/c_gpio.o build/cpuinfo.o -o build/GPIO.so

clean:
	rm -rf build
