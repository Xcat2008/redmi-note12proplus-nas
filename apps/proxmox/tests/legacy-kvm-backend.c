/* SPDX-License-Identifier: MIT
 * Hermetic regression backend: no KVM device or real CPU affinity is used.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <linux/kvm.h>
#include <sched.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <sys/ioctl.h>

static cpu_set_t mask;
static int block_a78;
void mock_reset(void) {
    CPU_ZERO(&mask);
    for (int i=0;i<8;i++) CPU_SET(i,&mask);
    block_a78=0;
}
unsigned mock_mask(void) {
    unsigned bits=0;
    for(int i=0;i<8;i++) if(CPU_ISSET(i,&mask)) bits|=1U<<i;
    return bits;
}
void mock_block_a78(int value) { block_a78=value; }
int sched_getaffinity(pid_t pid,size_t size,cpu_set_t *dest) {
    (void)pid;
    if(size<sizeof(mask)) { errno=EINVAL;return -1; }
    memcpy(dest,&mask,sizeof(mask));return 0;
}
int sched_setaffinity(pid_t pid,size_t size,const cpu_set_t *src) {
    (void)pid;
    if(size<sizeof(mask) || CPU_COUNT(src)==0) { errno=EINVAL;return -1; }
    for(int i=8;i<CPU_SETSIZE;i++) if(CPU_ISSET(i,src)) { errno=EINVAL;return -1; }
    if(block_a78 && (CPU_ISSET(6,src)||CPU_ISSET(7,src))) { errno=EINVAL;return -1; }
    memcpy(&mask,src,sizeof(mask));return 0;
}
int ioctl(int fd,unsigned long request,...) {
    (void)fd;
    va_list args;va_start(args,request);
    unsigned long argument=va_arg(args,unsigned long);va_end(args);
    if(request==KVM_GET_ONE_REG || request==KVM_SET_ONE_REG) {
        struct kvm_one_reg *reg=(void *)argument;
        int cpu=0;
        while(cpu<8 && !CPU_ISSET(cpu,&mask)) cpu++;
        uint32_t expected=cpu>=6 ? 0x7010001aU : 0x7000001aU;
        uint32_t *value=(void *)(uintptr_t)reg->addr;
        if(request==KVM_GET_ONE_REG) { *value=expected;return 0; }
        if(*value!=expected) { errno=EINVAL;return -1; }
        return 0;
    }
    errno=ENOTTY;return -1;
}
