#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revit API 工具模块

提供与 Revit pyRevit 扩展通信的函数。
这些函数会被 AI 代理调用来创建和查询建筑构件。
"""

import json
import urllib.request
from typing import Dict, Any, List, Optional

# Revit API 服务器地址
REVIT_API_URL = "http://localhost:48884/vibe-building"


def _make_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """发送 HTTP 请求到 Revit API"""
    url = f"{REVIT_API_URL}/{endpoint}"

    if data is not None:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={'Content-Type': 'application/json'},
            method=method
        )
    else:
        req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e), "status": "error"}


def health_check() -> Dict[str, Any]:
    """检查 Revit API 连接状态"""
    return _make_request("health")


def get_levels() -> List[Dict[str, Any]]:
    """获取所有标高"""
    result = _make_request("model/levels")
    return result.get("levels", [])


def list_walls() -> List[Dict[str, Any]]:
    """列出所有墙体"""
    result = _make_request("walls")
    return result.get("walls", [])


def create_wall(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    height: float = 3.0,
    level: str = "Level 1"
) -> Dict[str, Any]:
    """
    创建一面墙体

    Args:
        start_x: 起点 X 坐标（米）
        start_y: 起点 Y 坐标（米）
        end_x: 终点 X 坐标（米）
        end_y: 终点 Y 坐标（米）
        height: 墙体高度（米），默认 3.0
        level: 标高名称，默认 "Level 1"

    Returns:
        创建结果字典
    """
    data = {
        "start": {"x": start_x, "y": start_y, "z": 0},
        "end": {"x": end_x, "y": end_y, "z": 0},
        "height": height,
        "level": level
    }
    return _make_request("walls", method="POST", data=data)


def create_room(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    height: float = 3.0,
    level: str = "Level 1"
) -> Dict[str, Any]:
    """
    创建一个矩形房间（4面墙）

    Args:
        x1: 房间左下角 X 坐标（米）
        y1: 房间左下角 Y 坐标（米）
        x2: 房间右上角 X 坐标（米）
        y2: 房间右上角 Y 坐标（米）
        height: 墙体高度（米），默认 3.0
        level: 标高名称，默认 "Level 1"

    Returns:
        创建结果字典，包含所有墙体的 ID
    """
    # 创建4面墙
    walls = []

    # 底墙 (y = y1)
    wall1 = create_wall(x1, y1, x2, y1, height, level)
    walls.append(wall1)

    # 右墙 (x = x2)
    wall2 = create_wall(x2, y1, x2, y2, height, level)
    walls.append(wall2)

    # 顶墙 (y = y2)
    wall3 = create_wall(x2, y2, x1, y2, height, level)
    walls.append(wall3)

    # 左墙 (x = x1)
    wall4 = create_wall(x1, y2, x1, y1, height, level)
    walls.append(wall4)

    width = abs(x2 - x1)
    depth = abs(y2 - y1)

    return {
        "success": all(w.get("success") for w in walls),
        "room_dimensions": f"{width:.1f}m x {depth:.1f}m",
        "area_sqm": width * depth,
        "walls": walls,
        "wall_count": len(walls)
    }


def delete_wall(wall_id: int) -> Dict[str, Any]:
    """删除指定 ID 的墙体"""
    return _make_request(f"walls/{wall_id}", method="DELETE")


def delete_all_walls() -> Dict[str, Any]:
    """删除所有墙体"""
    return _make_request("walls/all", method="DELETE")


def get_wall_types() -> List[Dict[str, Any]]:
    """获取所有墙体类型"""
    result = _make_request("wall-types")
    return result.get("wall_types", [])


# 便捷函数
def create_square_room(
    center_x: float,
    center_y: float,
    size: float,
    height: float = 3.0,
    level: str = "Level 1"
) -> Dict[str, Any]:
    """
    创建一个正方形房间

    Args:
        center_x: 房间中心 X 坐标
        center_y: 房间中心 Y 坐标
        size: 房间边长（米）
        height: 墙体高度（米）
        level: 标高名称
    """
    half = size / 2
    return create_room(
        center_x - half, center_y - half,
        center_x + half, center_y + half,
        height, level
    )


def create_l_shaped_room(
    x: float,
    y: float,
    width1: float,
    depth1: float,
    width2: float,
    depth2: float,
    height: float = 3.0,
    level: str = "Level 1"
) -> Dict[str, Any]:
    """
    创建 L 形房间（两个矩形组合）

    Args:
        x, y: 起始点坐标
        width1, depth1: 第一个矩形的宽度和深度
        width2, depth2: 第二个矩形的宽度和深度
        height: 墙体高度
        level: 标高名称
    """
    # 创建第一个矩形
    room1 = create_room(x, y, x + width1, y + depth1, height, level)

    # 创建第二个矩形（与第一个相邻）
    room2 = create_room(x + width1, y, x + width1 + width2, y + depth2, height, level)

    return {
        "success": room1.get("success") and room2.get("success"),
        "room1": room1,
        "room2": room2,
        "total_area_sqm": room1.get("area_sqm", 0) + room2.get("area_sqm", 0)
    }
