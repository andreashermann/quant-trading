import pytz
from datetime import datetime

from zipline.algorithm import TradingAlgorithm
from zipline.utils.factory import load_bars_from_yahoo

# Load data manually from Yahoo! finance
stocks = ['AAPL']
start = datetime(2000, 1, 1, 0, 0, 0, 0, pytz.utc)
end = datetime(2012, 1, 1, 0, 0, 0, 0, pytz.utc)
data = load_bars_from_yahoo(stocks=stocks, start=start, end=end)


algo_obj = TradingAlgorithm(initialize=initialize, 
                            handle_data=handle_data)
perf_manual = algo_obj.run(data)
