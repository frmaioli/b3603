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

#include "display.h"
#include "stm8s.h"
#include "uart.h"

#include <string.h>

static uint8_t Display_idx;
static uint8_t Display_data[4];
static uint8_t Pending_display_data[4];
static uint8_t Pending_update;

#define NALFA 17
static const uint8_t num_code[NALFA] = {0xFC,0x60,0xDA,0xF2,0x66,0xB6,0xBE,0xE0,0xFE,0xF6,0xEE,0x9C,0x9E,0x8E,0xEC,0xFC,0x7C,};
static const char alfa_code[NALFA]   = {'0' ,'1' ,'2' ,'3' ,'4' ,'5' ,'6' ,'7' ,'8' ,'9' ,'A' ,'C' ,'E' ,'F' ,'N' ,'O' ,'V',};
static uint16_t divisor[3] = {100, 10, 1};

#define SET_DATA(bit) do { if (bit) { PD_ODR |= (1<<4); } else { PD_ODR &= ~(1<<4); }} while (0)
#define PULSE_CLOCK() do { PA_ODR |= (1<<1); PA_ODR &= ~(1<<1); } while (0)
#define SAVE_DATA() do { PA_ODR &= ~(1<<2); PA_ODR |= (1<<2); } while (0)

#undef DEBUG
#ifdef DEBUG
char get_alfa(uint8_t num, uint8_t *dot)
{
	uint8_t i;
	*dot = 0;

	if (num & 0x01) {
		*dot = 1;
		num &= 0xFE;
	}
	for (i = 0; i < NALFA; i++) {
		if (num == num_code[i])
			return alfa_code[i];
	}
	return 'X';
}

void debug_pending_display(void)
{
	uint8_t i, dot = 0;
	uart_write_str("DISPLAY: ");
	for (i = 0; i < 4; i++) {
		uart_write_ch(get_alfa(Pending_display_data[3-i], &dot));
		if (dot)
			uart_write_ch('.');
	}
	uart_write_str("\n");
}
#endif

inline void display_word(uint16_t word)
{
	uint8_t i;

	for (i = 0; i < 16; i++) {
		uint8_t bit = word & 1;
		word >>= 1;
		SET_DATA(bit);
		PULSE_CLOCK();
	}
	SAVE_DATA();
}

void display_refresh(void)
{
	int i = Display_idx++;
	uint8_t bit = 8+(i*2);
	uint16_t digit = 0xFF00 ^ (3<<bit);
	static uint16_t timer;

	if (timer > 0)
		timer--;
	if (((Pending_update == UPDATE_SLOW) && (timer == 0)) || Pending_update == UPDATE_FAST) {
		memcpy(Display_data, Pending_display_data, sizeof(Display_data));
		Pending_update = 0;
		timer = DFLT_DISPLAY_REFRESH;
#ifdef DEBUG
		debug_pending_display();
#endif
	}

	display_word(digit | Display_data[i]);

	if (Display_idx == 4)
		Display_idx = 0;
}

uint8_t display_char(uint8_t ch, uint8_t dot)
{
	if (dot)
		dot = 1;
	if (ch >= 0 && ch <= NALFA)
		return num_code[ch] | dot;
	return dot;
}

void display_smart_digits(uint32_t disp_value, uint8_t *pending_display_p)
{
	uint16_t three_dig;
	uint8_t dot_dig = 0, dot = 0, ch = 0, c = 0, i;

	//Display the number, with the dot changing position when skiping not significant zero
	if (disp_value >= 100000) {          //Ex: 123.  V
		three_dig = disp_value/1000;
		dot_dig = 3;
	} else if (disp_value >= 10000) {    //Ex: 12.3 V
		three_dig = disp_value/100;
		dot_dig = 2;
	} else {                             //Ex: 1.23 V or 0.12 V or 0.01 V or 0.00 V
		three_dig = disp_value/10;
		dot_dig = 1;
	}

	for (i = 0; i < 3; i++) {
		ch = (three_dig/divisor[i])%10;
		if (i+1 == dot_dig) dot = 1;
		*(pending_display_p - c++) = display_char(ch, dot);
		dot = 0;
	}
}

void display_vin(uint16_t vin_value, uint8_t update_type)
{
	//Display 'E' - Entrance.
	Pending_display_data[3] = display_char(12, 0);
	//Display Digits
	display_smart_digits(vin_value, &Pending_display_data[2]);
	Pending_update = update_type;
}

void display_vout(uint32_t vout_value, uint8_t update_type)
{
	//Display 'V' - Voltage.
	Pending_display_data[0] = display_char(16, 0);
	//Display Digits
	display_smart_digits(vout_value, &Pending_display_data[3]);
	Pending_update = update_type;
}

void display_iout(uint16_t iout_value, uint8_t update_type)
{
	//Display 'A' - Ampere.
	Pending_display_data[0] = display_char(10, 0);
	//Display Digits
	display_smart_digits(iout_value, &Pending_display_data[3]);
	Pending_update = update_type;
}

void display_conf(uint8_t update_type)
{
	//Display 'CONF.' - Confirm.
	Pending_display_data[3] = display_char(11, 0); //C
	Pending_display_data[2] = display_char(15, 0); //O
	Pending_display_data[1] = display_char(14, 0); //N
	Pending_display_data[0] = display_char(13, 1); //F.
	Pending_update = update_type;
}

void display_save(uint8_t update_type)
{
	//Display 'SAVE'
	Pending_display_data[3] = display_char(5, 0);  //S
	Pending_display_data[2] = display_char(10, 0); //A
	Pending_display_data[1] = display_char(16, 0); //V
	Pending_display_data[0] = display_char(12, 0); //E
	Pending_update = update_type;
}
