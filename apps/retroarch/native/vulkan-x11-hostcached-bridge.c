/* Host-cached readback requires invalidation after the producing GPU fence.
 * Private compatibility experiment: Android Vulkan rendering, X11 readback presentation.
 * No system libraries are replaced. No pixels or user filenames are written to disk.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#define _GNU_SOURCE
#define VK_USE_PLATFORM_XLIB_KHR
#define VK_USE_PLATFORM_XCB_KHR
#include <vulkan/vulkan.h>
#include <X11/Xutil.h>
#include <X11/extensions/XShm.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <locale.h>
#include <link.h>
#include <errno.h>
#include <unistd.h>
static PFN_vkGetInstanceProcAddr real_g;
static PFN_vkGetDeviceProcAddr real_d;
static VkInstance instance;
static VkPhysicalDevice physical;
static VkDevice device;
static VkQueue queue;
static uint32_t family;
static double epoch;
static unsigned presents;
static double clock_s(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static void init(void){
 if(real_g)return;
 const char*native=getenv("NAS_VK_NATIVE_DRIVER");
 if(native){void*v=dlopen(native,RTLD_NOW|RTLD_LOCAL);if(!v){fprintf(stderr,"NAS Vulkan bridge: native driver load failed: %s\n",dlerror());abort();}real_g=dlsym(v,"vk_icdGetInstanceProcAddr");if(!real_g)abort();fprintf(stderr,"NAS Vulkan bridge: native Linux driver initialized\n");return;}
 void*h=dlopen("libhybris-common.so.1",RTLD_NOW|RTLD_GLOBAL);if(!h)abort();
 void*(*ad)(const char*,int)=dlsym(h,"android_dlopen");void*(*as)(void*,const char*)=dlsym(h,"android_dlsym");
 ad("/android/vendor/lib64/egl/libGLES_mali.so",RTLD_NOW|RTLD_GLOBAL);
 ad("/android/vendor/lib64/hw/vulkan.mali.so",RTLD_NOW|RTLD_GLOBAL);
 const char*custom=getenv("NAS_VK_CUSTOM_DRIVER");
 void*v=ad(custom?custom:"/system/lib64/libvulkan.so",RTLD_NOW|RTLD_GLOBAL);if(!v)abort();
 real_g=as(v,custom?"vk_icdGetInstanceProcAddr":"vkGetInstanceProcAddr");if(!real_g)abort();
 fprintf(stderr,"NAS Vulkan bridge: Android loader initialized\n");
}
#define IP(name) ((PFN_##name)real_g(instance,#name))
#define DP(name) ((PFN_##name)real_d(device,#name))
typedef struct {Display*d;Window w;int owns_display;} Surface;
typedef struct {VkBuffer buffer;VkDeviceMemory memory;void*mapped;VkCommandBuffer cmd;VkFence fence;} Readback;
typedef struct {Readback frames[4];int last;XImage*shm_image;XShmSegmentInfo shm;int shm_attached;Surface*s;uint32_t width,height,count,next;VkFormat format;VkImage image[4];VkDeviceMemory mem[4];VkBuffer buffer;VkDeviceMemory buffer_mem;void*mapped;VkCommandPool pool;VkCommandBuffer cmd;GC gc;} Swap;
#define SURF(h) ((Surface*)(uintptr_t)(h))
#define SWAP(h) ((Swap*)(uintptr_t)(h))
VKAPI_ATTR VkResult VKAPI_CALL vkCreateInstance(const VkInstanceCreateInfo*c,const VkAllocationCallbacks*a,VkInstance*out){
 fprintf(stderr,"NAS Vulkan bridge: instance creation entered\n");
 init();VkInstanceCreateInfo n=*c;const char*ext[128];unsigned k=0;
 for(unsigned x=0;x<c->enabledExtensionCount;x++)if(strcmp(c->ppEnabledExtensionNames[x],VK_KHR_XLIB_SURFACE_EXTENSION_NAME)&&strcmp(c->ppEnabledExtensionNames[x],VK_KHR_XCB_SURFACE_EXTENSION_NAME)&&(!getenv("NAS_VK_CUSTOM_DRIVER")||strcmp(c->ppEnabledExtensionNames[x],VK_KHR_SURFACE_EXTENSION_NAME)))ext[k++]=c->ppEnabledExtensionNames[x];
 n.enabledExtensionCount=k;n.ppEnabledExtensionNames=ext;
 VkResult r=((PFN_vkCreateInstance)real_g(NULL,"vkCreateInstance"))(&n,a,out);
 if(!r){instance=*out;real_d=(void*)real_g(instance,"vkGetDeviceProcAddr");}fprintf(stderr,"NAS Vulkan bridge: instance result %d\n",r);return r;
}
VKAPI_ATTR VkResult VKAPI_CALL vkEnumerateInstanceVersion(uint32_t*v){init();PFN_vkEnumerateInstanceVersion p=(void*)real_g(NULL,"vkEnumerateInstanceVersion");if(p)return p(v);*v=VK_API_VERSION_1_0;return VK_SUCCESS;}
VKAPI_ATTR VkResult VKAPI_CALL vkEnumerateInstanceExtensionProperties(const char*l,uint32_t*n,VkExtensionProperties*p){
 init();PFN_vkEnumerateInstanceExtensionProperties f=(void*)real_g(NULL,"vkEnumerateInstanceExtensionProperties");uint32_t count=0;VkResult r=f(l,&count,NULL);if(r)return r;
 VkExtensionProperties*all=calloc(count+3,sizeof(*all));f(l,&count,all);int has_surface=0;for(unsigned x=0;x<count;x++)if(!strcmp(all[x].extensionName,VK_KHR_SURFACE_EXTENSION_NAME))has_surface=1;if(!has_surface){strcpy(all[count].extensionName,VK_KHR_SURFACE_EXTENSION_NAME);all[count++].specVersion=25;}strcpy(all[count].extensionName,VK_KHR_XLIB_SURFACE_EXTENSION_NAME);all[count++].specVersion=6;strcpy(all[count].extensionName,VK_KHR_XCB_SURFACE_EXTENSION_NAME);all[count++].specVersion=6;
 if(!p){*n=count;free(all);return VK_SUCCESS;}uint32_t take=*n<count?*n:count;memcpy(p,all,take*sizeof(*p));*n=take;free(all);return take<count?VK_INCOMPLETE:VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL vkEnumerateInstanceLayerProperties(uint32_t*n,VkLayerProperties*p){(void)p;*n=0;return VK_SUCCESS;}
VKAPI_ATTR void VKAPI_CALL vkDestroyInstance(VkInstance i,const VkAllocationCallbacks*a){init();((PFN_vkDestroyInstance)real_g(i,"vkDestroyInstance"))(i,a);if(instance==i)instance=VK_NULL_HANDLE;}
VKAPI_ATTR VkResult VKAPI_CALL vkCreateXlibSurfaceKHR(VkInstance i,const VkXlibSurfaceCreateInfoKHR*c,const VkAllocationCallbacks*a,VkSurfaceKHR*out){(void)i;(void)a;Surface*s=calloc(1,sizeof(*s));s->d=c->dpy;s->w=c->window;*out=(VkSurfaceKHR)(uintptr_t)s;return VK_SUCCESS;}
VKAPI_ATTR VkResult VKAPI_CALL vkCreateXcbSurfaceKHR(VkInstance i,const VkXcbSurfaceCreateInfoKHR*c,const VkAllocationCallbacks*a,VkSurfaceKHR*out){(void)i;(void)a;Surface*s=calloc(1,sizeof(*s));s->d=XOpenDisplay(NULL);s->w=c->window;s->owns_display=1;if(!s->d){free(s);return VK_ERROR_INITIALIZATION_FAILED;}*out=(VkSurfaceKHR)(uintptr_t)s;return VK_SUCCESS;}
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceXcbPresentationSupportKHR(VkPhysicalDevice p,uint32_t f,xcb_connection_t*c,xcb_visualid_t v){(void)p;(void)f;(void)c;(void)v;return VK_TRUE;}
VKAPI_ATTR void VKAPI_CALL vkDestroySurfaceKHR(VkInstance i,VkSurfaceKHR s,const VkAllocationCallbacks*a){(void)i;(void)a;Surface*p=SURF(s);if(p&&p->owns_display)XCloseDisplay(p->d);free(p);}
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceXlibPresentationSupportKHR(VkPhysicalDevice p,uint32_t f,Display*d,VisualID v){(void)p;(void)f;(void)d;(void)v;return VK_TRUE;}
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceSupportKHR(VkPhysicalDevice p,uint32_t f,VkSurfaceKHR s,VkBool32*out){(void)p;(void)f;(void)s;*out=VK_TRUE;return VK_SUCCESS;}
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceCapabilitiesKHR(VkPhysicalDevice p,VkSurfaceKHR h,VkSurfaceCapabilitiesKHR*c){
 (void)p;Surface*s=SURF(h);Window root;int x,y;unsigned w=1280,hh=720,b,depth;XGetGeometry(s->d,s->w,&root,&x,&y,&w,&hh,&b,&depth);
 memset(c,0,sizeof(*c));c->minImageCount=2;c->maxImageCount=3;c->currentExtent=(VkExtent2D){w,hh};c->minImageExtent=(VkExtent2D){1,1};c->maxImageExtent=(VkExtent2D){4096,4096};c->maxImageArrayLayers=1;c->supportedTransforms=c->currentTransform=VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR;c->supportedCompositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;c->supportedUsageFlags=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT;return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceFormatsKHR(VkPhysicalDevice p,VkSurfaceKHR s,uint32_t*n,VkSurfaceFormatKHR*f){
 (void)p;(void)s;if(!f){*n=1;return VK_SUCCESS;}if(*n){f[0]=(VkSurfaceFormatKHR){VK_FORMAT_B8G8R8A8_UNORM,VK_COLOR_SPACE_SRGB_NONLINEAR_KHR};*n=1;return VK_SUCCESS;}return VK_INCOMPLETE;
}
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfacePresentModesKHR(VkPhysicalDevice p,VkSurfaceKHR s,uint32_t*n,VkPresentModeKHR*m){(void)p;(void)s;if(!m){*n=1;return VK_SUCCESS;}if(*n){m[0]=VK_PRESENT_MODE_FIFO_KHR;*n=1;return VK_SUCCESS;}return VK_INCOMPLETE;}
VKAPI_ATTR VkResult VKAPI_CALL vkCreateDevice(VkPhysicalDevice p,const VkDeviceCreateInfo*c,const VkAllocationCallbacks*a,VkDevice*out){
 VkDeviceCreateInfo n=*c;const char*ext[256];unsigned k=0;for(unsigned x=0;x<c->enabledExtensionCount;x++)if(!getenv("NAS_VK_CUSTOM_DRIVER")||strcmp(c->ppEnabledExtensionNames[x],VK_KHR_SWAPCHAIN_EXTENSION_NAME))ext[k++]=c->ppEnabledExtensionNames[x];n.enabledExtensionCount=k;n.ppEnabledExtensionNames=ext;
 VkResult r=IP(vkCreateDevice)(p,&n,a,out);if(!r){physical=p;device=*out;family=c->pQueueCreateInfos[0].queueFamilyIndex;DP(vkGetDeviceQueue)(device,family,0,&queue);}fprintf(stderr,"NAS Vulkan bridge: device result %d\n",r);return r;
}
VKAPI_ATTR VkResult VKAPI_CALL vkEnumerateDeviceExtensionProperties(VkPhysicalDevice p,const char*l,uint32_t*n,VkExtensionProperties*out){
 PFN_vkEnumerateDeviceExtensionProperties f=IP(vkEnumerateDeviceExtensionProperties);uint32_t count=0;VkResult r=f(p,l,&count,NULL);if(r)return r;VkExtensionProperties*all=calloc(count+1,sizeof(*all));f(p,l,&count,all);int has=0;for(unsigned x=0;x<count;x++)if(!strcmp(all[x].extensionName,VK_KHR_SWAPCHAIN_EXTENSION_NAME))has=1;if(!has){strcpy(all[count].extensionName,VK_KHR_SWAPCHAIN_EXTENSION_NAME);all[count++].specVersion=70;}if(!out){*n=count;free(all);return VK_SUCCESS;}unsigned take=*n<count?*n:count;memcpy(out,all,take*sizeof(*out));*n=take;free(all);return take<count?VK_INCOMPLETE:VK_SUCCESS;
}
static uint32_t memory_type(uint32_t bits,VkMemoryPropertyFlags flags){VkPhysicalDeviceMemoryProperties p;IP(vkGetPhysicalDeviceMemoryProperties)(physical,&p);for(unsigned x=0;x<p.memoryTypeCount;x++)if((bits&(1u<<x))&&(p.memoryTypes[x].propertyFlags&flags)==flags)return x;return UINT32_MAX;}
static int shm_error;
static int capture_shm_error(Display*d,XErrorEvent*e){(void)d;(void)e;shm_error=1;return 0;}
static void prepare_shm(Swap*s){
 if(!XShmQueryExtension(s->s->d))return;
 s->shm_image=XShmCreateImage(s->s->d,DefaultVisual(s->s->d,DefaultScreen(s->s->d)),24,ZPixmap,NULL,&s->shm,s->width,s->height);
 if(!s->shm_image)return;
 size_t bytes=(size_t)s->shm_image->bytes_per_line*s->height;
 s->shm.shmid=shmget(IPC_PRIVATE,bytes,IPC_CREAT|0600);
 if(s->shm.shmid<0){XDestroyImage(s->shm_image);s->shm_image=NULL;return;}
 s->shm.shmaddr=shmat(s->shm.shmid,NULL,0);s->shm.readOnly=False;
 if(s->shm.shmaddr==(char*)-1){shmctl(s->shm.shmid,IPC_RMID,NULL);XDestroyImage(s->shm_image);s->shm_image=NULL;return;}
 s->shm_image->data=s->shm.shmaddr;
 XSync(s->s->d,False);shm_error=0;XErrorHandler old=XSetErrorHandler(capture_shm_error);
 Bool attached=XShmAttach(s->s->d,&s->shm);XSync(s->s->d,False);XSetErrorHandler(old);
 shmctl(s->shm.shmid,IPC_RMID,NULL);
 if(!attached||shm_error){s->shm_image->data=NULL;XDestroyImage(s->shm_image);s->shm_image=NULL;shmdt(s->shm.shmaddr);return;}
 s->shm_attached=1;fprintf(stderr,"NAS Vulkan bridge: shared-memory presentation enabled\n");
}
#define CHECK(call) do{VkResult r=(call);if(r){fprintf(stderr,"NAS Vulkan bridge: allocation error %d at %d\n",r,__LINE__);return r;}}while(0)
VKAPI_ATTR VkResult VKAPI_CALL vkCreateSwapchainKHR(VkDevice d,const VkSwapchainCreateInfoKHR*c,const VkAllocationCallbacks*a,VkSwapchainKHR*out){
 (void)a;Swap*s=calloc(1,sizeof(*s));s->last=-1;s->s=SURF(c->surface);s->width=c->imageExtent.width;s->height=c->imageExtent.height;s->format=c->imageFormat;s->count=c->minImageCount;if(s->count>4)s->count=4;
 VkCommandPoolCreateInfo pi={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};CHECK(DP(vkCreateCommandPool)(d,&pi,NULL,&s->pool));
 for(unsigned x=0;x<s->count;x++){
  VkImageCreateInfo ci={.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,.imageType=VK_IMAGE_TYPE_2D,.format=s->format,.extent={s->width,s->height,1},.mipLevels=1,.arrayLayers=1,.samples=VK_SAMPLE_COUNT_1_BIT,.tiling=VK_IMAGE_TILING_OPTIMAL,.usage=c->imageUsage|VK_IMAGE_USAGE_TRANSFER_SRC_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED};
  CHECK(DP(vkCreateImage)(d,&ci,NULL,&s->image[x]));VkMemoryRequirements mr;DP(vkGetImageMemoryRequirements)(d,s->image[x],&mr);uint32_t mt=memory_type(mr.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);if(mt==UINT32_MAX)mt=memory_type(mr.memoryTypeBits,0);
  VkMemoryAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=mr.size,.memoryTypeIndex=mt};CHECK(DP(vkAllocateMemory)(d,&ai,NULL,&s->mem[x]));CHECK(DP(vkBindImageMemory)(d,s->image[x],s->mem[x],0));
  Readback*f=&s->frames[x];VkBufferCreateInfo bi={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=(VkDeviceSize)s->width*s->height*4,.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};CHECK(DP(vkCreateBuffer)(d,&bi,NULL,&f->buffer));DP(vkGetBufferMemoryRequirements)(d,f->buffer,&mr);mt=memory_type(mr.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_CACHED_BIT);if(mt==UINT32_MAX)mt=memory_type(mr.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);if(mt==UINT32_MAX)return VK_ERROR_FEATURE_NOT_PRESENT;
  ai.allocationSize=mr.size;ai.memoryTypeIndex=mt;CHECK(DP(vkAllocateMemory)(d,&ai,NULL,&f->memory));CHECK(DP(vkBindBufferMemory)(d,f->buffer,f->memory,0));CHECK(DP(vkMapMemory)(d,f->memory,0,VK_WHOLE_SIZE,0,&f->mapped));
  VkCommandBufferAllocateInfo ca={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=s->pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};CHECK(DP(vkAllocateCommandBuffers)(d,&ca,&f->cmd));VkFenceCreateInfo fc={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,.flags=VK_FENCE_CREATE_SIGNALED_BIT};CHECK(DP(vkCreateFence)(d,&fc,NULL,&f->fence));
 }
 s->gc=XCreateGC(s->s->d,s->s->w,0,NULL);prepare_shm(s);*out=(VkSwapchainKHR)(uintptr_t)s;fprintf(stderr,"NAS Vulkan bridge: pipelined presentation %ux%u, %u images\n",s->width,s->height,s->count);return VK_SUCCESS;
}
VKAPI_ATTR VkResult VKAPI_CALL vkGetSwapchainImagesKHR(VkDevice d,VkSwapchainKHR h,uint32_t*n,VkImage*out){(void)d;Swap*s=SWAP(h);if(!out){*n=s->count;return VK_SUCCESS;}unsigned take=*n<s->count?*n:s->count;memcpy(out,s->image,take*sizeof(*out));*n=take;return take<s->count?VK_INCOMPLETE:VK_SUCCESS;}
/* Only an empty frontend menu is paced. Loaded emulation cores always
 * retain the existing presentation path, independently of policy state. */
