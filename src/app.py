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
            html.Div([
                # Container for Asset selection and input fields (Left-side table)
                html.Div([
                    html.Label("Select Assets:", style={"fontWeight": "bold", "marginBottom": "5px"}),
                    dcc.Checklist(
                        id="asset-selector",
                        options=[{"label": asset, "value": asset} for asset in self.available_assets],
                        value=self.available_assets[:3],
                        inline=True,
                        style={"display": "flex", "flexWrap": "wrap", "gap": "3px", "marginBottom": "15px"}
                    ),
                    
                    # Container for Lookback Period, Start Year, End Year in one line
                    html.Div([
                        html.Div([
                            html.Label("Lookback Period:", style={"fontWeight": "bold", "marginBottom": "0px"}),
                            dcc.Input(id="lookback-input", type="number", value=30, min=1, style={"width": "100%", "marginBottom": "10px"})
                        ], style={"flex": "1", "marginRight": "10px"}),  # Flex 1 to make it take equal space

                        html.Div([
                            html.Label("Start Year:", style={"fontWeight": "bold", "marginBottom": "0px"}),
                            dcc.Input(id="start-year", type="number", value=2023, min=2000, max=2024, style={"width": "100%", "marginBottom": "10px"})
                        ], style={"flex": "1", "marginRight": "10px"}),

                        html.Div([
                            html.Label("End Year:", style={"fontWeight": "bold", "marginBottom": "0px"}),
                            dcc.Input(id="end-year", type="number", value=2024, min=2000, max=2024, style={"width": "100%", "marginBottom": "10px"})
                        ], style={"flex": "1"})
                    ], style={"display": "flex", "marginBottom": "15px"}),

                    # Buttons (Run and Stop)
                    html.Div([
                        html.Button("Run", id="run-btn", n_clicks=0, style={
                            "width": "100%", "padding": "15px", "backgroundColor": "#4CAF50", "color": "white", 
                            "border": "none", "borderRadius": "15px", "cursor": "pointer", "marginBottom": "0px", "fontSize": "16px"
                        }),
                        html.Button("Stop", id="stop-btn", n_clicks=0, style={
                            "width": "100%", "padding": "15px", "backgroundColor": "#f44336", "color": "white", 
                            "border": "none", "borderRadius": "15px", "cursor": "pointer", "fontSize": "16px"
                        })
                    ], style={"display": "flex", "flexDirection": "column", "gap": "10px"})
                ], style={
                    "padding": "20px", "backgroundColor": "#f4f4f9", "borderRadius": "8px", 
                    "boxShadow": "0 4px 8px rgba(0,0,0,0.1)", "width": "35%", "display": "inline-block", 
                    "verticalAlign": "top", "maxHeight": "500px", "overflowY": "auto", "height": "100%"
                }),

                # Plot Area (Shifted to the right and higher)
                html.Div([
                    dcc.Graph(id="individual-returns-plot", style={"height": "48vh", "marginTop": "0px"}),
                    dcc.Graph(id="combined-returns-plot", style={"height": "48vh", "marginTop": "0px"}),

                    # Update interval for plot refresh
                    dcc.Interval(id="update-interval", interval=2000, n_intervals=0, disabled=True)
                ], style={"width": "70%", "display": "inline-block", "padding": "0px", "marginLeft": "5px"})
            ], style={
                "display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"
            })
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
                fig1.update_layout(
                    title={"text": "Individual Asset Cumulative Returns", "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top"},
                    margin=dict(l=20, r=20, t=50, b=20),
                    showlegend=True
                    )
                fig1.update_xaxes(title_text="")
                fig1.update_yaxes(title_text="")

                fig2 = px.line(df.sum(axis=1), title="Combined Portfolio Cumulative Return")
                fig2.update_layout(
                    title={"text": "Combined Portfolio Cumulative Return", "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top"},
                    margin=dict(l=20, r=20, t=50, b=20),
                    showlegend=True
                )                
                fig2.update_xaxes(title_text="")
                fig2.update_yaxes(title_text="")

                return fig1, fig2
            
            return px.line(title={"text": "Individual Asset Cumulative Returns", "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top"}).update_layout(margin=dict(l=20, r=20, t=50, b=20)), px.line(title={"text": "Combined Portfolio Cumulative Return", "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top"}).update_layout(margin=dict(l=20, r=20, t=50, b=20))


    def run(self):
        self.app.run_server(debug=True)