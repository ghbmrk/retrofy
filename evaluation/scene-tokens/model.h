#ifndef MODEL_DATA_H
#define MODEL_DATA_H
#if USE_MODEL==1
const int8_t weights[20][32]={
{3,-6,-6,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{-1,7,-7,2,0,2,1,1,0,0,-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{1,-7,8,0,0,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{-3,6,5,-2,0,-2,-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,2,3,-2,0,0,0,0,1,0,-1,0,-1,-2,-1,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{1,-2,-2,0,1,-1,0,0,-1,0,3,0,4,-1,-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{-1,3,-3,0,-2,1,0,0,0,0,-1,0,-2,4,-2,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,-3,2,2,1,0,0,0,0,0,-1,0,-1,-1,4,-2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{2,0,1,-10,1,1,-1,1,1,1,0,0,0,0,0,0,1,2,-1,0,0,0,0,0,0,0,0,0,0,0,0,0},
{-2,0,-1,10,-1,-1,1,-1,-1,-1,0,0,0,0,0,0,-1,-2,1,0,0,0,0,0,0,0,0,0,0,0,0,0},
{3,1,0,4,2,0,0,0,0,1,-8,0,0,0,0,0,0,0,0,0,-1,4,0,0,0,0,0,0,0,0,0,0},
{-3,-1,0,-4,-2,0,0,0,0,-1,8,0,0,0,0,0,0,0,0,0,1,-4,0,0,0,0,0,0,0,0,0,0},
{1,1,0,1,0,0,1,-7,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0},
{-1,-1,0,-1,0,0,-1,7,0,-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0,0,0,0,0,0},
{-2,-1,-1,-1,0,0,0,-1,9,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,-1,0,0,0,0,0,0},
{2,1,1,1,0,0,0,1,-9,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0},
{2,0,0,0,0,-7,0,-1,1,1,0,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0},
{-2,0,0,0,0,7,0,1,-1,-1,0,-9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,-1,0,0,0,0},
{1,-1,0,1,0,0,0,0,0,-8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0},
{-1,1,0,-1,0,0,0,0,0,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-1,0,0,0}
};
#elif USE_MODEL==2
static uint8_t predict_0(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=3;
if(context&1) score+=-6;
if(context&2) score+=-6;
if(context&512) score+=1;
if(context&1024) score+=2;
if(score>best){best=score;chosen=0;}
score=-1;
if(context&1) score+=7;
if(context&2) score+=-7;
if(context&4) score+=2;
if(context&16) score+=2;
if(context&32) score+=1;
if(context&64) score+=1;
if(context&512) score+=-1;
if(context&1024) score+=-1;
if(score>best){best=score;chosen=1;}
score=1;
if(context&1) score+=-7;
if(context&2) score+=8;
if(context&1024) score+=-1;
if(score>best){best=score;chosen=2;}
score=-3;
if(context&1) score+=6;
if(context&2) score+=5;
if(context&4) score+=-2;
if(context&16) score+=-2;
if(context&32) score+=-1;
if(context&64) score+=-1;
if(score>best){best=score;chosen=3;}
return chosen;
}
static uint8_t predict_1(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=0;
if(context&1) score+=2;
if(context&2) score+=3;
if(context&4) score+=-2;
if(context&128) score+=1;
if(context&512) score+=-1;
if(previous==0) score+=-1;
if(previous==1) score+=-2;
if(previous==2) score+=-1;
if(previous==3) score+=4;
if(score>best){best=score;chosen=4;}
score=1;
if(context&1) score+=-2;
if(context&2) score+=-2;
if(context&8) score+=1;
if(context&16) score+=-1;
if(context&128) score+=-1;
if(context&512) score+=3;
if(previous==0) score+=4;
if(previous==1) score+=-1;
if(previous==2) score+=-1;
if(previous==3) score+=-1;
if(score>best){best=score;chosen=5;}
score=-1;
if(context&1) score+=3;
if(context&2) score+=-3;
if(context&8) score+=-2;
if(context&16) score+=1;
if(context&512) score+=-1;
if(previous==0) score+=-2;
if(previous==1) score+=4;
if(previous==2) score+=-2;
if(previous==3) score+=-1;
if(score>best){best=score;chosen=6;}
score=0;
if(context&1) score+=-3;
if(context&2) score+=2;
if(context&4) score+=2;
if(context&8) score+=1;
if(context&512) score+=-1;
if(previous==0) score+=-1;
if(previous==1) score+=-1;
if(previous==2) score+=4;
if(previous==3) score+=-2;
if(score>best){best=score;chosen=7;}
return chosen;
}
static uint8_t predict_2(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=2;
if(context&2) score+=1;
if(context&4) score+=-10;
if(context&8) score+=1;
if(context&16) score+=1;
if(context&32) score+=-1;
if(context&64) score+=1;
if(context&128) score+=1;
if(context&256) score+=1;
if(previous==4) score+=1;
if(previous==5) score+=2;
if(previous==6) score+=-1;
if(score>best){best=score;chosen=8;}
score=-2;
if(context&2) score+=-1;
if(context&4) score+=10;
if(context&8) score+=-1;
if(context&16) score+=-1;
if(context&32) score+=1;
if(context&64) score+=-1;
if(context&128) score+=-1;
if(context&256) score+=-1;
if(previous==4) score+=-1;
if(previous==5) score+=-2;
if(previous==6) score+=1;
if(score>best){best=score;chosen=9;}
return chosen;
}
static uint8_t predict_3(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=3;
if(context&1) score+=1;
if(context&4) score+=4;
if(context&8) score+=2;
if(context&256) score+=1;
if(context&512) score+=-8;
if(previous==8) score+=-1;
if(previous==9) score+=4;
if(score>best){best=score;chosen=10;}
score=-3;
if(context&1) score+=-1;
if(context&4) score+=-4;
if(context&8) score+=-2;
if(context&256) score+=-1;
if(context&512) score+=8;
if(previous==8) score+=1;
if(previous==9) score+=-4;
if(score>best){best=score;chosen=11;}
return chosen;
}
static uint8_t predict_4(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=1;
if(context&1) score+=1;
if(context&4) score+=1;
if(context&32) score+=1;
if(context&64) score+=-7;
if(context&256) score+=1;
if(context&512) score+=1;
if(previous==11) score+=1;
if(score>best){best=score;chosen=12;}
score=-1;
if(context&1) score+=-1;
if(context&4) score+=-1;
if(context&32) score+=-1;
if(context&64) score+=7;
if(context&256) score+=-1;
if(context&512) score+=-1;
if(previous==11) score+=-1;
if(score>best){best=score;chosen=13;}
return chosen;
}
static uint8_t predict_5(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=-2;
if(context&1) score+=-1;
if(context&2) score+=-1;
if(context&4) score+=-1;
if(context&64) score+=-1;
if(context&128) score+=9;
if(context&256) score+=-1;
if(previous==12) score+=-1;
if(previous==13) score+=-1;
if(score>best){best=score;chosen=14;}
score=2;
if(context&1) score+=1;
if(context&2) score+=1;
if(context&4) score+=1;
if(context&64) score+=1;
if(context&128) score+=-9;
if(context&256) score+=1;
if(previous==12) score+=1;
if(previous==13) score+=1;
if(score>best){best=score;chosen=15;}
return chosen;
}
static uint8_t predict_6(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=2;
if(context&16) score+=-7;
if(context&64) score+=-1;
if(context&128) score+=1;
if(context&256) score+=1;
if(context&1024) score+=9;
if(previous==14) score+=1;
if(previous==15) score+=1;
if(score>best){best=score;chosen=16;}
score=-2;
if(context&16) score+=7;
if(context&64) score+=1;
if(context&128) score+=-1;
if(context&256) score+=-1;
if(context&1024) score+=-9;
if(previous==14) score+=-1;
if(previous==15) score+=-1;
if(score>best){best=score;chosen=17;}
return chosen;
}
static uint8_t predict_7(uint16_t context,uint8_t previous){
int16_t score,best=-32767;uint8_t chosen=0;
score=1;
if(context&1) score+=-1;
if(context&4) score+=1;
if(context&256) score+=-8;
if(previous==16) score+=1;
if(score>best){best=score;chosen=18;}
score=-1;
if(context&1) score+=1;
if(context&4) score+=-1;
if(context&256) score+=8;
if(previous==16) score+=-1;
if(score>best){best=score;chosen=19;}
return chosen;
}
static uint8_t compiled_predict(uint8_t phase,uint8_t t,uint8_t f,uint8_t k,uint8_t previous){
uint16_t context=(uint16_t)t|((uint16_t)f<<6)|((uint16_t)k<<10);
switch(phase){
case 0:return predict_0(context,previous);
case 1:return predict_1(context,previous);
case 2:return predict_2(context,previous);
case 3:return predict_3(context,previous);
case 4:return predict_4(context,previous);
case 5:return predict_5(context,previous);
case 6:return predict_6(context,previous);
case 7:return predict_7(context,previous);
}
return 0;
}
#endif
const uint8_t traits[32]={0,13,27,38,54,3,13,24,44,49,7,10,26,47,49,4,24,21,35,62,14,27,21,32,52,9,31,18,34,55,9,28};
#endif
