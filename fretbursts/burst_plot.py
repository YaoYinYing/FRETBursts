# encoding: utf-8
#
# FRETBursts - A single-molecule FRET burst analysis toolkit.
#
# Copyright (C) 2014 Antonino Ingargiola <tritemio@gmail.com>
#
"""
This module defines all the plotting functions for the `Data` object.

The main plot function is `dplot()` that takes, as parameters, a `Data()`
object and a 1-ch-plot-function and creates a subplot for each channel.

The 1-ch plot functions are usually called through `dplot` but can also be
called directly to make a single channel plot.

The 1-ch plot functions names all start with the plot type (`timetrace`,
`ratetrace`, `hist` or `scatter`).

**Example 1** - Plot the timetrace for all ch::

    dplot(d, timetrace_da, scroll=True)

**Example 2** - Plot a FRET histogramm for each ch with a fit overlay::

    dplot(d, hist_fret, show_fit=True)

"""

# Numeric imports
import numpy as np
from numpy import arange, r_
from matplotlib.mlab import normpdf
from scipy.stats import erlang
from scipy.interpolate import UnivariateSpline

# Graphics imports
import matplotlib.pyplot as plt
from matplotlib.pyplot import (plot, hist, xlabel, ylabel, grid, title, legend,
                               gca, gcf)
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
#from matplotlib.collections import PathCollection
#from matplotlib.path import Path
#import matplotlib.patches as patches
#from matplotlib.lines import Line2D

# Local imports
import burstlib as bl
import burstlib_ext as bext
import background as bg
from fit import gaussian_fitting
from utils.misc import binning, clk_to_s, pprint
from scroll_gui import ScrollingToolQT
from fit.weighted_kde import gaussian_kde_w
import gui_selection as gs

#ip = get_ipython()
#ip.magic("run -i scroll_gui.py")
#ip.magic("run -i gui_selection.py")
#ip.magic("run -i style.py")

params = {
        'font.size': 12,
        'legend.fontsize': 11,
        }
plt.rcParams.update(params)

##
#  Utility functions
#
def _normalize_kwargs(kwargs, kind='patch'):
    """Convert matplotlib keywords from short to long form."""
    if kind == 'line2d':
        long_names = dict(c='color', ls='linestyle', lw='linewidth',
                          mec='markeredgecolor', mew='markeredgewidth',
                          mfc='markerfacecolor', ms='markersize',)
    elif kind == 'patch':
        long_names = dict(c='color', ls='linestyle', lw='linewidth',
                          ec='edgecolor', fc='facecolor',)
    for short_name in long_names:
        if short_name in kwargs:
            kwargs[long_names[short_name]] = kwargs.pop(short_name)
    return kwargs

def bsavefig(d, s):
    """Save current figure with name in `d`, appending the string `s`."""
    plt.savefig(d.Name()+s)

##
#  Multi-channel plot functions
#

def mch_plot_bg(d, **kwargs):
    """Plot background vs channel for DA, D and A photons."""
    plot(r_[1:d.nch+1],[b.mean()*1e-3 for b in d.bg], lw=2, color='b',
            label=' T', **kwargs)
    plot(r_[1:d.nch+1],[b.mean()*1e-3 for b in d.bg_dd], color='g', lw=2,
            label=' D', **kwargs)
    plot(r_[1:d.nch+1],[b.mean()*1e-3 for b in d.bg_ad], color='r', lw=2,
            label=' A', **kwargs)
    xlabel("CH"); ylabel("kcps"); grid(True); legend(loc='best')
    title(d.name())

def mch_plot_bg_ratio(d):
    """Plot ratio of A over D background vs channel."""
    plot(r_[1:d.nch+1],[ba.mean()/bd.mean() for bd,ba in zip(d.bg_dd,d.bg_ad)],
            color='g', lw=2, label='A/D')
    xlabel("CH"); ylabel("BG Ratio A/D"); grid(True)
    title("BG Ratio A/D "+d.name())

def mch_plot_bsize(d):
    """Plot mean burst size vs channel."""
    CH = np.arange(1, d.nch+1)
    plot(CH, [b.mean() for b in d.nt], color='b', lw=2, label=' T')
    plot(CH, [b.mean() for b in d.nd], color='g', lw=2, label=' D')
    plot(CH, [b.mean() for b in d.na], color='r', lw=2, label=' A')
    xlabel("CH"); ylabel("Mean burst size")
    grid(True)
    legend(loc='best')
    title(d.name())


##
#  ALEX alternation period plots
#
def plot_alternation_hist(d, bins=100, **kwargs):
    plt.figure()
    ph_times_t, det_t, period = d.ph_times_t, d.det_t, d.alex_period
    d_ch, a_ch = d.det_donor_accept
    d_em_t = (det_t == d_ch)
    kwargs.update(bins=bins, alpha=0.2)
    hist(ph_times_t[d_em_t] % period, color='g', label='D', **kwargs)
    hist(ph_times_t[-d_em_t] % period, color='r', label='A', **kwargs)

    if d.D_ON[0] < d.D_ON[1]:
        plt.axvspan(d.D_ON[0], d.D_ON[1], color='g', alpha=0.1)
    else:
        plt.axvspan(0,d.D_ON[1], color='g', alpha=0.1)
        plt.axvspan(d.D_ON[0], period, color='g', alpha=0.1)

    if d.A_ON[0] < d.A_ON[1]:
        plt.axvspan(d.A_ON[0], d.A_ON[1], color='r', alpha=0.1)
    else:
        plt.axvspan(0, d.A_ON[1], color='r', alpha=0.1)
        plt.axvspan(d.A_ON[0], period, color='r', alpha=0.1)

    legend(loc='best')

def plot_alternation_hist_sel(d, **kwargs):
    plt.figure()
    ph_times, d_ex, period = d.get_ph_times(0), d.D_ex[0], d.alex_period
    bins = arange(0, period+1, period/100.)
    kwargs.update(bins=bins, alpha=0.2)
    hist(ph_times[d_ex] % period, color='g', label='D', **kwargs)
    hist(ph_times[-d_ex] % period, color='r', label='A', **kwargs)
    plt.axvline(d.D_ON[0], color='g', lw=2);
    plt.axvline(d.D_ON[1], color='g', lw=2)
    plt.axvline(d.A_ON[0], color='r', lw=2);
    plt.axvline(d.A_ON[1], color='r', lw=2)
    legend(loc='best')


## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
##  Multi-channel plots
## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

##
#  Timetrace plots
#
def _plot_bursts(d, i, t_max_clk, pmax=1e3, pmin=0):
    """Highlights bursts in a timetrace plot."""
    b = d.mburst[i]
    if np.size(b) == 0: return
    pprint("CH %d burst..." % (i+1))
    bs = b[bl.b_start(b) < t_max_clk]
    start = bl.b_start(bs)*d.clk_p
    end = bl.b_end(bs)*d.clk_p
    R, R2 = [], []
    width = end-start
    ax = gca()
    for s,w in zip(start,width):
        #codes = [Path.MOVETO,
        #    Path.LINETO,
        #    Path.LINETO,
        #    Path.LINETO,
        #    Path.CLOSEPOLY,
        #    ]
        #verts = array([[s,0],[s,pmax],[e,pmax],[e,0],[s,0]])
        #path = Path(verts, codes)
        #r = patches.PathPatch(path)

        r = Rectangle(xy=(s,pmin), height=pmax-pmin, width=w)
        r.set_clip_box(ax.bbox); r.set_zorder(0)

        #r2 = Line2D(xdata=[s+0.5*w,s+0.5*w], ydata=[-pmax,0])
        #axvspan(s, e, color='#DDDDDD', alpha=1)
        #ax.add_artist(r)
        R.append(r)
        #R2.append(r2)
    ax.add_artist(PatchCollection(R, lw=0,color="#999999"))
    #ax.add_artist(PatchCollection(R2, lw=2, color="#FF0000"))
    pprint("[DONE]\n")

