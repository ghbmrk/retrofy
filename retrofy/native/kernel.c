#include "kernel.h"
uint8_t world[CAPACITY];
uint16_t player, board_w, board_h;
uint8_t did_move, did_push;
uint16_t pushed_to, pushed_from;
uint8_t remaining;
void move_player(int8_t dx, int8_t dy) {
    int16_t x = (int16_t)(player % board_w) + dx;
    int16_t y = (int16_t)(player / board_w) + dy;
    uint16_t q, r;
    did_move = 0; did_push = 0;
    if(x < 0 || y < 0 || x >= board_w || y >= board_h) return;
    q = y * board_w + x;
    if(world[q] & 1) return;
    if(world[q] & 4) {
        x += dx; y += dy;
        if(x < 0 || y < 0 || x >= board_w || y >= board_h) return;
        r = y * board_w + x;
        if(world[r] & 5) return;
        did_push=1; pushed_to=r; pushed_from=q;
        if(world[q]&2) ++remaining;
        if(world[r]&2) --remaining;
        world[q] &= (uint8_t)~4; world[r] |= 4;
    }
    player = q; did_move = 1;
}
uint8_t is_won(void) { return remaining == 0; }
