#define _GNU_SOURCE
/* Private libretro ABI adapter. Upstream binary remains unmodified.
 * Select the phone's GLES context and isolate trial settings/memory cards.
 * GPL-3.0-or-later. */
#include "libretro.h"
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <stdint.h>
#include <stdatomic.h>
#include <locale.h>
#include <string.h>
static void *library;
static retro_environment_t frontend;
static retro_video_refresh_t video;
static retro_audio_sample_batch_t audio_batch;
static double now(void);
static _Atomic uint64_t audio_frames,last_audio_ns,max_audio_gap_ns;
static double max_core_ms,max_video_gap_ms,last_video_time;
static size_t audio_refresh(const int16_t *data,size_t n){atomic_fetch_add(&audio_frames,n);uint64_t t=(uint64_t)(now()*1e9),previous=atomic_exchange(&last_audio_ns,t);
if(previous){uint64_t gap=t-previous,peak=atomic_load(&max_audio_gap_ns);while(gap>peak&&!atomic_compare_exchange_weak(&max_audio_gap_ns,&peak,gap)){} }
return audio_batch?audio_batch(data,n):n;}
static uint64_t runs,frames,dupes;
static double epoch,cost_ms;
static int wait_for_frame=-1;
static bool defer_duplicate;
static unsigned last_width=640,last_height=448;
static double now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9; }
#include "cpu-tier-placement.h"
static void video_refresh(const void *data,unsigned w,unsigned h,size_t pitch) {
    if (data) {frames++;double t=now();if(last_video_time && (t-last_video_time)*1000>max_video_gap_ms)max_video_gap_ms=(t-last_video_time)*1000;last_video_time=t;} else dupes++;
    last_width=w;last_height=h;
    if (!data && defer_duplicate) return;
    video(data,w,h,pitch);
}
static void *symbol(const char *name) {
    if (!library) library=dlopen("/usr/local/lib/redmi-nas/retroarch/armsx2-official.so",RTLD_NOW|RTLD_LOCAL);
    void *p=library?dlsym(library,name):NULL;
    if (!p) { fprintf(stderr,"ARMSX2 adapter: unavailable ABI symbol %s\n",name); abort(); }
    return p;
}
static bool environment(unsigned cmd,void *data) {
    if (cmd==RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY) {
        *(const char **)data="/DATA/AppData/custom-retroarch/armsx2-system";
        return true;
    }
    if (cmd==RETRO_ENVIRONMENT_GET_VARIABLE) {
        struct retro_variable *v=data;
        bool ok=frontend(cmd,data);
        if (v && v->key && !strcmp(v->key,"armsx2_renderer")) {
            const char *requested=getenv("ARMSX2_RENDERER");
            v->value=requested && !strcmp(requested,"Vulkan")?"Vulkan":"OpenGL";ok=true;
        }
        if (v && v->key && getenv("ARMSX2_LOG_PROFILE")) {
            static unsigned seen;
            static const char *keys[]={"armsx2_renderer","armsx2_upscale","armsx2_mtvu","armsx2_hw_download_mode","armsx2_ee_cycle_rate","armsx2_ee_cycle_skip"};
            for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++)if(!strcmp(v->key,keys[i])&&!(seen&(1u<<i))){
                seen|=1u<<i;
                const char *value=ok&&v->value?v->value:"default";
                if(strlen(value)<40&&strspn(value,"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .%_-")==strlen(value))
                    fprintf(stderr,"ARMSX2 selected profile: %s=%s\n",keys[i],value);
            }
        }
        return ok;
    }
    if (cmd==RETRO_ENVIRONMENT_SET_HW_RENDER) {
        struct retro_hw_render_callback *h=data;
        if (h->context_type==RETRO_HW_CONTEXT_OPENGL_CORE || h->context_type==RETRO_HW_CONTEXT_OPENGL) {
            h->context_type=RETRO_HW_CONTEXT_OPENGLES_VERSION;
            h->version_major=3; h->version_minor=2;
            if (frontend(cmd,data)) return true;
            h->context_type=RETRO_HW_CONTEXT_OPENGLES3;
            h->version_major=3; h->version_minor=0;
            bool ok=frontend(cmd,data);
            fprintf(stderr,"ARMSX2 adapter: GLES3 request %s; actual GLES version is checked by GSDeviceOGL.\n",ok?"accepted":"rejected");
            return ok;
        }
    }
    return frontend(cmd,data);
}
void retro_set_environment(retro_environment_t cb) { frontend=cb; ((void(*)(retro_environment_t))symbol("retro_set_environment"))(environment); }
#define V0(n) void n(void){((void(*)(void))symbol(#n))();}
#define V1(n,t,a) void n(t a){((void(*)(t))symbol(#n))(a);}
#define R0(r,n) r n(void){return ((r(*)(void))symbol(#n))();}
#define R1(r,n,t,a) r n(t a){return ((r(*)(t))symbol(#n))(a);}
void retro_set_video_refresh(retro_video_refresh_t cb) { video=cb;((void(*)(retro_video_refresh_t))symbol("retro_set_video_refresh"))(video_refresh); }
V1(retro_set_audio_sample,retro_audio_sample_t,cb)
void retro_set_audio_sample_batch(retro_audio_sample_batch_t cb){audio_batch=cb;((void(*)(retro_audio_sample_batch_t))symbol("retro_set_audio_sample_batch"))(audio_refresh);}
V1(retro_set_input_poll,retro_input_poll_t,cb)
V1(retro_set_input_state,retro_input_state_t,cb)
V0(retro_init) V0(retro_reset)
void retro_deinit(void){ee_restore_placement();((void(*)(void))symbol("retro_deinit"))();}
void retro_run(void) {
    ee_update_placement();
    double t=now(); if (!epoch) epoch=t;
    if (wait_for_frame<0) { const char *v=getenv("ARMSX2_WAIT_FOR_FRAME"), *renderer=getenv("ARMSX2_RENDERER");wait_for_frame=v?*v=='1':renderer && !strcmp(renderer,"Vulkan"); }
    uint64_t before=frames;
    defer_duplicate=wait_for_frame;
    void (*run)(void)=symbol("retro_run");
    do {
        run();
        if (!wait_for_frame || frames!=before || now()-t>=0.020) break;
        struct timespec pause={0,1000000};nanosleep(&pause,NULL);
    } while (1);
    defer_duplicate=false;
    if (wait_for_frame && frames==before) video(NULL,last_width,last_height,0);
    runs++;double core_ms=(now()-t)*1000;cost_ms+=core_ms;if(core_ms>max_core_ms)max_core_ms=core_ms;
    double elapsed=now()-epoch;
    if (elapsed>=10) {
        FILE *f=fopen("/DATA/AppData/custom-retroarch/armsx2-trial/runtime-metrics.json.new","w");
        if (f) {
            locale_t loc=newlocale(LC_NUMERIC_MASK,"C",NULL),old=uselocale(loc);
            uint64_t audio=atomic_exchange(&audio_frames,0);
            fprintf(f,"{\"seconds\":%.3f,\"frontend_calls\":%llu,\"new_video_frames\":%llu,\"duplicate_frames\":%llu,\"new_video_fps\":%.3f,\"audio_frames_per_second\":%.3f,\"mean_core_call_ms\":%.3f,\"max_core_call_ms\":%.3f,\"max_video_gap_ms\":%.3f,\"max_audio_gap_ms\":%.3f,\"monotonic\":%.3f}\n",elapsed,(unsigned long long)runs,(unsigned long long)frames,(unsigned long long)dupes,frames/elapsed,audio/elapsed,cost_ms/runs,max_core_ms,max_video_gap_ms,atomic_exchange(&max_audio_gap_ns,0)/1e6,now());
            uselocale(old);freelocale(loc);
            fclose(f);rename("/DATA/AppData/custom-retroarch/armsx2-trial/runtime-metrics.json.new","/DATA/AppData/custom-retroarch/armsx2-trial/runtime-metrics.json");
        }
        epoch=now();runs=frames=dupes=0;cost_ms=0;max_core_ms=max_video_gap_ms=0;
    }
}
V0(retro_cheat_reset)
void retro_unload_game(void){((void(*)(void))symbol("retro_unload_game"))();ee_restore_placement();}
R0(unsigned,retro_api_version) R0(unsigned,retro_get_region)
R0(size_t,retro_serialize_size)
V1(retro_get_system_info,struct retro_system_info *,info)
V1(retro_get_system_av_info,struct retro_system_av_info *,info)
R1(bool,retro_load_game,const struct retro_game_info *,info)
R1(void *,retro_get_memory_data,unsigned,id)
R1(size_t,retro_get_memory_size,unsigned,id)
void retro_set_controller_port_device(unsigned p,unsigned d){((void(*)(unsigned,unsigned))symbol("retro_set_controller_port_device"))(p,d);}
bool retro_serialize(void *d,size_t s){return ((bool(*)(void *,size_t))symbol("retro_serialize"))(d,s);}
bool retro_unserialize(const void *d,size_t s){return ((bool(*)(const void *,size_t))symbol("retro_unserialize"))(d,s);}
void retro_cheat_set(unsigned i,bool e,const char *c){((void(*)(unsigned,bool,const char *))symbol("retro_cheat_set"))(i,e,c);}
bool retro_load_game_special(unsigned t,const struct retro_game_info *i,size_t n){return ((bool(*)(unsigned,const struct retro_game_info *,size_t))symbol("retro_load_game_special"))(t,i,n);}