def _timetrace_bg(d, i, BG, bin_width=None, F=None, Th=True, color='r'):
    """Plot an overlay of background rate on a timetrace plot."""
    if bin_width is None: bin_width = 1.
    for ii, (bg_i ,php) in enumerate(zip(BG[i], d.Ph_p[i])):
        ph_p = np.array(php)*d.clk_p
        plot(ph_p, [bg_i*bin_width]*2, ls='--', color=color)
        if hasattr(d, 'TT') and Th:
            plot(ph_p, [bin_width*d.m/d.TT[i][ii]]*2, color='orange')
        if F is not None:
            plot(ph_p,[F*bg*bin_width]*2, color='m')

def _gui_timetrace_burst_sel(d, i, func, fig, ax):
    """Add GUI burst selector via mouse click to the current plot."""
    if i == 0:
        func.burst_sel = gs.MultiAxPointSelection(fig, ax, d)
    else:
        func.burst_sel.ax_list.append(ax)

def timetrace_da(d, i=0, idx=0, bin_width=1e-3, bins=100000, bursts=False):
    """Timetrace of binned photons (donor-acceptor)."""
    if bursts:
        t_max_clk = int((bins*bin_width)/d.clk_p)
        _plot_bursts(d, i, t_max_clk, pmax=500, pmin=-500)

    if not bl.mask_empty(d.get_D_em(i)):
        ph_d = d.get_ph_times(i, ph_sel='D')
        tr_d, t_d = binning(ph_d,bin_width_ms=bin_width*1e3, max_num_bins=bins,
                clk_p=d.clk_p)
        t_d = t_d[1:]*d.clk_p-bin_width*0.5
        plot(t_d, tr_d, 'g', lw=1.5, alpha=0.8)
        if 'bg' in d:
            _timetrace_bg(d, i, d.bg_dd, bin_width=bin_width, color='k',
                          Th=False)

    if not bl.mask_empty(d.get_A_em(i)):
        ph_a = d.get_ph_times(i, ph_sel='A')
        tr_a, t_a = binning(ph_a,bin_width_ms=bin_width*1e3, max_num_bins=bins,
                clk_p=d.clk_p)
        t_a = t_a[1:]*d.clk_p-bin_width*0.5
        plot(t_a, -tr_a, 'r', lw=1.5, alpha=0.8)
        if 'bg' in d:
            _timetrace_bg(d, i, -r_[d.bg_ad], bin_width=bin_width, color='k',
                          Th=False)
    xlabel('Time (s)'); ylabel('# ph')
    _gui_timetrace_burst_sel(d, idx, timetrace_da, gcf(), gca())

def timetrace(d, i=0, idx=0, bin_width=1e-3, bins=100000, bursts=False, F=None,
              **kwargs):
    """Timetrace of binned photons (total: donor + acceptor)."""
    if bursts:
        t_max_clk = int((bins*bin_width)/d.clk_p)
        _plot_bursts(d, i, t_max_clk, pmax=500)
    #ph = d.ph_times_det[i]
    ph = d.get_ph_times(i)
    trace, time = binning(ph,bin_width_ms=bin_width*1e3, max_num_bins=bins,
            clk_p=d.clk_p)
    time = time[1:]*d.clk_p-bin_width*0.5
    plot(time, trace, **kwargs)
    if 'bg' in d:
        _timetrace_bg(d, i, d.bg, bin_width=bin_width, F=F)
    xlabel('Time (s)'); ylabel('# ph')
    _gui_timetrace_burst_sel(d, idx, timetrace, gcf(), gca())

def ratetrace(d, i=0, idx=0, m=None, max_ph=1e6, pmax=1e6, bursts=False,
              F=None):
    """Timetrace of photons rates (total: donor + acceptor)."""
    if m is None: m = d.m
    ph = d.get_ph_times(i)
    max_ph = min(max_ph, ph.size)
    if bursts:
        t_max_clk = ph[max_ph-1]
        _plot_bursts(d, i, t_max_clk, pmax=pmax)
    rates = bl.ph_rate(m, ph[:max_ph])/d.clk_p
    times = bl.ph_rate_t(m, ph[:max_ph])*d.clk_p
    plot(times, rates, lw=1.2)
    if 'bg' in d:
        _timetrace_bg(d, i, d.bg, F=F)
    xlabel('Time (s)'); ylabel('# ph')
    _gui_timetrace_burst_sel(d, idx, ratetrace, gcf(), gca())

def ratetrace_da(d, i=0, idx=0, m=None, max_ph=1e6, pmax=1e6, bursts=False,
                 F=None):
    """Timetrace of photons rates (donor-acceptor)."""
    if m is None: m = d.m
    ph_d = d.get_ph_times(i, ph_sel='D')
    ph_a = d.get_ph_times(i, ph_sel='A')
    if not d.ALEX:
        max_ph = min(max_ph, ph_d.size, ph_a.size)
    else:
        ph_aa = d.get_ph_times(i, ph_sel='AA')
        max_ph = min(max_ph, ph_d.size, ph_a.size, ph_aa.size)
    if bursts:
        t_max_clk = ph_d[max_ph-1]
        _plot_bursts(d, i, t_max_clk, pmax=pmax, pmin=-pmax)
    r_d = bl.ph_rate(m, ph_d[:max_ph])/d.clk_p
    t_d = bl.ph_rate_t(m, ph_d[:max_ph])*d.clk_p
    r_a = bl.ph_rate(m, ph_a[:max_ph])/d.clk_p
    t_a = bl.ph_rate_t(m, ph_a[:max_ph])*d.clk_p
    plot(t_d, r_d, 'g', lw=1.2)
    plot(t_a, -r_a, 'r', lw=1.2)
    if d.ALEX:
        r_aa = bl.ph_rate(m, ph_aa[:max_ph])/d.clk_p
        t_aa = bl.ph_rate_t(m, ph_aa[:max_ph])*d.clk_p
        plot(t_aa, -r_aa, 'm', lw=1.2)
    if 'bg' in d:
        _timetrace_bg(d, i, d.bg_dd, F=F, color='k')
        _timetrace_bg(d, i, -r_[d.bg_ad], F=F, color='k')
    xlabel('Time (s)'); ylabel('# ph')
    _gui_timetrace_burst_sel(d, idx, ratetrace_da, gcf(), gca())

def timetrace_alex(d, i=0, bin_width=1e-3, bins=100000, bursts=False,
                   **plot_kw):
    """Timetrace of binned photons (ALEX version: donor, acceptor, aa)."""
    b = d.mburst[i]
    ph_dd = d.get_ph_times(i, ph_sel='D')
    ph_ad = d.get_ph_times(i, ph_sel='A')
    ph_aa = d.get_ph_times(i, ph_sel='DA')

    t0 = d.ph_times_m[i][0]
    bin_width_clk = bin_width/d.clk_p
    rbins = arange(t0,t0+bins*bin_width_clk, bin_width_clk)
    tracedd, tdd = np.histogram(ph_dd, bins=rbins)
    tracead, tad = np.histogram(ph_ad, bins=rbins)
    traceaa, taa = np.histogram(ph_aa, bins=rbins)

    assert ((tdd == taa) + (tdd == tad)).all()
    t = tdd[1:]*d.clk_p

    plt.axhline( d.m/d.T[i]*bin_width, color='b')
    plt.axhline(-d.m/d.T[i]*bin_width, color='b')

    plot(t, tracedd, 'g', lw=1.5, alpha=0.8, label='DD', **plot_kw)
    plot(t, -tracead, 'r', lw=1.5, alpha=0.8, label='AD', **plot_kw)
    plot(t, -traceaa, color='orange', lw=1.5, alpha=0.8, label='AA', **plot_kw)
    xlabel('Time (s)'); ylabel('# ph')
    if bursts:
        imax = int((bins*bin_width)/d.clk_p)
        tstart, istart, iend = bl.b_start(b), bl.b_istart(b), bl.b_iend(b)
        burst_mask = (tstart < (bins*bin_width/d.clk_p))
        start = d.ph_times_m[i][:imax][bl.b_istart(b[burst_mask,:])]*d.clk_p
        end = d.ph_times_m[i][:imax][bl.b_iend(b[burst_mask,:])]*d.clk_p
        plt.vlines(start, -100,100, color='k')
        plt.vlines(end, -100,100, color='r')
        #for s,e in zip(start,end):
        #    axvspan(s, e, color='k', alpha=0.2)

