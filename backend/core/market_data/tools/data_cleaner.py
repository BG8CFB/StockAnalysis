"""
数据清洗工具 (ETL)
实现 A股数据统一存储方案 中的清洗规则
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

from core.market_data.tools.field_mapper import FieldMapper
from core.market_data.models import (
    StockInfo, StockQuote, StockFinancialIndicator, 
    FinancialIncome, FinancialBalance, FinancialCashFlow
)

logger = logging.getLogger(__name__)

class DataCleaner:
    """数据清洗器"""

    @staticmethod
    def clean_stock_info(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗股票基础信息"""
        try:
            result = {}
            if source == "tushare":
                # Tushare: ts_code=000001.SZ (Standard), symbol=000001 (Raw)
                result = {
                    "symbol": data.get("ts_code"), # Standardized code
                    "code": data.get("symbol"),    # Raw code
                    "name": data.get("name"),
                    "area": data.get("area"),
                    "industry": data.get("industry"),
                    "market": data.get("market"),
                    "list_date": data.get("list_date"),
                    "list_status": data.get("list_status"),
                    "exchange": data.get("exchange"),
                    "is_hs": data.get("is_hs"),
                    "fullname": data.get("fullname"),
                    "enname": data.get("enname"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                # AKShare 字段映射
                raw_code = str(data.get("股票代码", ""))
                exchange = FieldMapper.infer_exchange(raw_code)
                standard_symbol = f"{raw_code}.{exchange}" if "." not in raw_code else raw_code
                
                list_date = str(data.get("上市时间", ""))
                # 清洗日期格式
                if len(list_date) > 8:
                    try:
                        list_date = pd.to_datetime(list_date).strftime("%Y%m%d")
                    except:
                        pass

                result = {
                    "symbol": standard_symbol,
                    "code": raw_code,
                    "name": data.get("股票简称"),
                    "industry": data.get("行业"),
                    "list_date": list_date,
                    "exchange": exchange,
                    "data_source": "akshare"
                }
            
            # 移除空值
            return {k: v for k, v in result.items() if v is not None}
        except Exception as e:
            logger.error(f"Error cleaning stock info: {e}")
            return None

    @staticmethod
    def clean_daily_quote(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗日线行情"""
        try:
            result = {}
            if source == "tushare":
                # Tushare 返回的是手，需要转换为股 (*100)
                vol = float(data.get("vol", 0) or 0)
                volume = int(vol * 100)
                
                # Tushare 返回的是千元，需要转换为元 (*1000)
                amount = float(data.get("amount", 0) or 0) * 1000

                result = {
                    "symbol": data.get("ts_code"),
                    "market": "A_STOCK", # 默认为 A 股，后续可能需要根据 symbol 修正
                    "trade_date": FieldMapper.normalize_date(str(data.get("trade_date"))),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "pre_close": data.get("pre_close"),
                    "change_pct": data.get("pct_chg"),
                    "volume": volume,
                    "amount": amount,
                    "data_source": "tushare"
                }
            elif source == "akshare":
                date_str = str(data.get("日期", ""))
                trade_date = FieldMapper.normalize_date(date_str)
                
                result = {
                    "symbol": data.get("股票代码"), # 需调用者确保已处理为标准代码
                    "market": "A_STOCK",
                    "trade_date": trade_date,
                    "open": data.get("开盘"),
                    "high": data.get("最高"),
                    "low": data.get("最低"),
                    "close": data.get("收盘"),
                    "volume": data.get("成交量"),
                    "amount": data.get("成交额"),
                    "change_pct": data.get("涨跌幅"),
                    "data_source": "akshare"
                }
            
            return result
        except Exception as e:
            logger.error(f"Error cleaning daily quote: {e}")
            return None

    @staticmethod
    def clean_financial_income(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗利润表"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "end_date": data.get("end_date"),
                    "ann_date": data.get("ann_date"),
                    "revenue": data.get("total_revenue"), # 营业总收入
                    "op_income": data.get("operate_profit"),
                    "net_profit": data.get("n_income"),
                    "basic_eps": data.get("basic_eps"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                # AKShare 字段映射 (根据文档示例)
                result = {
                    "end_date": FieldMapper.normalize_date(str(data.get("报告日", ""))),
                    "revenue": data.get("营业收入"),
                    "op_income": data.get("营业利润"),
                    "net_profit": data.get("净利润"),
                    "basic_eps": data.get("基本每股收益"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning financial income: {e}")
            return None

    @staticmethod
    def clean_financial_balance(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗资产负债表"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "end_date": data.get("end_date"),
                    "ann_date": data.get("ann_date"),
                    "total_assets": data.get("total_assets"),
                    "total_liab": data.get("total_liab"),
                    "total_share": data.get("total_share"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                result = {
                    "end_date": FieldMapper.normalize_date(str(data.get("报告日", ""))),
                    "total_assets": data.get("资产总计"),
                    "total_liab": data.get("负债合计"),
                    "total_share": data.get("股本总计"), # 需确认字段名
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning financial balance: {e}")
            return None

    @staticmethod
    def clean_financial_cashflow(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗现金流量表"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "end_date": data.get("end_date"),
                    "ann_date": data.get("ann_date"),
                    "net_cash_flows_oper_act": data.get("n_cashflow_act"),
                    "net_cash_flows_inv_act": data.get("n_cashflow_inv_act"),
                    "net_cash_flows_fnc_act": data.get("n_cashflow_fnc_act"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                result = {
                    "end_date": FieldMapper.normalize_date(str(data.get("报告日", ""))),
                    "net_cash_flows_oper_act": data.get("经营活动产生的现金流量净额"),
                    "net_cash_flows_inv_act": data.get("投资活动产生的现金流量净额"),
                    "net_cash_flows_fnc_act": data.get("筹资活动产生的现金流量净额"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning financial cashflow: {e}")
            return None

    @staticmethod
    def clean_financial_indicator(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗财务指标"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "end_date": data.get("end_date"),
                    "ann_date": data.get("ann_date"),
                    "eps": data.get("eps"),
                    "bps": data.get("bps"),
                    "roe": data.get("roe"),
                    "roa": data.get("roa"),
                    "gross_margin": data.get("gross_margin"),
                    "net_margin": data.get("netprofit_margin"),
                    "current_ratio": data.get("current_ratio"),
                    "quick_ratio": data.get("quick_ratio"),
                    "debt_to_assets": data.get("debt_to_assets"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                # AKShare 需确认具体接口返回字段
                result = {
                    "end_date": FieldMapper.normalize_date(str(data.get("报告日", ""))),
                    "eps": data.get("基本每股收益"),
                    "bps": data.get("每股净资产"),
                    "roe": data.get("净资产收益率"),
                    "gross_margin": data.get("销售毛利率"),
                    "net_margin": data.get("销售净利率"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning financial indicator: {e}")
            return None

    @staticmethod
    def clean_daily_indicator(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗每日指标"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "trade_date": data.get("trade_date"),
                    "pe": data.get("pe"),
                    "pe_ttm": data.get("pe_ttm"),
                    "pb": data.get("pb"),
                    "ps_ttm": data.get("ps_ttm"),
                    "dv_ttm": data.get("dv_ttm"),
                    "total_mv": data.get("total_mv"),
                    "circ_mv": data.get("circ_mv"),
                    "turnover_rate": data.get("turnover_rate"),
                    "turnover_rate_f": data.get("turnover_rate_f"),
                    "volume_ratio": data.get("volume_ratio"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                result = {
                    "trade_date": FieldMapper.normalize_date(str(data.get("date", ""))),
                    "pe_ttm": data.get("pe_ttm"),
                    "pb": data.get("pb"),
                    "dv_ttm": data.get("dv_ttm"),
                    "total_mv": data.get("total_mv"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning daily indicator: {e}")
            return None

    @staticmethod
    def clean_minute_quote(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗分钟行情"""
        try:
            result = {}
            # 分钟数据通常来源于实时接口或特定历史接口
            if source == "tushare":
                # Tushare pro bar 接口
                result = {
                    "symbol": data.get("ts_code"),
                    "trade_time": data.get("trade_time"),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "vol": data.get("vol"),
                    "amount": data.get("amount"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                # AKShare 分钟数据
                result = {
                    "trade_time": data.get("day"), # 需转换为标准格式
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "vol": data.get("volume"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning minute quote: {e}")
            return None

    @staticmethod
    def clean_stock_money_flow(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗资金流向"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "symbol": data.get("ts_code"),
                    "trade_date": data.get("trade_date"),
                    "buy_sm_vol": data.get("buy_sm_vol"),
                    "net_mf_vol": data.get("net_mf_vol"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                result = {
                    "trade_date": FieldMapper.normalize_date(str(data.get("date", ""))),
                    "net_mf_vol": data.get("主力净流入"), # 示例字段
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning stock money flow: {e}")
            return None

    @staticmethod
    def clean_hsgt_money_flow(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗沪深港通资金流向"""
        try:
            result = {}
            if source == "tushare":
                result = {
                    "trade_date": data.get("trade_date"),
                    "north_money": data.get("north_money"),
                    "south_money": data.get("south_money"),
                    "hgt": data.get("hgt"),
                    "sgt": data.get("sgt"),
                    "data_source": "tushare"
                }
            elif source == "akshare":
                result = {
                    "trade_date": FieldMapper.normalize_date(str(data.get("date", ""))),
                    "north_money": data.get("北向资金"),
                    "south_money": data.get("南向资金"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning hsgt money flow: {e}")
            return None

    @staticmethod
    def clean_stock_top_list(data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """清洗龙虎榜数据"""
        try:
            result = {}
            if source == "akshare":
                # 假设字段映射
                result = {
                    "symbol": data.get("代码"), # 需后续处理为symbol
                    "trade_date": FieldMapper.normalize_date(str(data.get("日期", ""))),
                    "name": data.get("名称"),
                    "close": data.get("收盘价"),
                    "pct_chg": data.get("涨跌幅"),
                    "net_amount": data.get("净买入额"),
                    "buy_amount": data.get("买入额"),
                    "sell_amount": data.get("卖出额"),
                    "reason": data.get("上榜原因"),
                    "data_source": "akshare"
                }
            return result
        except Exception as e:
            logger.error(f"Error cleaning stock top list: {e}")
            return None
