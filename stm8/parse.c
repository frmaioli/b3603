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

#include "parse.h"
#include "uart.h"

#undef DEBUG
// If USE MILLI is defined the uart will expect to receive values like 12.345, otherwise it will be 12345
// Using now not defined to save space.

#define USE_MILLI


#ifdef USE_MILLI
uint32_t _parse_num(const char *s, const char **stop, uint8_t *digits_seen)
{
	uint8_t digit;
	uint32_t num = 0;

	*digits_seen = 0;

	for (; *s >= '0' && *s <= '9'; s++) {
		digit = *s - '0';
		num *= 10;
		num += digit;
		(*digits_seen)++;
	}

	*stop = s;
	return num;
}

uint32_t parse_millinum(const char *s)
{
	const char *t = s;
	const char *stop;
	uint32_t fraction_digits = 0;
	uint32_t whole_digits = 0;
	uint8_t digits_seen;

	whole_digits = _parse_num(s, &stop, &digits_seen);
	if (digits_seen > 3)
		goto invalid_number;

	whole_digits *= 1000;

	if (*stop == '\0')
		return whole_digits;

	if (*stop != '.')
		goto invalid_number;

	fraction_digits = _parse_num(stop+1, &stop, &digits_seen);
	if (fraction_digits > 999 || digits_seen > 3)
		goto invalid_number;

	if (digits_seen == 1)
		fraction_digits *= 100;
	else if (digits_seen == 2)
		fraction_digits *= 10;

	return whole_digits + fraction_digits;

invalid_number:
	uart_write_str("INVALID NUMBER '");
	uart_write_str(t);
	uart_write_ch('\'');
	uart_write_crlf();
	return 0xFFFF;
}
#endif

uint32_t parse_uint32(const char *s)
{
	uint32_t val = 0;

	for (; *s; s++) {
		uint8_t ch = *s;
		if (ch >= '0' && ch <= '9') {
			val = val*10 + (ch-'0');
		} else {
			//If 's' is like 111 333, it will return 111
			if (ch == ' ')
				break;
			else
				return 0xFFFFFFFF;
		}
	}

	return val;
}

uint32_t parse_set_value(const char *s)
{
#ifdef USE_MILLI
	return parse_millinum(s);
#else
	return parse_uint32(s);
#endif
}
