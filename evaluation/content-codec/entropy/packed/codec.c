/* Trusted, offline-validated ROM streams only. Not an untrusted-file parser. */
#include "codec.h"
#include <string.h>
#include "content.h"
uint8_t codec_error;
#if CODEC!=0
static const uint8_t tile_ids[5]={128,144,145,146,147};
#endif

#if CODEC==1 || CODEC>=4
static void unpack8(const uint8_t *s,uint8_t *d){
 uint8_t a=s[0],b=s[1],c=s[2];
 *d++=tile_ids[a&7];*d++=tile_ids[(a>>3)&7];
 *d++=tile_ids[((a>>6)|(b<<2))&7];*d++=tile_ids[(b>>1)&7];
 *d++=tile_ids[(b>>4)&7];*d++=tile_ids[((b>>7)|(c<<1))&7];
 *d++=tile_ids[(c>>2)&7];*d=tile_ids[c>>5];
}
#endif

void decode_scene(uint8_t room,uint8_t *output){
 const uint8_t *source=payload+offsets[room&31];
 codec_error=0;
#if CODEC==0
 memcpy(output,source,360);
#elif CODEC==1
 {
  uint8_t n;
  for(n=0;n<45;++n){unpack8(source,output);source+=3;output+=8;}
 }
#elif CODEC==2
 {
  uint8_t token,count,value;
  uint8_t *end=output+360;
  while(output<end){
   token=*source++;count=(token&31)+1;value=tile_ids[token>>5];
   do{*output++=value;}while(--count);
  }
 }
#elif CODEC==3
 {
  uint8_t token,count,distance;
  uint8_t *end=output+360,*copy;
  while(output<end){
   token=*source++;
   if(token&128){
    count=(token&127)+3;distance=*source++;copy=output-distance;
    do{*output++=*copy++;}while(--count);
   }else{
    count=token+1;
    do{*output++=tile_ids[*source++];}while(--count);
   }
  }
 }
#else
 {
  uint8_t patch[12],token,x,y,dy,i,a,b;
  const uint8_t *packed,*values=patch;
  uint8_t *dest,*row=output;
  for(y=0;y<6;++y){
   for(x=0;x<5;++x){
    token=*source++;
    if(token==255){packed=source;source+=5;}
#if CODEC==5
    else {packed=0;values=codebook+(uint16_t)token*12;}
    if(packed){
#else
    else packed=codebook+(uint16_t)token*5;
#endif
    unpack8(packed,patch);a=packed[3];b=packed[4];
    patch[8]=tile_ids[a&7];patch[9]=tile_ids[(a>>3)&7];
    patch[10]=tile_ids[((a>>6)|(b<<2))&7];patch[11]=tile_ids[(b>>1)&7];
    values=patch;
#if CODEC==5
    }
#endif
    dest=row+x*4;i=0;
    for(dy=0;dy<3;++dy){
     dest[0]=values[i++];dest[1]=values[i++];dest[2]=values[i++];dest[3]=values[i++];dest+=20;
    }
   }
   row+=60;
  }
 }
#endif
}
