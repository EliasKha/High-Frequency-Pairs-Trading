import os
import threading
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.express as px

from .strategy import Strategy
from .backtest import Backtest
from .data_manager import DataManager

class App:
    def __init__(self):
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.available_assets = self.get_available_assets()
        self.backtest = None
        self.stop_event = threading.Event()
        self.layout()
        self.callbacks()

    def get_available_assets(self):
        return ['eurusd', 'eurchf', 'eurgbp', 'eurjpy', 'euraud', 'usdcad', 'usdchf', 'usdjpy', 'usdmxn', 'gbpchf', 'gbpjpy',
                'gbpusd', 'audjpy', 'audusd', 'chfjpy', 'nzdjpy', 'nzdusd', 'xauusd', 'eurcad', 'audcad', 'cadjpy', 'eurnzd',
                'grxeur', 'nzdcad', 'sgdjpy', 'usdhkd', 'usdnok', 'usdtry', 'xauaud', 'audchf', 'auxaud', 'eurhuf', 'eurpln',
                'frxeur', 'hkxhkd', 'nzdchf', 'spxusd', 'usdhuf', 'usdpln', 'usdzar', 'xauchf', 'zarjpy', 'bcousd', 'etxeur',
                'eurczk', 'eursek', 'gbpaud', 'gbpnzd', 'jpxjpy', 'udxusd', 'usdczk', 'usdsek', 'wtiusd', 'xaueur', 'audnzd',
                'cadchf', 'eurdkk', 'eurnok', 'eurtry', 'gbpcad', 'nsxusd', 'ukxgbp', 'usddkk', 'usdsgd', 'xagusd', 'xaugbp']

    def layout(self):
        self.app.layout = html.Div([
            html.H1("FX Backtest Platform", style={"textAlign": "center", "marginBottom": "40px"}),

            html.Div([
                html.Div([
                    html.Label("Select Assets:"),
                    dcc.Checklist(
                        id="asset-selector",
                        options=[{"label": asset, "value": asset} for asset in self.available_assets],
                        value=self.available_assets[:3],
                        inline=True
                    ),

                    html.Label("Lookback Period:"),
                    dcc.Input(id="lookback-input", type="number", value=30, min=1),

                    html.Label("Start Year:"),
                    dcc.Input(id="start-year", type="number", value=2023, min=2000, max=2024),

                    html.Label("End Year:"),
                    dcc.Input(id="end-year", type="number", value=2024, min=2000, max=2024),

                    html.Button("Run Backtest", id="run-btn", n_clicks=0),
                    html.Button("Stop Backtest", id="stop-btn", n_clicks=0, style={"marginTop": "10px", "backgroundColor": "red", "color": "white"})
                ], style={"width": "30%", "padding": "20px"}),

                html.Div([
                    dcc.Graph(id="individual-returns-plot"),
                    dcc.Graph(id="combined-returns-plot"),
                    dcc.Interval(id="update-interval", interval=2000, n_intervals=0, disabled=True)
                ], style={"width": "65%", "padding": "20px"})
            ], style={"display": "flex", "justifyContent": "space-between"})
        ])

    def callbacks(self):
        @self.app.callback(
            Output("update-interval", "disabled"),
            Input("run-btn", "n_clicks"),
            Input("stop-btn", "n_clicks"),
            State("asset-selector", "value"),
            State("lookback-input", "value"),
            State("start-year", "value"),
            State("end-year", "value")
        )

        def manage_backtest(run_clicks, stop_clicks, selected_assets, lookback, start_year, end_year):
            ctx = callback_context
            if not ctx.triggered:
                return True 
            
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if triggered_id == "run-btn":
                self.stop_event.clear()
                os.makedirs("backtests", exist_ok=True)
                os.makedirs("data", exist_ok=True)

                filename = f"backtests/backtest_{lookback}_{start_year}_{end_year}.csv"
                
                data_manager = DataManager(fx_pairs=selected_assets, years=range(start_year, end_year))
                data_manager.download_missing_files()
                
                fx_data = data_manager.load_fx_data()

                strategy = Strategy(lookback=lookback)
                self.backtest = Backtest(fx_data, strategy, filename, self.stop_event)

                threading.Thread(target=self.backtest.execute, daemon=True).start()
                return False 
            
            elif triggered_id == "stop-btn":
                self.stop_event.set()
                return True
            
            return True


        @self.app.callback(
            [Output("individual-returns-plot", "figure"), Output("combined-returns-plot", "figure")],
            Input("update-interval", "n_intervals")
        )
        def update_plots(n_intervals):
            if self.backtest and hasattr(self.backtest, "results") and not self.backtest.results.empty:
                df = self.backtest.results.cumsum()
                fig1 = px.line(df, title="Individual Asset Cumulative Returns")
                fig2 = px.line(df.sum(axis=1), title="Combined Portfolio Cumulative Return")
                return fig1, fig2
            return px.line(title="No Data"), px.line(title="No Data")

    def run(self):
        self.app.run_server(debug=True)