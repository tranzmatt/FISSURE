#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-Channel LoRa Monitor
"""

from gnuradio import LoRa_AIS
from gnuradio import analog
from gnuradio import blocks
import math
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from gnuradio import uhd
from time import strftime
import gnuradio.lora_sdr as lora_sdr
import os

class lora_monitor(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Multi-Channel LoRa Monitor", catch_exceptions=True)
        self.samp_rate = samp_rate = 13e6
        self.bw_lora = bw_lora = 500e3
        self.ds_rate_lora = ds_rate_lora = int(samp_rate/bw_lora)
        self.usrp_gain = usrp_gain = 10
        self.squelch = squelch = -65
        self.samp_rate_lora = int(samp_rate/ds_rate_lora)
        self.fc = fc = 908.6e6

        # Output filename
        self.filename_hex = os.path.dirname(os.path.abspath(__file__)) + f"/monitor_output/monitor_output_{strftime('%Y-%m-%dT%H%M%S')}.hex"
        if os.path.dirname(self.filename_hex) and not os.path.exists(os.path.dirname(self.filename_hex)):
            os.makedirs(os.path.dirname(self.filename_hex))

        # SDR Source
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec(0))
        self.uhd_usrp_source_0.set_center_freq(fc, 0)
        self.uhd_usrp_source_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_source_0.set_gain(usrp_gain, 0)

        # Create multiple RX chains for different LoRa channels
        self.chains = []
        for chan_fc in [903.5e6]:#[902.3e6, 902.5e6, 902.7e6, 902.9e6, 903.1e6, 903.3e6, 903.5e6, 903.7e6]:
            chain = {}
            chain['chan_fc'] = chan_fc
            chain['freq_shift'] = blocks.rotator_cc(2.0*math.pi*(self.fc-chan_fc)/self.samp_rate)
            chain['lpf'] = filter.fir_filter_ccf(
                self.ds_rate_lora,
                firdes.low_pass(
                    1,
                    self.samp_rate,
                    80000,
                    45000,
                    window.WIN_HAMMING,
                    6.76
                )
            )
            chain['squelch'] = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
            chain['lora_rx'] = lora_sdr.lora_sdr_lora_rx(bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=self.samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
            chain['report'] = LoRa_AIS.reportPower(f'{chan_fc/1e6} MHz Magnitude')
            chain['file_sink'] = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
            chain['file_sink'].set_unbuffered(True)
            print(f"Created RX Chain for {chan_fc/1e6} MHz")

            # connect the chain components
            self.connect((self.uhd_usrp_source_0, 0), (chain['freq_shift'], 0))
            self.connect((chain['freq_shift'], 0), (chain['lpf'], 0))
            self.connect((chain['lpf'], 0), (chain['squelch'], 0))
            self.connect((chain['squelch'], 0), (chain['report'], 0))
            self.connect((chain['squelch'], 0), (chain['lora_rx'], 0))
            self.connect((chain['lora_rx'], 0), (chain['file_sink'], 0))

            self.chains.append(chain)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_ds_rate_lora(int(self.samp_rate/self.bw_lora))
        self.set_samp_rate_lora(int(self.samp_rate/self.ds_rate_lora))
        for chain in self.chains:
            chain['freq_shift'].set_phase_inc(2.0*math.pi*(self.fc - chain['chan_fc'])/self.samp_rate)
            chain['lpf'].set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_bw_lora(self):
        return self.bw_lora

    def set_bw_lora(self, bw_lora):
        self.bw_lora = bw_lora
        self.set_ds_rate_lora(int(self.samp_rate/self.bw_lora))

    def get_ds_rate_lora(self):
        return self.ds_rate_lora

    def set_ds_rate_lora(self, ds_rate_lora):
        self.ds_rate_lora = ds_rate_lora
        self.set_samp_rate_lora(int(self.samp_rate/self.ds_rate_lora))

    def get_usrp_gain(self):
        return self.usrp_gain

    def set_usrp_gain(self, usrp_gain):
        self.usrp_gain = usrp_gain
        self.uhd_usrp_source_0.set_gain(self.usrp_gain, 0)

    def get_squelch(self):
        return self.squelch

    def set_squelch(self, squelch):
        self.squelch = squelch
        for chain in self.chains:
            chain['squelch'].set_threshold(self.squelch)

    def get_samp_rate_lora(self):
        return self.samp_rate_lora

    def set_samp_rate_lora(self, samp_rate_lora):
        self.samp_rate_lora = samp_rate_lora

    def get_filename_hex(self):
        return self.filename_hex

    def set_filename_hex(self, filename_hex):
        self.filename_hex = filename_hex

    def get_fc(self):
        return self.fc

    def set_fc(self, fc):
        self.fc = fc
        for chain in self.chains:
            chain['freq_shift'].set_phase_inc(2.0*math.pi*(self.fc - chain['chan_fc'])/self.samp_rate)
        self.uhd_usrp_source_0.set_center_freq(self.fc, 0)

def main(top_block_cls=lora_monitor, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()

if __name__ == '__main__':
    main()
