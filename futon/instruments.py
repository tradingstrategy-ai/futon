import numpy as np
from .viz import create_candle_plot

from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import gridplot
from bokeh.io import show


class Crypto:
    def __init__(
        self,
        base_asset,
        quote_asset,
        provider,
        start_date=None,
        interval="1-min",
    ):
        self.base_asset = base_asset.upper()
        self.quote_asset = quote_asset.upper()

        # Provider init
        self.provider = provider
        self.provider.validate_asset_config(base_asset, quote_asset, interval)

        # Data
        self.start_date = start_date
        self.fetch_historical_data()

    def __repr__(self):
        return "Asset(base_asset={}, quote_asset={})".format(
            self.base_asset, self.quote_asset
        )

    def fetch_historical_data(self):
        self.data = self.provider.fetch_historical_klines(self.start_date)

        inc = self.data.close > self.data.open
        dec = ~inc

        # Data sources for plotting
        self._data_source_increasing = ColumnDataSource(
            data=dict(
                timestamp=list(self.data.index[inc]),
                open=self.data.open[inc].values,
                close=self.data.close[inc].values,
                high=self.data.high[inc].values,
                low=self.data.low[inc].values,
                volume=self.data.volume[inc].values,
            )
        )
        self._data_source_decreasing = ColumnDataSource(
            data=dict(
                timestamp=list(self.data.index[dec]),
                open=self.data.open[dec].values,
                close=self.data.close[dec].values,
                high=self.data.high[dec].values,
                low=self.data.low[dec].values,
                volume=self.data.volume[dec].values,
            )
        )
        self.scaling_source = ColumnDataSource(
            data=dict(
                timestamp=list(self.data.index),
                high=self.data.high.values,
                low=self.data.low.values,
            )
        )

        self.calculate_log_returns()

    def calculate_log_returns(self):
        self.data["log_returns"] = np.log(
            self.data.close / self.data.close.shift(1)
        )

    def plot_candles(self, fig_height=1000, notebook_handle=False):
        # Candle chart
        candle_plot, volume_chart = create_candle_plot(
            self, fig_height=fig_height
        )
        return show(
            gridplot([[candle_plot], [volume_chart]]),
            notebook_handle=notebook_handle,
        )

    def plot_returns(self, kind="ts"):
        stock = ColumnDataSource(
            data=dict(open=[], close=[], high=[], low=[], index=[])
        )
        stock.data = stock.from_df(self.data)

        if kind == "ts":
            p = figure(
                plot_width=800,
                plot_height=500,
                tools="xpan",
                toolbar_location=None,
                x_axis_type="datetime",
                title="{}/{} | Returns".format(
                    self.base_asset, self.quote_asset
                ),
            )
            p.grid.grid_line_alpha = 0.3
            p.line("timestamp", "log_returns", line_color="navy", source=stock)
            p.yaxis.axis_label = "Returns"
            show(p)

        elif kind == "hs":
            hist, edges = np.histogram(
                self.data.log_returns.dropna().values,
                bins=int(np.sqrt(len(self.data))),
            )
            p = figure(
                plot_width=800,
                plot_height=500,
                tools="xpan",
                toolbar_location=None,
                x_axis_type="datetime",
                title="{}/{} | Frequency of returns".format(
                    self.base_asset, self.quote_asset
                ),
            )
            p.grid.grid_line_alpha = 0.3
            p.quad(
                top=hist,
                bottom=0,
                left=edges[:-1],
                right=edges[1:],
                fill_color="navy",
                line_color="white",
            )
            p.y_range.start = 0
            show(p)

    def mean_return(self, freq=None):
        if freq is None:
            # Daily returns
            return self.data.log_returns.mean()
        else:
            resampled_price = self.data.close.resample(freq).last()
            resampled_returns = np.log(
                resampled_price / resampled_price.shift(1)
            )
            return resampled_returns.mean()

    def std_return(self, freq=None):
        if freq is None:
            # Daily std dev
            return self.data.log_returns.std()
        else:
            resampled_price = self.data.close.resample(freq).last()
            resampled_returns = np.log(
                resampled_price / resampled_price.shift(1)
            )
            return resampled_returns.std()

    def annualized_perf(self):
        mean_return = round(self.mean_return("Y") * 100, 3)
        risk = round(self.std_return("Y") * 100, 3)
        print("Return: {}% | Risk: {}%".format(mean_return, risk))