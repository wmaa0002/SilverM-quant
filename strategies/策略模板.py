"""
策略模板 - 基于打分系统的买入策略模板
继承BaseStrategy，使用@register装饰器注册

使用示例:
    from strategies.策略模板 import TemplateStrategy
    # 通过Registry加载策略
    from strategies.registry import Registry
    registry = Registry()
    strategy_class = registry.get('策略模板')
"""

import numpy as np
from datetime import datetime

from strategies.registry import register
from strategies.base.framework_strategy import BaseStrategy


STRATEGY_METADATA = {
    'name': '策略模板',
    'description': '新策略模板 - 基于打分系统的买入策略',
    'author': 'Your Name',
    'version': '1.0.0',
    'min_data_days': 60,
    'threshold_required': True,
}


@register(name='策略模板', threshold_required=True, min_data_days=60, description='新策略模板')
class TemplateStrategy(BaseStrategy):
    """策略模板类 - TODO: 修改为你的策略描述"""

    params = (
        ('threshold', 8.0),
        ('stop_loss_pct', 0.03),
        ('多空线缓冲', True),
    )

    def __init__(self):
        super().__init__()
        self.close = self.data.close
        self.open = self.data.open
        self.high = self.data.high
        self.low = self.data.low
        self.volume = self.data.volume
        self.entry_price = None
        self.order = None
        self.s1_half_sold = False
        self.pending_buy_reason = ""
        self.pending_sell_reason = ""
        self.pending_sell_half = False
        self.trade_records = []
        self.prev_k = None
        self.prev_d = None
        self.current_buy_score = 0
        self.current_s1_score = 0

    def calculate_score(self) -> float:
        """计算策略总分"""
        score = self._calculate_buy_score()
        self.current_buy_score = score
        return score

    def _calculate_buy_score(self) -> float:
        """计算买入分数 - TODO: 替换为你的打分逻辑"""
        score = 0.0
        k, d, j = self._calculate_kdj()
        if j < 13:
            score += 2.0
        if self._calculate_dif() > 0:
            score += 1.0
        if self._calculate_rsi() < 30:
            score += 2.0
        if self.volume[0] > self._calculate_ma(60):
            score += 2.0
        if len(self) >= 2:
            pct = (self.close[0] - self.close[-1]) / self.close[-1] * 100
            if pct > 3.0:
                score += 1.0
        return score

    def buy_condition(self) -> bool:
        """买入条件: 非ST股 AND 分数 >= threshold"""
        if 'ST' in self.data._name or '*ST' in self.data._name:
            return False
        return self.calculate_score() >= self.params.threshold

    def sell_condition(self) -> bool:
        """卖出条件: S1评分模式"""
        if not self.position:
            return False
        s1_score, signal_full, signal_half = self._calculate_s1_score()
        self.current_s1_score = s1_score
        if signal_full:
            self.pending_sell_reason = f"S1全卖:S1={s1_score:.1f}"
            self.s1_half_sold = True
            return True
        if signal_half:
            self.pending_sell_reason = f"S1半卖:S1={s1_score:.1f}"
            self.pending_sell_half = True
            return True
        if self.entry_price:
            loss_pct = (self.close[0] - self.entry_price) / self.entry_price
            if loss_pct < -self.params.stop_loss_pct:
                self.pending_sell_reason = f"止损:亏损{loss_pct*100:.1f}%"
                return True
        return False

    def _calculate_s1_score(self) -> tuple:
        """计算S1卖出评分"""
        close = self.close[0]
        high = self.high[0]
        open_price = self.open[0]
        volume = self.volume[0]
        close_arr = np.array(self.close.array[:len(self)])
        high_arr = np.array(self.high.array[:len(self)])
        volume_arr = np.array(self.volume.array[:len(self)])
        dif = self._calculate_dif()
        k, d, j = self._calculate_kdj()

        前10日涨幅 = (close / close_arr[-10] - 1) * 100 if len(close_arr) >= 10 else 0
        前50日涨幅 = (close / close_arr[-50] - 1) * 100 if len(close_arr) >= 50 else 0

        条件1基础 = (close < open_price) and (high == np.max(high_arr[-60:])) and (前10日涨幅 > 10 or 前50日涨幅 > 50)
        条件1评分 = 0
        if 条件1基础:
            hhv_vol = np.max(volume_arr[-60:])
            if volume >= hhv_vol:
                条件1评分 = 10
            elif volume * 1.42 >= hhv_vol:
                条件1评分 = 6.5

        条件1 = 条件1基础 and (volume * 1.42 >= np.max(volume_arr[-60:]))

        条件2基础 = False
        if len(high_arr) >= 60:
            hhv_h_4 = np.max(high_arr[-4:])
            hhv_h_60 = np.max(high_arr[-60:])
            if hhv_h_4 == hhv_h_60 and high != hhv_h_60:
                vol_ma5 = np.mean(volume_arr[-5:])
                涨幅 = (close - close_arr[-2]) / close_arr[-2] * 100 if close_arr[-2] != 0 else 0
                if (volume > vol_ma5) and 涨幅 < -0.03 and close < open_price:
                    条件2基础 = True

        条件2评分 = 0
        前3天最高位距今 = 0
        if len(high_arr) >= 3:
            recent_3 = high_arr[-3:]
            前3天最高位距今 = 2 - np.argmax(recent_3)

        if 条件2基础:
            ref_vol = volume_arr[-前3天最高位距今-1] if 前3天最高位距今 > 0 else volume_arr[-1]
            if volume >= ref_vol * 1.20:
                条件2评分 = 12
            elif volume >= ref_vol * 0.80:
                条件2评分 = 7.8

        dif_history = []
        for i in range(len(close_arr)):
            hist_close = close_arr[-i-1] if i < len(close_arr) else close
            hist_ema12 = hist_close
            for j_idx in range(1, min(13, i+1)):
                if i+j_idx < len(close_arr):
                    hist_ema12 = hist_ema12 * (11/13) + close_arr[-i-1-j_idx] * (2/13)
            hist_ema26 = hist_close
            for j_idx in range(1, min(27, i+1)):
                if i+j_idx < len(close_arr):
                    hist_ema26 = hist_ema26 * (25/27) + close_arr[-i-1-j_idx] * (2/27)
            dif_history.append(hist_ema12 - hist_ema26)

        hhv_dif_60 = np.max(dif_history[-60:]) if len(dif_history) >= 60 else dif

        加分1 = 1 if (条件1 and dif < hhv_dif_60) else 0
        实体 = open_price - close
        上影线 = high - max(close, open_price)
        加分2 = 0.5 if (条件1 and 上影线 > 实体 / 2 and close > close_arr[-1]) else 0
        加分3 = 1.8 if 条件2 else 0
        加分4 = 0.8 if (条件2 and j < k < d) else 0
        加分5 = 2 if (条件1 or 条件2) and close < close_arr[-1] else 0

        天量柱 = len(volume_arr) >= 2 and (volume_arr[-1] > volume_arr[-2] * 1.8) and (volume >= volume_arr[-1] * 1.8)
        加分6 = 3 if 天量柱 else 0

        score_s1 = 条件1评分 + 条件2评分 + 加分1 + 加分2 + 加分3 + 加分4 + 加分5 + 加分6
        return (score_s1, score_s1 > 10, score_s1 > 5 and not self.s1_half_sold)

    def _calculate_dif(self) -> float:
        return self.calculate_dif()

    def _calculate_rsi(self, period: int = 14) -> float:
        return self.calculate_rsi(period)

    def _calculate_kdj(self) -> tuple:
        return self.calculate_kdj()

    def _calculate_ma(self, period: int) -> float:
        return self.calculate_ma(period)

    def _calculate_short_trend_line(self) -> float:
        if len(self) < 5:
            return self.close[0]
        close_arr = np.array(self.close.array[:len(self)])
        return np.mean(close_arr[-5:])

    def _calculate_multilevel_line(self) -> float:
        if len(self) < 20:
            return self.close[0]
        close_arr = np.array(self.close.array[:len(self)])
        return np.mean(close_arr[-20:])

    def notify_order(self, order):
        if order.status in [order.Completed]:
            date = self.datas[0].datetime.datetime(0)
            if order.isbuy():
                self.entry_price = order.executed.price
                self._record_trade({
                    'date': date, 'action': 'BUY', 'price': order.executed.price,
                    'size': order.executed.size, 'reason': self.pending_buy_reason,
                })
            elif order.issell():
                pnl = (order.executed.price - self.entry_price) / self.entry_price * 100 if self.entry_price else 0
                if self.pending_sell_half:
                    self.s1_half_sold = True
                    self.pending_sell_half = False
                self._record_trade({
                    'date': date, 'action': 'SELL', 'price': order.executed.price,
                    'size': order.executed.size, 'pnl': pnl, 'reason': self.pending_sell_reason,
                })
                self.entry_price = None
            self.order = None

    def _record_trade(self, trade_record: dict):
        self.trade_records.append(trade_record)
        if self.params.debug_mode:
            print(f"交易: {trade_record['date']} {trade_record['action']} 价格:{trade_record['price']:.2f}")

    def get_trade_records(self) -> list:
        return self.trade_records
