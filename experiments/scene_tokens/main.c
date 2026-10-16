#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdio.h>
#include <gbdk/console.h>
#include "engine.h"
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
uint8_t adjacent(uint8_t x,uint8_t y){return (px==x && (py==y||py+1==y||y+1==py))||(py==y && (px+1==x||x+1==px));}
void meter_start(void){TAC_REG=0;TIMA_REG=0;TMA_REG=0;DIV_REG=0;IF_REG&=(uint8_t)~TIM_IFLAG;TAC_REG=0x04;}
void meter_stop(void){TAC_REG=0;}
uint8_t last_room=255,last_flags,last_key,last_px,last_py,last_info;
void draw(void){
 uint8_t marker=139,t=room_traits(room),f=flags[room],old_tile;
 if(last_room==room&&last_flags==f&&last_key==key&&last_info==info){
  old_tile=screen_map[(uint16_t)last_py*20+last_px];
  set_bkg_tiles(last_px,last_py,1,1,&old_tile);set_bkg_tiles(px,py,1,1,&marker);
  last_px=px;last_py=py;++generation;return;
 }
 meter_start();
 generate(t,f,key);
 TAC_REG=0;inference_ticks=TIMA_REG;inference_overflow=(IF_REG&TIM_IFLAG)!=0;IF_REG&=(uint8_t)~TIM_IFLAG;
 meter_start();render(t,f,key);meter_stop();render_ticks=TIMA_REG;render_overflow=(IF_REG&TIM_IFLAG)!=0;
 meter_start();DISPLAY_OFF;
 set_bkg_tiles(0,0,20,18,screen_map);
 gotoxy(0,0);printf("R%02u A:USE B:INFO",(unsigned)room);
 gotoxy(0,1);printf("KEY:%u QUEST:%u",(unsigned)key,(unsigned)((f&4)!=0));
 gotoxy(0,17);if(info)printf("CHEST NPC TORCH FLAG");else printf("DPAD MOVE 32 ROOMS");
 set_bkg_tiles(px,py,1,1,&marker);
 if(_cpu==CGB_TYPE){const uint16_t palette[]={RGB(28,30,24),RGB(14,22,15),RGB(6,13,15),RGB(2,4,7)};set_bkg_palette(0,1,palette);}
 SHOW_BKG;DISPLAY_ON;meter_stop();upload_ticks=TIMA_REG;upload_overflow=(IF_REG&TIM_IFLAG)!=0;
 last_room=room;last_flags=f;last_key=key;last_px=px;last_py=py;last_info=info;++generation;
}
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
 printf(" ");set_bkg_data(128,16,art);BGP_REG=0xe4;
 room=0;key=0;px=2;py=8;info=0;
 for(i=0;i<32;++i)flags[i]=0;
 draw();ready=1;
 while(1){
  vsync();keys=joypad();edge=keys&(uint8_t)~held;held=keys;
  if(edge&J_A){act();draw();}
  else if(edge&J_B){info=!info;draw();}
  else{dirs=keys&(J_LEFT|J_RIGHT|J_UP|J_DOWN);if((edge&dirs)&&dirs&&!(dirs&(dirs-1))){move(dirs);draw();}}
 }
}
