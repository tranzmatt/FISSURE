import time
import numpy as np
import pmt
from gnuradio import gr


class blk(gr.sync_block):
    def __init__(
        self,
        samp_rate=1e6,
        rx_freq_hz=433e6,
        tperiod=0.1,
        thresh=10.0,
        min_peak=12.0,
        holdoff_s=0.08,
        peak_window=8000,
    ):
        gr.sync_block.__init__(
            self,
            name='burst_detector',
            in_sig=[np.float32],
            out_sig=None
        )

        self.samp_rate = float(samp_rate)
        self.rx_freq_hz = float(rx_freq_hz)
        self.thresh = float(thresh)
        self.min_peak = float(min_peak)
        self.holdoff = int(float(holdoff_s) * self.samp_rate)
        self.peak_window = int(peak_window)

        self.n = 0
        self.next_ok = 0
        self.in_peak = False
        self.peak_val = 0.0
        self.peak_idx = 0
        self.peak_end = 0

        self.message_port_register_out(pmt.intern("det"))

    def set_rx_freq_hz(self, rx_freq_hz):
        self.rx_freq_hz = float(rx_freq_hz)

    def work(self, input_items, output_items):
        x = input_items[0]
        L = len(x)

        for i in range(L):
            idx = self.n + i
            v = float(x[i])

            if idx < self.next_ok:
                continue

            if not self.in_peak:
                if v >= self.thresh:
                    self.in_peak = True
                    self.peak_val = v
                    self.peak_idx = idx
                    self.peak_end = idx + self.peak_window
            else:
                if v > self.peak_val:
                    self.peak_val = v
                    self.peak_idx = idx

                if idx >= self.peak_end:
                    if self.peak_val >= self.min_peak:
                        ts = time.time()
                        msg = f"TSI:/LFM Beacon/{self.rx_freq_hz:.1f}/{self.peak_val:.2f}/{ts:.6f}"
                        self.message_port_pub(
                            pmt.intern("det"),
                            pmt.intern(msg)
                        )

                    self.next_ok = self.peak_end + self.holdoff
                    self.in_peak = False

        self.n += L
        return L
