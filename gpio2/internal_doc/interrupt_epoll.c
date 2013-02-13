#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <sys/types.h>

int main(int argc, char** argv) {
    int n;
    int epfd = epoll_create(1);
    int fd = open("/sys/class/gpio/gpio17/value", O_RDWR | O_NONBLOCK);
    printf("open returned %d: %s\n", fd, strerror(errno));
    if(fd > 0) {
        char buf = 0;

        struct epoll_event ev;
        struct epoll_event events;
        ev.events = EPOLLPRI;
        ev.data.fd = fd;

        n = epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev);
        printf("epoll_ctl returned %d: %s\n", n, strerror(errno));

        while(1) {
            n = epoll_wait(epfd, &events, 1, -1);
            printf("epoll returned %d: %s\n", n, strerror(errno));

            if(n > 0) {
                n = lseek(fd, 0, SEEK_SET);
                printf("seek %d bytes: %s\n", n, strerror(errno));
                n = read(fd, &buf, 1);
                printf("read %d bytes: %s\n", n, strerror(errno));
                printf("buf = 0x%x\n", buf);
            }
        }
    }

    return(0);
}

