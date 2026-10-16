#ifndef CONTENT_CODEC_H
#define CONTENT_CODEC_H
#include <stdint.h>
extern uint8_t codec_error;
void decode_scene(uint8_t room, uint8_t *output);
#endif
