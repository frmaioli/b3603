SRC=main.c display.c uart.c eeprom.c outputs.c config.c fixedpoint.c parse.c adc.c buttons.c fsm.c
CFLAGS= -lstm8 -mstm8 --opt-code-size --std-c99 --fverbose-asm
OBJ=$(SRC:.c=.rel)
DEP=$(SRC:%.c=.%.c.d)
SDCC=sdcc $(CFLAGS)
TESTUTILS=test_pwm_accuracy test_adc_accuracy test_parse

all: b3603.ihx check_size

test: $(TESTUTILS)

-include $(DEP)

check_size: b3603.ihx
	@CODESIZE=$$(perl -ne 'if (/^(HOME|GSINIT|GSFINAL|CODE|CONST|INITIALIZER)\s+\w+\s+(\w+)/) { $$c{$$1} ||= hex($$2) } END { $$sum += $$_ for values %c; print $$sum; }' b3603.map); \
			 if [ "$$CODESIZE" -gt 8192 ]; then echo "Code is too large, it is $$CODESIZE bytes"; exit 1; \
			 else echo "Code fits the flash, it is $$CODESIZE"; \
			 fi

deploy: b3603.ihx
	stm8flash -c stlinkv2 -p stm8s003f3 -w $<

b3603.ihx: $(OBJ)
	@echo LINK $@
	@$(SDCC) --out-fmt-ihx --code-size 8192 -o $@ $^

.%.c.d: %.c
	@echo DEP $<
	@$(SDCC) -M -o $@ $<

%.rel: %.c
	@echo CC $<
	@$(SDCC) -c -o $@ $<

%.o: %.c
	@$(CC) -c -g -Wall -o $@ $^ -DTEST=1 -DUSE_MILLI=1

test_pwm_accuracy: test_pwm_accuracy.o outputs.o config.o fixedpoint.o dummy.o
	@$(CC) -g -Wall -o $@ $^

test_adc_accuracy: test_adc_accuracy.o config.o adc.o fixedpoint.o dummy.o
	@$(CC) -g -Wall -o $@ $^

test_parse: test_parse.o parse.o
	@$(CC) -g -Wall -o $@ $^

clean:
	-rm -f *.rel *.ihx *.lk *.map *.rst *.lst *.asm *.sym *.adb *.cdb .*.d
	-rm -f $(TESTUTILS)
	-rm -f *~

.PHONY: all clean check_size test deploy
