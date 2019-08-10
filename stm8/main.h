#ifndef MAIN_H
#define MAIN_H

#include "display.h"
#include "config.h"
#include <stdint.h>
#include <stdbool.h>

#ifndef NULL
#define NULL ((void *) 0)
#endif

#define FW_VERSION "2.2.0"

#ifdef b3603
#define MODEL "B3603"
#define CAP_VMIN 10    // 10mV
#define CAP_VMAX 40000 // 40V
#define CAP_CMIN 1     // 1mA
#define CAP_CMAX 3000  // 3A
#endif
#ifdef b900w
#define MODEL "B900W"
#define CAP_VMIN 10000  // 10V
#define CAP_VMAX 120000 // 120V
#define CAP_CMIN 1      // 1mA
#define CAP_CMAX 15000  // 15A
#endif

extern state_t state;

bool set_output(const char *s);
bool set_voltage(uint32_t voltage);
bool set_current(uint32_t current);

#endif //MAIN_H
