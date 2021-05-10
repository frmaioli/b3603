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

#include "config.h"
#include "eeprom.h"
#include "fixedpoint.h"

#include <string.h>

#define SYSTEM_CONFIG ((cfg_system_t *)0x4000)
#define OUTPUT_CONFIG ((cfg_output_t *)0x4040)

#define SYSTEM_CFG_VERSION 2
#define OUTPUT_CFG_VERSION 2

#define DEFAULT_NAME_STR "Unnamed"

#ifdef __GNUC__
#define INLINE
#else
#define INLINE inline
#endif

cfg_system_t default_cfg_system = {
	.version = SYSTEM_CFG_VERSION,
	.name = "Unnamed",
	.default_on = 0,
	.output = 0,
	.autocommit = 1,

    // pwm = setvoltage * cal.a + cal.b
    // volt = adcvalue * cal.a - cal.b

	.vin_adc = { .a = FLOAT_TO_FIXED(0.649151), .b = 0 /* -FLOAT_TO_FIXED(9.77583) */ },   // problem : need negative number here.
	.vout_adc = { .a = FLOAT_TO_FIXED(0.5536), .b = FLOAT_TO_FIXED(56.3560) },
	.vout_pwm = { .a = FLOAT_TO_FIXED(1.8109), .b = FLOAT_TO_FIXED(107.5395) },

	.cout_adc = { .a = FLOAT_TO_FIXED(0.4935), .b = FLOAT_TO_FIXED(177) },
	.cout_pwm = { .a = FLOAT_TO_FIXED(2.0276), .b = FLOAT_TO_FIXED(369.8418) }, 
};

cfg_output_t default_cfg_output = {
	OUTPUT_CFG_VERSION,
	500, // 5V
	500, // 0.5A
};

void config_default_system(cfg_system_t *sys)
{
	memcpy(sys, &default_cfg_system, sizeof(default_cfg_system));
}

INLINE void validate_system_config(cfg_system_t *sys)
{
	if (sys->version != SYSTEM_CFG_VERSION ||
			sys->name[0] == 0 ||
			sys->vin_adc.a == 0 ||
			sys->vout_adc.a == 0 ||
			sys->cout_adc.a == 0 ||
			sys->vout_pwm.a == 0
			)
	{
		config_default_system(sys);
		// TODO: If we want easy upgradability we can implement it here to
		// upgrade from an old struct to a new one.
	}
}

void config_load_system(cfg_system_t *sys)
{
#if TEST
	memset(sys, 0, sizeof(*sys));
#else
	memcpy(sys, SYSTEM_CONFIG, sizeof(*sys));
#endif
	validate_system_config(sys);
}

uint8_t config_save_system(cfg_system_t *sys)
{
	return eeprom_save_data((uint8_t*)SYSTEM_CONFIG, (uint8_t*)sys, sizeof(*sys));
}

void config_default_output(cfg_output_t *cfg)
{
	memcpy(cfg, &default_cfg_output, sizeof(default_cfg_output));
}

INLINE void validate_output_config(cfg_output_t *cfg)
{
	if (cfg->version != OUTPUT_CFG_VERSION || cfg->vset == 0 || cfg->cset == 0) {
		config_default_output(cfg);
	}
}

void config_load_output(cfg_output_t *cfg)
{
#if TEST
	memset(cfg, 0, sizeof(*cfg));
#else
	memcpy(cfg, OUTPUT_CONFIG, sizeof(*cfg));
#endif
	validate_output_config(cfg);
}

uint8_t config_save_output(cfg_output_t *cfg)
{
	return eeprom_save_data((uint8_t*)OUTPUT_CONFIG, (uint8_t*)cfg, sizeof(*cfg));
}
