/* SPDX-License-Identifier: AGPL-3.0-only
 * The tested MediaTek RGB encoder converts with limited-range BT.601 but tags
 * matrix_coefficients as BT.709. Change only that existing SPS VUI field.
 * No resizing, re-encoding or guessed insertion of missing VUI fields. */
#ifndef REDMI_MEDIATEK_H264_COLOUR_H
#define REDMI_MEDIATEK_H264_COLOUR_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef struct {const unsigned char *p;size_t bits,pos;int failed;} redmi_bits;
static uint32_t redmi_read_bits(redmi_bits *b,unsigned n){
 if(n>32||b->pos>b->bits||n>b->bits-b->pos){b->failed=1;return 0;}
 uint32_t v=0;while(n--){v=(v<<1)|((b->p[b->pos/8]>>(7-b->pos%8))&1);b->pos++;}return v;
}
static uint32_t redmi_ue(redmi_bits *b){
 unsigned zero=0;while(!b->failed&&!redmi_read_bits(b,1)){if(++zero>30){b->failed=1;return 0;}}
 if(b->failed)return 0;
 return ((1U<<zero)-1)+redmi_read_bits(b,zero);
}
static int redmi_high_profile(uint32_t p){
 const unsigned profiles[]={100,110,122,244,44,83,86,118,128,138,139,134,135};
 for(unsigned i=0;i<sizeof(profiles)/sizeof(*profiles);i++)if(p==profiles[i])return 1;
 return 0;
}
static size_t redmi_sps_matrix_offset(const unsigned char *p,size_t length){
 redmi_bits b={p,length*8,0,0};uint32_t profile=redmi_read_bits(&b,8);
 redmi_read_bits(&b,16);redmi_ue(&b);
 if(redmi_high_profile(profile)){
  uint32_t chroma=redmi_ue(&b);if(chroma>3)return SIZE_MAX;
  if(chroma==3)redmi_read_bits(&b,1);
  redmi_ue(&b);redmi_ue(&b);redmi_read_bits(&b,1);
  if(redmi_read_bits(&b,1))for(unsigned i=0;i<(chroma==3?12U:8U)&&!b.failed;i++)if(redmi_read_bits(&b,1)){
   int last=8,next=8;unsigned count=i<6?16:64;
   for(unsigned j=0;j<count&&!b.failed;j++){
    if(next){uint32_t v=redmi_ue(&b);int64_t delta=(v&1)?(int64_t)(v+1)/2:-(int64_t)v/2;next=(int)((last+delta)%256);if(next<0)next+=256;}
    if(next)last=next;
   }
  }
 }
 redmi_ue(&b);uint32_t order=redmi_ue(&b);
 if(order==0)redmi_ue(&b);
 else if(order==1){
  redmi_read_bits(&b,1);redmi_ue(&b);redmi_ue(&b);uint32_t count=redmi_ue(&b);if(count>255)return SIZE_MAX;
  for(uint32_t i=0;i<count&&!b.failed;i++)redmi_ue(&b);
 }else if(order>2)return SIZE_MAX;
 redmi_ue(&b);redmi_read_bits(&b,1);redmi_ue(&b);redmi_ue(&b);
 if(!redmi_read_bits(&b,1))redmi_read_bits(&b,1);
 redmi_read_bits(&b,1);
 if(redmi_read_bits(&b,1))for(unsigned i=0;i<4;i++)redmi_ue(&b);
 if(!redmi_read_bits(&b,1)||b.failed)return SIZE_MAX;
 if(redmi_read_bits(&b,1)&&redmi_read_bits(&b,8)==255)redmi_read_bits(&b,32);
 if(redmi_read_bits(&b,1))redmi_read_bits(&b,1);
 if(!redmi_read_bits(&b,1))return SIZE_MAX;
 redmi_read_bits(&b,3);redmi_read_bits(&b,1);
 if(!redmi_read_bits(&b,1))return SIZE_MAX;
 redmi_read_bits(&b,16);size_t offset=b.pos;
 if(redmi_read_bits(&b,8)!=1||b.failed)return SIZE_MAX;
 return offset;
}
static int redmi_patch_sps_matrix(unsigned char *data,size_t length){
 if(length<2||length>4096||(data[0]&31)!=7)return 0;
 unsigned char rbsp[4096],encoded[8192];size_t n=0;unsigned zeros=0;
 for(size_t i=1;i<length;i++){
  unsigned char v=data[i];if(zeros==2&&v==3){zeros=0;continue;}
  rbsp[n++]=v;zeros=v==0?zeros+1:0;if(zeros>2)zeros=2;
 }
 size_t offset=redmi_sps_matrix_offset(rbsp,n);if(offset==SIZE_MAX)return 0;
 for(unsigned bit=0;bit<8;bit++){
  size_t at=offset+bit;unsigned char mask=(unsigned char)(1U<<(7-at%8));
  if((6U>>(7-bit))&1)rbsp[at/8]|=mask;else rbsp[at/8]&=(unsigned char)~mask;
 }
 size_t out=0;zeros=0;encoded[out++]=data[0];
 for(size_t i=0;i<n;i++){
  unsigned char v=rbsp[i];if(zeros==2&&v<=3){encoded[out++]=3;zeros=0;}
  encoded[out++]=v;zeros=v==0?zeros+1:0;if(zeros>2)zeros=2;
 }
 if(out!=length)return 0;
 memcpy(data,encoded,length);return 1;
}
static size_t redmi_start_code(const unsigned char *p,size_t n,size_t at){
 if(at+3<=n&&!p[at]&&!p[at+1]){
  if(p[at+2]==1)return 3;
  if(at+4<=n&&!p[at+2]&&p[at+3]==1)return 4;
 }return 0;
}
static unsigned redmi_correct_mtk_h264_colour(unsigned char *data,size_t length){
 unsigned changed=0;size_t i=0;
 while(i+3<=length){
  size_t prefix=redmi_start_code(data,length,i);if(!prefix){i++;continue;}
  size_t begin=i+prefix,end=begin;
  while(end<length&&!redmi_start_code(data,length,end))end++;
  if(begin<end&&(data[begin]&31)==7)changed+=(unsigned)redmi_patch_sps_matrix(data+begin,end-begin);
  i=end;
 }return changed;
}
#endif
