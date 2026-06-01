# -*- coding: utf-8 -*-
"""
Revit API 辅助工具
提供单位转换、类型查找等通用函数
"""

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *

# 英尺与米的转换常数
FT_PER_M = 3.28084


def m_to_ft(meters):
    """米 -> 英尺"""
    return meters * FT_PER_M


def pt(x_m, z_m, y_m=0.0):
    """创建 Revit XYZ 点（输入米，自动转换为英尺）"""
    return XYZ(m_to_ft(x_m), m_to_ft(z_m), m_to_ft(y_m))


def get_or_create_level(doc, name, elevation_m):
    """获取或创建标高"""
    elev_ft = m_to_ft(elevation_m)
    for lv in FilteredElementCollector(doc).OfClass(Level):
        if lv.Name == name:
            return lv
    t = Transaction(doc, "Create Level: " + name)
    t.Start()
    try:
        level = Level.Create(doc, elev_ft)
        level.Name = name
        t.Commit()
        return level
    except:
        t.RollBack()
        raise


def create_grid(doc, p1, p2, name):
    """创建轴网"""
    t = Transaction(doc, "Create Grid: " + name)
    t.Start()
    try:
        line = Line.CreateBound(p1, p2)
        grid = Grid.Create(doc, line)
        grid.Name = name
        t.Commit()
        return grid
    except:
        t.RollBack()
        raise


def find_wall_type(doc, name_contains=None, width_m=None):
    """
    查找墙体类型
    优先按名称匹配，其次按宽度匹配，最后返回任意可用类型
    """
    collector = FilteredElementCollector(doc).OfClass(WallType)
    all_types = list(collector)

    # 按名称匹配
    if name_contains:
        for wt in all_types:
            if name_contains in wt.Name:
                return wt

    # 按宽度匹配
    if width_m is not None:
        width_ft = m_to_ft(width_m)
        for wt in all_types:
            try:
                if abs(wt.Width - width_ft) < 0.01:
                    return wt
            except:
                continue

    # 返回第一个可用类型
    if all_types:
        return all_types[0]
    return None


def find_floor_type(doc, name_contains=None):
    """查找楼板类型"""
    collector = FilteredElementCollector(doc).OfClass(FloorType)
    all_types = list(collector)

    if name_contains:
        for ft in all_types:
            if name_contains in ft.Name:
                return ft

    if all_types:
        return all_types[0]
    return None


def get_level_by_name(doc, name):
    """按名称获取标高"""
    for lv in FilteredElementCollector(doc).OfClass(Level):
        if lv.Name == name:
            return lv
    return None


def collect_wall_segments(rooms):
    """
    从房间列表中提取所有唯一的墙段
    每个房间是矩形，产生4条墙段
    返回: [(x1, z1, x2, z2), ...]
    """
    segments = set()
    for room in rooms:
        x1, z1 = room["x1"], room["z1"]
        x2, z2 = room["x2"], room["z2"]
        # 南墙 (z1)
        seg = (min(x1, x2), z1, max(x1, x2), z1)
        segments.add(seg)
        # 北墙 (z2)
        seg = (min(x1, x2), z2, max(x1, x2), z2)
        segments.add(seg)
        # 西墙 (x1)
        seg = (x1, min(z1, z2), x1, max(z1, z2))
        segments.add(seg)
        # 东墙 (x2)
        seg = (x2, min(z1, z2), x2, max(z1, z2))
        segments.add(seg)
    return segments


def segment_key(seg):
    """生成墙段的唯一键，用于去重"""
    x1, z1, x2, z2 = seg
    # 标准化：确保起点在左/下方
    if x1 > x2 or (x1 == x2 and z1 > z2):
        x1, z1, x2, z2 = x2, z2, x1, z1
    return (round(x1, 2), round(z1, 2), round(x2, 2), round(z2, 2))
