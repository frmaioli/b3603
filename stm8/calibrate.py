#!/usr/bin/python3

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

class B3603(object):
    def __init__(self, portname):
        self.portname = portname
        self.debug = False

    def open(self):
        self.s = serial.Serial(self.portname, baudrate=38400, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.2, rtscts=0, dsrdtr=0)
        if self.s.isOpen():
            self.clear_input()
            s = self.system()
            print ('OPEN "%s"' % s)
            if s  == 'M: B3603':
                return True
            else:
                print ('Couldnt read the right model out of the serial port, got "%s", expected to see "MODEL: B3603"' % s)
        else:
            return False

    def close(self):
        self.s.close()

    def ser_write(self, data):
        if self.debug:
            print ('DEBUG OUT:', data)
        for d in data:
            self.s.write(d)
            #self.s.write((d).encode())

    def clear_input(self):
        # Clear previous buffer
        #while self.s.read().decode('utf-8') != '':
        while self.s.read() != '':
            pass

    def command(self, cmd):
        self.ser_write("%s\n" % cmd)
        data = ''
        while 1:
            #a = self.s.read().decode('utf-8')
            a = self.s.read()
            if a == '':
                break
            else:
                data += a
        lines = [line.strip() for line in data.split('\r')]
        if self.debug:
            for line in lines:
                print ('DEBUG IN', line)
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
        lines = self.command("VOLTAGE %s" % v)
        pwm_vout = None
        pwm_cout = None
        for line in lines:
            word = line.split(' ')
            if word[0] != 'PWM' and word[0] != 'aWM': continue
            if word[1] == 'VOLTAGE':
                pwm_vout = float(word[2])
            if word[1] == 'CURRENT':
                pwm_cout = float(word[2])
        return (pwm_vout, pwm_cout)

    def current(self, c):
        lines = self.command("CURRENT %s" % c)
        pwm_vout = None
        pwm_cout = None
        for line in lines:
            word = line.split(' ')
            if word[0] != 'PWM' and word[0] != 'aWM': continue
            if word[1] == 'VOLTAGE':
                pwm_vout = float(word[2])
            if word[1] == 'CURRENT':
                pwm_cout = float(word[2])
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
        for i in range(count):
            data.append(self._sample())
            if data[-1] == None:
                return None

        avg = calc_average(data)
        stddev = calc_stddev(data, avg)
        if stddev > 0.1:
            print ('Multimeter samples vary too much, stddev=%f, data:' % stddev, data)
            return None
        return avg

    def sample3(self, count):
        for i in range(3):
            s = self.sample1(count)
            if s != None:
                return s
            print ('Failed to read stable value, trying again, maybe')
            time.sleep(1)
        return None

