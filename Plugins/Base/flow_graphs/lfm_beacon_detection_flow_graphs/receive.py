#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Receive
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
from gnuradio import blocks, gr
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import soapy
import numpy as np
import receive_epy_block_0 as epy_block_0  # embedded python block
import sip



class receive(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Receive", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Receive")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "receive")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.ton = ton = 10e-3
        self.samp_rate = samp_rate = 1e6
        self.bw = bw = 200e3
        self.Nmatch = Nmatch = int(0.25 * ton * samp_rate)
        self.xlating_hz = xlating_hz = -150e3
        self.tperiod = tperiod = 0.1
        self.threshold = threshold = 30
        self.serial = serial = "False"
        self.rx_gain = rx_gain = 40
        self.rx_freq = rx_freq = 433e6
        self.peak_window = peak_window = 8000
        self.notes = notes = "Transmits an on message for a Monoprice Z-Wave Plus RGB Smart Bulb."
        self.min_peak = min_peak = 40
        self.matched_taps = matched_taps = np.conjugate(np.exp(1j*2*np.pi*np.cumsum(((-bw/2)+(bw/ton)*(np.arange(Nmatch)/samp_rate)))/samp_rate)[::-1])
        self.lpf_trans = lpf_trans = bw/2
        self.lpf_cutoff = lpf_cutoff = bw*1.2
        self.holdoff_s = holdoff_s = 0.08
        self.eps = eps = 1e-12
        self.avg_len = avg_len = int(0.01*samp_rate)

        ##################################################
        # Blocks
        ##################################################

        self.soapy_rtlsdr_source_0 = None
        dev = 'driver=rtlsdr'
        stream_args = 'bufflen=16384'
        tune_args = ['']
        settings = ['']

        def _set_soapy_rtlsdr_source_0_gain_mode(channel, agc):
            self.soapy_rtlsdr_source_0.set_gain_mode(channel, agc)
            if not agc:
                  self.soapy_rtlsdr_source_0.set_gain(channel, self._soapy_rtlsdr_source_0_gain_value)
        self.set_soapy_rtlsdr_source_0_gain_mode = _set_soapy_rtlsdr_source_0_gain_mode

        def _set_soapy_rtlsdr_source_0_gain(channel, name, gain):
            self._soapy_rtlsdr_source_0_gain_value = gain
            if not self.soapy_rtlsdr_source_0.get_gain_mode(channel):
                self.soapy_rtlsdr_source_0.set_gain(channel, gain)
        self.set_soapy_rtlsdr_source_0_gain = _set_soapy_rtlsdr_source_0_gain

        def _set_soapy_rtlsdr_source_0_bias(bias):
            if 'biastee' in self._soapy_rtlsdr_source_0_setting_keys:
                self.soapy_rtlsdr_source_0.write_setting('biastee', bias)
        self.set_soapy_rtlsdr_source_0_bias = _set_soapy_rtlsdr_source_0_bias

        self.soapy_rtlsdr_source_0 = soapy.source(dev, "fc32", 1, '',
                                  stream_args, tune_args, settings)

        self._soapy_rtlsdr_source_0_setting_keys = [a.key for a in self.soapy_rtlsdr_source_0.get_setting_info()]

        self.soapy_rtlsdr_source_0.set_sample_rate(0, samp_rate)
        self.soapy_rtlsdr_source_0.set_frequency(0, rx_freq)
        self.soapy_rtlsdr_source_0.set_frequency_correction(0, 0)
        self.set_soapy_rtlsdr_source_0_bias(bool(False))
        self._soapy_rtlsdr_source_0_gain_value = rx_gain
        self.set_soapy_rtlsdr_source_0_gain_mode(0, bool(False))
        self.set_soapy_rtlsdr_source_0_gain(0, 'TUNER', rx_gain)
        self.qtgui_time_sink_x_0_0_0_1_0_0 = qtgui.time_sink_f(
            300000, #size
            1, #samp_rate
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_0_0_1_0_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0_0_0_1_0_0.set_y_axis(-100, 100)

        self.qtgui_time_sink_x_0_0_0_1_0_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_tags(True)
        self.qtgui_time_sink_x_0_0_0_1_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_autoscale(True)
        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_grid(True)
        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_0_0_1_0_0.enable_stem_plot(False)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_0_0_1_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_0_0_1_0_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_0_0_1_0_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_x_0_0_0_1_0_0_win)
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(1, matched_taps, xlating_hz, samp_rate)
        self.epy_block_0 = epy_block_0.blk(samp_rate=samp_rate, rx_freq_hz=rx_freq, tperiod=tperiod, thresh=threshold, min_peak=min_peak, holdoff_s=holdoff_s, peak_window=peak_window)
        self.dc_blocker_xx_0 = filter.dc_blocker_cc(32, True)
        self.blocks_moving_average_xx_1 = blocks.moving_average_ff(64, (1/64), 4000, 1)
        self.blocks_moving_average_xx_0 = blocks.moving_average_ff(avg_len, (1/avg_len), 4000, 1)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(1)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.epy_block_0, 'det'), (self.blocks_message_debug_0, 'print'))
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_moving_average_xx_0, 0))
        self.connect((self.blocks_moving_average_xx_0, 0), (self.blocks_moving_average_xx_1, 0))
        self.connect((self.blocks_moving_average_xx_1, 0), (self.epy_block_0, 0))
        self.connect((self.blocks_moving_average_xx_1, 0), (self.qtgui_time_sink_x_0_0_0_1_0_0, 0))
        self.connect((self.dc_blocker_xx_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))
        self.connect((self.soapy_rtlsdr_source_0, 0), (self.dc_blocker_xx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "receive")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_ton(self):
        return self.ton

    def set_ton(self, ton):
        self.ton = ton
        self.set_Nmatch(int(0.25 * self.ton * self.samp_rate))
        self.set_matched_taps(np.conjugate(np.exp(1j*2*np.pi*np.cumsum(((-self.bw/2)+(self.bw/self.ton)*(np.arange(self.Nmatch)/self.samp_rate)))/self.samp_rate)[::-1]))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_Nmatch(int(0.25 * self.ton * self.samp_rate))
        self.set_avg_len(int(0.01*self.samp_rate))
        self.set_matched_taps(np.conjugate(np.exp(1j*2*np.pi*np.cumsum(((-self.bw/2)+(self.bw/self.ton)*(np.arange(self.Nmatch)/self.samp_rate)))/self.samp_rate)[::-1]))
        self.epy_block_0.samp_rate = self.samp_rate
        self.soapy_rtlsdr_source_0.set_sample_rate(0, self.samp_rate)

    def get_bw(self):
        return self.bw

    def set_bw(self, bw):
        self.bw = bw
        self.set_lpf_cutoff(self.bw*1.2)
        self.set_lpf_trans(self.bw/2)
        self.set_matched_taps(np.conjugate(np.exp(1j*2*np.pi*np.cumsum(((-self.bw/2)+(self.bw/self.ton)*(np.arange(self.Nmatch)/self.samp_rate)))/self.samp_rate)[::-1]))

    def get_Nmatch(self):
        return self.Nmatch

    def set_Nmatch(self, Nmatch):
        self.Nmatch = Nmatch
        self.set_matched_taps(np.conjugate(np.exp(1j*2*np.pi*np.cumsum(((-self.bw/2)+(self.bw/self.ton)*(np.arange(self.Nmatch)/self.samp_rate)))/self.samp_rate)[::-1]))

    def get_xlating_hz(self):
        return self.xlating_hz

    def set_xlating_hz(self, xlating_hz):
        self.xlating_hz = xlating_hz
        self.freq_xlating_fir_filter_xxx_0.set_center_freq(self.xlating_hz)

    def get_tperiod(self):
        return self.tperiod

    def set_tperiod(self, tperiod):
        self.tperiod = tperiod

    def get_threshold(self):
        return self.threshold

    def set_threshold(self, threshold):
        self.threshold = threshold
        self.epy_block_0.thresh = self.threshold

    def get_serial(self):
        return self.serial

    def set_serial(self, serial):
        self.serial = serial

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.set_soapy_rtlsdr_source_0_gain(0, 'TUNER', self.rx_gain)

    def get_rx_freq(self):
        return self.rx_freq

    def set_rx_freq(self, rx_freq):
        self.rx_freq = rx_freq
        self.epy_block_0.rx_freq_hz = self.rx_freq
        self.soapy_rtlsdr_source_0.set_frequency(0, self.rx_freq)

    def get_peak_window(self):
        return self.peak_window

    def set_peak_window(self, peak_window):
        self.peak_window = peak_window
        self.epy_block_0.peak_window = self.peak_window

    def get_notes(self):
        return self.notes

    def set_notes(self, notes):
        self.notes = notes

    def get_min_peak(self):
        return self.min_peak

    def set_min_peak(self, min_peak):
        self.min_peak = min_peak
        self.epy_block_0.min_peak = self.min_peak

    def get_matched_taps(self):
        return self.matched_taps

    def set_matched_taps(self, matched_taps):
        self.matched_taps = matched_taps
        self.freq_xlating_fir_filter_xxx_0.set_taps(self.matched_taps)

    def get_lpf_trans(self):
        return self.lpf_trans

    def set_lpf_trans(self, lpf_trans):
        self.lpf_trans = lpf_trans

    def get_lpf_cutoff(self):
        return self.lpf_cutoff

    def set_lpf_cutoff(self, lpf_cutoff):
        self.lpf_cutoff = lpf_cutoff

    def get_holdoff_s(self):
        return self.holdoff_s

    def set_holdoff_s(self, holdoff_s):
        self.holdoff_s = holdoff_s

    def get_eps(self):
        return self.eps

    def set_eps(self, eps):
        self.eps = eps

    def get_avg_len(self):
        return self.avg_len

    def set_avg_len(self, avg_len):
        self.avg_len = avg_len
        self.blocks_moving_average_xx_0.set_length_and_scale(self.avg_len, (1/self.avg_len))




def main(top_block_cls=receive, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
