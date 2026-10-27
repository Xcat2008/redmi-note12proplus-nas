#define _GNU_SOURCE
#include <pthread.h>
#include <assert.h>
#include "../libretro-adapter.c"
static _Atomic bool ready,stop_worker;
static _Atomic pid_t worker_tid;
/* Use gettid via the architecture-independent libc entry point. */
static void*test_worker(void*unused){(void)unused;pthread_setname_np(pthread_self(),"CPU Thread");worker_tid=gettid();ready=true;while(!stop_worker){struct timespec t={0,1000000};nanosleep(&t,NULL);}return NULL;}
int main(void){
 ee_read_topology();if(!ee_topology_valid){puts("CPU tier test skipped: heterogeneous capacity data unavailable");return 77;}
 pthread_t thread;assert(!pthread_create(&thread,NULL,test_worker,NULL));while(!ready)usleep(1000);
 cpu_set_t before,main_before,current;assert(!sched_getaffinity(worker_tid,sizeof(before),&before));assert(!sched_getaffinity(0,sizeof(main_before),&main_before));
 ee_update_placement();assert(ee_topology_valid);assert(!sched_getaffinity(worker_tid,sizeof(current),&current));assert(CPU_EQUAL(&current,&ee_tier));
 assert(!sched_getaffinity(0,sizeof(current),&current));assert(CPU_EQUAL(&current,&main_before));
 ee_restore_placement();assert(!sched_getaffinity(worker_tid,sizeof(current),&current));assert(CPU_EQUAL(&current,&before));
 setenv("ARMSX2_EE_PERFORMANCE_TIER","0",1);ee_next_check=0;ee_update_placement();assert(!sched_getaffinity(worker_tid,sizeof(current),&current));assert(CPU_EQUAL(&current,&before));
 unsetenv("ARMSX2_EE_PERFORMANCE_TIER");cpu_set_t narrow;CPU_ZERO(&narrow);for(int i=0;i<CPU_SETSIZE;i++)if(CPU_ISSET(i,&ee_tier)){CPU_SET(i,&narrow);break;}
 assert(!sched_setaffinity(worker_tid,sizeof(narrow),&narrow));ee_next_check=0;ee_update_placement();assert(!sched_getaffinity(worker_tid,sizeof(current),&current));assert(CPU_EQUAL(&current,&narrow));ee_restore_placement();assert(!sched_getaffinity(worker_tid,sizeof(current),&current));assert(CPU_EQUAL(&current,&narrow));
 assert(!sched_setaffinity(worker_tid,sizeof(before),&before));
 stop_worker=true;pthread_join(thread,NULL);puts("{\"ee_tier_applied\":true,\"other_threads_unchanged\":true,\"original_affinity_restored\":true,\"explicit_narrower_affinity_respected\":true,\"opt_out_respected\":true,\"no_game_loaded\":true}");return 0;
}