def lse(xdata, ydata):
    assert(len(xdata) == len(ydata))
    sum_xy = 0
    sum_x = 0
    sum_y = 0
    sum_x2 = 0
    n = len(xdata)
    for i in range(n):
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
    psu = B3603(sys.argv[3])
    print ('Attach multimeter to open circuit output of the device')
    print ('Set input voltage to between x and yV')
    if not psu.open():
        print ('Failed to open serial port to device on serial %s' % sys.argv[2])
        return

    if auto == True:
        dmm = Multimeter(sys.argv[3], sys.argv[4])
        if not dmm.open():
            print ('Failed to open serial port to multimeter on serial %s model %s' % (sys.argv[3], sys.argv[4]))
            psu.close()
            return

    #B3603 Limits
    vin = (psu.status()['vin']) #V
    NUM_STEPS = input("Enter the number of steps: ")
    MIN_VOLTAGE = 0.01 #V
    MAX_VOLTAGE = input("Enter the maximum Voltage in V: ")
    if MAX_VOLTAGE > (vin - 1):
        MAX_VOLTAGE = vin - 1
    STEP_SIZE = round(((MAX_VOLTAGE - MIN_VOLTAGE) / NUM_STEPS),2) #V
    print ('PSU Input voltage is %s V, will use %d steps between %s V and %s V' % (vin, NUM_STEPS, MIN_VOLTAGE, MAX_VOLTAGE))

    if STEP_SIZE < 0.010:
        print ('Step size is below 10mV, cannot test')
        return

    psu.output_on()
    psu.current(0.20) #200mA
    psu.voltage(MIN_VOLTAGE)

    pwm_data = []
    adc_data = []
    vout_data = []
    valid = True

    for step in range(NUM_STEPS):
        volt = round((MIN_VOLTAGE + step * STEP_SIZE),2)
        print (step , '. Setting voltage to', volt, 'V')
        (pwm_vout, pwm_cout) = psu.voltage(volt)
        # Wait 1 second for things to stabilize
        time.sleep(1)
        if auto == True:
            vout = dmm.sample3(3) # Use three samples
        else:
            vout = input("Enter the Vout measured with Multimeter in mV: ")  
            vout = vout/10		#Convert to centiVolts
        if vout == None:
            print ('Failed to get vout')
            valid = False
            break
        if vin - vout < 500:
            print ('Vout is %s and Vin is %s mV, this means that pwm calibration is saturated and the test will be meaningless' % (vout*10, vin))
            valid = False
            break
        rstatus = psu.rstatus()
        status = psu.status()
        adc_vout = rstatus['vout_adc']
        vout_calc = status['vout']

        pwm_data.append(pwm_vout)
        adc_data.append(adc_vout)
        vout_data.append(int(vout))
        print ('Step %d Set voltage %f mV Read voltage %f mV PWM %s ADC %s (%s)' % (step, volt, vout, pwm_vout, adc_vout, vout_calc))

    print (psu.output_off())

    if not valid:
        print ('Test is invalid, calibration cancelled')
        return

    print ('ADC')
    val = lse(adc_data, vout_data)
    adc_a = int(val[0]*65536)
    adc_b_tmp = val[1]
    if adc_b_tmp < 0:
        adc_b_tmp = -adc_b_tmp
    else:
        print ('Expected ADC_B to be negative... for some reason it\'ts not')
        adc_b_tmp = 0
    adc_b = int(adc_b_tmp*65536)
    if adc_b < 0:
        adc_b = 0
    print (adc_a, adc_b)
    print (psu.command('CAL_VOUTADC %d %d' % (adc_a, adc_b)))
    print ('PWM')
    val = lse(vout_data, pwm_data)
    pwm_a = int(val[0]*65536)
    pwm_b = int(val[1]*65536)
    if pwm_b < 0:
        pwm_b = 0
    print (pwm_a, pwm_b)
    print (psu.command('CAL_VOUTPWM %d %d' % (pwm_a, pwm_b)))

    psu.close()

