/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <linux/kvm.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
extern void mock_reset(void);
extern unsigned mock_mask(void);
extern void mock_block_a78(int);
static void pin(int cpu) {
    cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(cpu,&mask);
    assert(sched_setaffinity(0,sizeof(mask),&mask)==0);
}
int main(int argc,char **argv) {
    assert(argc==2);int adapted=strcmp(argv[1],"adapted")==0;
    mock_reset();uint64_t value=0;
    struct kvm_one_reg reg={.id=0x6020000000110000ULL,.addr=(uintptr_t)&value};
    assert(ioctl(900,KVM_GET_ONE_REG,&reg)==0);
    assert(mock_mask()==255);
    pin(adapted ? 0 : 6);
    int restored=ioctl(900,KVM_SET_ONE_REG,&reg);
    if(!adapted) {
        assert(restored==-1 && errno==EINVAL);
        puts("legacy mixed-cache failure reproduced");return 0;
    }
    assert(restored==0 && mock_mask()==1);
    value^=0xffffffffU;
    assert(ioctl(900,KVM_SET_ONE_REG,&reg)==-1 && errno==EINVAL);
    assert(mock_mask()==1);
    assert(ioctl(900,0xCAFEUL,0UL)==-1 && errno==ENOTTY);
    assert(mock_mask()==1);
    mock_reset();pin(7);
    assert(ioctl(900,KVM_GET_ONE_REG,&reg)==0 && value==0x7010001aU);
    assert(mock_mask()==128);
    mock_reset();pin(0);mock_block_a78(1);
    assert(ioctl(900,KVM_GET_ONE_REG,&reg)==-1 && errno==EINVAL);
    assert(mock_mask()==1);
    puts("cache restored across clusters; affinity/errors preserved; unavailable reference CPU rejected");
    return 0;
}
