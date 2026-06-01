#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: loved
# GNU Radio version: 3.10.9.2

import os
from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
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
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from time import strftime
import gnuradio.lora_sdr as lora_sdr
import sip



class lora_monitor(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
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

        self.settings = Qt.QSettings("GNU Radio", "lora_monitor")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 13e6+0*250e3 + 0*56e6/256
        self.fc = fc = 908.6e6
        self.bw_lora = bw_lora = 500e3
        self.timestamp = timestamp = strftime('%Y-%m-%dT%H%M%S')
        self.samp_rate_str = samp_rate_str = "{:.3f}Msps".format(samp_rate/1e6)
        self.fc_str = fc_str = "{:.3f}MHz".format(fc/1e6)
        self.ds_rate_lora = ds_rate_lora = int(samp_rate/bw_lora)
        self.usrp_gain = usrp_gain = 10 # good for nearby lora tx
        self.squelch = squelch = -65 # set based on usrp gain
        self.samp_rate_lora = samp_rate_lora = int(samp_rate/ds_rate_lora)
        self.samp_rate_0 = samp_rate_0 = 56e6/2
        self.lora_channel_0 = lora_channel_0 = 903.9e6 # base channel frequency

        self.filename_hex = os.path.dirname(os.path.abspath(__file__)) + f"/monitor_output/monitor_output_{timestamp}.hex"
        if os.path.dirname(self.filename_hex) and not os.path.exists(os.path.dirname(self.filename_hex)):
            os.makedirs(os.path.dirname(self.filename_hex))

        ##################################################
        # Blocks
        ##################################################

        self._usrp_gain_range = qtgui.Range(0, 76, 1, 10, 1)
        self._usrp_gain_win = qtgui.RangeWidget(self._usrp_gain_range, self.set_usrp_gain, "USRP Gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._usrp_gain_win)
        self._squelch_range = qtgui.Range(-100, 12, 1, -65, 1)
        self._squelch_win = qtgui.RangeWidget(self._squelch_range, self.set_squelch, "Squelch Threshold", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_win)
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
        self.qtgui_sink_x_0 = qtgui.sink_c(
            1024, #fftsize
            window.WIN_BLACKMAN_hARRIS, #wintype
            fc, #fc
            samp_rate, #bw
            "", #name
            True, #plotfreq
            True, #plotwaterfall
            True, #plottime
            True, #plotconst
            None # parent
        )
        self.qtgui_sink_x_0.set_update_time(1.0/10)
        self._qtgui_sink_x_0_win = sip.wrapinstance(self.qtgui_sink_x_0.qwidget(), Qt.QWidget)

        self.qtgui_sink_x_0.enable_rf_freq(True)

        self.top_layout.addWidget(self._qtgui_sink_x_0_win)
        self.low_pass_filter_0_0_2 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_1_0 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_1 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_0_1 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_0_0_0 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_0_0 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0_0 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.low_pass_filter_0_0 = filter.fir_filter_ccf(
            ds_rate_lora,
            firdes.low_pass(
                1,
                samp_rate,
                80000,
                45000,
                window.WIN_HAMMING,
                6.76))
        self.lora_rx_0_0_1_0_2 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_1_0 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_1 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_0_1 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_0_0_0 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_0_0 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0_0 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.lora_rx_0_0_1_0 = lora_sdr.lora_sdr_lora_rx( bw=125000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate_lora, sf=10, sync_word=[0x34], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self._lora_channel_0_range = qtgui.Range(902.3e6, 914.9e6, 0.2e6, 903.9e6, 1)
        self._lora_channel_0_win = qtgui.RangeWidget(self._lora_channel_0_range, self.set_lora_channel_0, "LoRa Channel", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._lora_channel_0_win)
        self.blocks_freqshift_cc_0_0_2 = blocks.rotator_cc(2.0*math.pi*(fc-903.1e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_1_0 = blocks.rotator_cc(2.0*math.pi*(fc-903.5e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_1 = blocks.rotator_cc(2.0*math.pi*(fc-902.7e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_0_1 = blocks.rotator_cc(2.0*math.pi*(fc-903.3e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_0_0_0 = blocks.rotator_cc(2.0*math.pi*(fc-903.7e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_0_0 = blocks.rotator_cc(2.0*math.pi*(fc-902.9e6)/samp_rate)
        self.blocks_freqshift_cc_0_0_0 = blocks.rotator_cc(2.0*math.pi*(fc-902.5e6)/samp_rate)
        self.blocks_freqshift_cc_0_0 = blocks.rotator_cc(2.0*math.pi*(fc-902.3e6)/samp_rate)
        self.blocks_file_sink_0_2_1 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2_1.set_unbuffered(True)
        self.blocks_file_sink_0_2_0_1 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2_0_1.set_unbuffered(True)
        self.blocks_file_sink_0_2_0_0_0 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2_0_0_0.set_unbuffered(True)
        self.blocks_file_sink_0_2_0_0 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2_0_0.set_unbuffered(True)
        self.blocks_file_sink_0_2_0 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2_0.set_unbuffered(True)
        self.blocks_file_sink_0_2 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_2.set_unbuffered(True)
        self.blocks_file_sink_0_0 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0_0.set_unbuffered(True)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, self.filename_hex, True)
        self.blocks_file_sink_0.set_unbuffered(True)
        self.analog_pwr_squelch_xx_0_0_2 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_1_0 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_1 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_0_2 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_0_1 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_0_0_0 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_0_0 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0_0 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.analog_pwr_squelch_xx_0_0 = analog.pwr_squelch_cc(squelch, (1e-4), 0, True)
        self.LoRa_AIS_reportPower_0_1 = LoRa_AIS.reportPower('Channel 5 Magnitude')
        self.LoRa_AIS_reportPower_0_0_1 = LoRa_AIS.reportPower('Channel 6 Magnitude')
        self.LoRa_AIS_reportPower_0_0_0_1 = LoRa_AIS.reportPower('Channel 7 Magnitude')
        self.LoRa_AIS_reportPower_0_0_0_0_0 = LoRa_AIS.reportPower('Channel 8 Magnitude')
        self.LoRa_AIS_reportPower_0_0_0_0 = LoRa_AIS.reportPower('Channel 4 Magnitude')
        self.LoRa_AIS_reportPower_0_0_0 = LoRa_AIS.reportPower('Channel 3 Magnitude')
        self.LoRa_AIS_reportPower_0_0 = LoRa_AIS.reportPower('Channel 2 Magnitude')
        self.LoRa_AIS_reportPower_0 = LoRa_AIS.reportPower('Channel 1 Magnitude')


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_pwr_squelch_xx_0_0, 0), (self.LoRa_AIS_reportPower_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0, 0), (self.lora_rx_0_0_1_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0, 0), (self.LoRa_AIS_reportPower_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0, 0), (self.lora_rx_0_0_1_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_0, 0), (self.LoRa_AIS_reportPower_0_0_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_0, 0), (self.lora_rx_0_0_1_0_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_0_0, 0), (self.LoRa_AIS_reportPower_0_0_0_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_0_0, 0), (self.lora_rx_0_0_1_0_0_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_1, 0), (self.LoRa_AIS_reportPower_0_0_1, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_1, 0), (self.lora_rx_0_0_1_0_0_1, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_0_2, 0), (self.qtgui_sink_x_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_1, 0), (self.LoRa_AIS_reportPower_0_0_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_1, 0), (self.lora_rx_0_0_1_0_1, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_1_0, 0), (self.LoRa_AIS_reportPower_0_0_0_1, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_1_0, 0), (self.lora_rx_0_0_1_0_1_0, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_2, 0), (self.LoRa_AIS_reportPower_0_1, 0))
        self.connect((self.analog_pwr_squelch_xx_0_0_2, 0), (self.lora_rx_0_0_1_0_2, 0))
        self.connect((self.blocks_freqshift_cc_0_0, 0), (self.low_pass_filter_0_0, 0))
        self.connect((self.blocks_freqshift_cc_0_0_0, 0), (self.low_pass_filter_0_0_0, 0))
        self.connect((self.blocks_freqshift_cc_0_0_0_0, 0), (self.low_pass_filter_0_0_0_0, 0))
        self.connect((self.blocks_freqshift_cc_0_0_0_0_0, 0), (self.low_pass_filter_0_0_0_0_0, 0))
        self.connect((self.blocks_freqshift_cc_0_0_0_1, 0), (self.low_pass_filter_0_0_0_1, 0))
        self.connect((self.blocks_freqshift_cc_0_0_1, 0), (self.low_pass_filter_0_0_1, 0))
        self.connect((self.blocks_freqshift_cc_0_0_1_0, 0), (self.low_pass_filter_0_0_1_0, 0))
        self.connect((self.blocks_freqshift_cc_0_0_2, 0), (self.low_pass_filter_0_0_2, 0))
        self.connect((self.lora_rx_0_0_1_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.lora_rx_0_0_1_0_0, 0), (self.blocks_file_sink_0_2, 0))
        self.connect((self.lora_rx_0_0_1_0_0_0, 0), (self.blocks_file_sink_0_2_0_0, 0))
        self.connect((self.lora_rx_0_0_1_0_0_0_0, 0), (self.blocks_file_sink_0_2_0_0_0, 0))
        self.connect((self.lora_rx_0_0_1_0_0_1, 0), (self.blocks_file_sink_0_2_1, 0))
        self.connect((self.lora_rx_0_0_1_0_1, 0), (self.blocks_file_sink_0_2_0, 0))
        self.connect((self.lora_rx_0_0_1_0_1_0, 0), (self.blocks_file_sink_0_2_0_1, 0))
        self.connect((self.lora_rx_0_0_1_0_2, 0), (self.blocks_file_sink_0_0, 0))
        self.connect((self.low_pass_filter_0_0, 0), (self.analog_pwr_squelch_xx_0_0, 0))
        self.connect((self.low_pass_filter_0_0_0, 0), (self.analog_pwr_squelch_xx_0_0_0, 0))
        self.connect((self.low_pass_filter_0_0_0_0, 0), (self.analog_pwr_squelch_xx_0_0_0_0, 0))
        self.connect((self.low_pass_filter_0_0_0_0_0, 0), (self.analog_pwr_squelch_xx_0_0_0_0_0, 0))
        self.connect((self.low_pass_filter_0_0_0_1, 0), (self.analog_pwr_squelch_xx_0_0_0_1, 0))
        self.connect((self.low_pass_filter_0_0_1, 0), (self.analog_pwr_squelch_xx_0_0_1, 0))
        self.connect((self.low_pass_filter_0_0_1_0, 0), (self.analog_pwr_squelch_xx_0_0_1_0, 0))
        self.connect((self.low_pass_filter_0_0_2, 0), (self.analog_pwr_squelch_xx_0_0_2, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.analog_pwr_squelch_xx_0_0_0_2, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_0_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_0_0_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_0_1, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_1, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_1_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_freqshift_cc_0_0_2, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "lora_monitor")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_ds_rate_lora(int(self.samp_rate/self.bw_lora))
        self.set_samp_rate_lora(int(self.samp_rate/self.ds_rate_lora))
        self.set_samp_rate_str("{:.3f}Msps".format(self.samp_rate/1e6))
        self.blocks_freqshift_cc_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.3e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.5e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.9e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-903.7e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_1.set_phase_inc(2.0*math.pi*(self.fc-903.3e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_1.set_phase_inc(2.0*math.pi*(self.fc-902.7e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_1_0.set_phase_inc(2.0*math.pi*(self.fc-903.5e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_2.set_phase_inc(2.0*math.pi*(self.fc-903.1e6)/self.samp_rate)
        self.low_pass_filter_0_0.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_0.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_0_0.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_0_0_0.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_0_1.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_1.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_1_0.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.low_pass_filter_0_0_2.set_taps(firdes.low_pass(1, self.samp_rate, 80000, 45000, window.WIN_HAMMING, 6.76))
        self.qtgui_sink_x_0.set_frequency_range(self.fc, self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_fc(self):
        return self.fc

    def set_fc(self, fc):
        self.fc = fc
        self.set_fc_str("{:.3f}MHz".format(self.fc/1e6))
        self.blocks_freqshift_cc_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.3e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.5e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-902.9e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_0_0.set_phase_inc(2.0*math.pi*(self.fc-903.7e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_0_1.set_phase_inc(2.0*math.pi*(self.fc-903.3e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_1.set_phase_inc(2.0*math.pi*(self.fc-902.7e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_1_0.set_phase_inc(2.0*math.pi*(self.fc-903.5e6)/self.samp_rate)
        self.blocks_freqshift_cc_0_0_2.set_phase_inc(2.0*math.pi*(self.fc-903.1e6)/self.samp_rate)
        self.qtgui_sink_x_0.set_frequency_range(self.fc, self.samp_rate)
        self.uhd_usrp_source_0.set_center_freq(self.fc, 0)

    def get_bw_lora(self):
        return self.bw_lora

    def set_bw_lora(self, bw_lora):
        self.bw_lora = bw_lora
        self.set_ds_rate_lora(int(self.samp_rate/self.bw_lora))

    def get_timestamp(self):
        return self.timestamp

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp
        self.set_filename("/home/loved/Projects/loved2024/iot_living_lab/KENNEL/collection/lora_collection_" + self.timestamp +  "_" + self.fc_str + "_" + self.samp_rate_str + ".32cf")

    def get_samp_rate_str(self):
        return self.samp_rate_str

    def set_samp_rate_str(self, samp_rate_str):
        self.samp_rate_str = samp_rate_str
        self.set_filename("/home/loved/Projects/loved2024/iot_living_lab/KENNEL/collection/lora_collection_" + self.timestamp +  "_" + self.fc_str + "_" + self.samp_rate_str + ".32cf")

    def get_fc_str(self):
        return self.fc_str

    def set_fc_str(self, fc_str):
        self.fc_str = fc_str
        self.set_filename("/home/loved/Projects/loved2024/iot_living_lab/KENNEL/collection/lora_collection_" + self.timestamp +  "_" + self.fc_str + "_" + self.samp_rate_str + ".32cf")

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
        self.analog_pwr_squelch_xx_0_0.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_0.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_0_0.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_0_0_0.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_0_1.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_0_2.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_1.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_1_0.set_threshold(self.squelch)
        self.analog_pwr_squelch_xx_0_0_2.set_threshold(self.squelch)

    def get_samp_rate_lora(self):
        return self.samp_rate_lora

    def set_samp_rate_lora(self, samp_rate_lora):
        self.samp_rate_lora = samp_rate_lora

    def get_samp_rate_0(self):
        return self.samp_rate_0

    def set_samp_rate_0(self, samp_rate_0):
        self.samp_rate_0 = samp_rate_0

    def get_lora_channel_0(self):
        return self.lora_channel_0

    def set_lora_channel_0(self, lora_channel_0):
        self.lora_channel_0 = lora_channel_0

def main(top_block_cls=lora_monitor, options=None):

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
