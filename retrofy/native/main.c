#include <gb/gb.h>
#include <gb/cgb.h>
#include <stdint.h>
#include "kernel.h"
#include "level.h"
uint8_t previous_push;
uint16_t previous_from, previous_to;
uint16_t previous_player, candidate_player;
uint8_t undo_available;
uint8_t displayed[CAPACITY];
/* Test mailbox is exported in .noi/.map. No guessed addresses. */
volatile uint8_t ready, victory, generation;
const uint8_t tiles[] = {
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
255,255,129,129,189,189,165,165,165,165,189,189,129,129,255,255,
0,0,0,0,24,24,60,60,60,60,24,24,0,0,0,0,
126,126,66,66,90,90,102,102,102,102,90,90,66,66,126,126,
126,126,90,90,102,102,90,90,90,90,102,102,90,90,126,126,
24,24,60,60,24,24,126,126,24,24,36,36,66,66,0,0,
255,255,129,129,165,165,153,153,153,153,165,165,129,129,255,255,
0,0,1,1,3,3,70,70,108,108,56,56,16,16,0,0
};
void reset_level(void) {
    uint16_t i;
    remaining=0;
    for(i=0;i<board_w*board_h;++i) {
        world[i]=level[i]; if((world[i]&6)==4) ++remaining;
    }
    player=LEVEL_PLAYER; undo_available=0;
}
uint8_t visual(uint16_t i) {
    if(i==player) return (world[i]&2) ? 6 : 5;
    if(world[i]&1) return 1;
    if(world[i]&4) return (world[i]&2) ? 4 : 3;
    return (world[i]&2) ? 2 : 0;
}
void draw_cell(uint16_t i) {
    uint8_t tile=visual(i);
    set_bkg_tiles(i%board_w,i/board_w,1,1,&tile); displayed[i]=tile;
}
void draw_move(void) {
    uint8_t tile;
    draw_cell(candidate_player); draw_cell(player);
    if(did_push) draw_cell(pushed_to);
    victory=is_won(); tile=victory ? 7 : 0;
    set_bkg_tiles(19,17,1,1,&tile); ++generation;
}
void draw(void) {
    uint16_t i;
    uint8_t tile;
    /* GBDK's tile write routines wait for safe VRAM access. No OAM used. */
    for(i=0;i<board_w*board_h;++i) {
        tile=visual(i);
        if(displayed[i]!=tile) {
            set_bkg_tiles(i%board_w, i/board_w, 1, 1, &tile); displayed[i]=tile;
        }
    }
    victory=is_won(); tile= victory ? 7 : 0;
    set_bkg_tiles(19,17,1,1,&tile);
    ++generation;
}
void main(void) {
    uint8_t held=0, keys, edge, dirs;
    uint16_t i;
    DISPLAY_OFF;
    board_w=LEVEL_W; board_h=LEVEL_H;
    fill_bkg_rect(0,0,32,32,0);
    set_bkg_data(0,8,tiles);
    BGP_REG=0xE4;
    if(_cpu==CGB_TYPE) {
        const uint16_t palette[]={RGB(29,30,25),RGB(17,23,18),RGB(7,14,14),RGB(2,5,8)};
        set_bkg_palette(0,1,palette);
    }
    for(i=0;i<CAPACITY;++i) displayed[i]=255;
    reset_level(); draw(); SHOW_BKG; DISPLAY_ON; ready=1;
    while(1) {
        vsync(); keys=joypad(); edge=keys & (uint8_t)~held; held=keys;
        if(edge & J_A) { reset_level(); draw(); }
        else if(edge & J_B) {
            if(undo_available) {
                candidate_player=player;
                if(previous_push) {
                    if(world[previous_to]&2) ++remaining;
                    if(world[previous_from]&2) --remaining;
                    world[previous_to] &= (uint8_t)~4; world[previous_from] |= 4;
                }
                player=previous_player; undo_available=0;
                did_push=previous_push; pushed_to=previous_to; draw_move();
            }
        } else {
            dirs=keys & (J_UP|J_DOWN|J_LEFT|J_RIGHT);
            if((edge & dirs) && dirs && !(dirs & (dirs-1))) {
                candidate_player=player;
                if(dirs==J_UP) move_player(0,-1);
                else if(dirs==J_DOWN) move_player(0,1);
                else if(dirs==J_LEFT) move_player(-1,0);
                else move_player(1,0);
                if(did_move) {
                    previous_push=did_push; previous_from=pushed_from; previous_to=pushed_to;
                    previous_player=candidate_player; undo_available=1;
                }
                draw_move();
            }
        }
    }
}