static int has_core(struct dl_phdr_info*info,size_t size,void*data){
 (void)size;(void)data;const char*n=info->dlpi_name;
 return n&&(strstr(n,"_libretro.")||strstr(n,"/libretro/")||strstr(n,"/cores/"));
}
static double menu_last_frame;
static int menu_fps(void){
 int fps=60;double expires=0;char path[100];snprintf(path,sizeof(path),"/run/redmi-gaming/menu-rate-%ld",(long)getpid());FILE*f=fopen(path,"r");
 if(f){int value=60;if(fscanf(f,"%d %lf",&value,&expires)==2&&value>=-1&&value<=60&&expires>clock_s())fps=value;fclose(f);}
 return fps;
}
static void pace_empty_menu(void){
 if(dl_iterate_phdr(has_core,NULL)){menu_last_frame=0;return;}
 for(;;){
  int fps=menu_fps();if(fps<0){menu_last_frame=0;return;}double now=clock_s(),remaining=fps?menu_last_frame+1.0/fps-now:1e9;
  if(!menu_last_frame||remaining<=0){menu_last_frame=now;return;}
  /* Policy changes wake a sleeping menu within 20 ms. */
  if(remaining>0.020)remaining=0.020;
  struct timespec delay={(time_t)remaining,(long)((remaining-(time_t)remaining)*1e9)};
  while(nanosleep(&delay,&delay)&&errno==EINTR){}
  if(dl_iterate_phdr(has_core,NULL)){menu_last_frame=0;return;}
 }
}
VKAPI_ATTR VkResult VKAPI_CALL vkAcquireNextImageKHR(VkDevice d,VkSwapchainKHR h,uint64_t t,VkSemaphore sem,VkFence fence,uint32_t*out){(void)d;(void)t;pace_empty_menu();Swap*s=SWAP(h);*out=s->next++%s->count;VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.signalSemaphoreCount=sem?1:0,.pSignalSemaphores=&sem};return DP(vkQueueSubmit)(queue,1,&si,fence);}
VKAPI_ATTR VkResult VKAPI_CALL vkAcquireNextImage2KHR(VkDevice d,const VkAcquireNextImageInfoKHR*c,uint32_t*out){return vkAcquireNextImageKHR(d,c->swapchain,c->timeout,c->semaphore,c->fence,out);}
VKAPI_ATTR VkResult VKAPI_CALL vkQueuePresentKHR(VkQueue q,const VkPresentInfoKHR*p){
 VkPipelineStageFlags*stages=calloc(p->waitSemaphoreCount+1,sizeof(*stages));for(unsigned k=0;k<p->waitSemaphoreCount;k++)stages[k]=VK_PIPELINE_STAGE_TRANSFER_BIT;
 for(unsigned x=0;x<p->swapchainCount;x++){
  Swap*s=SWAP(p->pSwapchains[x]);unsigned idx=p->pImageIndices[x];Readback*f=&s->frames[idx];VkImage im=s->image[idx];
  VkResult r=DP(vkWaitForFences)(device,1,&f->fence,VK_TRUE,UINT64_MAX);if(r){free(stages);return r;}DP(vkResetFences)(device,1,&f->fence);DP(vkResetCommandBuffer)(f->cmd,0);
  VkCommandBufferBeginInfo cb={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};DP(vkBeginCommandBuffer)(f->cmd,&cb);
  VkImageMemoryBarrier b={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_MEMORY_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT,.oldLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.image=im,.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
  DP(vkCmdPipelineBarrier)(f->cmd,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&b);
  VkBufferImageCopy cp={.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},.imageExtent={s->width,s->height,1}};DP(vkCmdCopyImageToBuffer)(f->cmd,im,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,f->buffer,1,&cp);
  VkMemoryBarrier host={.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT};DP(vkCmdPipelineBarrier)(f->cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&host,0,NULL,0,NULL);
  b.srcAccessMask=VK_ACCESS_TRANSFER_READ_BIT;b.dstAccessMask=0;b.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;DP(vkCmdPipelineBarrier)(f->cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&b);DP(vkEndCommandBuffer)(f->cmd);
  VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.waitSemaphoreCount=x?0:p->waitSemaphoreCount,.pWaitSemaphores=p->pWaitSemaphores,.pWaitDstStageMask=stages,.commandBufferCount=1,.pCommandBuffers=&f->cmd};r=DP(vkQueueSubmit)(q,1,&si,f->fence);if(p->pResults)p->pResults[x]=r;if(r){free(stages);return r;}
  if(s->last>=0){Readback*prev=&s->frames[s->last];r=DP(vkWaitForFences)(device,1,&prev->fence,VK_TRUE,UINT64_MAX);if(r){free(stages);return r;}
   VkMappedMemoryRange invalidate={.sType=VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE,.memory=prev->memory,.offset=0,.size=VK_WHOLE_SIZE};
   r=DP(vkInvalidateMappedMemoryRanges)(device,1,&invalidate);if(r){free(stages);return r;}
   if(s->shm_attached){
    if(s->shm_image->bytes_per_line==(int)(s->width*4))memcpy(s->shm.shmaddr,prev->mapped,(size_t)s->width*s->height*4);
    else for(unsigned y=0;y<s->height;y++)memcpy(s->shm.shmaddr+(size_t)y*s->shm_image->bytes_per_line,(char*)prev->mapped+(size_t)y*s->width*4,s->width*4);
    XShmPutImage(s->s->d,s->s->w,s->gc,s->shm_image,0,0,0,0,s->width,s->height,False);XSync(s->s->d,False);
   }else{
    XImage*xi=XCreateImage(s->s->d,DefaultVisual(s->s->d,DefaultScreen(s->s->d)),24,ZPixmap,0,prev->mapped,s->width,s->height,32,s->width*4);
    if(xi){XPutImage(s->s->d,s->s->w,s->gc,xi,0,0,0,0,s->width,s->height);XFlush(s->s->d);xi->data=NULL;XDestroyImage(xi);}
   }
  }
  s->last=(int)idx;
 }
 free(stages);presents++;double now=clock_s();if(!epoch)epoch=now;if(now-epoch>10){FILE*f=fopen("/DATA/AppData/custom-retroarch/armsx2-standalone-trial/vulkan-presentation.json.new","w");if(f){locale_t loc=newlocale(LC_NUMERIC_MASK,"C",NULL),old=uselocale(loc);fprintf(f,"{\"seconds\":%.3f,\"presentations\":%u,\"fps\":%.3f}\n",now-epoch,presents,presents/(now-epoch));uselocale(old);freelocale(loc);fclose(f);rename("/DATA/AppData/custom-retroarch/armsx2-standalone-trial/vulkan-presentation.json.new","/DATA/AppData/custom-retroarch/armsx2-standalone-trial/vulkan-presentation.json");}epoch=now;presents=0;}return VK_SUCCESS;
}
VKAPI_ATTR void VKAPI_CALL vkDestroySwapchainKHR(VkDevice d,VkSwapchainKHR h,const VkAllocationCallbacks*a){
 (void)a;Swap*s=SWAP(h);if(!s)return;DP(vkDeviceWaitIdle)(d);DP(vkDestroyCommandPool)(d,s->pool,NULL);
 for(unsigned x=0;x<s->count;x++){Readback*f=&s->frames[x];DP(vkDestroyFence)(d,f->fence,NULL);DP(vkUnmapMemory)(d,f->memory);DP(vkDestroyBuffer)(d,f->buffer,NULL);DP(vkFreeMemory)(d,f->memory,NULL);DP(vkDestroyImage)(d,s->image[x],NULL);DP(vkFreeMemory)(d,s->mem[x],NULL);}if(s->shm_attached){XShmDetach(s->s->d,&s->shm);XSync(s->s->d,False);s->shm_image->data=NULL;XDestroyImage(s->shm_image);shmdt(s->shm.shmaddr);}XFreeGC(s->s->d,s->gc);free(s);
}
static PFN_vkVoidFunction wrapped(const char*n){
#define W(f) if(!strcmp(n,#f))return (PFN_vkVoidFunction)f
 W(vkCreateXcbSurfaceKHR);W(vkGetPhysicalDeviceXcbPresentationSupportKHR);
 W(vkGetInstanceProcAddr);W(vkGetDeviceProcAddr);W(vkCreateInstance);W(vkEnumerateInstanceVersion);W(vkEnumerateInstanceExtensionProperties);W(vkEnumerateInstanceLayerProperties);W(vkCreateXlibSurfaceKHR);W(vkDestroySurfaceKHR);W(vkGetPhysicalDeviceXlibPresentationSupportKHR);W(vkGetPhysicalDeviceSurfaceSupportKHR);W(vkGetPhysicalDeviceSurfaceCapabilitiesKHR);W(vkGetPhysicalDeviceSurfaceFormatsKHR);W(vkGetPhysicalDeviceSurfacePresentModesKHR);W(vkCreateDevice);W(vkEnumerateDeviceExtensionProperties);W(vkCreateSwapchainKHR);W(vkGetSwapchainImagesKHR);W(vkAcquireNextImageKHR);W(vkAcquireNextImage2KHR);W(vkQueuePresentKHR);W(vkDestroySwapchainKHR);
#undef W
 return NULL;
}
VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(VkInstance i,const char*n){init();PFN_vkVoidFunction w=wrapped(n);PFN_vkVoidFunction p=w?w:real_g(i,n);if(!strcmp(n,"vkEnumeratePhysicalDevices"))fprintf(stderr,"NAS Vulkan bridge: enumeration lookup instance=%d pointer=%d\n",i!=NULL,p!=NULL);return p;}
VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr(VkDevice d,const char*n){init();PFN_vkVoidFunction w=wrapped(n);return w?w:real_d(d,n);}
