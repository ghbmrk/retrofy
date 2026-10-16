#include "engine.h"
#include <string.h>
#ifndef USE_MODEL
#define USE_MODEL 1
#endif
#include "model.h"
uint8_t proposals[8],tokens[8],screen_map[360],repairs;
#if USE_MODEL==1
static const uint8_t base[8]={0,4,8,10,12,14,16,18};
static const uint8_t counts[8]={4,4,2,2,2,2,2,2};
#endif
uint8_t room_traits(uint8_t room){return traits[room&31];}
static uint8_t fact(uint8_t phase,uint8_t t,uint8_t f,uint8_t k){
 switch(phase){
 case 0:return t&3;
 case 1:return 4+(((t&3)+1)&3);
 case 2:return 8+((t&4)!=0);
 case 3:return 10+((f&8)!=0 && (t&4)==0);
 case 4:return 12+((f&1)!=0);
 case 5:return 14+((f&2)==0);
 case 6:return 16+((t&16)!=0 && !k);
 default:return 18+((f&4)!=0);
 }
}
void generate(uint8_t t,uint8_t f,uint8_t k){
 uint8_t phase,previous=255,chosen,target;
#if USE_MODEL==1
 uint8_t candidate,b,active[14],n,end;
 uint16_t context;
 int16_t score,best;
#endif
 repairs=0;
 for(phase=0;phase<8;++phase){
  target=fact(phase,t,f,k);
#if USE_MODEL==1
  context=(uint16_t)t|((uint16_t)f<<6)|((uint16_t)k<<10);
  n=0;active[n++]=0;
  for(b=0;b<11;++b)if(context&((uint16_t)1<<b))active[n++]=b+1;
  if(previous<20)active[n++]=12+previous;
  chosen=base[phase];best=-32767;end=base[phase]+counts[phase];
  for(candidate=base[phase];candidate<end;++candidate){
   score=0;for(b=0;b<n;++b)score+=(int16_t)weights[candidate][active[b]];
   if(score>best){best=score;chosen=candidate;}
  }
#elif USE_MODEL==2
  chosen=compiled_predict(phase,t,f,k,previous);
#else
  chosen=target;
#endif
  proposals[phase]=chosen;
  if(chosen!=target){chosen=target;++repairs;}
  tokens[phase]=chosen;previous=chosen;
 }
}
void render(uint8_t t,uint8_t f,uint8_t k){
 uint8_t x,y,border=(tokens[1]&1)?143:129;
 (void)t;(void)f;(void)k;
 for(y=2;y<17;++y){screen_map[(uint16_t)y*20]=border;screen_map[(uint16_t)y*20+19]=border;}
 for(x=0;x<20;++x){screen_map[40+x]=border;screen_map[320+x]=border;}
 for(x=1;x<19;++x)screen_map[200+x]=(tokens[2]==9)?130:128;
 screen_map[160]=128;screen_map[179]=128;screen_map[50]=128;screen_map[330]=128;
 screen_map[125]=(tokens[4]==13)?133:132;
 screen_map[173]=(tokens[5]==15)?134:135;
 screen_map[209]=(tokens[3]==11)?131:141;
 screen_map[178]=(tokens[6]==17)?136:137;
 screen_map[269]=(tokens[7]==19)?138:142;
}
