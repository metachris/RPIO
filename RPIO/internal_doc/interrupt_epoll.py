import select

gpio_id = 17
sys_gpio_root = '/sys/class/gpio/'
pin_base = sys_gpio_root + "gpio%s/" % gpio_id

f = open(pin_base + 'value', 'r')

poll = select.epoll()
poll.register(f.fileno(), select.EPOLLPRI | select.EPOLLET)

while True:
    events = poll.poll(1)
    for fileno, event in events:
        if event & select.EPOLLPRI:
            val = f.read().strip()  # readline is workaround for not getting new values
            f.seek(0)
            print val  # 0 or 1
