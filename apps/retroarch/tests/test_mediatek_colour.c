/* SPDX-License-Identifier: AGPL-3.0-only */
#include "../mediatek-h264-colour.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 /* A synthetic solid-colour frame, never a game or a user's media. */
 unsigned char sps[]={0,0,0,1,0x67,0x42,0,0x0a,0x8d,0x8d,0x40,0x28,0x02,0xdd,0x35,1,1,1,0x07,0x84,0x42,0x35};
 unsigned char original[sizeof(sps)];memcpy(original,sps,sizeof(sps));
 assert(redmi_correct_mtk_h264_colour(sps,sizeof(sps))==1);
 assert(sps[17]==6);original[17]=6;assert(!memcmp(sps,original,sizeof(sps)));
 assert(redmi_correct_mtk_h264_colour(sps,sizeof(sps))==0);
 for(size_t n=0;n<sizeof(sps);n++){
  unsigned char truncated[sizeof(sps)];memcpy(truncated,original,sizeof(sps));
  redmi_correct_mtk_h264_colour(truncated,n);
  assert(!memcmp(truncated+n,original+n,sizeof(sps)-n));
 }
 unsigned char non_sps[]={0,0,1,0x65,0x80,0,0,1,0x68,0x80};
 assert(redmi_correct_mtk_h264_colour(non_sps,sizeof(non_sps))==0);
 uint32_t state=1234567;unsigned char random[128];
 for(unsigned trial=0;trial<10000;trial++){
  for(size_t i=0;i<sizeof(random);i++){state=state*1664525+1013904223;random[i]=(unsigned char)(state>>24);}
  random[0]=random[1]=0;random[2]=1;random[3]=0x67;
  redmi_correct_mtk_h264_colour(random,4+trial%(sizeof(random)-3));
 }
 puts("MediaTek SPS colour, truncation and bounded-input checks passed.");return 0;
}
