from __future__ import division

import math
import logging
import numpy as np

from gnuradio.filter import window

import consts
import utils


class configuration(object):
    """Container for configurable settings."""
    def __init__(self, args):
        # Set logging levels
        self.logger = logging.getLogger('gr-analyzer')
        console_handler = logging.StreamHandler()
        logfmt = logging.Formatter("%(levelname)s:%(funcName)s: %(message)s")
        console_handler.setFormatter(logfmt)
        self.logger.addHandler(console_handler)
        if args.debug:
            loglvl = logging.DEBUG
        else:
            loglvl = logging.INFO
        self.logger.setLevel(loglvl)

        # If set to True, raw data from next run of flowgraph will be exported
        self.export_raw_time_data = False
        self.export_raw_fft_data = False

        # Add command line argument values to config namespace
        self.__dict__.update(args.__dict__)
        self.overlap = self.overlap / 100.0 # percent to decimal
        self.requested_span = self.span
        self.cpu_format = 'fc32'            # hard coded for now

        # configuration variables set by update():
        self.span = None               # width in Hz of total area to sample
        self.deltaf = None             # width in Hz of one fft bin (delta f)
        self.freq_step = None          # step in Hz between center frequencies
        self.min_freq = None           # lowest sampled frequency
        self.max_freq = None           # highest sampled frequency
        self.center_freqs = None       # cached nparray of center (tuned) freqs
        self.n_segments = None         # number of rf frontend retunes required
        self.bin_freqs = None          # cached nparray of all sampled freqs
        self.bin_start = None          # array index of first usable bin
        self.bin_stop = None           # array index of last usable bin
        self.bin_offset = None         # offset of start/stop index from center
        self.max_plotted_bin = None    # absolute max bin in bin_freqs to plot
        self.update()

        # commented-out windows require extra parameters that we're not set up
        # to handle at this time
        self.windows = {
            'Bartlett':         window.bartlett,
            'Blackman':         window.blackman,
            'Blackman2':        window.blackman2,
            'Blackman3':        window.blackman3,
            'Blackman4':        window.blackman4,
            'Blackman-Harris':  window.blackman_harris,
            'Blackman-Nuttall': window.blackman_nuttal,
            #'Cosine':           window.coswindow,
            #'Exponential':      window.exponential,
            'Flattop':          window.flattop,
            'Hamming':          window.hamming,
            'Hann':             window.hann,
            'Hanning':          window.hanning,
            #'Kaiser':           window.kaiser,
            'Nuttall':          window.nuttal,
            'Nuttall CFD':      window.nuttal_cfd,
            'Parzen':           window.parzen,
            'Rectangular':      window.rectangular,
            'Riemann':          window.riemann,
            'Welch':            window.welch
        }
        self.window = None # Name of window, set by set_window
        self.window_coefficients = None # Set by set_window
        self.set_window('Blackman-Harris')

    def set_wire_format(self, fmt):
        """Set the ethernet wire format between the USRP and host."""
        if fmt in consts.WIRE_FORMATS:
            self.wire_format = str(fmt) # ensure not unicode str

    def set_fft_size(self, size):
        """Set the fft size in bins (must be 2^n between 32 and 8192)."""
        if size in consts.FFT_SIZES:
            self.fft_size = size
        else:
            msg = "Unable to set fft size to {}, must be one of {!r}"
            self.logger.warn(msg.format(size, sorted(list(consts.FFT_SIZES))))

        self.logger.debug("fft size is {} bins".format(self.fft_size))

    def set_window(self, fn_name):
        """Set the window"""
        if fn_name in self.windows.keys():
            self.window = fn_name

        self.window_coefficients = self.windows[self.window](self.fft_size)

    def update(self):
        """Convencience function to update various variables and caches"""
        self.update_deltaf()
        self.update_freq_step()
        self.update_span()
        self.update_min_max_freq()
        self.update_tuned_freq_cache()
        self.update_bin_freq_cache()
        self.update_bin_indices()

    def update_deltaf(self):
        """Update the bin width"""
        self.deltaf = self.sample_rate / self.fft_size

    def update_freq_step(self):
        """Set the freq_step to a percentage of the actual data throughput.

        This allows us to discard bins on both ends of the spectrum.
        """
        self.freq_step = self.adjust_rate(self.sample_rate,
                                          self.deltaf,
                                          self.overlap)

    def update_span(self):
        """If no requested span, set max span using only one center frequency"""
        if self.requested_span:
            self.span = self.requested_span
        else:
            self.span = self.freq_step

    def update_min_max_freq(self):
        """Calculate actual start and end of requested span"""
        self.min_freq = self.center_freq - (self.span / 2) + (self.deltaf / 2)
        self.max_freq = self.min_freq + self.span - self.deltaf

    def update_tuned_freq_cache(self):
        """Cache center (tuned) frequencies.

        Sets:
          self.center_freqs     - array of all frequencies to be tuned
          self.n_segments       - length of self.center_freqs
        """
        # calculate min and max center frequencies
        min_fc = self.min_freq + (self.freq_step / 2)
        if self.span <= self.freq_step:
            self.center_freqs = np.array([min_fc])
        else:
            initial_n_segments = math.floor(self.span / self.freq_step)
            max_fc = min_fc + (initial_n_segments * self.freq_step)
            self.center_freqs = np.arange(min_fc, max_fc + 1, self.freq_step)

        self.n_segments = len(self.center_freqs)

    def update_bin_freq_cache(self):
        """Cache frequencies at the center of each FFT bin"""
        # cache all fft bin frequencies
        max_fc = self.center_freqs[-1]
        max_bin_freq = max_fc + (self.freq_step / 2)
        self.bin_freqs = np.arange(self.min_freq, max_bin_freq, self.deltaf)

    def update_bin_indices(self):
        """Update common indices used in cropping and overlaying DFTs"""
        self.bin_start = int(self.fft_size * (self.overlap / 2))
        self.bin_stop = int(self.fft_size - self.bin_start)
        self.max_plotted_bin = utils.find_nearest(self.bin_freqs, self.max_freq) + 1
        self.bin_offset = (self.bin_stop - self.bin_start) / 2

    @staticmethod
    def adjust_rate(samp_rate, deltaf, overlap):
        """Reduce rate by a user-selected percentage and round it.

        The adjusted sample size is used to calculate a smaller frequency
        step. This allows us to overlap a percentage of bins which are most
        affected by filter rolloff.

        The adjusted sample size is then rounded so that a whole number of bins
        of size deltaf go into it.
        """
        ratio_valid_bins = 1.0 - overlap
        return int(round((samp_rate * ratio_valid_bins) / deltaf) * deltaf)

    def export_to_matlab(self):
        """Export current configuration settings to .settings.mat"""
        e = """TODO: Export config and raw bin data, then use octave script to
               translate it into matlab format"""
        raise NotImplementedError(e)
