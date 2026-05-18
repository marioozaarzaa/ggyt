from ggyt_bot.data.indicators import atr, ema, macd, relative_volume, rsi


def test_indicators_produce_values_with_enough_history() -> None:
    closes = [100 + i * 0.1 for i in range(240)]
    highs = [value + 1 for value in closes]
    lows = [value - 1 for value in closes]
    volumes = [100] * 220 + [150] * 20

    assert ema(closes, 20) is not None
    assert rsi(closes, 14) is not None
    assert macd(closes)[0] is not None
    assert atr(highs, lows, closes, 14) is not None
    assert relative_volume(volumes, 20) is not None
