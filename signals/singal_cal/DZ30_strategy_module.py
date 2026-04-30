import os
import sys
import logging
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger('scan_signals')


def calculate_倍量柱_arr(indicators):
    """
    计算倍量柱arr
    倍量柱条件: VOL > 参考成交量 * 1.8 AND C>O AND C>REF(C,1)
    """
    volume_arr = indicators['volume_arr']
    close_arr = indicators['close_arr']
    open_arr = indicators['open_arr']

    n = len(volume_arr)
    result = np.zeros(n, dtype=bool)
    
    for i in range(1, n):
        if volume_arr[i-1] <= volume_arr[i] / 8:
            reference_volume = volume_arr[i-2] if i >= 2 else volume_arr[i-1]
        else:
            reference_volume = volume_arr[i-1]
        
        is_bullish = close_arr[i] > open_arr[i]
        is_up = close_arr[i] > close_arr[i-1]
        is_volume_up = volume_arr[i] > reference_volume * 1.8
        
        result[i] = is_bullish and is_up and is_volume_up
    
    return result

def check_前20日非阴(indicators):
    """检查19日内最大量当天是否非阴线"""

    close_arr = indicators['close_arr']
    open_arr = indicators['open_arr']
    volume_arr = indicators['volume_arr']

    if len(volume_arr) < 20:
        return False
    
    past_18_days_vol = volume_arr[-19:-1]
    
    if len(past_18_days_vol) == 0:
        return False
    
    max_vol_idx = np.argmax(past_18_days_vol)
    highest_volume_days_ago = 18 - max_vol_idx
    
    if highest_volume_days_ago > 19:
        return False
    
    ref_idx = -highest_volume_days_ago
    
    if abs(ref_idx) > len(close_arr) or ref_idx >= 0:
        return False
    
    close_at_high = close_arr[ref_idx]
    open_at_high = open_arr[ref_idx]

    if close_at_high >= open_at_high:
        return True
    else:
        return False


def check_长短期KD(indicators):

    close = indicators['close']
    low_arr = indicators['low_arr']
    high_arr = indicators['high_arr']

    short_kd_n = 100 * (close - np.min(low_arr[-3:])) / (np.max(high_arr[-3:]) - np.min(low_arr[-3:])) if np.max(high_arr[-3:]) != np.min(low_arr[-3:]) else 50
    long_kd_n = 100 * (close - np.min(low_arr[-21:])) / (np.max(high_arr[-21:]) - np.min(low_arr[-21:])) if np.max(high_arr[-21:]) != np.min(low_arr[-21:]) else 50
    
    短期KD = short_kd_n
    print(短期KD)
    长期KD = long_kd_n
    print(长期KD)

    return 短期KD, 长期KD