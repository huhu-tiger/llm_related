#!/usr/bin/env python3
"""
测试 get_images 函数的脚本
"""

import logging
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_mcp import get_images

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_get_images():
    """测试 get_images 函数"""
    print("开始测试 get_images 函数...")
    
    # 测试查询
    test_query = "新能源汽车 2025年"
    
    try:
        result = get_images(test_query)
        print(f"\n测试结果:")
        print(f"查询: {test_query}")
        print(f"结果类型: {type(result)}")
        print(f"结果内容: {result}")
        
        if isinstance(result, dict):
            print(f"\n找到 {len(result)} 张图片:")
            for img_url, description in result.items():
                print(f"- 图片URL: {img_url}")
                print(f"  描述: {description}")
                print()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_images() 