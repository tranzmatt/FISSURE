import numpy as np
import pmt
from gnuradio import gr

class blk(gr.sync_block):
    def __init__(self, samp_rate=1e6, tperiod=0.1, thresh=10.0, holdoff_s=0.08, peak_window=2000):
        gr.sync_block.__init__(self,
            name='burst_detector',
            in_sig=[np.float32],
            out_sig=None)

        self.samp_rate = float(samp_rate)
        self.thresh = float(thresh)
        self.holdoff = int(float(holdoff_s) * self.samp_rate)
        self.peak_window = int(peak_window)

        self.n = 0                      # absolute sample counter
        self.next_ok = 0                # next sample index allowed to trigger
        self.in_peak = False
        self.peak_val = 0.0
        self.peak_idx = 0

        self.message_port_register_out(pmt.intern("det"))

    def work(self, input_items, output_items):
        x = input_items[0]
        L = len(x)

        for i in range(L):
            idx = self.n + i
            v = float(x[i])

            if idx < self.next_ok:
                continue

            # start "peak capture" when we cross threshold
            if not self.in_peak:
                if v >= self.thresh:
                    self.in_peak = True
                    self.peak_val = v
                    self.peak_idx = idx
                    self.peak_end = idx + self.peak_window
            else:
                # track maximum until peak_window ends
                if v > self.peak_val:
                    self.peak_val = v
                    self.peak_idx = idx

                if idx >= self.peak_end:
                    # emit detection
                    d = pmt.make_dict()
                    d = pmt.dict_add(d, pmt.intern("sample_index"), pmt.from_uint64(self.peak_idx))
                    d = pmt.dict_add(d, pmt.intern("metric"), pmt.from_double(self.peak_val))
                    self.message_port_pub(pmt.intern("det"), d)

                    # enforce holdoff
                    self.next_ok = self.peak_idx + self.holdoff

                    # reset peak capture
                    self.in_peak = False

        self.n += L
        return L