def sort_burst_sizes(sizes, levels=np.arange(1, 102, 20)):
    """Return a list of masks that split `sizes` in levels.
    Used by timetrace_fret to select burst based on size groups.
    """
    masks = []
    for level1, level2 in zip(levels[:-1], levels[1:]):
        masks.append((sizes >= level1)*(sizes < level2))
    masks.append(sizes >= level2)
    return masks

def timetrace_fret(d, i=0, gamma=1., **kwargs):
    """Timetrace of burst FRET vs time. Uses `plot`."""
    b = d.mburst[i]
    bsizes = bl.select_bursts.get_burst_size(d, ich=i, gamma=gamma)

    style_kwargs = dict(marker='o', mew=0.5, color='b', mec='grey',
                        alpha=0.4, ls='')
    style_kwargs.update(**kwargs)

    t, E = bl.b_start(b)*d.clk_p, d.E[i]
    levels = sort_burst_sizes(bsizes)
    for ilev, level in enumerate(levels):
        plt.plot(t[level], E[level], ms=np.sqrt((ilev+1)*15),
                 **style_kwargs)
    plt.plot(bl.b_start(b)*d.clk_p, d.E[i], '-k', alpha=0.1, lw=1)
    xlabel('Time (s)'); ylabel('E')
    _gui_timetrace_burst_sel(d, i, timetrace_fret, gcf(), gca())

def timetrace_fret_scatter(d, i=0, gamma=1., **kwargs):
    """Timetrace of burst FRET vs time. Uses `scatter` (slow)."""
    b = d.mburst[i]
    bsizes = bl.select_bursts.get_burst_size(d, ich=i, gamma=gamma)

    style_kwargs = dict(s=bsizes, marker='o', alpha=0.5)
    style_kwargs.update(**kwargs)
    plt.scatter(bl.b_start(b)*d.clk_p, d.E[i], **style_kwargs)
    xlabel('Time (s)'); ylabel('E')

def timetrace_bg(d, i=0, nolegend=False, ncol=3):
    """Timetrace of background rates."""
    t = arange(d.bg[i].size)*d.bg_time_s
    plot(t, 1e-3*d.bg[i], 'k', lw=2, label="T: %d cps" % d.rate_m[i])
    plot(t, 1e-3*d.bg_dd[i], 'g', lw=2, label="DD: %d cps" % d.rate_dd[i])
    plot(t, 1e-3*d.bg_ad[i], 'r', lw=2, label="AD: %d cps" % d.rate_ad[i])
    if d.ALEX:
        plot(t, 1e-3*d.bg_aa[i], 'm', lw=2, label="AA: %d cps" % d.rate_aa[i])
    if not nolegend:
        legend(loc='best', frameon=False, ncol=ncol)
    xlabel("Time (s)"); ylabel("BG rate (kcps)"); grid(True)
    plt.ylim(ymin=0)

def timetrace_b_rate(d, i=0):
    """Timetrace of bursts-per-second in each period."""
    t = arange(d.bg[i].size)*d.bg_time_s
    b_rate = r_[[(d.bp[i] == p).sum() for p in xrange(d.bp[i].max()+1)]]
    b_rate /= d.bg_time_s
    if t.size == b_rate.size+1:
        t = t[:-1] # assuming last period without bursts
    else:
        assert t.size == b_rate.size
    plot(t, b_rate, lw=2, label="CH%d" % (i+1))
    legend(loc='best', fancybox=True, frameon=False, ncol=3)
    xlabel("Time (s)"); ylabel("Burst per second"); grid(True)
    plt.ylim(ymin=0)

def time_ph(d, i=0, num_ph=1e4, ph_istart=0):
    """Plot 'num_ph' ph starting at 'ph_istart' marking burst start/end.
    TODO: Update to use the new matplotlib eventplot.
    """
    b = d.mburst[i]
    SLICE = slice(ph_istart, ph_istart+num_ph)
    ph_d = d.ph_times_m[i][SLICE][-d.A_em[i][SLICE]]
    ph_a = d.ph_times_m[i][SLICE][d.A_em[i][SLICE]]

    BSLICE = (bl.b_end(b) < ph_a[-1])
    start, end = bl.b_start(b[BSLICE]), bl.b_end(b[BSLICE])

    u = d.clk_p # time scale
    plt.vlines(ph_d*u, 0, 1, color='k', alpha=0.02)
    plt.vlines(ph_a*u, 0, 1, color='k', alpha=0.02)
    plt.vlines(start*u, -0.5, 1.5, lw=3, color='g', alpha=0.5)
    plt.vlines(end*u, -0.5, 1.5, lw=3, color='r', alpha=0.5)
    xlabel("Time (s)")


##
#  Histogram plots
#

def _get_fit_E_text(d, pylab=True):
    """Return a formatted string for fitted E."""
    delta = (d.E_fit.max()-d.E_fit.min())*100
    fit_text = r'\langle{E}_{fit}\rangle = %.3f \qquad ' % d.E_fit.mean()
    fit_text += r'\Delta E_{fit} = %.2f \%%' % delta
    if pylab: fit_text = r'$'+fit_text+r'$'
    return fit_text

def _fitted_E_plot(d, i=0, F=1, no_E=False, ax=None, show_model=True,
                   verbose=False, two_gauss_model=False, lw=2.5, color='k',
                   alpha=0.5, fillcolor=None):
    """Plot a fitted model overlay on a FRET histogram."""
    if ax is None:
        ax2 = gca()
    else:
        ax2 = plt.twinx(ax=ax)
        ax2.grid(False)

    if d.fit_E_curve and show_model:
        x = r_[-0.2:1.21:0.002]
        y = d.fit_E_model(x, d.fit_E_res[i, :])
        scale = F*d.fit_E_model_F[i]
        if two_gauss_model:
            assert d.fit_E_res.shape[1] > 2
            if d.fit_E_res.shape[1] == 5:
                m1, s1, m2, s2, a1 =  d.fit_E_res[i, :]
                a2 = (1-a1)
            elif d.fit_E_res.shape[1] == 6:
                m1, s1, a1, m2, s2, a2 =  d.fit_E_res[i, :]
            y1 = a1*normpdf(x, m1, s1)
            y2 = a2*normpdf(x, m2, s2)
            ax2.plot(x, scale*y1, ls='--', lw=lw, alpha=alpha, color=color)
            ax2.plot(x, scale*y2, ls='--', lw=lw, alpha=alpha, color=color)
        if fillcolor == None:
            ax2.plot(x, scale*y, lw=lw, alpha=alpha, color=color)
        else:
            ax2.fill_between(x, scale*y, lw=lw, alpha=alpha, edgecolor=color,
                             facecolor=fillcolor, zorder=10)
        if verbose:
            print 'Fit Integral:', np.trapz(scale*y, x)

    ax2.axvline(d.E_fit[i], lw=3, color='r', ls='--', alpha=0.6)
    xtext = 0.6 if d.E_fit[i] < 0.6 else 0.2
    if d.nch > 1 and not no_E:
        ax2.text(xtext, 0.81,"CH%d: $E_{fit} = %.3f$" % \
                (i+1, d.E_fit[i]),
                transform = gca().transAxes, fontsize=16,
                bbox=dict(boxstyle='round', facecolor='#dedede', alpha=0.5))


