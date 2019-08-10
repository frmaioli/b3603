#!/usr/bin/python

import serial
import sys
import time
import csv
import os
import math

def calc_average(data):
    return reduce(lambda x,y: x+y, data) / len(data)

def calc_stddev(data, avg):
    tmp1 = map(lambda x: (x-avg)*(x-avg), data)
    tmp2 = calc_average(tmp1)
    return math.sqrt(tmp2)

class B900W(object):
    def __init__(self, portname):
        self.portname = portname
        self.debug = False

    def open(self):
        self.s = serial.Serial(self.portname, baudrate=38400, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.2)
        if self.s.isOpen():
            self.clear_input()
            s = self.system()
            print 'OPEN "%s"' % s
            if s  == 'M: B900W':
                return True
            else:
                print 'Couldnt read the right model out of the serial port, got "%s", expected to see "MODEL: B900W"' % s
        else:
            return False

    def close(self):
        self.s.close()

    def ser_write(self, data):
        if self.debug:
            print 'DEBUG OUT:', data
        for d in data:
            self.s.write(d)

    def clear_input(self):
        # Clear previous buffer
        while self.s.read() != '':
            pass

    def command(self, cmd):
        self.ser_write("%s\n" % cmd)
        data = ''
        while 1:
            a = self.s.read()
            if a == '':
                break
            else:
                data += a
        lines = [line.strip() for line in data.split('\r')]
        if self.debug:
            for line in lines:
                print 'DEBUG IN', line
        return lines

    def system(self):
        return self.command('SYSTEM')[0]

    def status(self):
        lines = self.command("STATUS")
        output = 'UNKNOWN'
        vin = 0
        vout = 0
        cout = 0
        constant = 'UNKNOWN'

        for line in lines:
            part = line.split(' ')
            if part[0] == 'OUTPUT:':
                output = part[1].strip()
            elif part[0] == 'VIN:':
                vin = float(part[2].strip())
            elif part[0] == 'VOUT:':
                vout = float(part[1].strip())
            elif part[0] == 'COUT:':
                cout = float(part[1].strip())
            elif part[0] == 'CONSTANT:':
                constant = part[1].strip()

        return dict(output=output, vin=vin, vout=vout, cout=cout, constant=constant)

    def rstatus(self):
        lines = self.command("STATUS")
        output = 'UNKNOWN'
        vin = 0
        vout = 0
        cout = 0
        constant = 'UNKNOWN'

        for line in lines:
            part = line.split(' ')
            if part[0] == 'OUTPUT:':
                output = part[1].strip()
            elif part[0] == 'VIN:':
                vin = float(part[3].strip())
            elif part[0] == 'VOUT:':
                vout = float(part[2].strip())
            elif part[0] == 'COUT:':
                cout = float(part[2].strip())
            elif part[0] == 'CONSTANT:':
                constant = part[1].strip()

        return dict(output=output, vin_adc=vin, vout_adc=vout, cout_adc=cout, constant=constant)

    def output_on(self):
        return self.command("OUTPUT 1")

    def output_off(self):
        return self.command("OUTPUT 0")

    def voltage(self, v):
        lines = self.command("VOLTAGE %i" % v)
        pwm_vout = None
        pwm_cout = None
        for line in lines:
            word = line.split(' ')
            if word[0] != 'PWM' and word[0] != 'aWM': continue
            if word[1] == 'VOLTAGE':
                pwm_vout = float(word[3])
            if word[1] == 'CURRENT':
                pwm_cout = float(word[3])
        return (pwm_vout, pwm_cout)

    def current(self, c):
        lines = self.command("CURRENT %i" % c)
        pwm_vout = None
        pwm_cout = None
        for line in lines:
            word = line.split(' ')
            if word[0] != 'PWM' and word[0] != 'aWM': continue
            if word[1] == 'VOLTAGE':
                pwm_vout = float(word[3])
            if word[1] == 'CURRENT':
                pwm_cout = float(word[3])
        return (pwm_vout, pwm_cout)


class Multimeter(object):
    def __init__(self, portname, model):
        self.portname = portname
        self.model = model

    def open(self):
        return self._sample() != None

    def _sample(self):
        p = os.popen('sigrok-cli -d %s:conn=%s --samples 1' % (self.model, self.portname))
        s = p.read()
        p.close()
        return float(s.split(' ')[1])

    def sample1(self, count):
        count = int(count)
        if count < 1:
            raise Exception("Invalid count value, must be above 0")
        if count == 1:
            return self._sample()

        data = []
        for i in xrange(count):
            data.append(self._sample())
            if data[-1] == None:
                return None

        avg = calc_average(data)
        stddev = calc_stddev(data, avg)
        if stddev > 0.1:
            print 'Multimeter samples vary too much, stddev=%f, data:' % stddev, data
            return None
        return avg

    def sample3(self, count):
        for i in range(3):
            s = self.sample1(count)
            if s != None:
                return s
            print 'Failed to read stable value, trying again, maybe'
            time.sleep(1)
        return None

