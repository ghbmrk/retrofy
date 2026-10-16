#ifndef ENGINE_H
#define ENGINE_H
#include <stdint.h>
extern uint8_t proposals[8], tokens[8], screen_map[360], repairs;
void generate(uint8_t attributes,uint8_t flags,uint8_t key);
void render(uint8_t attributes,uint8_t flags,uint8_t key);
uint8_t room_traits(uint8_t room);
#endif