def hist_width(d, i=0, bins=r_[0:10:0.025], yscale='log', density=True,
               **kwargs):
    b = d.mburst[i]
    histog, bins = np.histogram(bl.b_width(b)*d.clk_p*1e3, bins=bins,
                                density=density)
    #bins *= d.clk_p  # (ms)
    bins = bins[:-1]#+(bins[1]-bins[0])/2.
    plot_style = dict(color='red', lw=2)
    plot_style.update(**kwargs)
    plot(bins, histog, **plot_style)
    gca().set_yscale(yscale)
    #fill_between(bins,0,histog,color='red', alpha=0.5)
    xlabel('Burst width (ms)'); ylabel('# Burst')
    plt.xlim(xmin=0); plt.ylim(ymin=0)

def hist_size(d, i=0, vmax=1000, bins=r_[:1e3:2]-1, which='all', yscale='log',
        legend=True, **kwargs):
    assert which in ["all", "nt", "nd", "na", "naa"]
    if which == 'nt' or which == 'all':
        H, A = np.histogram(d.nt[i], bins=bins)
        plot_style = dict(lw=2, color='k'); plot_style.update(**kwargs)
        plot(A[:-1]-0.5*(A[1]-A[0]), H, label='T', **plot_style)
    if which == 'nd' or which == 'all':
        H, A = np.histogram(d.nd[i], bins=bins)
        plot_style = dict(lw=2, color='g'); plot_style.update(**kwargs)
        plot(A[:-1]-0.5*(A[1]-A[0]), H, label='D', **plot_style)
    if which == 'na' or which == 'all':
        H, A = np.histogram(d.na[i], bins=bins)
        plot_style = dict(lw=2, color='r'); plot_style.update(**kwargs)
        plot(A[:-1]-0.5*(A[1]-A[0]), H, label='A', **plot_style)
    if d.ALEX and (which == 'naa' or which == 'all'):
        H, A = np.histogram(d.naa[i], bins=bins)
        plot_style = dict(lw=2, color='orange'); plot_style.update(**kwargs)
        plot(A[:-1]-0.5*(A[1]-A[0]), H, label='AA', **plot_style)
    gca().set_yscale(yscale)
    xlabel('# Ph.'); ylabel('# Bursts')
    if legend: gca().legend(loc='best')

def hist_fret(d, i=0, bins=None, binw=0.02, show_fit=False, show_model=True,
        no_text=False, normed=False, weights=None, gamma=1., verbose=False,
        fit_color='k', fit_alpha=0.5, fit_lw=2.5, fit_fillcolor=None,
        two_gauss_model=False, **kwargs):
    """Plot the FRET histogram and optionally the fitted peak
    """
    if bins is None: bins = r_[-0.2:1.2:binw]
    #plot_style = dict(color='#4f8ae3', alpha=1, histtype='bar',
    #        edgecolor='white', lw=1.2)
    style_kwargs = dict(bins=bins, normed=normed, histtype='stepfilled',
                        facecolor='#80b3ff', edgecolor='#5f8dd3',
                        linewidth=1.5, alpha=1)
    # kwargs overwrite style_kwargs
    style_kwargs.update(**_normalize_kwargs(kwargs))
    if weights is not None:
        w = bl.fret_fit.get_weights(d.nd[i], d.na[i], weights, gamma=gamma)
        w *= w.size/w.sum()
        style_kwargs.update(weights=w)
    hist(1.*d.E[i], **style_kwargs)
    xlabel('FRET Efficiency'); ylabel('# Bursts')
    if normed: ylabel('PDF')
    plt.ylim(ymin=0); plt.xlim(-0.2,1.2)
    if show_fit:
        F = 1 if normed else d.E[i].size*binw
        kw = dict(color=fit_color, alpha=fit_alpha, lw=fit_lw,
                  fillcolor=fit_fillcolor)
        _fitted_E_plot(d, i, F=F, no_E=no_text, show_model=show_model,
                 verbose=verbose, two_gauss_model=two_gauss_model, **kw)
        if i == 1 and not no_text:
            plt.figtext(0.4, 0.01, _get_fit_E_text(d), fontsize=14)
hist_E = hist_fret

def kde_fret(d, i=0, bandwidth=0.04, show_fit=False, show_model=False,
             weights=None, gamma=1., no_text=False, verbose=False,
             fit_color='k', fit_alpha=0.5, fit_lw=2.5, fit_fillcolor=None,
             **kwargs):
    """Plot the KDE for FRET distribution and optionally the fitted peak
    """
    E_ax = np.arange(-0.19, 1.19, 0.001)
    w = bl.fret_fit.get_weights(d.nd[i], d.na[i], weights=weights, gamma=gamma)
    kde = gaussian_kde_w(d.E[i], bw_method=bandwidth, weights=w)
    E_pdf = kde.evaluate(E_ax)
    if verbose: print 'KDE Integral:', np.trapz(E_pdf, E_ax)

    style_kwargs = dict(facecolor='#80b3ff', edgecolor='#5f8dd3',
                        linewidth=1.5, alpha=1)
    # kwargs overwrite plot_style
    style_kwargs.update(**_normalize_kwargs(kwargs))
    if style_kwargs['facecolor'] is None:
        style_kwargs.pop('facecolor')
        if not 'color' in style_kwargs:
            style_kwargs.update(color=style_kwargs.pop('edgecolor'))
        plot(E_ax, E_pdf, **style_kwargs)
    else:
        plt.fill_between(E_ax, E_pdf, **style_kwargs)
    xlabel('FRET Efficiency')
    ylabel('PDF')
    if show_fit:
        kw = dict(color=fit_color, alpha=fit_alpha, lw=fit_lw,
                  fillcolor=fit_fillcolor)
        _fitted_E_plot(d, i, F=1, no_E=no_text, show_model=show_model,
                 verbose=verbose, **kw)
        if i==0 and not no_text:
            plt.figtext(0.4, 0.01, _get_fit_E_text(d), fontsize=14)

def hist_fret_kde(d, i=0, bins=None, binw=0.02, bandwidth=0.04, show_fit=False,
        no_text=False, weights=None, gamma=1., **kwargs):
    """Plot the FRET histogram and a KDE overlay
    """
    hist_fret(d, i, bins=bins, binw=binw, show_fit=show_fit,
              no_text=no_text, weights=weights, gamma=gamma,
              show_model=False, normed=True, **kwargs)
    kde_fret(d, i, bandwidth=bandwidth, show_fit=False,
             weights=weights, gamma=gamma,
             facecolor='#8c8c8c', edgecolor='k', lw=2, alpha=0.5, zorder=2)

