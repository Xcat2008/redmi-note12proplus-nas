#include "libretro.h"
#include <time.h>
static retro_video_refresh_t video;
static double next_frame;
static int frozen;
static double clock_seconds(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
void retro_set_video_refresh(retro_video_refresh_t cb){video=cb;}
void mock_freeze(int enabled){frozen=enabled;}
void retro_run(void){double t=clock_seconds();if(!frozen && t>=next_frame){next_frame=t+1.0/60;video(RETRO_HW_FRAME_BUFFER_VALID,640,448,0);}else video(NULL,640,448,0);}
