import numpy as np
from gnuradio import gr
import time
import pmt


class blk(gr.sync_block):

    def __init__(
        self,
        vec_len=8192,
        sample_rate=1000000,
        rx_freq_mhz=2412,
        min_publish_interval_s=1.0,
    ):
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',
            in_sig=[(np.float32, vec_len), (np.float32, vec_len)],
            out_sig=None
        )

        self.message_port_register_out(pmt.intern('detected_signals'))

        self.sample_rate = float(sample_rate)
        self.fft_size = int(vec_len)
        self.rx_freq_mhz = float(rx_freq_mhz)
        self.min_publish_interval_s = float(min_publish_interval_s)
        self.last_publish_time = 0.0

    def set_rx_freq_mhz(self, freq_mhz):
        self.rx_freq_mhz = float(freq_mhz)

    def set_min_publish_interval_s(self, value):
        self.min_publish_interval_s = float(value)

    def work(self, input_items, output_items):
        for vecindx in range(len(input_items[0])):
            above_threshold = np.nonzero(
                input_items[0][vecindx] > input_items[1][vecindx][0]
            )[0]

            if len(above_threshold) == 0:
                continue

            now = time.time()

            if now - self.last_publish_time < self.min_publish_interval_s:
                continue

            self.last_publish_time = now

            max_index = input_items[0][vecindx].argmax()

            max_freq_hz = (
                (max_index / float(self.fft_size)) * self.sample_rate
                - (self.sample_rate / 2.0)
                + (self.rx_freq_mhz * 1e6)
            )

            max_power = int(input_items[0][vecindx].max())

            self.message_port_pub(
                pmt.intern('detected_signals'),
                pmt.intern(
                    f"TSI:/Signal Found/{max_freq_hz}/{max_power}/{now}"
                )
            )

        return len(input_items[0])