def lse(xdata, ydata):
    assert(len(xdata) == len(ydata))
    sum_xy = 0
    sum_x = 0
    sum_y = 0
    sum_x2 = 0
    n = len(xdata)
    for i in xrange(n):
        x_i = xdata[i]
        y_i = ydata[i]
        sum_xy += x_i*y_i
        sum_x += x_i
        sum_y += y_i
        sum_x2 += x_i*x_i

    alpha = (n * sum_xy - sum_x*sum_y) / (n * sum_x2 - sum_x*sum_x)
    beta = (sum_y - alpha * sum_x) / n

    return (alpha, beta)

def calibration_voltage(auto):
    psu = B900W(sys.argv[3])
    if not psu.open():
        print 'Failed to open serial port to B900W on serial %s' % sys.argv[2]
        return

    if auto == True:
        dmm = Multimeter(sys.argv[3], sys.argv[4])
        if not dmm.open():
            print 'Failed to open serial port to multimeter on serial %s model %s' % (sys.argv[3], sys.argv[4])
            psu.close()
            return

    #B900W Limits
    vin = (psu.status()['vin'])*1000 #mV
    NUM_STEPS = 3
    MIN_VOLTAGE = vin + 4000 #mV
    MAX_VOLTAGE = 120000
    STEP_SIZE = int((MAX_VOLTAGE - MIN_VOLTAGE) / NUM_STEPS) #mV
    print 'PSU Input voltage is %s mV, will use %d steps between %s mV and %s mV' % (vin, NUM_STEPS, MIN_VOLTAGE, MAX_VOLTAGE)

    if STEP_SIZE < 10:
        print 'Step size is below 10mV, cannot test'
        return

    psu.output_on()
    psu.current(200) #200mA
    psu.voltage(MIN_VOLTAGE)

    pwm_data = []
    adc_data = []
    vout_data = []
    valid = True

    for step in xrange(NUM_STEPS):
        volt = MIN_VOLTAGE + step * STEP_SIZE
        print step , '. Setting voltage to', volt, 'mV'
        (pwm_vout, pwm_cout) = psu.voltage(volt)
        # Wait 1 second for things to stabilize
        time.sleep(1)
        if auto == True:
            vout = dmm.sample3(3) # Use three samples
        else:
            vout = input("Enter the Vout measuerd with Multimeter in mV: ")  

        if vout == None:
            print 'Failed to get vout'
            valid = False
            break
        if vout - vin < 1000:
            print 'Vout is %s and Vin is %s mV, this means that pwm calibration is saturated and the test will be meaningless' % (vout, vin)
            valid = False
            break
        rstatus = psu.rstatus()
        status = psu.status()
        adc_vout = rstatus['vout_adc']
        vout_calc = status['vout']

        pwm_data.append(pwm_vout)
        adc_data.append(adc_vout)
        vout_data.append(int(vout))
        print 'Step %d Set voltage %f mV Read voltage %f mV PWM %s ADC %s (%s)' % (step, volt, vout, pwm_vout, adc_vout, vout_calc)

    print psu.output_off()

    if not valid:
        print 'Test is invalid, calibration cancelled'
        return

    print 'ADC'
    val = lse(adc_data, vout_data)
    adc_a = int(val[0]*65536)
    adc_b_tmp = val[1]
    if adc_b_tmp < 0:
        adc_b_tmp = -adc_b_tmp
    else:
        print 'Expected ADC_B to be negative... for some reason it\'ts not'
        adc_b_tmp = 0
    adc_b = int(adc_b_tmp*65536)
    print val, adc_a, adc_b
    print psu.command('CAL_VOUTADC %d %d' % (adc_a, adc_b))
    print 'PWM'
    val = lse(vout_data, pwm_data)
    pwm_a = int(val[0]*65536)
    pwm_b = int(val[1]*65536)
    print val, pwm_a, pwm_b
    print psu.command('CAL_VOUTPWM %d %d' % (pwm_a, pwm_b))

    psu.close()

