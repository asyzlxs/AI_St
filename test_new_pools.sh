#!/bin/bash

# 测试新增股票池功能
# 使用较短的日期范围来加快测试速度

echo "========================================="
echo "测试新增股票池功能"
echo "========================================="
echo ""

# 测试 1: 沪股通
echo "【测试 1】沪股通 - 获取前5名"
stock discover --pool hgt --start 2026-01-01 --end 2026-04-13 --top 5 --no-chart
echo ""
echo "按任意键继续..."
read -n 1 -s
echo ""

# 测试 2: 深股通
echo "【测试 2】深股通 - 获取前5名"
stock discover --pool sgt --start 2026-01-01 --end 2026-04-13 --top 5 --no-chart
echo ""
echo "按任意键继续..."
read -n 1 -s
echo ""

# 测试 3: 芯片板块
echo "【测试 3】芯片板块 - 获取前5名"
stock discover --pool chip --start 2026-01-01 --end 2026-04-13 --top 5 --no-chart
echo ""
echo "按任意键继续..."
read -n 1 -s
echo ""

# 测试 4: 新能源板块
echo "【测试 4】新能源板块 - 获取前5名"
stock discover --pool newenergy --start 2026-01-01 --end 2026-04-13 --top 5 --no-chart
echo ""
echo "按任意键继续..."
read -n 1 -s
echo ""

# 测试 5: 人工智能板块
echo "【测试 5】人工智能板块 - 获取前5名"
stock discover --pool ai --start 2026-01-01 --end 2026-04-13 --top 5 --no-chart
echo ""
echo "按任意键继续..."
read -n 1 -s
echo ""

echo "========================================="
echo "所有测试完成！"
echo "========================================="
