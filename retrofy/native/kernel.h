#ifndef RETROFY_KERNEL_H
#define RETROFY_KERNEL_H
#include <stdint.h>
#define CAPACITY 320
/* Tile flags: wall=1, goal=2, box=4. Player is separate. */
extern uint8_t world[CAPACITY];
extern uint16_t player, board_w, board_h;
extern uint8_t did_move, did_push;
extern uint16_t pushed_to, pushed_from;
extern uint8_t remaining;
void move_player(int8_t dx, int8_t dy);
uint8_t is_won(void);
#endif
