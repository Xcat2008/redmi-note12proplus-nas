/* Process-local EE placement for heterogeneous Linux CPUs. No clock changes.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <dirent.h>
#include <sched.h>
#include <unistd.h>
static cpu_set_t ee_tier;
static bool ee_topology_checked,ee_topology_valid;
static double ee_next_check;
static struct {pid_t tid;cpu_set_t original;} ee_placements[8];
static unsigned ee_placement_count;
static void ee_read_topology(void){
 unsigned capacity[CPU_SETSIZE]={0},maximum=0,minimum=~0u;
 cpu_set_t allowed;if(sched_getaffinity(0,sizeof(allowed),&allowed))return;
 long n=sysconf(_SC_NPROCESSORS_CONF);if(n<=0||n>CPU_SETSIZE)return;
 for(int i=0;i<n;i++)if(CPU_ISSET(i,&allowed)){
  char path[128];snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/cpu_capacity",i);
  FILE*f=fopen(path,"r");if(!f)return;int valid=fscanf(f,"%u",&capacity[i]);fclose(f);
  if(valid!=1||!capacity[i])return;
  if(capacity[i]>maximum)maximum=capacity[i];
  if(capacity[i]<minimum)minimum=capacity[i];
 }
 CPU_ZERO(&ee_tier);for(int i=0;i<n;i++)if(capacity[i]==maximum)CPU_SET(i,&ee_tier);
 ee_topology_valid=minimum<maximum && CPU_COUNT(&ee_tier)>=2 && CPU_COUNT(&ee_tier)<CPU_COUNT(&allowed);
}
static bool ee_thread_name(pid_t tid){
 char path[96],name[32]={0};snprintf(path,sizeof(path),"/proc/self/task/%d/comm",tid);
 FILE*f=fopen(path,"r");if(!f)return false;bool ok=fgets(name,sizeof(name),f)!=NULL;fclose(f);
 return ok && !strcmp(name,"CPU Thread\n");
}
static void ee_restore_placement(void){
 for(unsigned i=0;i<ee_placement_count;i++){
  cpu_set_t current;
  if(ee_thread_name(ee_placements[i].tid) && !sched_getaffinity(ee_placements[i].tid,sizeof(current),&current) && CPU_EQUAL(&current,&ee_tier))
   sched_setaffinity(ee_placements[i].tid,sizeof(current),&ee_placements[i].original);
 }
 ee_placement_count=0;ee_next_check=0;
}
static void ee_update_placement(void){
 double t=now();if(t<ee_next_check)return;ee_next_check=t+1;
 const char*disabled=getenv("ARMSX2_EE_PERFORMANCE_TIER");if(disabled && !strcmp(disabled,"0"))return;
 if(!ee_topology_checked){ee_topology_checked=true;ee_read_topology();}if(!ee_topology_valid)return;
 DIR*d=opendir("/proc/self/task");if(!d)return;struct dirent*entry;
 while((entry=readdir(d))){
  char*end;long number=strtol(entry->d_name,&end,10);if(*end || number<=0)continue;pid_t tid=(pid_t)number;
  if(!ee_thread_name(tid))continue;
  cpu_set_t current;
  if(sched_getaffinity(tid,sizeof(current),&current) || CPU_EQUAL(&current,&ee_tier))continue;
  /* Respect a narrower affinity explicitly selected elsewhere. */
  if(CPU_COUNT(&current)<=CPU_COUNT(&ee_tier))continue;
  cpu_set_t intersection;CPU_AND(&intersection,&current,&ee_tier);if(!CPU_EQUAL(&intersection,&ee_tier))continue;
  unsigned index=0;for(;index<ee_placement_count;index++)if(ee_placements[index].tid==tid)break;
  if(index==ee_placement_count){if(index>=8)continue;ee_placements[index].tid=tid;ee_placements[index].original=current;ee_placement_count++;}
  sched_setaffinity(tid,sizeof(ee_tier),&ee_tier);
 }
 closedir(d);
}