def hist_S(d, i=0, fit=None, bins=None, **kwargs):
    if bins is None: bins = arange(-0.2,1.21,0.02)
    Q = d.S[i]
    H = hist(Q, bins=bins, color='#4f8ae3', alpha=0.5, **kwargs)
    xlabel('S'); ylabel('# Bursts')
    plt.ylim(ymin=0); plt.xlim(-0.2,1.2)
    sn = np.sqrt(Q.size)
    if fit == 'two_gauss':
        mu1,sig1,mu2, sig2, a = gaussian_fitting.two_gaussian_fit_hist(Q)
        x = r_[-0.2:1.2:0.01]
        y = a*normpdf(x,mu1,sig1) + (1-a)*normpdf(x,mu2,sig2)
        print "D-only peak: %5.2f  - " % max([mu1,mu2]),
        mu = min([mu1,mu2])
        mu_sig = sig2/((1-a)*sn) if mu == mu2 else sig1/(a*sn)
    elif fit == 'gauss':
        mu,sig = gaussian_fitting.gaussian_fit_hist(Q)
        x = r_[-0.2:1.2:0.01]
        y = normpdf(x,mu,sig)
        mu_sig = sig/sn # std dev. of the mu estimator

    if fit == 'gauss' or fit == 'two_gauss':
        F = Q.size*(H[1][1]-H[1][0]) # Normalization factor
        plot(x,F*y, lw=2, alpha=0.5, color='k')
        plt.axvline(mu, lw=2, color='r', ls='--', alpha=0.5)
        plt.axvspan(mu-2*mu_sig,mu+2*mu_sig, color='r', alpha=0.1)
        print "Fitted S peak [CH%d]: %.2f " % (i+1,mu)
    elif fit is not None:
        print "Unrecognized fit name."

def hist2d_alex(d, i=0, vmin=2, vmax=0, bin_step=None,
                interp='bicubic', cmap='hot', under_color='white',
                over_color='white', scatter=True, scatter_ms=3,
                scatter_color='orange', scatter_alpha=0.2, gui_sel=False):
    """Plot 2D ALEX histogram and scatterplot overlay."""
    if bin_step is not None: d.calc_alex_hist(bin_step=bin_step)
    AH, E_bins,S_bins, E_ax,S_ax = d.AH[i], d.E_bins,d.S_bins, d.E_ax,d.S_ax

    colormap = plt.get_cmap(cmap)
    if vmax <= vmin:
        #E_range = (E_bins > 0.4)*(E_bins < 0.8)
        S_range = (S_bins < 0.8)
        vmax = AH[:,S_range].max()
        if vmax <= vmin: vmax = 10*vmin
    if scatter:
        plot(d.E[i],d.S[i], 'o', mew=0, ms=scatter_ms, alpha=scatter_alpha,
                color=scatter_color)
    im = plt.imshow(AH[:,::-1].T, interpolation=interp,
            extent=(E_bins[0],E_bins[-1],S_bins[0],S_bins[-1]),
            vmin=vmin, vmax=vmax, cmap=colormap)
    im.cmap.set_under(under_color)
    im.cmap.set_over(over_color)
    gcf().colorbar(im)
    plt.xlim(-0.2,1.2); plt.ylim(-0.2,1.2)
    xlabel('E'); ylabel('S'); grid(color='gray')
    if gui_sel:
        # the selection object must be saved (otherwise will be destroyed)
        hist2d_alex.gui_sel = gs.rectSelection(gcf(), gca())

def get_ES_range():
    """Get the range of ES histogram selected via GUI.

    Prints E1, E2, S1, S2 and return a dict containig these values.
    """
    sel = None
    if hasattr(hist2d_alex.gui_sel, 'selection'):
        sel = hist2d_alex.gui_sel.selection
        print 'E1={E1:.3}, E2={E2:.3}, S1={S1:.3}, S2={S2:.3}'.format(**sel)
    return sel

def hist_sbr(d, ich=0, **hist_kwargs):
    """Histogram of per-burst Signal-to-Background Ratio (SBR).
    """
    if not 'sbr' in d:
        d.calc_sbr()
    style_kwargs = dict(bins=np.r_[0:20:0.5])  # default style
    style_kwargs.update(**hist_kwargs)
    hist(d.sbr[ich], **style_kwargs)
    xlabel('SBR'); ylabel('# Bursts')

def hist_bg_fit_single(d, i=0, bp=0, bg='bg_dd', bin_width_us=10, yscale='log',
        F=0.15, **kwargs):
    """Histog. of ph-delays compared with BG fitting in burst period 'bp'.
    """
    l1, l2 = d.Lim[i][bp][0], d.Lim[i][bp][1]
    ph = d.ph_times_m[i][l1:l2+1]*d.clk_p
    a_em = d.A_em[i][l1:l2+1]
    d_em = -a_em
    if bg=='bg': dph = np.diff(ph)
    if bg=='bg_dd': dph = np.diff(ph[d_em])
    if bg=='bg_ad': dph = np.diff(ph[a_em])
    hist_kwargs = dict(bins=r_[0:2000:bin_width_us], histtype='step',
                       color='k', lw=1)
    hist_kwargs.update(**kwargs)
    H = hist(dph*1e6, color='k', **hist_kwargs)
    gca().set_yscale('log')
    xlabel(u'Ph delay time (μs)')
    ylabel("# Ph")

    efun = lambda t, r: np.exp(-r*t)*r
    r = d[bg][i][bp]
    t = r_[0:2000]*1e-6
    #nF = 1 if 'normed' in hist_kwargs else H[0].sum()*(bin_width_us)

    bins = hist_kwargs['bins']
    ibin = bins.size*F
    t_min = bins[ibin]*1e-6
    C = H[0][ibin]/efun(t_min, r)
    plot(t*1e6, C*efun(t, r), lw=3, alpha=0.5, color='r',
        label="%s:  %d cps" % (bg, r))
    ym = 0.5
    if 'normed' in hist_kwargs and hist_kwargs['normed']: ym = 0.1/ph.size
    legend(loc='best', fancybox=True)
    plt.xlim(0,1500)
    plt.ylim(ymin=ym)

def hist_bg_fit(d, i=0, bp=0, bin_width_us=10, yscale='log',
                t_min_us=300, **kwargs):
    """Histog. of ph-delays compared with BG fitting in burst period 'bp'.
    """
    l1, l2 = d.Lim[i][bp][0], d.Lim[i][bp][1]
    ph = d.ph_times_m[i][l1:l2+1]*d.clk_p

    if d.ALEX:
        dd_mask = d.D_em[i][l1:l2+1]*d.D_ex[i][l1:l2+1]
        ad_mask = d.A_em[i][l1:l2+1]*d.D_ex[i][l1:l2+1]
        aa_mask = d.A_em[i][l1:l2+1]*d.A_ex[i][l1:l2+1]
    else:
        ad_mask = d.A_em[i][l1:l2+1]
        dd_mask = -ad_mask

    dph = np.diff(ph)
    dph_d, dph_a = np.diff(ph[dd_mask]), np.diff(ph[ad_mask])
    plot_kw = dict(bins=r_[0:3000:bin_width_us], histtype='step', lw=1.,
                          normed=False)
    plot_kw.update(**kwargs)
    H = hist(dph*1e6, color='k', **plot_kw)
    Hd = hist(dph_d*1e6, color='g', **plot_kw)
    Ha = hist(dph_a*1e6, color='r', **plot_kw)
    if d.ALEX:
        Haa = hist(np.diff(ph[aa_mask])*1e6, color='m', **plot_kw)

    gca().set_yscale('log')
    xlabel(u'Ph delay time (μs)'); ylabel("# Ph")

    efun = lambda t, r: np.exp(-r*t)*r
    r, rd, ra, = d.bg[i][bp], d.bg_dd[i][bp], d.bg_ad[i][bp]
    raa = d.bg_aa[i][bp]
    t = r_[0:plot_kw['bins'].max()]*1e-6
    #nF = 1 if plot_kw['normed'] else H[0].sum()*(bin_width_us)

    bins = plot_kw['bins'] #; ibin = bins.size*F; t_min = bins[ibin]*1e-6
    ibin = np.where(bins >= t_min_us)[0][0]
    C = H[0][ibin]/efun(t_min_us*1e-6, r)
    Cd = Hd[0][ibin]/efun(t_min_us*1e-6, rd)
    Ca = Ha[0][ibin]/efun(t_min_us*1e-6, ra)
    plot(t*1e6, C*efun(t, r), lw=3, alpha=0.5, color='k',
        label="T:  %d cps" % r)
    plot(t*1e6, Cd*efun(t, rd), lw=3, alpha=0.5, color='g',
        label="DD:  %d cps" % rd)
    plot(t*1e6, Ca*efun(t, ra), lw=3, alpha=0.5, color='r',
        label="AD:  %d cps" % ra)
    if d.ALEX:
        Caa = Haa[0][ibin]/efun(t_min_us*1e-6, raa)
        plot(t*1e6, Caa*efun(t, raa), lw=3, alpha=0.5, color='m',
            label="AA:  %d cps" % raa)
    ym = 0.5
    if plot_kw['normed']: ym = 0.1/ph.size
    plt.legend(loc='best', fancybox=True); plt.ylim(ymin=ym)

