// SPDX-License-Identifier: AGPL-3.0-only
// Redmi NAS integration by José Miranda (Xcat2008).
#define _GNU_SOURCE
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

/* FFmpeg MMAP buffers -> MediaTek ION DMA-BUF for the pinned Redmi vendor ABI.
 * Only affects the mtk-vcodec-enc device in the process explicitly loading it.
 * No global loader setting or kernel modification is made. */
struct ion_alloc {size_t len,align;unsigned int heaps,flags;int handle;};
struct ion_fd {int handle,fd;};
#define ION_ALLOC _IOWR('I',0,struct ion_alloc)
#define ION_FREE _IOWR('I',1,int)
#define ION_SHARE _IOWR('I',4,struct ion_fd)
#define MAX_FDS 4096
#define MAX_BUFFERS 64
struct plane {int fd;size_t length;off_t offset;};
struct buffer {unsigned int nplanes;struct plane plane[VIDEO_MAX_PLANES];};
struct queue {int active;unsigned int count;struct buffer buffers[MAX_BUFFERS];};
struct device {int checked,enabled;struct queue capture,output;};
static struct device devices[MAX_FDS];
static int (*original_ioctl)(int,unsigned long,...);
static int (*original_close)(int);
static void *(*original_mmap)(void*,size_t,int,int,int,off_t);
static pthread_once_t init_once=PTHREAD_ONCE_INIT;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static void initialize(void){original_ioctl=dlsym(RTLD_NEXT,"ioctl");original_mmap=dlsym(RTLD_NEXT,"mmap");original_close=dlsym(RTLD_NEXT,"close");}
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
  struct buffer *buffer=&q->buffers[b->index];
  for(unsigned int p=0;p<buffer->nplanes;p++){planes[p].m.fd=buffer->plane[p].fd;planes[p].length=buffer->plane[p].length;}
 }
 pthread_mutex_unlock(&lock);
 int ret=original_ioctl(fd,request,&copy);int saved=errno;
 if(ret==0){
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
    return original_mmap(address,length,protection,flags,dmafd,0);
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