def calibration_current(auto):
    psu = B3603(sys.argv[3])
    print ('Attach multimeter in current mode in series with a dummy load  capable of sinking a substantial current.')
    print ('Device will be operating in Constant Current mode. Actual output voltage MUST be above input voltage at all times.')
    if not psu.open():
        print ('Failed to open serial port to device on serial %s' % sys.argv[2])
        return

    if auto == True:
        dmm = Multimeter(sys.argv[3], sys.argv[4])
        if not dmm.open():
            print ('Failed to open serial port to multimeter on serial %s model %s' % (sys.argv[3], sys.argv[4]))
            psu.close()
            return

 #B3603 Limits
    MIN_CURRENT = input("Enter the minimum current in Amps: ")
    MAX_CURRENT = input("Enter the maximum current in Amps: ")
    if MAX_CURRENT > 3
	MAX_CURRENT = 3 #A
    NUM_STEPS = input("Enter the number of steps: ")
    TEST_VOLTAGE = input("Enter the test Voltage in Volts: ")

    STEP_SIZE = ((MAX_CURRENT - MIN_CURRENT) / NUM_STEPS) #A
    print ('It will use %d steps between %s A and %s A' % (NUM_STEPS, MIN_CURRENT, MAX_CURRENT))

    if STEP_SIZE < 0.01:
        print ('Step size is below 10mA, cannot test')
        return

    psu.output_on()
    #psu.voltage(3) #3V (Should be enough for Curt Circuit Test. Take care...) 
    psu.voltage(TEST_VOLTAGE)
    psu.current(MIN_CURRENT)

    pwm_data = []
    adc_data = []
    cout_data = []
    valid = True

    for step in range(NUM_STEPS):
        curr = round((MIN_CURRENT + step * STEP_SIZE),3)
        print (step , '. Setting current to', curr, 'A')
        (pwm_vout, pwm_cout) = psu.current(curr)
        # Wait 1 second for things to stabilize
        time.sleep(1)
        if auto == True:
            print ('Sorry, this functionality was not implemented yet')
            return
        else:
            cout = input("Enter the Iout measured with Multimeter in mA: ")  

        if cout == None:
            print ('Failed to get Iout')
            valid = False
            break
        rstatus = psu.rstatus()
        status = psu.status()
        adc_cout = rstatus['cout_adc']
        cout_calc = status['cout']

        pwm_data.append(pwm_cout)
        adc_data.append(adc_cout)
        cout_data.append(int(cout))
        print ('Step %d Set current %f mA Read current %f mA PWM %s ADC %s (%s)' % (step, curr, cout, pwm_cout, adc_cout, cout_calc))

    print (psu.output_off())

    if not valid:
        print ('Test is invalid, calibration cancelled')
        return

    print ('ADC')
    val = lse(adc_data, cout_data)
    adc_a = int(val[0]*65536)
    adc_b_tmp = val[1]
    if adc_b_tmp < 0:
        adc_b_tmp = -adc_b_tmp
    else:
        print ('Expected ADC_B to be negative... for some reason it\'ts not')
        adc_b_tmp = 0
    adc_b = int(adc_b_tmp*65536)
    if adc_b < 0:
        adc_b = 0
    print (adc_a, adc_b)
    print (psu.command('CAL_COUTADC %d %d' % (adc_a, adc_b)))
    print
    # Coutpwm calibration not necessary in new firmware due to closed loop feedback
    #print ('PWM')
    #val = lse(cout_data, pwm_data)
    #pwm_a = int(val[0]*65536)
    #pwm_b = int(val[1]*65536)
    #print (val, pwm_a, pwm_b)
    #print (psu.command('CAL_COUTPWM %d %d' % (pwm_a, pwm_b)))

    psu.close()

def calibration_init():
    psu = B3603(sys.argv[2])
    if not psu.open():
        print ('Failed to open serial port to device on serial %s' % sys.argv[2])


    #Current
    adc_a = int(0000.4860 * 65536)
    adc_b = int(0173.3114 * 65536)
    pwm_a = int(0002.0585 * 65536)
    pwm_b = int(0368.0794 * 65536)
    print (psu.command('CAL_COUTADC %d %d' % (adc_a, adc_b)))
    print (psu.command('CAL_COUTPWM %d %d' % (pwm_a, pwm_b)))

    #Voltage
    adc_a = int(000.55681 * 65536)
    adc_b = int(058.06878 * 65536)
    pwm_a = int(000.01803 * 65536)
    pwm_b = int(011.17264 * 65536)
    print (psu.command('CAL_VOUTADC %d %d' % (adc_a, adc_b)))
    print (psu.command('CAL_VOUTPWM %d %d' % (pwm_a, pwm_b)))

    #Vin
    print (psu.command('CAL_VINADC %d %d' % (41930, 0)))
    
    print ('First Calibration completed. Use the save command if you would like to keep it.')
    
    psu.close()


def usage():
    print ('Usage:')
    print (' Automatic: %s -a <voltage|current> <b3603 serial> <multimeter serial> <multimeter model>' % sys.argv[0])
    print (' Manual:    %s -m <voltage|current> <b3603 serial>' % sys.argv[0])
    print (' Init:      %s -i <b3603 serial>' % sys.argv[0])
    print ('Perform Voltage calibration first, then Current.')

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
