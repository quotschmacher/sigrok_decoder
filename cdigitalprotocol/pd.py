import sigrokdecode as srd
import math

class Decoder(srd.Decoder):
    api_version = 3
    id = 'c_digital'
    name = 'C-Digital Decoder'
    longname = 'longname'
    desc = 'was macht der wohl?'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['C Digital']
    channels = (
        {'id': 'data', 'name': 'Data', 'desc': 'Data line'},
    )
    optional_channels = ()
    options = (
        { 'id': 'invert', 'desc': 'Signal ist invertiert',
          'default': 'nein', 'values': ('ja', 'nein') },
    )
    annotations = (
        ('controller_0', 'Reglerwort ID 0'), # 0
        ('controller_1', 'Reglerwort ID 1'), # 1
        ('controller_2', 'Reglerwort ID 2'), # 2
        ('controller_3', 'Reglerwort ID 3'), # 3
        ('controller_4', 'Reglerwort ID 4'), # 4
        ('controller_5', 'Reglerwort ID 5'), # 5
        ('controller_sc', 'Reglerwort SC/Ghost'), # 6
        ('controller_prog', 'Programmierwort'), # 7
        ('controller_active', 'Aktivdatenwort'), # 8
        ('controller_different_new', 'Was ganz anderes'), # 9
        ('bit', 'Bit'), # 10
        ('quittierung', 'Quittierungswort'), # 11}
    )
    annotation_rows = (
        ('word_bit_value', 'Bits', (10,)),
        ('word_controller', 'Reglerwort', (0,1,2,3,4,5,6,)),
        ('active_quit', 'Aktiv-/Quittierungswort', (8, 11,)),
    )
    marker = 0

    def init_variables(self):
        self.count = 0
        self.currentMicros = 0
        self.previousMicros = 0
        self.intervalMicros = 0
        self.wordStart = 0
        self.wordEnd = 0
        self.bitStart = 0
        self.dataWord = 1
        self.beginDataWord = 0
        self.endDatatWord = 0
        self.next_could_be_active_data_word = False

    def __init__(self):
        self.reset()

    def reset(self):
        self.init_variables()

    def metadata(self, key, value):
       if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def get_usec_from_samples(self, samplenum) -> float:
        usec = float(samplenum) * 1000000.0
        usec /= float(self.samplerate)
        return float(usec)

    def get_msec_from_sample(self, samplenum) -> float:
        msec = float(samplenum) * 1000.0
        msec /= float(self.samplerate)
        return float(msec)

    def get_samples_from_usec(self, usec) -> int:
        retval = 1000000.0 / self.samplerate
        retval *= usec
        return int(retval)

    def get_samples_from_msec(self, msec) -> int:
        retval = 1000000.0 / float(self.samplerate)
        retval *= msec * 1000
        return int(retval)

    def get_value_from_dataword(self, bitsToShift = 0, bitWidth = 1) -> int:
        compare_val = int(math.pow(2, bitWidth))
        compare_val -= 1
        retval = (self.dataWord >> bitsToShift) & compare_val
        return int(retval)

    def start(self):
        #pass
        self.init_variables()
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def checkBit(self, bit):
        self.currentMicros = self.get_usec_from_samples(self.samplenum)
        self.intervalMicros = self.currentMicros - self.previousMicros
        #self.put(self.samplenum - 100, self.samplenum, self.out_ann, [4, [str(self.currentMicros)]])
        if 75.0 <= self.intervalMicros <= 125.0:
            self.put(self.get_samples_from_usec(self.previousMicros), self.samplenum, self.out_ann, [4, [str(bit)]])
            self.previousMicros = self.currentMicros
            self.dataWord <<= 1 # ein bit shiften
            if bit == 0:
                self.dataWord |= 1

    def print_reglerdatenwort(self):
        regler_id = self.get_value_from_dataword(6, 3)
        regler_str = str(regler_id)
        ta = str(self.get_value_from_dataword())

        if regler_id == 2 or regler_id == 7:
            self.next_could_be_active_data_word = True

        if regler_id == 7:
            regler_id -= 1
            regler_str = "SC"
            pc = str(self.get_value_from_dataword(1))
            nh = str(self.get_value_from_dataword(2))
            fr = str(self.get_value_from_dataword(3))
            tk = str(self.get_value_from_dataword(4))
            kfr = str(self.get_value_from_dataword(5))
            desc_long = "KFR:{} TK:{} FR:{} NH:{} PC:{} TA:{}".format(kfr, tk, fr, nh, pc, ta)
        else:
            # einzelne Werte
            gas = str((self.dataWord >> 1) & 15)
            wt = str(self.get_value_from_dataword(5))
            desc_long = "ID:{} G: {} WT:{} TA:{}".format(regler_str, gas, wt, ta)
        desc_short = "R " + regler_str
        desc = "Regler " + regler_str

        self.put(self.beginDataWord, self.endDatatWord, self.out_ann, [regler_id, [desc_short, desc, desc_long]])

    def print_aktivdatenwort(self):
        ie = str(self.get_value_from_dataword())
        r5 = str(self.get_value_from_dataword(1))
        r4 = str(self.get_value_from_dataword(2))
        r3 = str(self.get_value_from_dataword(3))
        r2 = str(self.get_value_from_dataword(4))
        r1 = str(self.get_value_from_dataword(5))
        r0 = str(self.get_value_from_dataword(6))

        desc_short = "IE:" + ie
        desc_long = "R0:{} R1:{} R2:{} R3:{} R4:{} R5:{} IE:{}".format(r0, r1, r2, r3, r4, r5, ie)

        self.put(self.beginDataWord, self.endDatatWord, self.out_ann, [8, [desc_short, desc_long]])

    def print_quittierungswort(self):
        self.put(self.beginDataWord, self.endDatatWord, self.out_ann, [11, [str(format(self.dataWord, '9b'))]])

    def print_programmierdatenwort(self):
        #self.put(self.beginDataWord, self.endDatatWord, self.out_ann, [1, [str(format(self.dataWord, '13b'))]])
        pass

    def print_bit(self, value):
        self.put(self.bitStart, self.samplenum, self.out_ann, [10, [str(value)]])

    def decode(self):
        invert = self.options['invert'] == 'ja'
        bit = 0
        if invert:
            bit = 1
        while True:
            pin = self.wait({0: 'e'}) # wir warten auf die naechste level-aenderung
            self.currentMicros = self.get_usec_from_samples(self.samplenum)
            self.intervalMicros = self.currentMicros - self.previousMicros
            if self.intervalMicros < 200:
                self.endDatatWord = self.samplenum
            if 75.0 <= self.intervalMicros <= 125.0:
                self.previousMicros = self.currentMicros
                self.dataWord <<= 1
                if pin[0] == bit:
                    self.dataWord |= 1
                    self.print_bit(1)
                else:
                    self.print_bit(0)
                self.bitStart = self.samplenum
            elif self.intervalMicros > 6000.0:
                if self.next_could_be_active_data_word:
                    if 127 < self.dataWord < 256:
                        self.print_aktivdatenwort()
                    elif self.dataWord < 512:
                        self.print_quittierungswort()
                    self.next_could_be_active_data_word = False
                elif self.dataWord < 1024:
                    self.print_reglerdatenwort()
                else:
                    self.print_programmierdatenwort()
                self.dataWord = 1
                self.previousMicros = self.currentMicros
                self.beginDataWord = self.samplenum
                self.bitStart = self.samplenum