def hist_ph_delays(d, i=0, time_min_s=0, time_max_s=30, bin_width_us=10,
        mask=None, yscale='log', hfit_bin_ms=1, efit_tail_min_us=1000,
        **kwargs):
    """Histog. of ph delays and comparison with 3 BG fitting functions.
    """
    ph = d.ph_times_m[i].copy()
    if mask is not None: ph = ph[mask[i]]
    ph = ph[(ph < time_max_s/d.clk_p)*(ph > time_min_s/d.clk_p)]
    dph = np.diff(ph)*d.clk_p
    H = hist(dph*1e6, bins=r_[0:1200:bin_width_us], histtype='step', **kwargs)
    gca().set_yscale('log')
    xlabel(u'Ph delay time (μs)'); ylabel("# Ph")

    efun = lambda t, r: np.exp(-r*t)*r
    re = bg.exp_fit(ph, tail_min_us=efit_tail_min_us)
    rg = bg.exp_hist_fit(ph, tail_min_us=efit_tail_min_us, binw=hfit_bin_ms*1e3)
    rc = bg.exp_cdf_fit(ph, tail_min_us=efit_tail_min_us)
    t = r_[0:1200]*1e-6
    F = 1 if 'normed' in kwargs else H[0].sum()*(bin_width_us)
    plot(t*1e6, 0.65*F*efun(t,rc)*1e-6, lw=3, alpha=0.5, color='m',
            label="%d cps - Exp CDF (tail_min_p=%.2f)" % (rc, efit_tail_min_us))
    plot(t*1e6, 0.65*F*efun(t,re)*1e-6, lw=3, alpha=0.5, color='r',
            label="%d cps - Exp ML (tail_min_p=%.2f)" % (re, efit_tail_min_us))
    plot(t*1e6, 0.68*F*efun(t,rg)*1e-6, lw=3, alpha=0.5, color='g',
            label=u"%d cps - Hist (bin_ms=%d) [Δ=%d%%]" % (hfit_bin_ms, rg,
                                                           100*(rg-re)/re))
    plt.legend(loc='best', fancybox=True)

def hist_mdelays(d, i=0, m=10, bins_s=(0, 10, 0.02), bp=0,
                  no_bg_fit=True, hold=False, bg_ppf=0.01, ph_sel='DA',
                  spline=True, s=1., bg_fit=True, bg_F=0.8):
    """Histogram of m-ph delays (all ph vs in-burst ph)."""
    ax = gca()
    if not hold:
        #ax.clear()
        for _ind in range(len(ax.lines)): ax.lines.pop()

    results = bext.calc_mdelays_hist(
                        d=d, ich=i, m=m, bp=bp, bins_s=bins_s, ph_sel=ph_sel,
                        bursts=True, bg_fit=bg_fit, bg_F=bg_F)
    bin_x, histog_y = results[:2]
    bg_dist = results[2]
    rate_ch_kcps = 1./bg_dist.kwds['scale']  # extract the rate
    if bg_fit:
        a, rate_kcps = results[3:5]

    mdelays_hist_y = histog_y[0]
    mdelays_b_hist_y = histog_y[1]

    # Center of mass (COM)
    binw = bins_s[2]
    com = np.sum(bin_x*mdelays_hist_y)*binw
    com_b = np.sum(bin_x*mdelays_b_hist_y)*binw
    #print com, com_b

    # Compute a spline smoothing of the PDF
    mdelays_spline = UnivariateSpline(bin_x, mdelays_hist_y, s=s*com)
    mdelays_b_spline = UnivariateSpline(bin_x, mdelays_b_hist_y, s=s*com_b)
    mdelays_spline_y = mdelays_spline(bin_x)
    mdelays_b_spline_y = mdelays_b_spline(bin_x)
    if spline:
        mdelays_pdf_y = mdelays_spline_y
        mdelays_b_pdf_y = mdelays_b_spline_y
    else:
        mdelays_pdf_y = mdelays_hist_y
        mdelays_b_pdf_y = mdelays_b_hist_y

    # Thresholds and integrals
    max_delay_th_P = bg_dist.ppf(bg_ppf)
    max_delay_th_F = m/rate_ch_kcps/d.F

    burst_domain = bin_x < max_delay_th_F
    burst_integral = np.trapz(x=bin_x[burst_domain],
                              y=mdelays_hist_y[burst_domain])

    title("I = %.1f %%" % (burst_integral*100), fontsize='small')
    #text(0.8,0.8,"I = %.1f %%" % (integr*100), transform = gca().transAxes)

    ## MDelays plot
    plot(bin_x, mdelays_pdf_y, lw=2, color='b', alpha=0.5,
         label="Delays dist.")
    plot(bin_x, mdelays_b_pdf_y, lw=2, color='r', alpha=0.5,
         label="Delays dist. (in burst)")
    plt.axvline(max_delay_th_P, color='k',
                label="BG ML dist. @ %.1f%%" % (bg_ppf*100))
    plt.axvline(max_delay_th_F, color='m',
                label="BS threshold (F=%d)" % d.F)

    ## Bg distribution plots
    bg_dist_y = bg_dist.pdf(bin_x)
    ibin_x_bg_mean = np.abs(bin_x - bg_dist.mean()).argmin()
    bg_dist_y *= mdelays_pdf_y[ibin_x_bg_mean]/bg_dist_y[ibin_x_bg_mean]
    plot(bin_x, bg_dist_y, '--k', alpha=1.,
         label='BG ML dist.')
    plt.axvline(bg_dist.mean(), color='k', ls='--', label="BG mean")
    if bg_fit:
        bg_y = a*erlang.pdf(bin_x, a=m, scale=1./rate_kcps)
        plot(bin_x, bg_y, '--k', alpha=1.)
    plt.legend(ncol=2, frameon=False)
    xlabel("Time (ms)")

def hist_mrates(d, i=0, m=10, bins=r_[0:20e3:20], yscale='log', normed=True,
        dense=True):
    """Histogram of m-photons rates."""
    ph = d.ph_times_m[i]
    if dense:
        ph_mrates = 1.*m/((ph[m-1:]-ph[:ph.size-m+1])*d.clk_p*1e3)
    else:
        ph_mrates = 1.*m/(np.diff(ph[::m])*d.clk_p*1e3)
    #gauss = lambda M,std: gaussian(M,std)/gaussian(M,std).sum()
    H = np.histogram(ph_mrates, bins=bins, normed=normed)
    epdf_x = H[1][:-1]
    epdf_y = H[0]
    plot(epdf_x, epdf_y, '.-')
    #plot(epdf_x, convolve(epdf_y, gauss(30,4),'same'), lw=2)
    gca().set_yscale(yscale)
    xlabel("Rates (kcps)")

## Bursts stats
def hist_rate_in_burst(d, i=0, bins=20):
    """Histogram of total photon rate in each burst."""
    b = d.mburst[i]
    rate = 1e-3*d.nt[i]/(bl.b_width(b)*d.clk_p)
    hist(rate, bins=bins, color="blue")
    xlabel('In-burst ph. rate (kcps)'); ylabel('# Bursts')
    #xlim(xmin=d.L/2); ylim(ymin=0)

