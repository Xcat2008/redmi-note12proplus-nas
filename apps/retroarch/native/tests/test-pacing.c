#define _GNU_SOURCE
#include <assert.h>
#include <unistd.h>
#include "../libretro-adapter.c"
static unsigned copies,new_copies;
static void synthetic_display(const void*data,unsigned w,unsigned h,size_t pitch){(void)w;(void)h;(void)pitch;copies++;if(data)new_copies++;usleep(4000);}
int main(int argc,char**argv){
 assert(argc==2);
 library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);assert(library);retro_set_video_refresh(synthetic_display);
 setenv("ARMSX2_RENDERER","Vulkan",1);setenv("ARMSX2_WAIT_FOR_FRAME","0",1);wait_for_frame=-1;
 double start=now();while(now()-start<1)retro_run();unsigned before=copies,before_new=new_copies;copies=new_copies=0;
 unsetenv("ARMSX2_WAIT_FOR_FRAME");wait_for_frame=-1;start=now();while(now()-start<1)retro_run();unsigned after=copies,after_new=new_copies;
 assert(after<before/2 && after_new>=45 && before_new>=40);
 ((void(*)(int))dlsym(library,"mock_freeze"))(1);start=now();retro_run();double no_frame_ms=(now()-start)*1000;assert(no_frame_ms>=19 && no_frame_ms<100);
 setenv("ARMSX2_WAIT_FOR_FRAME","0",1);wait_for_frame=-1;start=now();retro_run();double opt_out_ms=(now()-start)*1000;assert(opt_out_ms<19);
 printf("{\"synthetic_display_calls_before\":%u,\"synthetic_display_calls_after\":%u,\"new_frames_before\":%u,\"new_frames_after\":%u,\"no_frame_wait_ms\":%.3f,\"opt_out_ms\":%.3f,\"no_game_loaded\":true}\n",before,after,before_new,after_new,no_frame_ms,opt_out_ms);return 0;
}
