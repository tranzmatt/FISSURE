"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import time
import pmt
import zmq

class blk(gr.sync_block):

    def __init__(self, vec_len=8192, sample_rate=1000000, rx_freq_mhz=2412):
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',
            in_sig=[(np.float32,vec_len),(np.float32,vec_len)],
            out_sig=None
        )
        self.message_port_register_out(pmt.intern('detected_signals'))
        self.sample_rate = sample_rate
        self.fft_size = vec_len
        self.rx_freq_mhz = rx_freq_mhz

    # NEW: allow external code to update frequency dynamically
    def set_rx_freq_mhz(self, freq_mhz):
        self.rx_freq_mhz = freq_mhz

    def work(self, input_items,output_items):
        for vecindx in range(len(input_items[0])):

            if len(np.nonzero(input_items[0][vecindx] > input_items[1][vecindx][0])[0]) > 0:
                max_index = input_items[0][vecindx].argmax()

                max_freq_hz = (
                    (max_index / float(self.fft_size)) * self.sample_rate
                    - (self.sample_rate / 2.0)
                    + (self.rx_freq_mhz * 1e6)
                )

                max_power = str(int(input_items[0][vecindx].max()))

                self.message_port_pub(
                    pmt.intern('detected_signals'),
                    pmt.intern(
                        f"TSI:/Signal Found/{max_freq_hz}/{max_power}/{time.time()}"
                    )
                )

        return len(input_items[0])
