{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Implementing FIR filters\n",
    "\n",
    "In real-time filtering applications, filters are implemented by using some variation or other of their constant-coefficient difference equation (CCDE), so that one new output sample is generated for each new input sample. If all input data is available in advance, as in non-real-time (aka \"offline\") applications, then the CCDE-based algorithm is iteratively applied to all samples in the buffer.\n",
    "\n",
    "In the case of FIR filters, the CCDE coefficients correspond to the impulse response and implementing the CCDE is equivalent to performing a convolution sum. In this notebook we will look at different ways to implement FIR filters."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "%matplotlib inline\n",
    "import matplotlib\n",
    "import matplotlib.pyplot as plt\n",
    "import numpy as np"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Online implementation\n",
    "\n",
    "The classic way to implement a filter is the one-in one-out approach. We will need to implement a persistent delay line. In Python we can either define a class or use function attributes; classes are tidier and reusable:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 3,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "class FIR_loop():\n",
    "    def __init__(self, h):\n",
    "        self.h = h\n",
    "        self.ix = 0\n",
    "        self.M = len(h)\n",
    "        self.buf = np.zeros(self.M)\n",
    "\n",
    "    def filter(self, x):\n",
    "        y = 0\n",
    "        self.buf[self.ix] = x\n",
    "        for n in range(0, self.M):\n",
    "            y += self.h[n] * self.buf[(self.ix+self.M-n) % self.M]\n",
    "        self.ix = (self.ix + 1) % self.M\n",
    "        return y"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "0.0, 0.2, 0.6, 1.2, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, "
     ]
    }
   ],
   "source": [
    "# simple moving average:\n",
    "h = np.ones(5)/5\n",
    "\n",
    "f = FIR_loop(h)\n",
    "for n in range(0, 10):\n",
    "    print(f.filter(n), end=\", \")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "While there's nothing wrong with the above implementation, when the data to be filtered is known in advance, it makes no sense to explicitly iterate over its element and it's better to use higher-level commands to perform the convolution. In Numpy, the command is `convolve`; before we use it, though, we need to take border effects into consideration."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Offline implementations: border effects\n",
    "\n",
    "When filtering a finite-length data vector with a finite-length impulse response, we need to decide what to do with the \"invalid\" shifts appearing in the terms of the convolution sum. Remember that, in the infinite-length case, the output is defined as\n",
    "\n",
    "$$\n",
    "    y[n] = \\sum_{k=-\\infty}^{\\infty} h[k]x[n-k]\n",
    "$$\n",
    "\n",
    "Let's say that the impulse response is $M$ points long, so that $h[n]$ is nonzero only between $0$ and $M-1$; this means that the sum is reduced to \n",
    "\n",
    "$$\n",
    "    y[n] = \\sum_{k=0}^{M-1} h[k]x[n-k]\n",
    "$$\n",
    "\n",
    "Now assume that $x[n]$ is a length-$N$ signal, so it is defined only for $0 \\leq n \\le N$ (we can safely consider $N > M$, otherwise exchange the roles of $x$ and $h$). In this case, the above sum is properly defined only for $M - 1 \\le n \\le N-1$; for any other value of $n$, the sum will contain an element $x[n-k]$ outside of the valid range of indices for the input. \n",
    "\n",
    "So, if we start with an $N$-point input, we can only formally compute $N-M+1$ output samples. While this may not be a problem in some applications, it certainly is troublesome if repeated filtering operations end up \"chipping away\" at the signal little by little.\n",
    "\n",
    "The solution is to \"embed\" the finite-length input data signal into an infinite-length sequence and, as always, the result will depend on the method we choose: finite support or periodization. (Note that the impulse response is already an infinite sequence since it's the response of the filter to the infinite sequence $\\delta[n]$). \n",
    "\n",
    "However, the embedding will create \"artificial\" data points that are dependent on the chosen embedding: these data points are said to suffer from **border effects**."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's build a simple signal and a simple FIR filter:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 5,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  21\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f094b227be0>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "# let's use a simple moving average:\n",
    "M = 5\n",
    "h = np.ones(M)/float(M)\n",
    "\n",
    "# let's build a signal with a ramp and a plateau\n",
    "x = np.concatenate((np.arange(1, 9), np.ones(5) * 8, np.arange(8,0,-1)))\n",
    "plt.stem(x);\n",
    "print('signal length: ', len(x))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 1) No border effects\n",
    "\n",
    "We may choose to accept the loss of data points and use only the $N-M+1$ output samples that correspond to a full overlap between the input data and the impulse response. This can be achieved by selecting `mode='valid'` in `correlate`:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  17\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f094b22ab00>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = np.convolve(x, h, mode='valid')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 2) finite-support extension\n",
    "\n",
    "By embedding the input into a finite-support signal, the convolution sum is now well defined for all values of $n$, which now creates a new problem: the output will be nonzero for all values of $n$ for which $x[n-k]$ is nonzero, that is for $0 \\le n \\le N+M-1$: we end up with a *longer* support for the output sequence. This is the default in `correlate`  and corresponds to `mode='full'`:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 7,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  25\n"
     ]
    },
    {
     "data": {
      "image/png": "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\nb/Nyto9ExGiWdbN84vYGyy5Ie9v7Je2XpGuvvTbL332BV+94hS776cD2K7Zddmn2dcu+DXVRV57b\nUFd/6nr1jld0vF03snzivlHSxyNirP39hCRFxD2bbdPtJ24AqKtOPnFnuarkXyX9ku3X2b5U0h2S\nvnYxBQIAurftUElEvGj7Q5JmJA1Iui8iHs+9MgDAhjLd8h4RD0l6KOdaAAAZlOLOSQBAdgQ3ACSG\n4AaAxBDcAJAYghsAErPtDThd/VK7KelHXW5+paRne1hOSurcdqne7aft9bXW/l+IiEaWDXIJ7oth\nezbr3UNVU+e2S/VuP22vZ9ul7trPUAkAJIbgBoDElDG4DxZdQIHq3Hap3u2n7fXVcftLN8YNANha\nGT9xAwC2UJrgzntC4rKz/aTtedtHbVf6Yea277N9yvZjL1v2atvfsv0f7a9XFFljnjZp/8dtL7b7\n/6jt3yyyxrzYvsb2P9o+bvtx2x9pL698/2/R9o77vhRDJe0Jif9d0tskndTqM8D3RUTP5rUsO9tP\nShqNiMpfz2r7ZkkvSPpCRLyxvezPJP0kIu5t/8N9RUT8cZF15mWT9n9c0gsR8Ykia8ub7askXRUR\nj9q+XNIRSXslvU8V7/8t2v576rDvy/KJ+6UJiSPitKS1CYlRQRHxXUk/Wbf4nZLub7++X6s7dCVt\n0v5aiIinI+LR9uvnJR2XNKwa9P8Wbe9YWYJ7WNJTL/v+pLpsUMJC0jdtH2nP31k3r4mIp6XVHVzS\nzxdcTxE+ZPtYeyilckMF69neLWmPpIdVs/5f13apw74vS3BnmpC44m6KiDdJuk3SB9v/nUZ9fEbS\nL0q6XtLTkv682HLyZfuVkr4q6c6IeK7oevppg7Z33PdlCe6Tkq552fdXS1oqqJZCRMRS++spSQ9q\ndfioTp5pjwGujQWeKrievoqIZyJiJSLOSvorVbj/bQ9qNbi+GBFT7cW16P+N2t5N35cluGs9IbHt\nHe2TFbK9Q9LbJT229VaV8zVJ722/fq+kvyuwlr5bC62231FF+9+2JX1O0vGI+OTLflT5/t+s7d30\nfSmuKpGk9iUwn9K5CYn/tOCS+sb267X6KVtanQf0S1Vuv+1Dkt6s1aeiPSPpY5KmJX1F0rWSTkj6\n3Yio5Am8Tdr/Zq3+VzkkPSnpwNqYb5XY/nVJ/yRpXtLZ9uKPanWst9L9v0Xb96nDvi9NcAMAsinL\nUAkAICOCGwASQ3ADQGIIbgBIDMENAIkhuAEgMQQ3ACSG4AaAxPw/UsuxYbP4mzIAAAAASUVORK5C\nYII=\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0948ff9630>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = np.convolve(x, h, mode='full')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "If we want to preserve the same length for input and output, we need to truncate the result. You can keep the *first* $N$ samples and discard the tail; this corresponds to the online implementation of the FIR filter. Alternatively, you can discard half the extra samples from the beginning and half from the end of the output and distribute the border effect evenly; this is achieved in `correlate`  by setting `mode='same'`: "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 8,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  21\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n3L3w9cx8NjN/0nx8K7AmIk6tu67MPNj8+TRwC40/Weer0qZ1uRi4JzOfWvhCt9qr6am57qLmz6cX\nmacr7dY8QPV24Ley2RG6UIV1vqIy86nMnM3MF4C/bfF+3Wqv44ArgJ2t5qm7vVpkQ1e2sW4Fd5UB\niL8GzB19fQdwR6sNfKU0+9A+BzyQmZ9sMc+r5/raI+JcGm34XzXXdWJEnDT3mMbBrfsWzPY14Lej\n4Y3AM3N/wnVAy29C3WiveeZvQ+8G/mmReUaBt0XEyc2ugbc1p9UmIi4C/gi4NDN/2mKeKut8peua\nf0zkN1q8X7cGD38r8GBmPrHYi3W31xLZ0J1trI4jsBWP0l5C48jsI8CHm9P+lMbGDPBSGn96Pwzc\nDZzZgZp+mcafMPuBfc1/lwDvB97fnOda4H4aR9PvBN7UgbrObL7fvc33nmuv+XUF8Jlmex4Ahju0\nHk+gEcSvmDet4+1F4z+OJ4FDNL7hvJfGMZF/AR5q/jylOe8w8Nl5y76nuZ09DFzdgboeptHnObeN\nzZ09tQ64dal1XnNdf9fcdvbTCKTTFtbVfH7EvltnXc3pX5jbpubN28n2apUNXdnGvHJSkgrjlZOS\nVBiDW5IKY3BLUmEMbkkqjMEtSYUxuCWpMAa3JBXG4Jakwvw/31v3hc4da7MAAAAASUVORK5CYII=\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0948f17e48>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = np.convolve(x, h, mode='same')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 3) Periodic extension \n",
    "\n",
    "As we know, the other way of embedding a finite-length signal is to build a periodic extension. The convolution in this case will return an $N$-periodic output:\n",
    "\n",
    "$$\n",
    "    \\tilde{y}[n] = \\sum_{k=0}^{M-1} h[k]\\tilde{x}[n-k]\n",
    "$$\n",
    "\n",
    "We can easily implement a circular convolution using `convolve` like so: since the overlap between time-reversed impulse response and input is already good for the last $N-M$ points in the output, we just need to consider two periods of the input to compute the first $M$: "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 9,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def cconv(x, h):\n",
    "    # as before, we assume len(h) < len(x)\n",
    "    L = len(x)\n",
    "    xp = np.concatenate((x,x))\n",
    "    # full convolution\n",
    "    y = np.convolve(xp, h)\n",
    "    return y[L:2*L]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 15,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  21\n"
     ]
    },
    {
     "data": {
      "text/plain": [
       "<matplotlib.text.Text at 0x7f0948c5b978>"
      ]
     },
     "execution_count": 15,
     "metadata": {},
     "output_type": "execute_result"
    },
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAAW4AAAEICAYAAAB/Dx7IAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz\nAAALEgAACxIB0t1+/AAAGDVJREFUeJzt3X+cHPV93/HX2ycJnzBwEM42OoRlnFQxgcbiccUo2JQC\n8YHigqqmfcDD8Q+IK3jUduw+HNkoaW0/Uuchp0pit45jV+aHnQbLcrBQXQdbOCWOH26CyAnJCAxX\nAxaIk0BH7EPYvhYhPv1j5uhq2b2d1e3s7nf3/Xw89qHZmfnufnZm9q25mZ35KiIwM7N0vKzTBZiZ\nWXMc3GZmiXFwm5klxsFtZpYYB7eZWWIc3GZmiXFwW1tIekDSRcfYNiT9fD78OUn/oaXFdQFJb5Y0\n0ek6LA3y77it20kK4Bci4uEOvPe7gHdHxJva/d5m9XiP20olaUGnazDrNQ5uq0nSXknrJX1f0o8l\n3SLp5RXT3yppt6RpSX8r6R9Xtf2wpPuAn0pakI+7NJ9+nKRPSdqfPz4l6biK9uskHcinXVtV1xck\nfbzi+ZV5HYckPSLpsjqfZ4mkr0qakvRDSb9VMe0OSX9U8XyLpJslvR74HLBS0k8kTVfU/4eSHpf0\nVH74ZjCfdpGkJyR9UNLB/HNcU/Haq/Jl+qykSUm/XdmuYr7XS/p2vnwfkHRF1TL4jKS/zF9nh6TX\nFVqx1hsiwg8/XvIA9gL3A0uBU4D/BXw8n3YucBB4IzAAvDOf/7iKtrvztoMV4y7Nh38PuBt4JTAM\n/C3wH/NplwFPAWcDxwNfAgL4+Xz6FyrqOA94BvhVsp2QEeAXa3yWlwE7gY8Ai4AzgUeBsXz6q/PP\nczHwtnzaCfm0dwHfrXq9TwFfy5fLCcD/ADbk0y4Cns8/40JgFfAz4OR8+gHgzfnwycC5Fe2eyIcX\nAg8Dv5PXezHwLLC8Yhn8KP/8C4BbgS93epvxo43fz04X4Ed3PvKgvb7i+SrgkXz4s7NBWzF9Avin\nFW2vrfF6s8H9CLCqYtoYsDcfvhn4RMW0fzRHcP9X4JMFPssbgcerxq0Hbql4vgbYBzwNvKli/FHB\nDQj4KfC6inErgR/mwxcBM8CCiukHgfPz4ceB64ATq+qpDO43A08CL6uYvhn4WMUyuLFq3TzU6W3G\nj/Y9fKjE5rKvYvgxYEk+/Brgg/mf8dP5IYSlFdOr21Zbkr9erddeUuN961lK9p9AI68BllTV+zvA\nqyrm+TrZXw8TEfHdOV5rGFgM7Kx4rW/m42f9Q0Q8X/H8Z8Ar8uF/SRa0j0n6G0kra7zHEmBfRLxQ\nMe4xsr8oZj1Z5/WtDzi4bS5LK4bPAPbnw/uA34+IoYrH4ojYXDH/XD9X2k8WprVe+0CN961nH1Dk\n2O4+sj3iynpPiIhVFfP8PvAgcJqkqyvGV3+Op8n2qH+p4rVOiohCwRkRfx8RV5IdJtoGfKXGbPuB\npZIqv59nAJNF3sN6n4Pb5vIeSadLOoVsD3VLPv7zwPWS3qjM8ZJ+TdIJBV93M/DvJQ1LOpXs2POf\n59O+ArxL0lmSFgMfneN1bgKukXSJpJdJGpH0izXmuwc4lJ8wHZQ0IOlsSf8EQNKFwDXAO/LHpyXN\n7t0+BZwuaRFAvhf8eeCTkl6Ztx+RNNboQ0taJOltkk6KiMPAIeBIjVl3kB2O+ZCkhcp+//7PgS83\neg/rDw5um8uXgDvJTtY9CnwcICLGgX8D/AnwY7ITae9q4nU/DowD9wF7gHsrXvsbZCf/7spf9656\nLxIR95AF7ifJTlL+DUfvyc/Od4Qs+N4A/JBsr/lG4CRJJwJ/Brw3IibzwyQ3AbdIUv7+DwBPSno6\nf8kP57XdLekQ8FfA8oKf/e3A3rzd9cBv1Kj3OeAK4PK81j8F3hERDxV8D+txvgDHapK0l+zCk7/q\ndC1mdjTvcZuZJcbBbWaWGB8qMTNLjPe4zcwSU8oNgE499dRYtmxZGS9tZtaTdu7c+XREDDees6Tg\nXrZsGePj42W8tJlZT5I011XCR/GhEjOzxDi4zcwS4+A2M0uMg9vMLDEObjOzxBT6VYmkfwe8m+wW\nl3uAayLi/5RZmFm32LZrko3bJ9g/PcOSoUHWjS1n9YqRxg3n2bYV7a03Ndzjzm9v+VvAaEScTXaz\n+avKLsysG2zbNcn6rXuYnJ4hgMnpGdZv3cO2XY1vjT2ftq1ob72r6KGSBcCgsh67F/P/b3pv1tM2\nbp9g5vDRt8yeOXyEjdsnSm3bivbWuxoGd0RMAn9I1lfeAeCZiLizej5JayWNSxqfmppqfaVmHbB/\neqap8a1q24r21ruKHCo5GbgSeC1ZX3jHS6p18/dNETEaEaPDw4Wu2jTrekuGBpsa36q2rWhvvavI\noZJLyfrrm8q7W9oK/Eq5ZZm11rZdk1zwibt47Q1/yQWfuKvwceJ1Y8sZXDhw1LjBhQOsG2vc4c18\n2rai/bF+Zut+RX5V8jhwft7/3wxwCVm3U2ZJmD3JN3u8ePYkH9DwFxqz0z902308d+QFRpr4Zcd8\n2s63/Xw+s3W/hsEdETsk3UbWL+DzwC5gU9mFmbXKXCf5igbw5nseB2DLdSubeu/5tJ1P+/l+Zutu\nhX7HHREfZe7ets26Vj+e5OvHz9xPfOWk9bx+PMnXj5+5nzi4refN9yRfivrxM/eTUjpSMOsm8z1J\nmKJ+/Mz9xMFtfWG+JwlT1I+fuV/4UImZWWIc3GZmifGhEkuGb3HaPl7W3c3BbUnwlYDt42Xd/Xyo\nxJLgW5y2j5d193NwWxJ8JWD7eFl3Pwe3JcFXAraPl3X3c3BbEnwlYPt4WXc/n5y0JPhKwPbxsu5+\nDm5Lhq8EbB8v6+7mQyVmZolxcJuZJaZIZ8HLJe2ueByS9IF2FGdmZi9VpOuyCeANAJIGgEng9pLr\nMjOzOpo9VHIJ8EhEPFZGMWZm1lizwX0VsLnWBElrJY1LGp+ampp/ZWZmVlPh4Ja0CLgC+Ita0yNi\nU0SMRsTo8PBwq+ozM7MqzfyO+3Lg3oh4qqxirPf5dqG9z+u4fM0E99XUOUxiVoRvF9r7vI7bo9Ch\nEkmLgV8FtpZbjvUy3y6093kdt0ehPe6I+BnwcyXXYj3OtwvtfV7H7eErJ61tfLvQ3ud13B4Obmsb\n3y6093kdt4fvDmht49uF9j6v4/ZwcFtb+Xahvc/ruHw+VGJmlhgHt5lZYhzcZmaJcXCbmSXGwW1m\nlhgHt5lZYhzcZmaJcXCbmSXGwW1mlhgHt5lZYhzcZmaJcXCbmSWm0E2mJA0BNwJnAwFcGxF/V2Zh\n1p3cn6CVzdtYY0XvDvifgW9GxK/nvb0vLrEm61LuT9DK5m2smIaHSiSdCFwI3AQQEc9FxHTZhVn3\ncX+CVjZvY8UUOcZ9JjAF3CJpl6QbJR1fPZOktZLGJY1PTU21vFDrPPcnaGXzNlZMkeBeAJwLfDYi\nVgA/BW6onikiNkXEaESMDg8Pt7hM6wbuT9DK5m2smCLB/QTwRETsyJ/fRhbk1mfcn6CVzdtYMQ2D\nOyKeBPZJml1ylwDfL7Uq60qrV4ywYc05LBrINpuRoUE2rDnHJ42sZbyNFVP0VyXvA27Nf1HyKHBN\neSVZN3N/glY2b2ONFQruiNgNjJZci5mZFeArJ83MEuPgNjNLjIPbzCwxDm4zs8Q4uM3MEuPgNjNL\njIPbzCwxDm4zs8Q4uM3MEuPgNjNLjIPbzCwxDm4zs8Q4uM3MEuPgNjNLjIPbzCwxhe7HLWkv8Cxw\nBHg+Inxv7oRt2zXJxu0T7J+eYcnQIOvGlruHEesJ/bJtF+0BB+CfRcTTpVVibbFt1yTrt+5h5vAR\nACanZ1i/dQ9AT27g1j/6adv2oZI+s3H7xIsb9qyZw0fYuH2iQxWZtUY/bdtFgzuAOyXtlLS21gyS\n1koalzQ+NTXVugqtpfZPzzQ13iwV/bRtFw3uCyLiXOBy4D2SLqyeISI2RcRoRIwODw+3tEhrnSVD\ng02NN0tFP23bhYI7Ivbn/x4EbgfOK7MoK8+6seUMLhw4atzgwgHWjS3vUEVmrdFP23bD4JZ0vKQT\nZoeBtwD3l12YlWP1ihE2rDmHRQPZqh8ZGmTDmnN67uSN9Z9+2raL/KrkVcDtkmbn/1JEfLPUqqxU\nq1eMsPmexwHYct3KDldj1jr9sm03DO6IeBT45TbUYmZmBfjngGZmiXFwm5klxsFtZpYYB7eZWWIc\n3GZmiXFwm5klxsFtZpYYB7eZWWIc3GZmiXFwm5klxsFtZpYYB7eZWWIc3GZmiXFwm5klxsFtZpYY\nB7eZWWKK9IADgKQBYByYjIi3lleSFbFt1yQbt0+wf3qGJUODrBtb3pNdNJm1S0rfqcLBDbwfeBA4\nsaRarKBtuyZZv3UPM4ePADA5PcP6rXsAunZDM+tmqX2nCh0qkXQ68GvAjeWWY0Vs3D7x4gY2a+bw\nETZun+hQRWZpS+07VfQY96eADwEv1JtB0lpJ45LGp6amWlKc1bZ/eqap8WY2t9S+Uw2DW9JbgYMR\nsXOu+SJiU0SMRsTo8PBwywq0l1oyNNjUeDObW2rfqSJ73BcAV0jaC3wZuFjSn5dalc1p3dhyBhcO\nHDVucOEA68aWd6gis7Sl9p1qGNwRsT4iTo+IZcBVwF0R8RulV2Z1rV4xwoY157BoIFt9I0ODbFhz\nTleeRDFLQWrfqWZ+VWJdZPWKETbf8zgAW65b2eFqzNKX0neqqeCOiG8D3y6lEjMzK8RXTpqZJcbB\nbWaWGAe3mVliHNxmZolxcJuZJcbBbWaWGAe3mVliHNxmZolxcJuZJcbBbWaWGAe3mVliHNxmZolx\ncJuZJcbBbWaWGAe3mVliHNxmZolp2JGCpJcD3wGOy+e/LSI+WnZh/WDbrkk2bp9g//QMS4YGWTe2\nvGu7SjKz+tr9XS7SA87/BS6OiJ9IWgh8V9I3IuLu0qrqA9t2TbJ+6x5mDh8BYHJ6hvVb9wA4vM0S\n0onvcpHOgiMifpI/XZg/opRq+sjG7RMvruhZM4ePsHH7RIcqMrNj0YnvcqFj3JIGJO0GDgLfiogd\nNeZZK2lc0vjU1FSr6+w5+6dnmhpvZt2pE9/lQsEdEUci4g3A6cB5ks6uMc+miBiNiNHh4eFW19lz\nlgwNNjXezLpTJ77LTf2qJCKmyXp5v6yUavrIurHlDC4cOGrc4MIB1o0t71BFZnYsOvFdbhjckoYl\nDeXDg8ClwEOlVdQnVq8YYcOac1g0kK2CkaFBNqw5xycmzRLTie9ykV+VnAZ8UdIAWdB/JSK+XlpF\nfWT1ihE23/M4AFuuW9nhaszsWLX7u9wwuCPiPmBF6ZWYmVkhvnLSzCwxDm4zs8Q4uM3MEuPgNjNL\njIPbzCwxDm4zs8Q4uM3MEuPgNjNLjIPbzCwxDm4zs8Q4uM3MElPkJlNtkWL/iynWbGbp64rgTrH/\nxRRrNrPe0BWHSlLsfzHFms2sN3RFcKfY/2KKNZtZbyjSA85SSX8t6UFJD0h6f6uLSLH/xRRrNrPe\nUGSP+3nggxHxeuB84D2SzmplESn2v5hizWbWG4r0gHMAOJAPPyvpQWAE+H6ripg9mfeh2+7juSMv\nMJLALzRSrNnMekNTvyqRtIysG7MdNaatBdYCnHHGGU0XkmL/iynWbGbpK3xyUtIrgK8CH4iIQ9XT\nI2JTRIxGxOjw8HArazQzswqF9rglLSQL7VsjYmu5JTVvPhfC+CIaM0tNw+CWJOAm4MGI+OPyS2rO\nfC6E8UU0ZpaiIodKLgDeDlwsaXf+WFVyXYXN50IYX0RjZikq8quS7wJqQy3HZD4XwvgiGjNLUVdc\nOTkf87kQxhfRmFmKkg/u+VwI44tozCxFXXF3wPmYz4UwvojGzFKUfHDD/C6E8UU0Zpaa5A+VmJn1\nGwe3mVliHNxmZolxcJuZJcbBbWaWGAe3mVliHNxmZolxcJuZJcbBbWaWGAe3mVliHNxmZolxcJuZ\nJaZhcEu6WdJBSfe3oyAzM5tbkT3uLwCXlVyHmZkV1DC4I+I7wI/aUIuZmRXQsmPcktZKGpc0PjU1\n1aqXNTOzKi0L7ojYFBGjETE6PDzcqpc1M7Mq/lWJmVliHNxmZokp8nPAzcDfAcslPSHpN8svy8zM\n6mnYWXBEXN2OQszMrBgfKjEzS4yD28wsMQ5uM7PEOLjNzBLj4DYzS4yD28wsMQ5uM7PEOLjNzBLj\n4DYzS4yD28wsMQ5uM7PEOLjNzBLj4DYzS4yD28wsMQ5uM7PEOLjNzBJTKLglXSZpQtLDkm4ouygz\nM6uvSNdlA8BngMuBs4CrJZ1VdmFmZlabImLuGaSVwMciYix/vh4gIjbUazM6Ohrj4+NNF3PL1e/j\n1VP7OOu0E5tu+/0DhwCSatvJ9/ZnTqNtJ9/bn7n5tk8OL+WazZ9uui2ApJ0RMVpk3oZ9TgIjwL6K\n508Ab6zxpmuBtQBnnHFGkfd+iVOOP47FzwwcU9vFi46tXSfbdvK9/ZnTaNvJ9/Znbr7tKccfd8zt\nm1Fkj/tfAWMR8e78+duB8yLiffXaHOset5lZv2pmj7vIyckngKUVz08H9h9LYWZmNn9FgvvvgV+Q\n9FpJi4CrgK+VW5aZmdXT8Bh3RDwv6b3AdmAAuDkiHii9MjMzq6nIyUki4g7gjpJrMTOzAnzlpJlZ\nYhzcZmaJcXCbmSXGwW1mlpiGF+Ac04tKU8Bjx9j8VODpFpbTKq6rOa6rOa6rOb1Y12siYrjIjKUE\n93xIGi969VA7ua7muK7muK7m9HtdPlRiZpYYB7eZWWK6Mbg3dbqAOlxXc1xXc1xXc/q6rq47xm1m\nZnPrxj1uMzObg4PbzCwxHQvuRh0QSzpO0pZ8+g5Jy9pQ01JJfy3pQUkPSHp/jXkukvSMpN354yNl\n15W/715Je/L3fEkvFcr8l3x53Sfp3DbUtLxiOeyWdEjSB6rmacvyknSzpIOS7q8Yd4qkb0n6Qf7v\nyXXavjOf5weS3tmGujZKeihfT7dLGqrTds51XkJdH5M0WbGuVtVpW1rn4XXq2lJR015Ju+u0LXN5\n1cyGjm1jEdH2B9ntYR8BzgQWAd8Dzqqa598Cn8uHrwK2tKGu04Bz8+ETgP9do66LgK93YJntBU6d\nY/oq4BuAgPOBHR1Yp0+SXUTQ9uUFXAicC9xfMe4/ATfkwzcAf1Cj3SnAo/m/J+fDJ5dc11uABfnw\nH9Sqq8g6L6GujwG/XWA9z/ndbXVdVdP/CPhIB5ZXzWzo1DbWqT3u84CHI+LRiHgO+DJwZdU8VwJf\nzIdvAy6RpDKLiogDEXFvPvws8CBZn5spuBL4s8jcDQxJOq2N738J8EhEHOsVs/MSEd8BflQ1unIb\n+iKwukbTMeBbEfGjiPgx8C3gsjLriog7I+L5/OndZL1KtVWd5VVEke9uKXXl3/9/DWxu1fsVNUc2\ndGQb61Rw1+qAuDogX5wn38ifAX6uLdUB+aGZFcCOGpNXSvqepG9I+qU2lRTAnZJ2KuuYuVqRZVqm\nq6j/herE8gJ4VUQcgOyLB7yyxjydXm7Xkv2lVEujdV6G9+aHcG6u82d/J5fXm4GnIuIHdaa3ZXlV\nZUNHtrFOBXetPefq3yUWmacUkl4BfBX4QEQcqpp8L9nhgF8GPg1sa0dNwAURcS5wOfAeSRdWTe/k\n8loEXAH8RY3JnVpeRXVyuf0u8Dxwa51ZGq3zVvss8DrgDcABssMS1Tq2vICrmXtvu/Tl1SAb6jar\nMW5ey6xTwV2kA+IX55G0ADiJY/vTrimSFpKtmFsjYmv19Ig4FBE/yYfvABZKOrXsuiJif/7vQeB2\nsj9ZK3WyU+fLgXsj4qnqCZ1aXrmnZg8X5f8erDFPR5ZbfoLqrcDbIj8QWq3AOm+piHgqIo5ExAvA\n5+u8X6eW1wJgDbCl3jxlL6862dCRbaxTwV2kA+KvAbNnX38duKveBt4q+TG0m4AHI+KP68zz6tlj\n7ZLOI1uG/1ByXcdLOmF2mOzk1v1Vs30NeIcy5wPPzP4J1wZ194Q6sbwqVG5D7wT+e415tgNvkXRy\nfmjgLfm40ki6DPgwcEVE/KzOPEXWeavrqjwn8i/qvF+nOg+/FHgoIp6oNbHs5TVHNnRmGyvjDGzB\ns7SryM7MPgL8bj7u98g2ZoCXk/3p/TBwD3BmG2p6E9mfMPcBu/PHKuB64Pp8nvcCD5CdTb8b+JU2\n1HVm/n7fy997dnlV1iXgM/ny3AOMtmk9LiYL4pMqxrV9eZH9x3EAOEy2h/ObZOdE/ifwg/zfU/J5\nR4EbK9pem29nDwPXtKGuh8mOec5uY7O/nloC3DHXOi+5rv+Wbzv3kQXSadV15c9f8t0ts658/Bdm\nt6mKedu5vOplQ0e2MV/ybmaWGF85aWaWGAe3mVliHNxmZolxcJuZJcbBbWaWGAe3mVliHNxmZon5\nfxTaCYgFVtuVAAAAAElFTkSuQmCC\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0948f32b70>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = cconv(x, h)\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);\n",
    "plt.title('periodic extension')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "OK, clearly the result is not necessarily what we expected; note however that in both circular and \"normal\" convolution, you still have $M-1$ output samples \"touched\" by border effects, it's just that the border effects act differently in the two cases.\n",
    "\n",
    "Interestingly, you can still obtain a \"normal\" convolution using a circular convolution if you zero-pad the input signal with $M-1$ zeros:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 11,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  25\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0948ea8898>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = cconv(np.concatenate((x, np.zeros(M-1))), h)\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);\n",
    "# plot in red the difference with the standard conv\n",
    "plt.stem(y - np.convolve(x, h, mode='full'), markerfmt='ro');"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Why is this interesting? Because of the DFT...."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Offline implementations using the DFT\n",
    "\n",
    "The convolution theorem states that, for infinite sequences, \n",
    "\n",
    "$$\n",
    "    (x\\ast y)[n] = \\mbox{IDTFT}\\{X(e^{j\\omega})Y(e^{j\\omega})\\}[n]\n",
    "$$\n",
    "\n",
    "Can we apply this result to the finite-length case? In other words, what is the inverse DFT of the product of two DFTs? Let's see:\n",
    "\n",
    "\\begin{align}\n",
    "    \\sum_{k=0}^{N-1}X[k]Y[k]e^{j\\frac{2\\pi}{N}nk} &= \\sum_{k=0}^{N-1}\\sum_{p=0}^{N-1}x[p]e^{-j\\frac{2\\pi}{N}pk}\\sum_{q=0}^{N-1}y[q]e^{-j\\frac{2\\pi}{N}qk} \\,e^{j\\frac{2\\pi}{N}nk} \\\\\n",
    "    &= \\sum_{p=0}^{N-1}\\sum_{q=0}^{N-1}x[p]y[q]\\sum_{k=0}^{N-1}e^{j\\frac{2\\pi}{N}(n-p-q)k} \\\\\n",
    "    &= N\\sum_{p=0}^{N-1}x[p]y[(n-p) \\mod N]\n",
    "\\end{align}\n",
    "\n",
    "The results follows from the fact that $\\sum_{k=0}^{N-1}e^{j\\frac{2\\pi}{N}(n-p-q)k}$ is nonzero only for $n-p-q$ multiple of $N$; as $p$ varies from $0$ to $N-1$, the corresponding value of $q$ between $0$ and $N$ that makes $n-p-q$ multiple of $N$ is $(n-p) \\mod N$.\n",
    "\n",
    "So the fundamental result is: **the inverse DFT of the product of two DFTs is the circular convolution of the underlying time-domain sequences!**\n",
    "\n",
    "\n",
    "To apply this result to FIR filtering, the first step is to choose the space for the DFTs. In our case we have a finite-length data vector of length $N$ and a finite-support impulse response of length $M$ with $M<N$ so let's operate in $\\mathbb{C}^N$ by zero-padding the impulse response to size $N$. Also, we most likely want the normal convolution, so let's zero-pad both signals by an additional $M-1$ samples"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 12,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "def DFTconv(x, h, mode='full'):\n",
    "    # we want the compute the full convolution\n",
    "    N = len(x)\n",
    "    M = len(h)\n",
    "    X = np.fft.fft(x, n=N+M-1)\n",
    "    H = np.fft.fft(h, n=N+M-1)\n",
    "    # we're using real-valued signals, so drop the imaginary part\n",
    "    y = np.real(np.fft.ifft(X * H))\n",
    "    if mode == 'valid':\n",
    "        # only N-M+1 points, starting at M-1\n",
    "        return y[M-1:N]\n",
    "    elif mode == 'same':\n",
    "        return y[int((M-1)/2):int((M-1)/2)+N]\n",
    "    else:\n",
    "        return y"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Let's verify that the results are the same"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 13,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  17\n",
      "signal length:  17\n"
     ]
    },
    {
     "data": {
      "image/png": "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\nSYWxuCWpMP8PZwljxA7aAi4AAAAASUVORK5CYII=\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0949133550>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = np.convolve(x, h, mode='valid')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);\n",
    "y = DFTconv(x, h, mode='valid')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y, markerfmt='ro');"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 14,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "signal length:  21\n",
      "signal length:  21\n"
     ]
    },
    {
     "data": {
      "image/png": "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\n",
      "text/plain": [
       "<matplotlib.figure.Figure at 0x7f0949167d30>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "y = np.convolve(x, h, mode='same')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y);\n",
    "y = DFTconv(x, h, mode='same')\n",
    "print('signal length: ', len(y))\n",
    "plt.stem(y, markerfmt='ro');"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Of course the question at this point is: why go through the trouble of taking DFTs if all we want is the standard convolution? The answer is: **computational efficiency.**\n",
    "\n",
    "If you look at the convolution sum, each output sample requires $M$ multiplications (and $M-1$ additions but let's just consider multiplications). In order to filter an $N$-point signal we will need $NM$ multiplications. Assume $N \\approx M$ and you can see that the computational requirements are on the order of $M^2$. If we go the DFT route using an efficient FFT implementation we have approximately: \n",
    "\n",
    " * $M\\log_2 M$ multiplication to compute $H[k]$\n",
    " * $M\\log_2 M$ multiplication to compute $X[k]$\n",
    " * $M\\log_2 M$ multiplication to compute $X[k]H[k]$\n",
    " * $M\\log_2 M$ multiplication to compute the inverse DFT\n",
    " \n",
    "Even considering that we now have to use complex multiplications (which will cost twice as much), we can estimate the cost of the DFT based convolution at around $8M\\log_2M$, which is smaller than $M^2$ as soon as $M>44$.  "
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "In practice, the data vector is much longer than the impulse response so that filtering via standard convolution requires on the order of $MN$ operations. Two techniques, called [Overlap Add](https://en.wikipedia.org/wiki/Overlap%E2%80%93add_method) and [Overlap Save](https://en.wikipedia.org/wiki/Overlap%E2%80%93save_method)\n",
    "can be used to divide the convolution into $N/M$ independent convolutions between $h[n]$ and an $M$-sized piece of $x[n]$; FFT-based convolution can then be used on each piece. While the exact cost per sample of each technique is a bit complicated to estimate, as a rule of thumb **as soon as the impulse response is longer than 50 samples, it's more convenient to use DFT-based filtering.** "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": []
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
   "version": "3.6.2"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 1
}