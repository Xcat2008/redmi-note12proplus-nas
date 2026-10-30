// SPDX-License-Identifier: AGPL-3.0-only
// Redmi NAS integration by Jose Miranda (Xcat2008).
#define _GNU_SOURCE
#include "mediatek-h264-colour.h"
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <unistd.h>

/* Pixelflux MMAP buffers -> MediaTek ION DMA-BUF for the pinned Redmi vendor ABI.
 * Only affects the mtk-vcodec-enc device in the process explicitly loading it.
 * No global loader setting or kernel modification is made. */
struct ion_alloc {size_t len,align;unsigned int heaps,flags;int handle;};
struct ion_fd {int handle,fd;};
#define ION_ALLOC _IOWR('I',0,struct ion_alloc)
#define ION_FREE _IOWR('I',1,int)
#define ION_SHARE _IOWR('I',4,struct ion_fd)
#define MAX_FDS 4096
#define MAX_BUFFERS 64
struct plane {int fd;size_t length;off_t offset;void *view;};
struct buffer {unsigned int nplanes;struct plane plane[VIDEO_MAX_PLANES];};
struct queue {int active;unsigned int count;struct buffer buffers[MAX_BUFFERS];};
struct device {int checked,enabled,first_frame;unsigned width,height,format;struct queue capture,output;};
static struct device devices[MAX_FDS];
static int (*original_ioctl)(int,unsigned long,...);
static int (*original_close)(int);
static void *(*original_mmap)(void*,size_t,int,int,int,off_t);
static pthread_once_t init_once=PTHREAD_ONCE_INIT;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static void before_fork(void){pthread_mutex_lock(&lock);}
static void after_fork(void){pthread_mutex_unlock(&lock);}
static void initialize(void){
 original_ioctl=dlsym(RTLD_NEXT,"ioctl");original_mmap=dlsym(RTLD_NEXT,"mmap");original_close=dlsym(RTLD_NEXT,"close");
 /* Pixelflux forks encoder workers from a threaded capture process. */
 pthread_atfork(before_fork,after_fork,after_fork);
}
static int eligible(int fd){
 if(fd<0||fd>=MAX_FDS)return 0;
 struct device *d=&devices[fd];
 if(!d->checked){
  struct v4l2_capability cap={0};d->checked=1;
  if(original_ioctl(fd,VIDIOC_QUERYCAP,&cap)==0&&!strcmp((char*)cap.driver,"mtk-vcodec-enc")){
   d->enabled=1;fprintf(stderr,"[NAS-DMA] %s fd=%d selected\n",cap.driver,fd);
  }
 }
 return d->enabled;
}
static struct queue *queue_for(int fd,unsigned int type){
 if(type==V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE)return &devices[fd].capture;
 if(type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE)return &devices[fd].output;
 return NULL;
}
static void release_queue(struct queue *q){
 for(unsigned int i=0;i<q->count;i++)for(unsigned int p=0;p<q->buffers[i].nplanes;p++){
  if(q->buffers[i].plane[p].fd>=0)original_close(q->buffers[i].plane[p].fd);
 }
 memset(q,0,sizeof(*q));
}
static int allocate_ion(size_t length){
 int ion=open("/dev/ion",O_RDWR|O_CLOEXEC);if(ion<0)return -1;
 struct ion_alloc a={.len=(length+4095)&~(size_t)4095,.align=4096,.heaps=1U<<10,.flags=0};
 if(original_ioctl(ion,ION_ALLOC,&a)<0){int e=errno;original_close(ion);errno=e;return -1;}
 struct ion_fd data={.handle=a.handle,.fd=-1};
 int ret=original_ioctl(ion,ION_SHARE,&data);int saved=errno;
 original_ioctl(ion,ION_FREE,&a.handle);original_close(ion);
 if(ret<0){errno=saved;return -1;}
 fcntl(data.fd,F_SETFD,FD_CLOEXEC);return data.fd;
}
int ioctl(int fd,unsigned long request,...){
 va_list args;va_start(args,request);void *arg=va_arg(args,void*);va_end(args);
 pthread_once(&init_once,initialize);
 /* The driver's default H.264 level is 1.0, below a 720p desktop. Select a
  * real supported level after geometry and frame rate are known. */
 if(request==VIDIOC_S_PARM){
  pthread_mutex_lock(&lock);int applies=eligible(fd);pthread_mutex_unlock(&lock);
  int r=original_ioctl(fd,request,arg);
  if(r||!applies||devices[fd].format!=V4L2_PIX_FMT_H264)return r;
  struct v4l2_streamparm *p=arg;
  if(p->type!=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE)return r;
  unsigned n=p->parm.output.timeperframe.numerator,d=p->parm.output.timeperframe.denominator;
  if(!n||!d){errno=EINVAL;return -1;}
  uint64_t blocks=((devices[fd].width+15U)/16U)*((uint64_t)(devices[fd].height+15U)/16U);
  uint64_t rate=(blocks*d+n-1)/n;int level;
  if(blocks<=3600&&rate<=108000)level=V4L2_MPEG_VIDEO_H264_LEVEL_3_1;
  else if(blocks<=5120&&rate<=216000)level=V4L2_MPEG_VIDEO_H264_LEVEL_3_2;
  else if(blocks<=8192&&rate<=245760)level=V4L2_MPEG_VIDEO_H264_LEVEL_4_0;
  else if(blocks<=8704&&rate<=522240)level=V4L2_MPEG_VIDEO_H264_LEVEL_4_2;
  else if(blocks<=36864&&rate<=983040)level=V4L2_MPEG_VIDEO_H264_LEVEL_5_1;
  else level=V4L2_MPEG_VIDEO_H264_LEVEL_5_2;
  struct v4l2_control control={.id=V4L2_CID_MPEG_VIDEO_H264_LEVEL,.value=level};
  return original_ioctl(fd,VIDIOC_S_CTRL,&control);
 }
 /* Translate the sequence-header request to the vendor's joined-header control. */
 if(request==VIDIOC_S_CTRL){
  struct v4l2_control *c=arg;
  if(c->id==V4L2_CID_MPEG_VIDEO_REPEAT_SEQ_HEADER&&c->value==1){
   pthread_mutex_lock(&lock);int applies=eligible(fd);pthread_mutex_unlock(&lock);
   if(applies){unsigned id=c->id;c->id=V4L2_CID_MPEG_VIDEO_HEADER_MODE;
    c->value=V4L2_MPEG_VIDEO_HEADER_MODE_JOINED_WITH_1ST_FRAME;
    int r=original_ioctl(fd,request,arg);c->id=id;c->value=1;return r;}
  }
 }
 /* pixelflux names X11 BGRA as AB24; this vendor names the same
  * little-endian byte layout AR24. Scope the translation to its encoder. */
 if(request==VIDIOC_ENUM_FMT||request==VIDIOC_S_FMT||request==VIDIOC_G_FMT||request==VIDIOC_TRY_FMT){
  pthread_mutex_lock(&lock);int applies=eligible(fd);pthread_mutex_unlock(&lock);
  if(!applies)return original_ioctl(fd,request,arg);
  if(request==VIDIOC_ENUM_FMT){
   int r=original_ioctl(fd,request,arg);struct v4l2_fmtdesc *f=arg;
   if(!r&&f->type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE&&f->pixelformat==v4l2_fourcc('A','R','2','4'))f->pixelformat=v4l2_fourcc('A','B','2','4');
   return r;
  }
  struct v4l2_format *f=arg;int translate=f->type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE&&f->fmt.pix_mp.pixelformat==v4l2_fourcc('A','B','2','4');
  if(request==VIDIOC_S_FMT){
   f->fmt.pix_mp.colorspace=V4L2_COLORSPACE_SMPTE170M;
   f->fmt.pix_mp.ycbcr_enc=V4L2_YCBCR_ENC_601;
   f->fmt.pix_mp.quantization=V4L2_QUANTIZATION_LIM_RANGE;
   f->fmt.pix_mp.xfer_func=V4L2_XFER_FUNC_709;
  }
  if(translate)f->fmt.pix_mp.pixelformat=v4l2_fourcc('A','R','2','4');
  int r=original_ioctl(fd,request,arg);
  if(!r&&request==VIDIOC_S_FMT&&f->type==V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE){
   devices[fd].width=f->fmt.pix_mp.width;devices[fd].height=f->fmt.pix_mp.height;devices[fd].format=f->fmt.pix_mp.pixelformat;devices[fd].first_frame=1;
  }
  if(translate&&f->fmt.pix_mp.pixelformat==v4l2_fourcc('A','R','2','4'))f->fmt.pix_mp.pixelformat=v4l2_fourcc('A','B','2','4');
  return r;
 }
 if(request!=VIDIOC_REQBUFS&&request!=VIDIOC_QUERYBUF&&request!=VIDIOC_QBUF&&request!=VIDIOC_DQBUF&&request!=VIDIOC_EXPBUF)return original_ioctl(fd,request,arg);
 pthread_mutex_lock(&lock);
 if(!eligible(fd)){pthread_mutex_unlock(&lock);return original_ioctl(fd,request,arg);}
 if(request==VIDIOC_REQBUFS){
  struct v4l2_requestbuffers *r=arg;struct queue *q=queue_for(fd,r->type);
  if(!q||r->memory!=V4L2_MEMORY_MMAP){pthread_mutex_unlock(&lock);return original_ioctl(fd,request,arg);}
  if(r->count>MAX_BUFFERS){pthread_mutex_unlock(&lock);errno=E2BIG;return -1;}
  unsigned int original=r->memory;r->memory=V4L2_MEMORY_DMABUF;
  int ret=original_ioctl(fd,request,r);int saved=errno;r->memory=original;
  if(ret==0){
   release_queue(q);q->active=r->count>0;q->count=r->count;
   for(unsigned int i=0;i<q->count;i++)for(unsigned int p=0;p<VIDEO_MAX_PLANES;p++)q->buffers[i].plane[p].fd=-1;
   fprintf(stderr,"[NAS-DMA] queue=%u buffers=%u imported through DMA-BUF\n",r->type,r->count);
  }
  pthread_mutex_unlock(&lock);errno=saved;return ret;
 }
 if(request==VIDIOC_EXPBUF){
  struct v4l2_exportbuffer *b=arg;struct queue *q=queue_for(fd,b->type);
  if(q&&q->active&&b->index<q->count&&b->plane<q->buffers[b->index].nplanes){
   b->fd=fcntl(q->buffers[b->index].plane[b->plane].fd,F_DUPFD_CLOEXEC,0);
   int ret=b->fd<0?-1:0;pthread_mutex_unlock(&lock);return ret;
  }
  pthread_mutex_unlock(&lock);return original_ioctl(fd,request,arg);
 }
 struct v4l2_buffer *b=arg;struct queue *q=queue_for(fd,b->type);
 if(!q||!q->active){pthread_mutex_unlock(&lock);return original_ioctl(fd,request,arg);}
 if(b->memory!=V4L2_MEMORY_MMAP){pthread_mutex_unlock(&lock);return original_ioctl(fd,request,arg);}
 if(request==VIDIOC_QUERYBUF){
  b->memory=V4L2_MEMORY_DMABUF;int ret=original_ioctl(fd,request,b);int saved=errno;b->memory=V4L2_MEMORY_MMAP;
  if(ret==0&&b->index<q->count&&b->length<=VIDEO_MAX_PLANES){
   struct buffer *buffer=&q->buffers[b->index];buffer->nplanes=b->length;
   for(unsigned int p=0;p<b->length;p++){
    struct plane *plane=&buffer->plane[p];plane->length=b->m.planes[p].length;
    if(plane->fd<0)plane->fd=allocate_ion(plane->length);
    if(plane->fd<0){saved=errno;ret=-1;fprintf(stderr,"[NAS-DMA] ION allocation failed: %s\n",strerror(saved));break;}
    plane->offset=((off_t)b->type<<24)|((off_t)b->index<<16)|((off_t)p<<12);
    b->m.planes[p].m.mem_offset=plane->offset;
   }
  }
  pthread_mutex_unlock(&lock);errno=saved;return ret;
 }
 struct v4l2_buffer copy=*b;struct v4l2_plane planes[VIDEO_MAX_PLANES]={0};
 if(b->length>VIDEO_MAX_PLANES){pthread_mutex_unlock(&lock);errno=EINVAL;return -1;}
 memcpy(planes,b->m.planes,b->length*sizeof(*planes));copy.m.planes=planes;copy.memory=V4L2_MEMORY_DMABUF;
 if(request==VIDIOC_QBUF){
  if(b->index>=q->count){pthread_mutex_unlock(&lock);errno=EINVAL;return -1;}
  /* This vendor can hold the first desktop picture without an explicit IDR.
   * Ask before its first input buffer, rather than waiting for a timeout and
   * relying on the caller to reopen the entire encoder with force_idr set. */
  if(b->type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE&&devices[fd].first_frame){
   struct v4l2_control idr={.id=V4L2_CID_MPEG_VIDEO_FORCE_KEY_FRAME,.value=1};
   if(original_ioctl(fd,VIDIOC_S_CTRL,&idr)<0){int saved=errno;pthread_mutex_unlock(&lock);errno=saved;return -1;}
   devices[fd].first_frame=0;
  }
  struct buffer *buffer=&q->buffers[b->index];
  for(unsigned int p=0;p<buffer->nplanes;p++){planes[p].m.fd=buffer->plane[p].fd;planes[p].length=buffer->plane[p].length;}
 }
 pthread_mutex_unlock(&lock);
 int ret=original_ioctl(fd,request,&copy);int saved=errno;
 if(ret==0){
  if(request==VIDIOC_DQBUF&&q==&devices[fd].capture&&copy.index<q->count&&copy.length){
   struct plane *plane=&q->buffers[copy.index].plane[0];
   if(plane->view&&planes[0].bytesused<=plane->length&&planes[0].data_offset<=planes[0].bytesused)
    redmi_correct_mtk_h264_colour((unsigned char*)plane->view+planes[0].data_offset,planes[0].bytesused-planes[0].data_offset);
  }
  struct v4l2_plane *destination=b->m.planes;*b=copy;b->m.planes=destination;b->memory=V4L2_MEMORY_MMAP;
  memcpy(destination,planes,copy.length*sizeof(*planes));
  if(copy.index<q->count)for(unsigned int p=0;p<copy.length;p++)destination[p].m.mem_offset=q->buffers[copy.index].plane[p].offset;
 }
 errno=saved;return ret;
}
void *mmap(void *address,size_t length,int protection,int flags,int fd,off_t offset){
 pthread_once(&init_once,initialize);
 pthread_mutex_lock(&lock);
 if(fd>=0&&fd<MAX_FDS&&devices[fd].enabled){
  struct queue *queues[]={&devices[fd].capture,&devices[fd].output};
  for(unsigned int k=0;k<2;k++)if(queues[k]->active)for(unsigned int i=0;i<queues[k]->count;i++)for(unsigned int p=0;p<queues[k]->buffers[i].nplanes;p++){
   struct plane *plane=&queues[k]->buffers[i].plane[p];
   if(plane->fd>=0&&plane->offset==offset){
    int dmafd=plane->fd;pthread_mutex_unlock(&lock);
    void *mapped=original_mmap(address,length,protection,flags,dmafd,0);
    if(mapped!=MAP_FAILED)plane->view=mapped;
    return mapped;
   }
  }
 }
 pthread_mutex_unlock(&lock);return original_mmap(address,length,protection,flags,fd,offset);
}
void *mmap64(void *address,size_t length,int protection,int flags,int fd,off64_t offset){return mmap(address,length,protection,flags,fd,(off_t)offset);}
int close(int fd){
 pthread_once(&init_once,initialize);pthread_mutex_lock(&lock);
 if(fd>=0&&fd<MAX_FDS){
  if(devices[fd].enabled){release_queue(&devices[fd].capture);release_queue(&devices[fd].output);}
  if(devices[fd].checked)memset(&devices[fd],0,sizeof(devices[fd]));
 }
 pthread_mutex_unlock(&lock);return original_close(fd);
}