"""     def decode(self):
        while True:
            pin = self.wait({0: 'f'})
            if self.wordStart == self.wordEnd:
                self.wordStart = self.samplenum
            self.bitStart = self.samplenum
            self.dataWord = 1
            self.previousMicros = self.get_usec_from_samples(self.samplenum)
            self.checkBit(0)
            self.put(self.get_samples_from_usec(self.currentMicros - 100), self.samplenum, self.out_ann, [4, [str(1)]])

            while True:
                pin = self.wait({0: 'r'})
                self.wordEnd = self.samplenum
                self.checkBit(0)
                self.wait([{0: 'f'}, {'skip': int(self.get_samples_from_msec(2))}])
                if self.matched == (False, True): # hier haben wir 2 ms keine fallende Flanke gehabt
                    # haben wir eine mindestlaenge von 150 us?
                    if self.get_usec_from_samples(self.wordEnd - self.wordStart) > 150.0:
                        self.put(self.wordStart, self.wordEnd, self.out_ann, [2, [str(self.dataWord)]])
                    self.wordStart = self.wordEnd
                    self.dataWord = 1
                    break
                self.checkBit(1) """
                


"""     def decode(self):
        self.put(0, 1000, self.out_ann, [4, ['1']])
        self.put(1000, 2000, self.out_ann, [5, ['0']])
        #waittime = self.get_samples_from_msec(4)
        waittime = self.get_samples_from_usec(4000)
        #print(f"self.samplerate: {self.samplerate} ... 20 * (1000 / self.samplerate): {20 * (1000 / self.samplerate)}")
        #pin = self.wait({'skip': 4 * (1000 / self.samplerate)})
        #pin = self.wait({'skip': 4000})
        pin = self.wait({'skip':  waittime})
        self.put(self.samplenum, self.samplenum + 1000, self.out_ann, [3, [str( waittime)]])
        while True:
            self.wait({0: 'r'})
            self.marker = self.samplenum
            self.wait({0: 'f'})
            elapsed = 1 / float(self.samplerate)
            elapsed *= (self.samplenum - self.marker )
            
            if elapsed == 0 or elapsed >= 1:
                delta_s = '%.1fs' % (elapsed)
            elif elapsed <= 1e-12:
                delta_s = '%.1ffs' % (elapsed * 1e15)
            elif elapsed <= 1e-9:
                delta_s = '%.1fps' % (elapsed * 1e12)
            elif elapsed <= 1e-6:
                delta_s = '%.1fns' % (elapsed * 1e9)
            elif elapsed <= 1e-3:
                delta_s = '%.1fμs' % (elapsed * 1e6)
            else:
                delta_s = '%.1fms' % (elapsed * 1e3)
            self.put(self.marker, self.samplenum, self.out_ann, [0, [str(delta_s), 'test']])
            #self.put(self.marker, self.samplenum, self.out_ann, [3, [str(self.get_usec(self.samplenum)), 'test']])
            #self.wait({0: 'e'})
            ##self.wait()
            #self.count += 1
            #if self.count == 10:
            #    self.put(self.samplenum - 100, self.samplenum, self.out_ann, [0, [str(self.samplenum), 'test', 't']])
            #    self.put(self.samplenum - 300, self.samplenum-100, self.out_ann, [1, [str(self.samplenum), 'test', 't']])
            #    self.put(self.samplenum - 600, self.samplenum-300, self.out_ann, [2, [str(self.samplenum), 'test', 't']])
            #    self.put(self.samplenum - 100, self.samplenum, self.out_ann, [3, [str(self.samplenum), 'test', 't']])
            #    self.count = 0
        #pass """