def hist_burst_delays(d, i=0, tmax_seconds=0.5, bins=100, **kwargs):
    """Histogram of waiting times between bursts."""
    b = d.mburst[i]
    bd = clk_to_s(np.sort(np.diff(b[:,0].astype(float))))[:-20]
    hist(bd[bd<tmax_seconds], bins=bins, **kwargs)
    xlabel('Delays between bursts (s)'); ylabel('# bursts')

## Burst internal "symmetry"
def hist_bleaching(d, i=0, bins=None,use_median=True, normalize=True, **kwargs):
    if bins is None: bins=arange(-1,1.01,0.1)
    # bleaching() defined in burstlib_misc.py
    data, s1, s2 = bleaching(d, i, use_median=use_median, normalize=normalize)
    h,x,_ = hist(data, alpha=0.5, bins=bins,**kwargs)
    width = x[1]-x[0]
    #xc = x[:-1]
    #h_mask_neg = (x<-1e-14)[:-1];h_mask_pos = (x>-1e-14)[:-1]
    #bh = (h-h[::-1])
    bh = h - h[::-1]
    #x_neg = x[x<-1e-14]
    #bar(x_neg,h[h_mask_neg]-h[h_mask_pos][::-1],width=0.2,color='m',alpha=0.5)
    plt.bar(x[:-1],bh,width=width,color='red',alpha=0.6,linewidth=0)
    xlabel(s1); title(s2, fontsize=12)

def hist_asymmetry(d, i=0, bins=None, **kwargs):
    if bins is None: bins=arange(-100,101,10)
    data, s = asymmetry(d, i)
    h,x,_ = hist(data, alpha=0.5, bins=bins,**kwargs)
    width = x[1]-x[0]
    h_mask_neg = (x<-1e-14)[:-1]; h_mask_pos = (x>-1e-14)[:-1]
    bh = (h - h[::-1])
    plt.bar(x[:-1], bh, width=width, color='red', alpha=0.6, linewidth=0)
    xlabel(s)#; title(s2, fontsize=12)

##
#  Scatter plots
#

def scatter_width_size(i, d):
    """Scatterplot of burst width versus size."""
    b = d.mburst[i]
    plot(bl.b_width(b)*d.clk_p*1e3, d.nt[i], 'o', mew=0, ms=3, alpha=0.7,
         color='blue')
    t_ms = arange(0,50)
    plot(t_ms,((d.m)/(d.T[i]))*t_ms*1e-3,'--', lw=2, color='k',
            label='Slope = m/T = min. rate = %1.0f cps' % (d.m/d.T[i]))
    plot(t_ms,d.rate_m[i]*t_ms*1e-3,'--', lw=2, color='r',
            label='Noise rate: BG*t')
    xlabel('Burst width (ms)'); ylabel('Burst size (# ph.)')
    plt.xlim(0,10); plt.ylim(0,300)
    legend(frameon=False)

def scatter_rate_da(i, d):
    """Scatter of nd rate vs na rate (rates for each burst)."""
    b = d.mburst[i]
    Rate = lambda nX: nX[i]/bl.b_width(b)/d.clk_p*1e-3
    plot(Rate(d.nd), Rate(d.na), 'o', mew=0,ms=3,alpha=0.1,color='blue')
    xlabel('D burst rate (kcps)'); ylabel('A burst rate (kcps)')
    plt.xlim(-20,100); plt.ylim(-20,100)
    legend(frameon=False)

def scatter_fret_size(i, d):
    """Scatterplot of FRET efficiency versus burst size (nt)."""
    plot(d.E[i], d.nt[i], 'o', mew=0, ms=3, alpha=0.1, color="blue")
    xlabel("FRET Efficiency (E)")
    ylabel("Burst size (#ph)")

def scatter_fret_nd_na(d, i=0, show_fit=False, no_text=False, gamma=1.,
                       **kwargs):
    """Scatterplot of FRET versus gamma-corrected burst size."""
    default_kwargs = dict(mew=0, ms=3, alpha=0.3, color="blue")
    default_kwargs.update(**kwargs)
    plot(d.E[i], gamma*d.nd[i]+d.na[i], 'o', **default_kwargs)
    xlabel("FRET Efficiency (E)")
    ylabel("Burst size (#ph)")
    if show_fit:
        _fitted_E_plot(d, i, F=1., no_E=no_text, ax=gca())
        if i==0 and not no_text:
            plt.figtext(0.4,0.01, _get_fit_E_text(d),fontsize=14)

def scatter_fret_width(i, d):
    """Scatterplot of FRET versus burst width."""
    b = d.mburst[i]
    plot(d.E[i],(b[:,1]*d.clk_p)*1e3, 'o', mew=0, ms=3, alpha=0.1,
         color="blue")
    xlabel("FRET Efficiency (E)")
    ylabel("Burst width (ms)")

def scatter_da(d, i=0, alpha=0.3):
    """Scatterplot of donor vs acceptor photons (nd, vs na) in each burst."""
    plot(d.nd[i], d.na[i],'o', mew=0,ms=3, alpha=alpha, color='blue')
    xlabel('# donor ph.'); ylabel('# acceptor ph.')
    plt.xlim(-5,200); plt.ylim(-5,120)

def scatter_naa_nt(d, i=0, alpha=0.5):
    """Scatterplot of nt versus naa."""
    plot(d.nt[i], d.naa[i],'o', mew=0,ms=3, alpha=alpha, color='blue')
    plot(arange(200), color='k', lw=2)
    xlabel('Total burst size (nd+na+naa)'); ylabel('Accept em-ex BS (naa)')
    plt.xlim(-5,200); plt.ylim(-5,120)

def scatter_alex(d, i=0, **kwargs):
    """Scatterplot of E vs S. Keyword arguments passed to `plot`."""
    plot_style = dict(marker='o', mew=0, ms=3, alpha=0.2)
    plot_style.update(**kwargs)
    plot(d.E[i], d.S[i], 'd', **plot_style)
    xlabel("E"); ylabel('S')
    plt.xlim(-0.2,1.2); plt.ylim(-0.2,1.2)


## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  High-level plot wrappers
## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def dplot_48ch(d, fun=scatter_width_size, sharex=True, sharey=True,
        scroll=False, pgrid=True, figsize=None, AX=None, nosuptitle=False,
        scale=True, ich=None, **kwargs):
    """Plot wrapper for 48-spot measurements. Use `dplot` instead."""
    # Some function need an index of the number of calls so they are sure
    # that when idx == 0 it is thet first call of a series
    idx_funcs = [timetrace, timetrace_da, ratetrace, ratetrace_da]

    if ich is None:
        iter_ch = xrange(d.nch)
        if d.nch == 48:
            top_adjust = 0.95
            ax_ny, ax_nx = 6, 8
            if figsize is None:
                figsize = (20, 16)
        elif d.nch == 8:
            top_adjust = 0.93
            ax_ny, ax_nx = 4, 2
            if figsize is None:
                figsize = (12, 9)
    else:
        top_adjust = 0.9
        iter_ch = [ich]
        ax_ny, ax_nx = 1, 1
        if figsize is None:
            figsize = (8, 5)

    if AX is None:
        fig, AX = plt.subplots(ax_ny, ax_nx, figsize=figsize, sharex=sharex,
                               sharey=sharey, squeeze=False)
        fig.subplots_adjust(left=0.08, right=0.96, top=top_adjust,
                            bottom=0.07, wspace=0.05)
        old_ax = False
    else:
        fig = AX[0,0].figure
        old_ax = True

    for i, ich in enumerate(iter_ch):
        b = d.mburst[ich] if 'mburst' in d else None
        ax = AX.ravel()[i]
        if i == 0 and not nosuptitle:
            fig.suptitle(d.status())
        s = u'[%d]' % (ich+1)
        if 'rate_m' in d: s += (' BG=%.1fk' % (d.rate_m[ich]*1e-3))
        if b is not None: s += (', #bu=%d' %  b.shape[0])
        ax.set_title(s, fontsize=12)
        ax.grid(pgrid)
        plt.sca(ax)
        if fun in idx_funcs: kwargs.update(idx=i)
        fun(d, ich, **kwargs)
    [a.set_xlabel('') for a in AX[:-1,:].ravel()]
    [a.set_ylabel('') for a in AX[:,1:].ravel()]
    if sharex:
        plt.setp([a.get_xticklabels() for a in AX[:-1,:].ravel()], visible=False)
        [a.set_xlabel('') for a in AX[:-1,:].ravel()]
        if not old_ax: fig.subplots_adjust(hspace=0.15)
    if sharey:
        if AX.shape[1] > 1:
             plt.setp([a.get_yticklabels() for a in AX[:, 1]], visible=False)
        fig.subplots_adjust(wspace=0.08)
        if scale: ax.autoscale(enable=True, axis='y')
    s = None
    if scroll: s = ScrollingToolQT(fig)
    #s = RangeToolQT(fig)
    return AX, s

