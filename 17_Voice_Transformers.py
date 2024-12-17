{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "\n",
    "# A Gallery of Voice Transformers\n",
    "\n",
    "\n",
    "In this notebook we will explore various ways to implement a system that changes the voice of a speaker. Typical applications for these devices are international spy missions and prank calls, and devices such as the one displayed here can be easily bought on the dark web... \n",
    "\n",
    "<img width=\"250\" style=\"float: left; margin: 10px 20px 0 0;\" src=\"voice_changer.jpg\">\n",
    "\n",
    "More seriously, our goal is to illustrate a range of techniques that allow us to modify a digital audio signal in ways that are increasingly more sophisticated  -- and increasingly more non-linear: a nice departure from the usual LTI signal processing paradigm!. Also, our focus is on algorithms that can be implemented in efficiently and with minimal latency, so that we can use them to modify the voice of a speaker in real time; we will concentrate mainly on changing the pitch of a spoken utterance, which can be used to turn the speaker into a chipmunk or into Darth Vader. \n",
    "\n",
    "Let's start with the standard initial bookkeeping and let's define some helper functions that will be useful in the notebook:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "%matplotlib inline\n",
    "import matplotlib.pyplot as plt\n",
    "import numpy as np\n",
    "import scipy.signal as sp\n",
    "import IPython\n",
    "from scipy.io import wavfile"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "plt.rcParams[\"figure.figsize\"] = (14,4)\n",
    "plt.rcParams['image.cmap'] = 'tab10'"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Although we are interested in a low-latency, real-time algorithm, in this notebook we will process a sample speech file to illustrate the various techniques that we can implement. Let's load it and listen to it:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "Fs, s = wavfile.read('speech.wav')\n",
    "s = s / 32767.0 # scale the signal to floats in [-1, 1]\n",
    "print('sampling rate: {}Hz'.format(Fs))\n",
    "IPython.display.Audio(s, rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Here's a simple helper function to convert milliseconds to samples:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def ms2smp(ms, Fs):\n",
    "    return int(float(Fs) * float(ms) / 1000.0)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's also define a function to plot the magnitude spectrum of the speech signal (or of a portion thereof) with the labeling of the frequency axis in Hertz:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def plot_spec(x, Fs, max_freq=None, do_fft=True):\n",
    "    C = int(len(x) / 2)  # positive frequencies only\n",
    "    if max_freq:\n",
    "        C = int(C * max_freq / float(Fs) * 2) \n",
    "    X = np.abs(np.fft.fft(x)[0:C]) if do_fft else x[0:C]\n",
    "    N = Fs * np.arange(0, C) / len(x);\n",
    "    plt.plot(N, X)\n",
    "    return N, X"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "plot_spec(s, Fs, 8000);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1 - The \"Alien Voice\"\n",
    "\n",
    "The cheapest trick in the book to alter a person's voice is to use standard sinusoidal modulation to shift the voice spectrum up or down:\n",
    "\n",
    "$$\n",
    "    y[n] = x[n] \\, \\cos(\\omega_0 n)\n",
    "$$\n",
    "\n",
    "Since the modulation frequency must be kept small to preserve intelligibility, the resulting signal will be severely affected by aliasing. Acoustically, this produces the \"robotic\" voice that can be heard in old, low-budget sci-fi movies:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def alien_voice(x, f, Fs):\n",
    "    w = (float(f) / Fs) * 2 * np.pi  # normalized modulation frequency\n",
    "    return 2 * np.multiply(x, np.cos(w * np.arange(0,len(x))))\n",
    "\n",
    "IPython.display.Audio(alien_voice(s, 500, Fs), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "If we plot the spectrum of the modulated signal, we can immediately see the effect of aliasing in the two peaks at $500\\pm100$Hz (where 100Hz is the approximate frequency of the peak in the original signal and 500Hz is the modulation frequency)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "plot_spec(alien_voice(s, 500, Fs), Fs, 8000);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "The only selling points for this voice transformer are related to its simplicity:\n",
    "  * it works in real time with no delay (modulation is a memoryless operator)\n",
    "  * it can be easily implemented in analog hardware\n",
    "  \n",
    "On the other hand, the end result is not particularly satisfying:\n",
    "  * intelligibility is poor\n",
    "  * harmonicity of voiced sounds is not preserved (the voice is \"bell\"-like)\n",
    "  * there are a lot of artifacts, including a noticeable sinusoidal component at the modulation frequency (now you know why those cheap sci-fi movies had that constant hum in the background!)\n",
    "\n",
    "We will revisit the last point in more detail in Section 4."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2 - \"Turntable\" pitch shifting\n",
    "\n",
    "<img width=\"200\" style=\"float: right;\" src=\"turntable.jpg\"> While the alien voice effect can be used as a simple voice obfuscator, we will now consider the problem of changing the pitch of a voice signal to make it sound higher or lower but without the artefacts of sinusoidal modulation.\n",
    " \n",
    "Let's first introduce a utility function to perform simple fractional resampling, since we will use this function a few times in the rest of the notebook. Given a discrete-time signal $x[n]$ and a real valued time index $N \\le t < N+1$, the function returns the approximate value $x(t)$ as the _linear interpolation_ between $x[N]$ and $x[N+1]$ computed in $t-N$: "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def subsample(x, t):\n",
    "    n = int(t)\n",
    "    a = 1.0 - (t - n)\n",
    "    try:\n",
    "        return a * x[n] + (1 - a) * x[n + 1] \n",
    "    except IndexError:\n",
    "        try:\n",
    "            return a * x[n]\n",
    "        except IndexError:\n",
    "            return 0"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "With our subsample interpolator, it's now easy to perform a basic change of pitch for the speech signal; the result is equivalent to what we would obtain by spinning a record player faster or slower than the nominal RPM value of the record:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def resample(x, f):\n",
    "    # length of the output signal after resampling\n",
    "    n_out = int(np.floor(len(x) / f))\n",
    "    y = np.zeros(n_out)\n",
    "    for n in range(0, n_out):\n",
    "        y[n] = subsample(x, float(n) * f)\n",
    "    return y"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "We can for instance lower the pitch, and obtain a \"Darth Vader\" voice:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true,
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(resample(s, 0.6), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "or we can increase the pitch, and obtain a \"Chipmunk\" voice:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true,
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(resample(s, 2), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "The obvious main problem with this approach, **which also makes it impossible to implement in real time,** is that the resampling changes the speed and the duration of the voice signal. In fact, we need to change the pitch without altering the time scale of the signal and therefore we need more sophisticated techniques."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3 - Pitch shift via Granular Synthesis\n",
    "\n",
    "The idea behind [Granular Synthesis](https://en.wikipedia.org/wiki/Granular_synthesis) (GS) is that complex waveforms can be built by collating together very short sound snippets called \"grains\". By varying the content of the grains and by adjusting their rate, composers can generate complex timbres at arbitrary pitches. The psychoacoustic phenomenon underlying GS is that sound grains of short (but not too short) duration will be perceived as \"pitched\" events and they can therefore be joined together to create sustained waveforms. \n",
    "\n",
    "<img width=\"500\" style=\"float: center;\" src=\"gsplot.jpg\">"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "For instance, we can use granular synthesis to easily stretch a signal in time; all we need to do is to split the signal into small grains (around 30ms) and repeat each grain twice in a row:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def double_len(x, G):\n",
    "    N = len(x)\n",
    "    y = np.zeros(2 * N)\n",
    "    for n in range(0, len(x) - G, G):\n",
    "        y[2*n:2*n+G] = x[n:n+G]\n",
    "        y[2*n+G:2*n+2*G] = x[n:n+G]\n",
    "    return y"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "G = ms2smp(30, Fs)\n",
    "IPython.display.Audio(double_len(s, G), rate=Fs)    "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "It works, although we encounter a classic audio artefact of block-based audio processing: when we double each block, we are introducing with high probability a large amplitude jump at the junction point between a grain and its copy, since the last and first sample of each grain may be very different. This generates a clicking sound as if we were adding a pulse train at half the grain rate. Here is proof: the audio file sounds very much like the disturbance in the double-length speech signal:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "y = np.zeros(Fs * 2)\n",
    "y[0:-1:2*G] = 1\n",
    "IPython.display.Audio(y, rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "To mitigate this click noise we need to *crossfade* the grains. To do so, we employ a *tapered* window that smooths to zero the beginning and end of each grain. The following function returns a simple window shaped as an isosceles trapezoid. The parameter $0 \\le a \\le 1$ determines the *total* amount of taper. The function also returns a stride value which can be used to shift the analysis window so that the tapered parts align exactly: "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def win_taper(N, a):\n",
    "    R = int(N * a / 2)\n",
    "    r = np.arange(0, R) / float(R)\n",
    "    win = np.r_[r, np.ones(N - 2*R), r[::-1]]\n",
    "    stride = N - R - 1\n",
    "    return win, stride"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "# generate a window with 40% taper (20% left and 20% right)\n",
    "win, stride = win_taper(100, .4)\n",
    "# align two windows using the given stride and sum them \n",
    "win1 = np.r_[win, np.zeros(stride)]\n",
    "win2 = np.r_[np.zeros(stride), win]\n",
    "plt.plot(win1);\n",
    "plt.plot(win2);\n",
    "# if the windows are properly aligned, the tapered areas compensate\n",
    "plt.plot(win1 + win2);\n",
    "plt.gca().set_ylim([0, 1.1]);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "With this we can rewrite the function that doubles the audio length as such:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def double_len2(x, G):\n",
    "    N = len(x)\n",
    "    y = np.zeros(2 * N)\n",
    "    overlap = 0.4\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    ix = 0\n",
    "    for n in range(0, len(x) - G, G):\n",
    "        for k in [0, 1]:\n",
    "            y[ix:ix+G] += x[n:n+G] * win\n",
    "            ix += stride\n",
    "    return y"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "and indeed things sounds better:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(double_len2(s, ms2smp(30, Fs)), rate=Fs)  "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "OK, so here's an idea: if we have managed to *double* the signal's length without changing the pitch, we could apply the \"turntable\" resampler to the twice-long signal and obtain a signal at twice the pitch but with the same length as the original! And indeed:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(resample(double_len2(s, ms2smp(30, Fs)), 2), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "In fact, we can combine time stretching and resampling in a single opearation, by synthesizing the output via *resampled grains*. This leads to a simple pitch shifter that works in real time with just a small processing delay; also, the pitch shifter works for all frequency shift factors.\n",
    "\n",
    "The principle behind granular pitch shifting is best understood graphically. Consider initially a fractional resampling function that, for each value of the *output* index $n$, returns the (potentially non-integer) index $i$ of the input signal that we have to use to produce the output: $i[n] = R(n, f)$; $f$ here is the resampling factor.\n",
    "\n",
    "We can plot $i[n]$ for different values of $f$. When $f=1$, as in the first panel below, each output sample coincides with an input sample and $i[n] = n$, resulting in a 45-degree line. If we increase the speed, say $f=1.6$, we \"use up\" the input signal faster; this corresponds to the second panel, in which we run out of input samples in less than the length of the output. Finally, if we slow down the input, we only use a smaller number of input samples over the support of the output, as shown in the third panel."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "n = np.arange(0, 100)\n",
    "for ix, f in enumerate([1, 1.6, 0.6]):\n",
    "    plt.subplot(1, 3, ix+1)\n",
    "    plt.plot(resample(n, f))\n",
    "    plt.gca().set_xlim([0, 100])"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "In granular pitch shifting we generate output grains by performing fractional resampling on portions of the input; the start times for input and output grains are synchronized but the number of (fractional) *input* samples used to produce the corresponding output grain will be larger or smaller than the size of the output grain according to whether we're raising or lowering the pitch. But, in any case, the maximum buffer delay to produce a grain will be less than $Gf$ samples, where $G$ is the size of the grain and $f$ is the resampling factor. \n",
    "\n",
    "Again, things are best illustrated graphically. The following function computes the (fractional) index of the input signal for each output index value $n$ based on the resampling factor $f$ and a grain size $G$:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def gs_map(n, f, G):\n",
    "    # beginning of grain\n",
    "    t = np.floor(n / G) * G # * float(G)\n",
    "    # fractional index in input grain\n",
    "    t += (n - t) * f\n",
    "    return t"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "If we plot the input time index as a function of the output index we can see that we're traversing the input signal in a zig-zagging pattern; the slope of each segment is equal to $f$ as in the global resampler, but the input time index is pulled back or advanced appropriately to keep an average ratio of 1:1 between input and output:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "n = np.arange(0, 100)\n",
    "for ix, f in enumerate([1, 1.6, 0.6]):\n",
    "    plt.subplot(1, 3, ix+1)\n",
    "    plt.plot(gs_map(n, f, 12))\n",
    "    plt.gca().set_xlim([0, 100])\n",
    "    plt.gca().set_ylim([0, 100])\n",
    "    plt.xlabel('output index')    \n",
    "    plt.ylabel('input index')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "You can see that input and output indices \"resynchronize\" at the beginning of each grain (they touch the 45-degree slope). \n",
    "\n",
    "Note that in the above plots we are not using any overlap between grains. Of course in practice we are going to use overlapping grains with a tapering window, as in the following function:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def GS_pshift(x, f, G, overlap=0.5):\n",
    "    N = len(x)\n",
    "    y = np.zeros(N)\n",
    "    # size of input buffer given grain size and resampling factor\n",
    "    igs = int(G * f + 0.5)\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    for n in range(0, len(x) - max(igs, G), stride):\n",
    "        w = resample(x[n:n+igs], f)\n",
    "        y[n:n+G] += w * win\n",
    "    return y"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's try it out on some audio; here comes the chipmunk:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true,
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(GS_pshift(s, 1.5, ms2smp(40, Fs), .25), rate=Fs) "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(GS_pshift(s, 1.5, ms2smp(40, Fs), .5), rate=Fs) "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "and here is Darth Vader:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(GS_pshift(s, 0.6, ms2smp(31, Fs), .25), rate=Fs) "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(GS_pshift(s, 0.6, ms2smp(31, Fs), .5), rate=Fs) "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Although we have just described a purely digital version of grain-based pitch shifting, it is interesting to remark that, before digital audio was a reality, the only true pitch-shifting devices available to the music industry were extremely complex (and costly) mechanical devices that implemented, in analog, the same principle behind granular synthesis. <img width=\"400\" style=\"float: left; margin-right: 30px;\" src=\"pitchshift.jpg\"> \n",
    "\n",
    "Here is the block diagram of such a contraption: the original sound is recorded on the main tape spool, which is run at a speed that can vary with respect to the nominal recording speed to raise or lower the pitch. To compensate for these changes in speed the tape head is actually a rotating disk with four tape heads; at any given time, at least two heads are picking up the signal from the tape, with an automatic fade-in and fade-out as they approach and leave the tape. The disk rotates at a speed that compensates for the change in speed of the main tape, therefore keeping the timebase constant. The heads on the disk picking up the signal are in fact producing overlapping \"grains\" that are mixed together in the output signal.  "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4 - DFT-based pitch shift\n",
    "\n",
    "The next pitch shifting technique that we will explore moves us to the frequency domain. To set the stage, let's initially consider a simple pitched sound, i.e. a signal that appears, to the human ear, to have a discernible pitch; this could be a vowel sound in a speech signal or a note played by a musical instrument. Spectrally, a pitched sound possesses a *harmonic* structure, that is, as we scan the spectrum from left to right, we will encounter a first clear spectral line (called the *fundamental*) followed by other peaks (called the *partials*) at exact multiples of the fundamental. The frequency of the fundamental is the perceived pitch of the sound and the regular pattern of spectral lines at precise multiples of the fundamental is what determines the \"naturalness\" of a pitched sound. \n",
    "\n",
    "Here is for instance an example of a (synthetic) clarinet note with pitch D4 (293.6 Hz). The spectrum shows the typical pattern of woodwinds, where only the even-numbered partials have significant energy."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "Fs_y, y = wavfile.read('clarinet.wav')\n",
    "IPython.display.Audio(y, rate=Fs_y)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "plot_spec(y, Fs_y, 4000);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "<img width=\"140\" style=\"float: right; margin: 0 30px 0 30px;\" src=\"bell.jpg\">If we now want to change the frequency content of the previous sound without altering its duration, we could take a Fourier transform, move the frequencies around and then invert the transform. As long as the Hermitial symmetry of the modified spectrum is preserved, we would obtain a real-valued time-domain signal. Now, if we simply shift the spectrum up and down, we can move the position of the fundamental, but we will lose the harmonicity relation between the partials, which will no longer fall at multiples of the fundamental (this is why the \"robot voice\" sounds weird - incidentally, the only (common) musical \"instrument\" that produces non-harmonic sounds is the bell).  \n",
    "\n",
    "Let's quickly demonstrate what happens when the proportionality between partials is broken:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def DFT_translate(x, k):\n",
    "    N = len(x)        \n",
    "    X = np.fft.fft(x - np.mean(x))\n",
    "    Y = np.r_[np.zeros(k), X[0:int(N/2-k)]]\n",
    "    y = np.fft.ifft(np.r_[Y, np.conj(Y[-1:0:-1])])\n",
    "    return np.real(y[0:N])\n",
    "\n",
    "IPython.display.Audio(DFT_translate(y, 210), rate=Fs_y)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "The proper way to change the pitch is, instead, to *stretch* (or compress) the frequency axis via a scaling factor, which preserves the proportionality relationship between the partials. \n",
    "\n",
    "Here is a function that does just that:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def DFT_rescale(x, f):\n",
    "    X = np.fft.fft(x)\n",
    "    # separate even and odd lengths\n",
    "    parity = (len(X) % 2 == 0)\n",
    "    N = int(len(X) / 2) + 1 if parity else (len(X) + 1) / 2\n",
    "    Y = np.zeros(N, dtype=np.complex)\n",
    "    # work only in the first half of the DFT vector since input is real\n",
    "    for n in range(0, N):\n",
    "        # accumulate original frequency bins into rescaled bins\n",
    "        ix = int(n * f)\n",
    "        if ix < N:\n",
    "            Y[ix] += X[n]\n",
    "    # now rebuild a Hermitian-symmetric DFT\n",
    "    Y = np.r_[Y, np.conj(Y[-2:0:-1])] if parity else np.r_[Y, np.conj(Y[-1:0:-1])]\n",
    "    return np.real(np.fft.ifft(Y))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "We're now ready to try our pitch shifter:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(DFT_rescale(y, 1.4), rate=Fs_y)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "OK, it works, at least for sustained sounds.\n",
    "\n",
    "However, if we want to apply the same approach to speech, we run into the problem that speech is a nonstationary signal where pitched sounds (the vowels) alternate with non-pitched sounds (the consonants). The ideal solution would be to segment the speech signal into portions that isolate individual sounds and then apply spectral shifting to the vowels. In practice, we can just try to segment the incoming signal into small pieces and apply spectral shifting to each piece independently; applying pitch shifting to the unvoiced portions doesn't affect their nature much.\n",
    "\n",
    "The length of the segments over which we compute (and shift) the DFT should be short enough to encompass a single pitched event but long enough to allow for a good resolution in the DFT. Usually, a window between 40 and 100 milliseconds is OK. Again, we will use a tapering window to minimize border effects in the result. "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def DFT_pshift(x, f, G, overlap=0):\n",
    "    N = len(x)\n",
    "    y = np.zeros(N)\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    for n in range(0, len(x) - G, stride):\n",
    "        w = DFT_rescale(x[n:n+G] * win, f)\n",
    "        y[n:n+G] += w * win\n",
    "    return y"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's try the \"Darth Vader\" voice again: "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(DFT_pshift(s, 0.6, ms2smp(40, Fs), 0.2), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "and now let's try to raise the pitch:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(DFT_pshift(s, 1.5, ms2smp(40, Fs), 0.4), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "This pitch-shifting technique can be implemented in real time, with a processing delay equal to the size of the analysis window. Also, more advanced versions (such as commercial \"auto-tune\" applications) take great care to minimize the artifacts that you can still hear in this very simple version using way more sophisticated frame analysis. We won't pursue this approach here because, in all of the methods we have seen so far, we have neglected one fundamental aspect of voice manipulation, namely, preserving the position of the formants. This can only be achieved by doing a more sophisticated analysis of each speech segment. "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3 - LPC and the Vocoder\n",
    "\n",
    "Although the preceding methods yield increasingly acceptable ways to shift the pitch of a voice, they all produce slighty unnatural-sounding speech. The reason behind this lack of naturality is to be found in the particular inner structure of a speech signal. Although the spectral structure of the voiced part is indeed that of an harmonic sound, the distribution of energy across the partial happens to be *independent* of the fundamental frequency. When we perform pitch shifting and we scale the whole spectrum up or down we also move the overall envelope, which results in an unnatural-sounding voice. \n",
    "\n",
    "Consider the spectrum below, corresponding to a short voiced speech segment (40ms); you can see the harmonic structure of the signal and, superimposed, you can see the overall energy envelope of the spectrum. If we want to change the pitch of this segment and still have it sound natural, we should make sure to keep the overall orange envelope in place. "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "Fs_y, y = wavfile.read('voiced.wav')\n",
    "y = y / 32767.0 # cast to floats in [-1, 1]\n",
    "plot_spec(y, Fs_y)\n",
    "Y = np.fft.fft([1.0, -2.1793, 2.4140, -1.6790, 0.3626, 0.5618, -0.7047, \n",
    "                0.1956, 0.1872, -0.2878, 0.2354, -0.0577, -0.0815, 0.0946, \n",
    "                0.1242, -0.1360, 0.0677, -0.0622, -0.0306, 0.0430, -0.0169], len(y))\n",
    "plot_spec(np.abs(np.divide(1.0, Y)), Fs_y, do_fft=False);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "The common model for the speech production mechanism is that of a source followed by a resonator. The source can be a pitched sound produced by the vocal cords, or a noise-like excitation produced by a flow of air; the resonator is the transfer function of the speech apparatus (mouth and head), which is independent of the source. Think of when you whisper: you are replacing the pitched excitation with air \"noise\" but you preserve the resonances of normal speech. A schematic view of the model is shown on the right.\n",
    "\n",
    "<img width=\"400\" style=\"float: right; margin-right: 30px;\" src=\"lpc.jpg\"> \n",
    "\n",
    "Mathematically we can express the production mechanism (in the $z$-domain) as $X(z) = A(z)E(z)$ where $E(z)$ is the excitation and $A(z)$ the resonance transfer function. Of course, in a spoken sentence, both $A(z)$ and $E(z)$ vary over time, but let's assume we have segmented the speech signal and we're operating over a stationary portion of the utterance. Our job is to estimate $A(z)$, i.e., the green overall envelope in the spectrum above; unfortunately, however, both $A(z)$ and $E(z)$ are unknown, so we need to massage the problem a bit. \n",
    "\n",
    "Experimentally, first of all, it turns out that the resonance transfer function can be described very well by an all-pole model (with poles inducing peaks in the spectral envelope):\n",
    "\n",
    "$$\n",
    "\tA(z) = \\frac{1}{1 - \\sum_{k=1}^{p}a_kz^{-k}};\n",
    "$$ \n",
    "\n",
    "with this representation we can rewrite the estimation problem in the time domain as\n",
    "\n",
    "$$\n",
    "\tx[n] = \\sum_{k=1}^{p}a_k x[n-k] + e[n]\n",
    "$$\n",
    "\n",
    "which becomes\n",
    "\n",
    "$$\n",
    "\te[n] = x[n] - \\sum_{k=1}^{p}a_k x[n-k]\n",
    "$$\n",
    "\n",
    "The above equation is identical to the expression for the prediction error in a standard **AR linear prediction** problem. In those cases, the canonical approach to find the optimal coefficients for the all-pole filter is to *minimize the second moment (i.e. the energy) of the error*, that is, minimize $E[e^2[n]]$. In order to understand why this is a good criterion consider that, when the energy of the error is minimized, [the error is orthogonal to the input](https://en.wikipedia.org/wiki/Orthogonality_principle). In our speech analysis setup, what we call \"error\" is in fact the excitation source; the optimal coefficients will therefore give us a filter that, when used on the input, produces a signal that is orthogonal (i.e. maximally different) to the excitation. In other words, the optimal filter captures all the information that is *not* in the excitation.\n",
    "\n",
    "The coefficients of the filter $A(z)$ are called the **linear prediction coding (LPC)** coefficients. There are a lot of good references on the web both on the theory of LPC (for example [here](https://ccrma.stanford.edu/~hskim08/lpc/)) and on good numerical LPC algorithms (see for instance [here](https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-341-discrete-time-signal-processing-fall-2005/lecture-notes/lec13.pdf)); without going through the derivation, suffice it to say that the coefficients are determined by solving the following system of equations\n",
    "\n",
    "$$\n",
    "    \\begin{bmatrix}\n",
    "        r_0 & r_1 & r_2 & \\ldots & r_{p-1} \\\\\n",
    "        r_1 & r_0 & r_1 & \\ldots & r_{p-2} \\\\        \n",
    "        & & & \\vdots \\\\\n",
    "        r_{p-1} & r_{p-2} & r_{p-3} & \\ldots & r_{0} \\\\\n",
    "    \\end{bmatrix}\n",
    "    \\begin{bmatrix}\n",
    "        a_1 \\\\\n",
    "        a_2 \\\\        \n",
    "        \\vdots \\\\\n",
    "        a_{p}\n",
    "    \\end{bmatrix} = \n",
    "    \\begin{bmatrix}\n",
    "        r_1 \\\\\n",
    "        r_2 \\\\        \n",
    "        \\vdots \\\\\n",
    "        r_{p}\n",
    "    \\end{bmatrix}\n",
    "$$\n",
    "\n",
    "where $r$ is the biased autocorrelation of the $N$-point input data:\n",
    "\n",
    "$$\n",
    "    r_m = (1/N)\\sum_{k = 0}^{N-m-1}x[k]x[k+m]\n",
    "$$\n",
    "\n",
    "Because of the Toeplitz structure of the autocorrelation matrix, the system of equations can be solved very efficiently using the Levinson-Durbin algorithm. Here is a direct implementation of the method:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def bac(x, p):\n",
    "    # compute the biased autocorrelation for x up to lag p\n",
    "    L = len(x)\n",
    "    r = np.zeros(p+1)\n",
    "    for m in range(0, p+1):\n",
    "        for n in range(0, L-m):\n",
    "            r[m] += x[n] * x[n+m]\n",
    "        r[m] /= float(L)\n",
    "    return r"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def ld(r, p):\n",
    "    # solve the toeplitz system using the Levinson-Durbin algorithm\n",
    "    g = r[1] / r[0]\n",
    "    a = np.array([g])\n",
    "    v = (1. - g * g) * r[0];\n",
    "    for i in range(1, p):\n",
    "        g = (r[i+1] - np.dot(a, r[1:i+1])) / v\n",
    "        a = np.r_[ g,  a - g * a[i-1::-1] ]\n",
    "        v *= 1. - g*g\n",
    "    # return the coefficients of the A(z) filter\n",
    "    return np.r_[1, -a[::-1]]     "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def lpc(x, p):\n",
    "    # compute p LPC coefficients for a speech segment\n",
    "    return ld(bac(x, p), p)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Now that we have the LPC function in place, we can re-plot the initial spectrum with the overall envelope using an explicit computation:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "plot_spec(y, Fs_y)\n",
    "A = np.fft.fft(lpc(y, 20), len(y))\n",
    "plot_spec(np.abs(np.divide(1.0, A)), Fs_y, do_fft=False);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Back to pitch shifting problem: in order to properly pitch-shift a speech signal we willnow perform the following operations on each segment:\n",
    "\n",
    " 1. compute the LPC coefficients\n",
    " * inverse-filter the segment and recover the excitation signal\n",
    " * pitch-shift the excitation\n",
    " * forward-filter the shifted excitation to re-apply the formants' envelope.\n",
    "\n",
    "In theory, we should determine whether the excitation signal for a segment is harmonic or not and apply pitch shfting only in the former case. For simplicity, we will just process all segments as if they were voiced, at the price of a little loss of quality.\n",
    " \n",
    "To pitch-shift the excitation you can use either the DFT scaling method or the Granular Synthesis method. Below are both functions:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def LPC_DFT_pshift(x, f, G, P, th, overlap):\n",
    "    N = len(x)\n",
    "    y = np.zeros(N)\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    for n in range(0, len(x) - G, stride):\n",
    "        w = x[n:n+G]\n",
    "        a = lpc(w, P)\n",
    "        e = sp.lfilter(a, [1], w)\n",
    "        e = DFT_rescale(e, f)\n",
    "        w = sp.lfilter([1], a, e)\n",
    "        y[n:n+G] += w * win\n",
    "    return y    "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(LPC_DFT_pshift(s, 0.6, ms2smp(40, Fs), 20, 0.00, 0.2), rate=Fs)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(LPC_DFT_pshift(s, 1.5, ms2smp(40, Fs), 20, 0.002, 0.2), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's try the same, but with granular pitch shifting; it's actually simpler to implement (no FFT is required) and it sounds better!"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def LPC_GS_pshift(x, f, G, P, overlap=0.2):\n",
    "    N = len(x)\n",
    "    y = np.zeros(N)\n",
    "    igs = int(G * f + 0.5)\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    for n in range(0, len(x) - max(igs, G), stride):\n",
    "        w = x[n:n+igs]\n",
    "        a = lpc(w, P)\n",
    "        e = sp.lfilter(a, [1], w)\n",
    "        e = resample(e, f)\n",
    "        w = sp.lfilter([1], a, e)\n",
    "        y[n:n+G] += w * win\n",
    "    return y"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(LPC_GS_pshift(s, 0.6, ms2smp(40, Fs), 20, 0.2), rate=Fs)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(LPC_GS_pshift(s, 1.5, ms2smp(40, Fs), 20, 0.3), rate=Fs)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "The LPC analysis can also be used to produce extremely artificial-sounding voices, as demonstrated here, where we replace the excitation siganl by a square wave of constant frequency. This is the type of sound created by the early [Vocoder](https://en.wikipedia.org/wiki/Vocoder) machines, for instance."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def LPC_daft(x, f, Fs, G, P, th, overlap):\n",
    "    d = (float(f) / Fs) * 2 * np.pi  \n",
    "    e = np.sign(np.cos(d * np.arange(0, G)))\n",
    "    N = len(x)\n",
    "    y = np.zeros(N)\n",
    "    win, stride = win_taper(G, overlap)\n",
    "    for n in range(0, len(x) - G, stride):\n",
    "        a = ld(bac(x[n:n+G], P), P)\n",
    "        w = sp.lfilter([1], a, e)\n",
    "        y[n:n+G] += w * win\n",
    "    return y    "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "IPython.display.Audio(LPC_daft(s, 140, Fs, ms2smp(40, Fs), 20, 0.002, 0.2), rate=Fs)"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.7"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}