"""
统一指标计算器

提供标准化的技术指标计算接口
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class IndicatorsCalculator:
    """
    技术指标计算器
    
    提供统一的指标计算接口，支持信号系统和回测系统
    """
    
    def calculate(self, df: pd.DataFrame, code: str) -> Optional[Dict[str, Any]]:
        """
        计算所有技术指标
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            code: 股票代码
        
        Returns:
            包含所有指标的字典
        """
        if df is None or len(df) < 60:
            return None
        
        close_arr = df['close'].values
        open_arr = df['open'].values
        high_arr = df['high'].values
        low_arr = df['low'].values
        volume_arr = df['volume'].values
        volume_arr = np.nan_to_num(volume_arr, nan=0)
        
        close = close_arr[-1]
        open_price = open_arr[-1]
        high = high_arr[-1]
        low = low_arr[-1]
        volume = volume_arr[-1]
        
        n = len(close_arr)
        
        prev_close = close_arr[-2] if n >= 2 else close_arr[-1]
        涨幅 = (close_arr[-1] - prev_close) / prev_close * 100 if prev_close != 0 else 0
        振幅 = (high_arr[-1] - low_arr[-1]) / prev_close * 100 if prev_close != 0 else 0
        
        波幅 = np.mean(np.abs(high_arr[-30:] - low_arr[-30:]))
        波动率 = 波幅 / prev_close * 100 if prev_close != 0 else 0
        涨跌幅 = (close - prev_close) / prev_close * 100 if prev_close != 0 else 0
        大长阳 = close > open_price and 涨跌幅 > 波动率 * 1.5 and 涨跌幅 > 2
        大长阴 = close < open_price and abs(涨跌幅) > 波动率 * 1.1 and abs(涨跌幅) > 2
        参考成交量 = volume_arr[-2] if volume_arr[-1] <= volume / 8 else volume_arr[-1]
        关键K = close > close_arr[-2] and volume > 参考成交量 * 1.8 and 大长阳 and volume > np.mean(volume_arr[-40:]) if len(volume_arr) >= 40 else False
        暴力K = close > close_arr[-2] and volume > 参考成交量 * 1.8 and 涨跌幅 > 4 and (high - max(close, open_price)) <= (high - open_price) / 4 and volume > np.mean(volume_arr[-60:]) if len(volume_arr) >= 60 else False
        
        ma5 = np.mean(close_arr[-5:]) 
        ma10 = np.mean(close_arr[-10:]) 
        ma14 = np.mean(close_arr[-14:]) 
        ma20 = np.mean(close_arr[-20:]) 
        ma28 = np.mean(close_arr[-28:]) 
        ma30 = np.mean(close_arr[-30:]) 
        ma50 = np.mean(close_arr[-50:]) 
        ma57 = np.mean(close_arr[-57:]) 
        ma60 = np.mean(close_arr[-60:]) 
        ma114 = np.mean(close_arr[-114:]) 
        
        ma3 = np.mean(close_arr[-3:])
        ma6 = np.mean(close_arr[-6:])
        ma12 = np.mean(close_arr[-12:])
        ma24 = np.mean(close_arr[-24:])
        
        vol_ma5 = np.mean(volume_arr[-5:]) if n >= 5 else volume_arr[-1]
        vol_ma10 = np.mean(volume_arr[-10:]) if n >= 10 else volume_arr[-1]
        vol_ma20 = np.mean(volume_arr[-20:]) if n >= 20 else volume_arr[-1]
        vol_ma60 = np.mean(volume_arr[-60:]) if n >= 60 else volume_arr[-1]
        
        dif_arr = self._calculate_dif_array(close_arr)
        dif = dif_arr[-1]
        
        知行短期趋势线 = self._calculate_知行短期趋势线(close_arr)
        知行多空线 = (ma14 + ma28 + ma57 + ma114) / 4
        
        dea = 0
        if len(dif_arr) >= 9:
            dea = np.mean(dif_arr[-9:])
        
        macd = (dif - dea) * 2
        
        k, d, j = self._calculate_kdj(close_arr, high_arr, low_arr)
        
        rsi1 = self._calculate_rsi(close_arr, 6)
        rsi2 = self._calculate_rsi(close_arr, 12)
        rsi3 = self._calculate_rsi(close_arr, 24)
        rsi4 = self._calculate_rsi(close_arr, 50)
        
        bbi = (ma3 + ma6 + ma12 + ma24) / 4
        前20日BBI = np.mean([bbi] * 20) if n >= 20 else bbi
        
        return {
            'code': code,
            'close': close,
            'open': open_price,
            'high': high,
            'low': low,
            'volume': volume,
            'close_arr': close_arr,
            'open_arr': open_arr,
            'high_arr': high_arr,
            'low_arr': low_arr,
            'volume_arr': volume_arr,
            '涨幅': 涨幅,
            '振幅': 振幅,
            '大长阳': 大长阳,
            '大长阴': 大长阴,
            '关键K': 关键K,
            '暴力K': 暴力K,
            'ma5': ma5,
            'ma10': ma10,
            'ma14': ma14,
            'ma20': ma20,
            'ma28': ma28,
            'ma30': ma30,
            'ma50': ma50,
            'ma57': ma57,
            'ma60': ma60,
            'ma114': ma114,
            'ma3': ma3,
            'ma6': ma6,
            'ma12': ma12,
            'ma24': ma24,
            'vol_ma5': vol_ma5,
            'vol_ma10': vol_ma10,
            'vol_ma20': vol_ma20,
            'vol_ma60': vol_ma60,
            'dif': dif,
            'dif_arr': dif_arr,
            'dea': dea,
            'macd': macd,
            'k': k,
            'd': d,
            'j': j,
            'rsi1': rsi1,
            'rsi2': rsi2,
            'rsi3': rsi3,
            'rsi4': rsi4,
            '知行短期趋势线': 知行短期趋势线,
            '知行多空线': 知行多空线,
            'bbi': bbi,
            '前20日BBI': 前20日BBI,
        }
    
    def _calculate_dif_array(self, close_arr: np.ndarray) -> np.ndarray:
        """计算 DIF 数组"""
        dif_arr = []
        for idx in range(len(close_arr)):
            c = close_arr[idx]
            ema12_i = c
            ema26_i = c
            for j in range(1, min(13, idx + 1)):
                ema12_i = ema12_i * (2/13) + close_arr[idx - j] * (1 - 2/13)
            for j in range(1, min(27, idx + 1)):
                ema26_i = ema26_i * (2/27) + close_arr[idx - j] * (1 - 2/27)
            dif_arr.append(ema12_i - ema26_i)
        return np.array(dif_arr)
    
    def _calculate_知行短期趋势线(self, close_arr: np.ndarray) -> float:
        """计算知行短期趋势线"""
        ema10_1 = close_arr[-1]
        for i in range(2, 11):
            if i < len(close_arr):
                ema10_1 = ema10_1 * (2/11) + close_arr[-i] * (1 - 2/11)
        ema10_2 = ema10_1
        for i in range(2, 11):
            if i < len(close_arr):
                ema10_2 = ema10_2 * (2/11) + ema10_1 * (1 - 2/11)
        return ema10_2
    
    def _calculate_kdj(
        self,
        close_arr: np.ndarray,
        high_arr: np.ndarray,
        low_arr: np.ndarray,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> tuple:
        """计算 KDJ 指标"""
        k_arr = []
        d_arr = []
        j_arr = []
        
        for i in range(len(close_arr)):
            start = max(0, i - n + 1)
            low_n = np.min(low_arr[start:i+1])
            high_n = np.max(high_arr[start:i+1])
            
            if high_n != low_n:
                rsv = (close_arr[i] - low_n) / (high_n - low_n) * 100
            else:
                rsv = 50
            
            if i == 0:
                k = rsv
                d = rsv
            else:
                k = (2/3) * k_arr[-1] + (1/3) * rsv
                d = (2/3) * d_arr[-1] + (1/3) * k
            
            j = 3 * k - 2 * d
            
            k_arr.append(k)
            d_arr.append(d)
            j_arr.append(j)
        
        return k_arr[-1], d_arr[-1], j_arr[-1]
    
    def _calculate_rsi(self, close_arr: np.ndarray, period: int = 14) -> float:
        """计算 RSI 指标"""
        if len(close_arr) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            diff = close_arr[-i] - close_arr[-i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses) if np.mean(losses) != 0 else 0.001
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
