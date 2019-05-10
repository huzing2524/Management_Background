# -*- coding: utf-8 -*-

BG_QUEUE_NAME = "DSD-ERL-Backend"  # RabbitMQ routing_key

RIGHTS_LIST = [
    {"key": "1", "value": "超级管理员"},
    {"key": "2", "value": "高级管理员"},
    {"key": "3", "value": "市场部"},
    {"key": "4", "value": "财务部"},
    {"key": "5", "value": "采购部"},
    {"key": "6", "value": "客户管理"},
    {"key": "7", "value": "生产部"},
    {"key": "8", "value": "权限管理"},
    {"key": "9", "value": "仓库部"},
]

RIGHTS_DICT = {
    "1": "超级管理员",
    "2": "高级管理员",
    "3": "订单",
    # "4": "财务部",
    "5": "采购",
    # "6": "客户管理",
    "7": "生产",
    "8": "权限管理",
    "9": "仓库"
}

EDIT_RIGHTS_LIST = [
    {"key": "3", "value": "订单"},
    # {"key": "4", "value": "财务部"},
    {"key": "5", "value": "采购"},
    # {"key": "6", "value": "客户管理"},
    {"key": "7", "value": "生产"},
    {"key": "8", "value": "权限管理"},
    {"key": "9", "value": "仓库"},
]

INDUSTRY_PLUS_LIST = [
    {"key": "1", "value": "数据可视化"},
    {"key": "2", "value": "数据分析"},
    {"key": "3", "value": "机器代替人工"},
    {"key": "4", "value": "机器远程控制"},
    {"key": "5", "value": "智能预测、预警"},
]

INDUSTRY_PLUS_SCORE_DICT = {
    "1": 10.34,  # 数据可视化
    "2": 15.45,  # 数据分析
    "3": 20.56,  # 机器替代人工
    "4": 25.67,  # 机器远程控制
    "5": 27.98  # 智能预测、预警
}

# 正式：2019-3-16 00:00:00
START_TIME = 1552665600
# 测试：2018.9.1
# START_TIME = 1535731200
