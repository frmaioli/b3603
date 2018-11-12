
// Finite State Enginer for menu structure

#include <stdint.h>
#include "buttons.h"
#include "main.h"
#include "fsm.h"
#include "uart.h"

#define TIMER 8000
fsm_states_t Fsm_state = FSM_DISP_VIN;
fsm_states_t Fsm_state_chain = FSM_DISP_VIN;

void fsm_event_update(fsm_event_t *evt, button_t button, cfg_system_t *sys)
{
	static uint16_t count = 0;

	//Update Button events
	evt->event_flag = button;
	evt->st.is_button_set = 0; //this is special

	//Holding Button Set will enter in save state
	if (button == BUTTON_SET) {
		if (count < TIMER)  count++;
		if (count >= TIMER) evt->st.is_save = 1;
	}

	//Actions when no Button is pressed
	if (!button) {
		evt->st.is_button_none = 1;
		evt->st.is_save = 0;
		//Button Set is set if it is released before the timeout
		if ((count > 0) && (count < TIMER))
			evt->st.is_button_set = 1;
		count = 0;
	}

	//Is Output?
	evt->st.is_output = sys->output;
}

void change_control(fsm_event_t *event, bool(*set)(uint16_t), uint16_t val, uint8_t reset)
{
	static uint16_t count = 0;
	uint8_t increment = 10;

	if (reset) {
		count = 0;
		return;
	}

	count++;

	//Execute first time. Start running after ~1s. And do not run too fast
	if (((count > 1) && (count < 5000)) || (count%80 != 1))
		return;

	//Test if the number is like 32.1 or 3.21 and make a logic to increment the last digit
	//But only for first touch (count = 1). Keep the same running speed for the rest
	if (((val/10000)%10) && (count == 1))
		increment = 100;

	if (event->st.is_button_up) val += increment;
	if (event->st.is_button_down) val -= increment;

	(*set)(val);
}

void process_fsm(button_t button, cfg_system_t *sys, cfg_output_t *cfg, state_t *stt) 
{
	fsm_event_t event;
	static uint16_t latch_cfg = TIMER;
	static uint8_t wait_button_release = 0;
	
	fsm_event_update(&event, button, sys);

	//Be sure button was released to avoid undesired run
	if (wait_button_release) {
		if (event.st.is_button_none) wait_button_release = 0;
		return;
	}
	//The follow events will always require the release and new press before go to new state
	if ((event.st.is_button_ok))
		wait_button_release = 1;

	/* Update to New State */
	switch (Fsm_state) {
		case FSM_DISP_VIN:
			Fsm_state_chain = Fsm_state;
			if (event.st.is_button_set) Fsm_state = FSM_DISP_VOUT;
			if (event.st.is_save) Fsm_state = FSM_DISP_SAVE;
			if (event.st.is_button_ok) {
				if (event.st.is_output) Fsm_state = FSM_OUT_DISABLE;
				else Fsm_state = FSM_DISP_CONF;
			}
			break;
		case FSM_DISP_VOUT:
			Fsm_state_chain = Fsm_state;
			if ((event.st.is_button_up) || (event.st.is_button_down)) Fsm_state = FSM_VOUT_CHANGE;
			if (event.st.is_button_set) Fsm_state = FSM_DISP_IOUT;
			if (event.st.is_save) Fsm_state = FSM_DISP_SAVE;
			if (event.st.is_button_ok) {
				if (event.st.is_output) Fsm_state = FSM_OUT_DISABLE;
				else Fsm_state = FSM_DISP_CONF;
			}
			break;
		case FSM_DISP_IOUT:
			Fsm_state_chain = Fsm_state;
			if ((event.st.is_button_up) || (event.st.is_button_down)) Fsm_state = FSM_IOUT_CHANGE;
			if (event.st.is_button_set) Fsm_state = FSM_DISP_VIN;
			if (event.st.is_save) Fsm_state = FSM_DISP_SAVE;
			if (event.st.is_button_ok) {
				if (event.st.is_output) Fsm_state = FSM_OUT_DISABLE;
				else Fsm_state = FSM_DISP_CONF;
			}
			break;
		case FSM_VOUT_CHANGE:
		case FSM_IOUT_CHANGE:
			if ((!event.st.is_button_up) && (!event.st.is_button_down)) Fsm_state = Fsm_state_chain;
			break;
		case FSM_DISP_CONF:
			if (event.st.is_button_ok) Fsm_state = FSM_OUT_ENABLE;
			if ((event.st.is_button_up) || (event.st.is_button_down) || (event.st.is_button_set))
				Fsm_state = Fsm_state_chain;
			break;
		case FSM_OUT_ENABLE:
		case FSM_OUT_DISABLE:
			Fsm_state = Fsm_state_chain;
			break;
		case FSM_DISP_SAVE:
			if (event.st.is_button_set) Fsm_state = FSM_SAVE_CFG;
			if ((event.st.is_button_up) || (event.st.is_button_down) || (event.st.is_button_ok))
				Fsm_state = Fsm_state_chain;
			break;
		case FSM_SAVE_CFG:
			Fsm_state = Fsm_state_chain;
			break;
	}

	/* Execute instruction inside new state */
	
	switch (Fsm_state) {
		case FSM_DISP_VIN:
			display_vin(stt->vin, (Fsm_state == Fsm_state_chain) ? UPDATE_SLOW : UPDATE_FAST);
			break;
		case FSM_DISP_VOUT:
			if (latch_cfg) latch_cfg--;
			//First test is to stay showing CFG for a while after release the button increase/decrese
			//Second test is to switch quickly when a button is pressed, but after it can update slower 
			display_vout((sys->output && !latch_cfg) ? stt->vout : cfg->vset,
					(Fsm_state == Fsm_state_chain) ? UPDATE_SLOW : UPDATE_FAST);
			change_control(NULL, NULL, 0, 1);
			break;
		case FSM_DISP_IOUT:
			if (latch_cfg) latch_cfg--;
			display_iout((sys->output && !latch_cfg) ? stt->cout : cfg->cset,
					(Fsm_state == Fsm_state_chain) ? UPDATE_SLOW : UPDATE_FAST);
			change_control(NULL, NULL, 0, 1);
			break;
		case FSM_VOUT_CHANGE:
			change_control(&event, set_voltage, cfg->vset, 0);
			display_vout(cfg->vset, UPDATE_FAST);
			latch_cfg = TIMER;
			break;
		case FSM_IOUT_CHANGE:
			change_control(&event, set_current, cfg->cset, 0);
			display_iout(cfg->cset, UPDATE_FAST);
			latch_cfg = TIMER;
			break;
		case FSM_DISP_CONF:
			display_conf((Fsm_state == Fsm_state_chain) ? UPDATE_SLOW : UPDATE_FAST);
			break;
		case FSM_OUT_ENABLE:
			set_output((uint8_t*)"1");
			break;
		case FSM_OUT_DISABLE:
			set_output((uint8_t*)"0");
			break;
		case FSM_DISP_SAVE:
			display_save((Fsm_state == Fsm_state_chain) ? UPDATE_SLOW : UPDATE_FAST);
			break;
		case FSM_SAVE_CFG:
			uart_write_str((config_save_output(cfg) == 0) ? "E!\r\n" : "OK\r\n");
			break;
	}
}
