/* CGB-only: padded WRAM tilemap committed during VBlank. Pan Docs VRAM DMA.
   LCD stays enabled after startup. */
uint8_t transfer_storage[591],font_tiles[59];
uint8_t *transfer_map;
volatile uint8_t dma_start_ly,dma_end_ly,dma_error;
volatile uint8_t full_generation;
void text_at(uint16_t offset,const char *text){
 uint8_t value;
 while((value=*text++))transfer_map[offset++]=font_tiles[value-32];
}
void display_init(void){
 uint8_t i;
 transfer_map=(uint8_t *)(((uint16_t)transfer_storage+15)&0xfff0);
 for(i=0;i<59;++i){gotoxy(0,0);putchar(i+32);get_bkg_tiles(0,0,1,1,&font_tiles[i]);}
 memset(transfer_map,128,576);
 if(_cpu==CGB_TYPE){const uint16_t palette[]={RGB(28,30,24),RGB(14,22,15),RGB(6,13,15),RGB(2,4,7)};set_bkg_palette(0,1,palette);}
 SHOW_BKG;DISPLAY_ON;
}
void transfer(void){
 uint8_t y,*dest=transfer_map;
 const uint8_t *source=screen_map;
 for(y=0;y<18;++y){memcpy(dest,source,20);dest+=32;source+=20;}
 memset(transfer_map,font_tiles[0],20);memset(transfer_map+32,font_tiles[0],20);memset(transfer_map+544,font_tiles[0],20);
 text_at(0,"R00 A:USE B:INFO");
 transfer_map[1]=font_tiles['0'-32+room/10];transfer_map[2]=font_tiles['0'-32+room%10];
 text_at(32,"KEY:0 QUEST:0");transfer_map[36]=font_tiles['0'-32+key];transfer_map[44]=font_tiles['0'-32+((flags[room]&4)!=0)];
 text_at(544,info?"CHEST NPC TORCH FLAG":"DPAD MOVE 32 ROOMS");
 transfer_map[(uint16_t)py*32+px]=139;
 /* 36 blocks = 1152 T-cycles. Start by LY149, leaving over four lines. */
 do{vsync();}while(LY_REG>149||LY_REG<144);
 CRITICAL {
  dma_start_ly=LY_REG;
  HDMA1_REG=(uint16_t)transfer_map>>8;HDMA2_REG=(uint16_t)transfer_map&0xf0;
  HDMA3_REG=0x18;HDMA4_REG=0;HDMA5_REG=35;
  dma_end_ly=LY_REG;
  if(dma_start_ly<144||dma_end_ly<144||dma_end_ly>153)dma_error=1;
 }
}
void draw(void){
 uint8_t marker=139,t=room_traits(room),f=flags[room],old_tile;
 if(last_room==room&&last_flags==f&&last_key==key&&last_info==info){
  old_tile=screen_map[(uint16_t)last_py*20+last_px];
  set_bkg_tiles(last_px,last_py,1,1,&old_tile);set_bkg_tiles(px,py,1,1,&marker);
  last_px=px;last_py=py;++generation;return;
 }
 meter_start();generate(t,f,key);
 TAC_REG=0;inference_ticks=TIMA_REG;inference_overflow=(IF_REG&TIM_IFLAG)!=0;IF_REG&=(uint8_t)~TIM_IFLAG;
 meter_start();decode_scene(room,screen_map);render(t,f,key);meter_stop();render_ticks=TIMA_REG;render_overflow=(IF_REG&TIM_IFLAG)!=0;
 meter_start();transfer();meter_stop();upload_ticks=TIMA_REG;upload_overflow=(IF_REG&TIM_IFLAG)!=0;
 last_room=room;last_flags=f;last_key=key;last_px=px;last_py=py;last_info=info;++full_generation;++generation;
}
