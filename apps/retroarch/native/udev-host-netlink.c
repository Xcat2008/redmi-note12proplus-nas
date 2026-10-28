#define _GNU_SOURCE
#include <sys/socket.h>
#include <linux/netlink.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <pthread.h>

/* Only the native RetroArch process uses this inherited host-udev socket pool.
 * X11 remains in the container network, while gamepad notifications originate
 * in the host network. No privilege or setns operation is needed in RetroArch.
 */
static pthread_mutex_t pool_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned pool_index;

int socket(int domain, int type, int protocol) {
    static int (*next_socket)(int, int, int);
    if (!next_socket) next_socket = dlsym(RTLD_NEXT, "socket");
    if (domain == AF_NETLINK && protocol == NETLINK_KOBJECT_UEVENT) {
        const char *pool = getenv("REDMI_NAS_UDEV_FDS");
        if (pool && *pool) {
            pthread_mutex_lock(&pool_lock);
            unsigned current = 0;
            const char *cursor = pool;
            while (*cursor && current < pool_index) {
                if (*cursor++ == ',') current++;
            }
            if (*cursor) {
                char *end;
                long inherited = strtol(cursor, &end, 10);
                struct sockaddr_nl address;
                socklen_t length = sizeof(address);
                if (end != cursor && inherited >= 3 && inherited <= 1048575 &&
                    getsockname((int)inherited, (struct sockaddr *)&address, &length) == 0 &&
                    address.nl_family == AF_NETLINK) {
                    int fd = fcntl((int)inherited, (type & SOCK_CLOEXEC) ? F_DUPFD_CLOEXEC : F_DUPFD, 3);
                    if (fd >= 0) {
                        pool_index++;
                        if (type & SOCK_NONBLOCK) {
                            int flags = fcntl(fd, F_GETFL);
                            if (flags >= 0) fcntl(fd, F_SETFL, flags | O_NONBLOCK);
                        }
                        close((int)inherited);
                        pthread_mutex_unlock(&pool_lock);
                        return fd;
                    }
                }
            }
            pthread_mutex_unlock(&pool_lock);
        }
    }
    return next_socket(domain, type, protocol);
}
