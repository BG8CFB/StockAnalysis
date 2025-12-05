from fastapi import APIRouter, Depends
from typing import Any, Dict
from datetime import datetime
import random

from core.auth.dependencies import get_current_active_user
from core.auth.models import User

# 创建路由器
router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取仪表盘概览数据"""

    # 模拟数据 - 在实际应用中这些数据应该从数据库或其他服务获取
    summary_data = {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "last_login": current_user.last_login
        },
        "system_stats": {
            "total_users": 1247,
            "active_users": 89,
            "total_stocks_analyzed": 15420,
            "analysis_requests_today": 342
        },
        "portfolio_summary": {
            "total_value": 156789.32,
            "daily_change": 2345.67,
            "daily_change_percent": 1.52,
            "total_return": 12890.45,
            "total_return_percent": 8.96
        },
        "market_overview": {
            "market_status": "open" if datetime.now().hour >= 9 and datetime.now().hour <= 15 else "closed",
            "major_indices": [
                {
                    "name": "上证指数",
                    "value": 3124.67,
                    "change": 15.23,
                    "change_percent": 0.49
                },
                {
                    "name": "深证成指",
                    "value": 10234.56,
                    "change": -23.45,
                    "change_percent": -0.23
                },
                {
                    "name": "创业板指",
                    "value": 2045.78,
                    "change": 8.92,
                    "change_percent": 0.44
                }
            ],
            "hot_sectors": [
                {"name": "新能源", "change_percent": 3.45, "stocks_count": 127},
                {"name": "人工智能", "change_percent": 2.78, "stocks_count": 89},
                {"name": "生物医药", "change_percent": 1.92, "stocks_count": 156}
            ]
        },
        "recent_activities": [
            {
                "id": "1",
                "type": "analysis_completed",
                "title": "股票分析完成",
                "description": "贵州茅台 (600519) 分析报告已生成",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "2",
                "type": "alert_triggered",
                "title": "价格预警触发",
                "description": "宁德时代 (300750) 价格突破 450 元",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "3",
                "type": "portfolio_update",
                "title": "投资组合更新",
                "description": "已新增 比亚迪 (002594) 到观察列表",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "performance_metrics": {
            "weekly_returns": [1.2, -0.8, 2.1, 1.5, -0.3, 0.9, 1.8],
            "monthly_comparison": {
                "current_month": 5.67,
                "previous_month": 3.45,
                "change": 2.22
            }
        }
    }

    return summary_data


@router.get("/charts/portfolio")
async def get_portfolio_chart_data(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取投资组合图表数据"""

    # 模拟时间序列数据
    import pandas as pd
    from datetime import datetime, timedelta

    # 生成过去30天的数据
    dates = []
    values = []
    base_value = 100000

    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        dates.append(date.strftime('%Y-%m-%d'))
        # 模拟每日波动
        daily_change = random.uniform(-0.03, 0.03)
        base_value *= (1 + daily_change)
        values.append(round(base_value, 2))

    return {
        "dates": dates,
        "values": values,
        "benchmark": [100000 + i * 1000 for i in range(30)]  # 基准数据
    }


@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取用户通知"""

    notifications = [
        {
            "id": "1",
            "type": "info",
            "title": "系统公告",
            "message": "系统将于今晚23:00进行维护，预计持续1小时",
            "read": False,
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "id": "2",
            "type": "success",
            "title": "分析完成",
            "message": "您的股票分析请求已完成，请查看报告",
            "read": False,
            "timestamp": "2024-01-15T09:15:00Z"
        },
        {
            "id": "3",
            "type": "warning",
            "title": "价格预警",
            "message": "关注股票价格已达到预警阈值",
            "read": True,
            "timestamp": "2024-01-14T15:45:00Z"
        }
    ]

    return {"notifications": notifications, "unread_count": 2}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """标记通知为已读"""

    return {"message": "Notification marked as read"}