def calibration_current(auto):
    psu = B900W(sys.argv[3])
    if not psu.open():
        print 'Failed to open serial port to B900W on serial %s' % sys.argv[2]
        return

    if auto == True:
        dmm = Multimeter(sys.argv[3], sys.argv[4])
        if not dmm.open():
            print 'Failed to open serial port to multimeter on serial %s model %s' % (sys.argv[3], sys.argv[4])
            psu.close()
            return

    #B900W Limits
    NUM_STEPS = 4
    MIN_CURRENT = 600 #mA
    MAX_CURRENT = 1500 #mA
    STEP_SIZE = int((MAX_CURRENT - MIN_CURRENT) / NUM_STEPS) #mA
    print 'It will use %d steps between %s mA and %s mA' % (NUM_STEPS, MIN_CURRENT, MAX_CURRENT)

    if STEP_SIZE < 10:
        print 'Step size is below 10mA, cannot test'
        return

    psu.output_on()
    psu.voltage(120000) #120V
    psu.current(MIN_CURRENT)

    pwm_data = []
    adc_data = []
    cout_data = []
    valid = True

    for step in xrange(NUM_STEPS):
        curr = MIN_CURRENT + step * STEP_SIZE
        print step , '. Setting current to', curr, 'mA'
        (pwm_vout, pwm_cout) = psu.current(curr)
        # Wait 1 second for things to stabilize
        time.sleep(1)
        if auto == True:
            print 'Sorry, this functionality was not implemented yet'
            return
        else:
            cout = input("Enter the Iout measuerd with Multimeter in mA: ")  

        if cout == None:
            print 'Failed to get Iout'
            valid = False
            break
        rstatus = psu.rstatus()
        status = psu.status()
        adc_cout = rstatus['cout_adc']
        cout_calc = status['cout']

        pwm_data.append(pwm_cout)
        adc_data.append(adc_cout)
        cout_data.append(int(cout))
        print 'Step %d Set current %f mA Read current %f mA PWM %s ADC %s (%s)' % (step, curr, cout, pwm_cout, adc_cout, cout_calc)

    print psu.output_off()

    if not valid:
        print 'Test is invalid, calibration cancelled'
        return

    print 'ADC'
    val = lse(adc_data, cout_data)
    adc_a = int(val[0]*65536)
    adc_b_tmp = val[1]
    if adc_b_tmp < 0:
        adc_b_tmp = -adc_b_tmp
    else:
        print 'Expected ADC_B to be negative... for some reason it\'ts not'
        adc_b_tmp = 0
    adc_b = int(adc_b_tmp*65536)
    print val, adc_a, adc_b
    print psu.command('CAL_COUTADC %d %d' % (adc_a, adc_b))
    print
    print 'PWM'
    val = lse(cout_data, pwm_data)
    pwm_a = int(val[0]*65536)
    pwm_b_tmp = val[1]
    if pwm_b_tmp < 0:
        pwm_b_tmp = -pwm_b_tmp
    else:
        print 'Expected PWM_B to be negative... for some reason it\'ts not'
        pwm_b_tmp = 0
    pwm_b = int(pwm_b_tmp*65536)

    print val, pwm_a, pwm_b
    print psu.command('CAL_COUTPWM %d %d' % (pwm_a, pwm_b))

    psu.close()

def calibration_init():
    psu = B900W(sys.argv[2])
    if not psu.open():
        print 'Failed to open serial port to B900W on serial %s' % sys.argv[2]


    #Current
    adc_a = int(0001.9000 * 65536)
    adc_b = int(0173.3114 * 65536)
   # pwm_a = int(0002.0585 * 65536)
    pwm_a = int(0001.0585 * 65536)
    pwm_b = int(0568.0800 * 65536)
   # pwm_b = int(0368.0794 * 65536)
    print psu.command('CAL_COUTADC %d %d' % (adc_a, adc_b))
    print psu.command('CAL_COUTPWM %d %d' % (pwm_a, pwm_b))

    #Voltage
    adc_a = int(0025.5681 * 65536)
    adc_b = int(0580.6878 * 65536)


#    adc_a = int(0001.1600 * 65536)
#    adc_b = int(0 * 65536)
    pwm_a = int(0000.0375 * 65536)
#    pwm_b = int(0111.7264 * 65536)
    pwm_b = int(0 * 65536)
    print psu.command('CAL_VOUTADC %d %d' % (adc_a, adc_b))
    print psu.command('CAL_VOUTPWM %d %d' % (pwm_a, pwm_b))

    #Vin
    print psu.command('CAL_VINADC %d %d' % (910000, 0))
    
    print 'First Calibration completed. Use the save command if you would like to keep it.'
    
    psu.close()


def usage():
    print 'Usage:'
    print ' Automatic: %s -a <voltage|current> <b900w serial> <multimeter serial> <multimeter model>' % sys.argv[0]
    print ' Manual:    %s -m <voltage|current> <b900w serial>' % sys.argv[0]
    print ' Init:      %s -i <b900w serial>' % sys.argv[0]

def main():
    if len(sys.argv) < 3:
        return usage()

    if sys.argv[1] == '-a':
        if len(sys.argv) != 6:
            return usage()
        else:
            if sys.argv[2] == 'voltage':
                calibration_voltage(True)
            elif sys.argv[2] == 'current':
                calibration_current(True)
            else:
                return usage()

    if sys.argv[1] == '-m':
        if len(sys.argv) != 4:
            return usage()
        else:
            if sys.argv[2] == 'voltage':
                calibration_voltage(False)
            elif sys.argv[2] == 'current':
                calibration_current(False)
            else:
                return usage()
    
    if sys.argv[1] == '-i':
        if len(sys.argv) != 3:
            return usage()
        else:
            calibration_init()
   
if __name__ == '__main__':
    main()
