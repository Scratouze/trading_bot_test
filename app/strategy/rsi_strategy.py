import pandas as pd

class RsiStrategy:
    def __init__(self, rsi_low=30, rsi_high=70):
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high

    def signal(self, df: pd.DataFrame) -> str:
        df['change'] = df['close'].diff()
        df['gain'] = df['change'].clip(lower=0)
        df['loss'] = -df['change'].clip(upper=0)
        avg_gain = df['gain'].rolling(14).mean()
        avg_loss = df['loss'].rolling(14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        latest_rsi = df['rsi'].iloc[-1]

        if latest_rsi < self.rsi_low:
            return 'BUY'
        elif latest_rsi > self.rsi_high:
            return 'SELL'
        return None
