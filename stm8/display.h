/* Copyright (C) 2015 Baruch Even
 *
 * This file is part of the B3603 alternative firmware.
 *
 *  B3603 alternative firmware is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  B3603 alternative firmware is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with B3603 alternative firmware.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

#define DFLT_DISPLAY_REFRESH 2000 //around 0.5s
#define UPDATE_FAST 1
#define UPDATE_SLOW 2

void display_refresh(void);
void display_vin(uint16_t vin_value, uint8_t update_type);
void display_vout(uint32_t vout_value, uint8_t update_type);
void display_iout(uint16_t iout_value, uint8_t update_type);
void display_conf(uint8_t update_type);
void display_save(uint8_t update_type);

#endif //DISPLAY_H
