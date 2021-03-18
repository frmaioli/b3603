#ifndef MAIN_H
#define MAIN_H

#include "display.h"
#include <stdint.h>
#include <stdbool.h>

#ifndef NULL
#define NULL ((void *) 0)
#endif

#define FW_VERSION "2.1.0"
#define MODEL "B3603"

#define CAP_VMIN 1 // 0.01V --centiVolts
#define CAP_VMAX 3500 // 35 V --centiVolts
#define CAP_VSTEP 1 // 0.01V --centiVolts

#define CAP_CMIN 1 // 1 mA
#define CAP_CMAX 3000 // 3 A
#define CAP_CSTEP 1 // 1 mA

bool set_output(const char *s);
bool set_voltage(uint16_t voltage);
bool set_current(uint16_t current);

#endif //MAIN_H
