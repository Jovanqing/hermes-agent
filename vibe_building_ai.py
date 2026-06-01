#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vibe Building - AI 驱动的 Revit 建模助手

这个脚本启动一个 hermes-agent 会话，配置为使用 Revit API 工具。
用户可以通过自然语言与 AI 交互，AI 会调用 Revit API 来创建建筑构件。
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from run_agent import HermesAgent
from model_tools import ToolRegistry

def main():
    print("=" * 60)
    print("🏗️  Vibe Building - AI 驱动的 Revit 建模助手")
    print("=" * 60)
    print()

    # 检查 Revit API 连接
    print("正在检查 Revit API 连接...")
    try:
        from tools import revit_api
        health = revit_api.health_check()
        if health.get("status") == "ok":
            print(f"✅ Revit 已连接: {health.get('version')}")
            print(f"   文档: {health.get('document')}")
        else:
            print("❌ Revit API 未响应")
            print("   请确保 Revit 已启动且 pyRevit 扩展已加载")
            return
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("   请确保 Revit 已启动且 pyRevit 扩展已加载")
        return

    print()
    print("=" * 60)
    print("AI 助手已就绪！你可以用自然语言描述建筑需求。")
    print()
    print("示例命令:")
    print("  - '在标高1创建一面10米长、3米高的墙'")
    print("  - '创建一个5x4米的房间'")
    print("  - '在坐标(0,0)到(10,0)之间创建墙体'")
    print("  - '列出所有墙体'")
    print()
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60)
    print()

    # 启动 AI 代理
    try:
        agent = HermesAgent()
        agent.chat_loop()
    except KeyboardInterrupt:
        print("\n\n再见！")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
