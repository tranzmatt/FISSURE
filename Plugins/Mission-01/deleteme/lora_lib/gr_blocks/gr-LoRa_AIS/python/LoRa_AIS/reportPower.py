#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 AIS.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
import numpy as np
from gnuradio import gr

class reportPower(gr.sync_block):
    """
    docstring for block reportPower
    """
    def __init__(self, channel_tag:str):
        gr.sync_block.__init__(self,
            name="reportPower",
            in_sig=[np.complex64, ],
            out_sig=None)
        self.channel_tag = channel_tag

    def work(self, input_items, output_items):
        in0 = input_items[0]
        if len(in0) >= 4096:
            sys.stdout.write(f"{self.channel_tag} = {np.mean(np.abs(in0)):0.3f}\n")
            sys.stdout.flush()
            # <+signal processing here+>
            return len(input_items[0])
        return 0
