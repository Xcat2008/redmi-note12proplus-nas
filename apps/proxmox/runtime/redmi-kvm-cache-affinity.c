/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 José Miranda (Xcat2008)
 * Userspace compatibility for the 4.19 ARM KVM per-CPU CCSIDR ioctls.
 * Keep only cache-description GET/SET_ONE_REG calls on a consistent CPU.
 * Actual guest execution and all other ioctls retain their original affinity.
 * The kernel still validates every register; values/errors are never replaced.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdarg.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <linux/kvm.h>

static int (*original_ioctl)(int, unsigned long, ...);
static pthread_once_t once = PTHREAD_ONCE_INIT;
static void resolve_ioctl(void) {
    *(void **)(&original_ioctl) = dlsym(RTLD_NEXT, "ioctl");
}

int ioctl(int fd, unsigned long request, ...) {
    va_list args;
    va_start(args, request);
    unsigned long argument = va_arg(args, unsigned long);
    va_end(args);
    pthread_once(&once, resolve_ioctl);
    if (!original_ioctl) { errno = ENOSYS; return -1; }

    int cache = 0;
    if ((request == KVM_GET_ONE_REG || request == KVM_SET_ONE_REG) && argument) {
        const struct kvm_one_reg *reg = (const void *)argument;
        cache = ((reg->id & 0xffff0000ULL) == 0x00110000ULL)
             && ((reg->id >> 60) == 6);
    }
    if (!cache) return original_ioctl(fd, request, argument);

    cpu_set_t saved, fixed;
    if (sched_getaffinity(0, sizeof(saved), &saved)) return -1;
    /* Metadata always comes from an A78, even if a vCPU executes on an A55.
     * This does not escape cgroup CPU restrictions: sched_setaffinity still
     * enforces them. CPU7 has the same cache geometry and is a safe fallback.
     */
    if (CPU_COUNT(&saved) == 1 && (CPU_ISSET(6, &saved) || CPU_ISSET(7, &saved)))
        return original_ioctl(fd, request, argument);
    CPU_ZERO(&fixed); CPU_SET(6, &fixed);
    if (sched_setaffinity(0, sizeof(fixed), &fixed)) {
        CPU_ZERO(&fixed); CPU_SET(7, &fixed);
        if (sched_setaffinity(0, sizeof(fixed), &fixed)) return -1;
    }
    int result = original_ioctl(fd, request, argument);
    int result_errno = errno;
    if (sched_setaffinity(0, sizeof(saved), &saved)) return -1;
    errno = result_errno;
    return result;
}