def dplot_8ch(d, fun=scatter_width_size, sharex=True,sharey=True,
        scroll=False,pgrid=True, figsize=(12,9), nosuptitle=False, AX=None,
        scale=True, **kwargs):
    """Plot wrapper for 8-spot measurements. Use `dplot` instead."""
    if AX is None:
        fig, AX = plt.subplots(4,2,figsize=figsize, sharex=sharex,
                               sharey=sharey)
        fig.subplots_adjust(left=0.08, right=0.96, top=0.93, bottom=0.07,
                wspace=0.05)
        old_ax = False
    else:
        fig = AX[0,0].figure
        old_ax = True
    for i in xrange(d.nch):
        b = d.mburst[i] if 'mburst' in d else None
        if (not fun in [timetrace, ratetrace, hist_bg_fit_single, hist_bg_fit,
            timetrace_bg]) and np.size(b) == 0:
            continue
        ax = AX.ravel()[i]
        if i == 0 and not nosuptitle:
            fig.suptitle(d.status())
        s = u'[%d]' % (i+1)
        if 'rate_m' in d: s += (' BG=%.1fk' % (d.rate_m[i]*1e-3))
        if 'T' in d: s += (u', T=%dμs' % (d.T[i]*1e6))
        if b is not None: s += (', #bu=%d' %  b.shape[0])
        ax.set_title(s, fontsize=12)
        ax.grid(pgrid)
        plt.sca(ax)
        fun(d, i, **kwargs)
        if i % 2 == 1: ax.yaxis.tick_right()
    [a.set_xlabel('') for a in AX[:-1,:].ravel()]
    [a.set_ylabel('') for a in AX[:,1:].ravel()]
    if sharex:
        plt.setp([a.get_xticklabels() for a in AX[:-1,:].ravel()], visible=False)
        [a.set_xlabel('') for a in AX[:-1,:].ravel()]
        if not old_ax: fig.subplots_adjust(hspace=0.15)
    if sharey:
        plt.setp([a.get_yticklabels() for a in AX[:,1]], visible=False)
        fig.subplots_adjust(wspace=0.08)
        if scale: ax.autoscale(enable=True, axis='y')
    s = None
    if scroll: s = ScrollingToolQT(fig)
    #s = RangeToolQT(fig)
    return AX, s

def dplot_1ch(d, fun, scroll=False, pgrid=True, ax=None,
              figsize=(9,4.5), fignum=None, nosuptitle=False, **kwargs):
    """Plot wrapper for single-spot measurements. Use `dplot` instead."""
    if ax is None:
        fig = plt.figure(num=fignum, figsize=figsize)
        ax = fig.add_subplot(111)
    else:
        fig = ax.figure
    s = d.name()
    if 'rate_m' in d: s += (' BG=%.1fk' % (d.rate_m[0]*1e-3))
    if 'T' in d: s += (u', T=%dμs' % (d.T[0]*1e6))
    if 'mburst' in d: s += (', #bu=%d' %  d.mburst[0].shape[0])
    if not nosuptitle: ax.set_title(s, fontsize=12)
    ax.grid(pgrid)
    plt.sca(ax)
    fun(d, **kwargs)
    s = None
    if scroll: s = ScrollingToolQT(fig)
    return ax, s

def dplot(d, fun, **kwargs):
    """Main plot wrapper for single and multi-spot measurements."""
    if d.nch == 1:
        return dplot_1ch(d=d, fun=fun, **kwargs)
    elif d.nch == 8:
        return dplot_8ch(d=d, fun=fun, **kwargs)
    elif d.nch == 48:
        return dplot_48ch(d=d, fun=fun, **kwargs)

##
#  Other plot wrapper functions
#

def wplot(*args, **kwargs):
    AX, s = dplot_8ch(*args, **kwargs)
    kwargs.update(AX=AX)
    q = gs.mToolQT(gcf(), dplot_8ch, *args, **kwargs)
    return AX, q

def splot(d, fun=scatter_width_size,
        scroll=False, pgrid=True, figsize=(10, 8), nosuptitle=False, ax=None,
        scale=True, **kwargs):
    if ax is None:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
    else:
        fig = ax.figure
    for i in xrange(d.nch):
        try:
            if i == 0 and not nosuptitle: fig.set_title(d.status())
        except:
            print "WARNING: No title in plots."
        ax.grid(pgrid)
        fun(d, i, **kwargs)
    s = None
    if scroll: s = ScrollingToolQT(fig)
    return ax, s

##
#  Other misc plot functions
#
def bplot(d, ich, b_index,  ph0=True, pad=0):
    """Plot a single burst in d.mburst[ich][b_index]."""
    br = bl.b_irange(d.mburst[ich], b_index, pad=pad)
    accept = d.A_em[ich][br]
    donor = -accept
    ph = d.ph_times_m[ich][br]
    if ph0: ph -= ph[0]
    dtime = (ph[donor])*d.clk_p*1e6
    atime = (ph[accept])*d.clk_p*1e6
    plt.vlines(dtime,0,1, lw=2, color='g', alpha=0.8)
    plt.vlines(atime,0,1, lw=2, color='r', alpha=0.8)
    #plot(dtime, ones_like(ph[donor]), '^', color='g', alpha=0.5)
    #plot(atime, -ones_like(ph[accept]), 'o', color='r', alpha=0.5)
    xlabel("Time (us)")
    nd, na, nt = donor.sum(), accept.sum(), ph.size
    E = float(na)/(nt)
    title("#ph = %d, #D-ph = %d, #A-ph = %d, E = %.2f" % (nt,nd,na,E))
    plt.ylim(-10,10)


def bg_legend_8ch(d):
    ax = gca()
    L = ax.get_lines()[1::2]
    for i,l in enumerate(L):
        ich = i/3
        x = i%3
        s = ['Tot', 'D', 'A']
        r = [d.rate_m[ich], d.rate_dd[ich], d.rate_ad[ich]]
        l.set_label("CH%d, %s %d cps" % (ich+1, s[x], r[x]))
    ax.legend()
    plt.draw()

def bg_legend_alex(d):
    ax = gca()
    L = ax.get_lines()[1::2]
    for i,l in enumerate(L):
        ich = i/4
        x = i%4
        s = ['Tot', 'DD', 'AD', 'AA']
        r = [d.rate_m[ich], d.rate_dd[ich], d.rate_ad[ich], d.rate_aa[ich]]
        l.set_label("CH%d, %s %d cps" % (ich+1, s[x], r[x]))
    ax.legend()
    plt.draw()