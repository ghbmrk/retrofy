#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdio.h>
#include <gbdk/console.h>
#include "engine.h"
#include "codec.h"
#include <string.h>
volatile uint8_t ready,generation,room,key,px,py,info;
volatile uint8_t flags[32];
volatile uint8_t inference_ticks,inference_overflow,render_ticks,render_overflow,upload_ticks,upload_overflow;
/* Timer ticks are coarse 1024 CPU T-cycles; overflow explicitly invalidates timing. */
const uint8_t art[]={
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
255,255,129,129,165,165,129,129,153,153,129,129,165,165,255,255,
0,0,85,85,170,170,0,0,85,85,170,170,0,0,85,85,
16,16,24,24,44,44,54,54,90,90,126,126,60,60,0,0,
0,0,126,126,66,66,126,126,90,90,66,66,126,126,0,0,
126,126,66,66,126,126,0,0,66,66,66,66,126,126,0,0,
24,24,60,60,24,24,126,126,24,24,36,36,66,66,0,0,
0,0,0,0,66,66,36,36,24,24,36,36,66,66,0,0,
60,60,66,66,66,66,126,126,90,90,90,90,126,126,0,0,
0,0,126,126,66,66,66,66,66,66,66,66,126,126,0,0,
8,8,12,12,126,126,63,63,30,30,54,54,34,34,0,0,
0,0,24,24,60,60,24,24,60,60,90,90,24,24,0,0,
0,0,0,0,0,0,24,24,36,36,24,24,0,0,0,0,
0,0,16,16,8,8,0,0,8,8,16,16,0,0,0,0,
60,60,66,66,2,2,12,12,16,16,0,0,16,16,0,0,
255,255,129,129,189,189,165,165,165,165,189,189,129,129,255,255
};
const uint8_t decor[]={0,0,17,17,0,0,68,68,0,0,17,17,0,0,68,68,0,0,0,0,126,126,0,0,0,0,126,126,0,0,0,0,128,128,64,64,32,32,16,16,8,8,4,4,2,2,1,1,0,0,24,24,36,36,66,66,66,66,36,36,24,24,0,0};
uint8_t adjacent(uint8_t x,uint8_t y){return (px==x && (py==y||py+1==y||y+1==py))||(py==y && (px+1==x||x+1==px));}
void meter_start(void){TAC_REG=0;TIMA_REG=0;TMA_REG=0;DIV_REG=0;IF_REG&=(uint8_t)~TIM_IFLAG;TAC_REG=0x04;}
void meter_stop(void){TAC_REG=0;}
uint8_t last_room=255,last_flags,last_key,last_px,last_py,last_info;
#include "display.inc"
void act(void){
 uint8_t f=flags[room];
 if(adjacent(5,6)){flags[room]=f|1;key=1;}
 else if(adjacent(13,8))flags[room]=f|2;
 else if(adjacent(9,10))flags[room]=f^8;
 else if(adjacent(9,13))flags[room]=f|4;
}
void move(uint8_t direction){
 if(direction==J_LEFT){if(px>1)--px;else if(py==8){room=(room&24)|((room-1)&7);px=18;}}
 if(direction==J_RIGHT){if(px<18)++px;else if(py==8&&(!(room_traits(room)&16)||key)){room=(room&24)|((room+1)&7);px=1;}}
 if(direction==J_UP){if(py>3)--py;else if(px==10){room=(room-8)&31;py=15;}}
 if(direction==J_DOWN){if(py<15)++py;else if(px==10){room=(room+8)&31;py=3;}}
}
void main(void){
 uint8_t held=0,keys,edge,dirs,i;
 DISPLAY_OFF;
 printf(" ");set_bkg_data(128,16,art);set_bkg_data(144,4,decor);BGP_REG=0xe4;
 room=0;key=0;px=2;py=8;info=0;
 for(i=0;i<32;++i)flags[i]=0;
 display_init();draw();ready=1;
 while(1){
  vsync();keys=joypad();edge=keys&(uint8_t)~held;held=keys;
  if(edge&J_A){act();draw();}
  else if(edge&J_B){info=!info;draw();}
  else{dirs=keys&(J_LEFT|J_RIGHT|J_UP|J_DOWN);if((edge&dirs)&&dirs&&!(dirs&(dirs-1))){move(dirs);draw();}}
 }
}
