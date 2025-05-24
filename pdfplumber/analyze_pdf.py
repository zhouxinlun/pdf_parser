#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF分析工具

分析PDF文件的结构，包括页面、文本、图像、矢量图形等
"""

import os
import sys
import pdfplumber
import argparse
import json

def analyze_pdf(pdf_path):
    """
    分析PDF文件的结构
    
    参数:
        pdf_path (str): PDF文件路径
        
    返回:
        dict: PDF分析结果
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    analysis = {
        "文件名": os.path.basename(pdf_path),
        "文件路径": pdf_path,
        "页面信息": [],
        "元数据": {}
    }
    
    # 打开PDF
    with pdfplumber.open(pdf_path) as pdf:
        # 获取基本信息
        analysis["页数"] = len(pdf.pages)
        
        # 获取元数据
        if pdf.metadata:
            analysis["元数据"] = pdf.metadata
        
        # 分析每一页
        for i, page in enumerate(pdf.pages):
            page_info = {
                "页码": i + 1,
                "宽度": page.width,
                "高度": page.height,
                "旋转": page.rotation,
                "文本字符数": 0,
                "图像数": 0,
                "矢量图形数": 0,
                "图像详情": [],
                "曲线数": 0,
                "直线数": 0,
                "矩形数": 0
            }
            
            # 提取文本
            text = page.extract_text() or ""
            page_info["文本字符数"] = len(text)
            page_info["文本摘要"] = text[:200] + "..." if len(text) > 200 else text
            
            # 提取图像
            images = page.images
            page_info["图像数"] = len(images)
            
            # 图像详情
            for j, img in enumerate(images):
                img_info = {
                    "索引": j,
                    "位置": {
                        "x0": img.get("x0", 0),
                        "y0": img.get("top", 0),
                        "x1": img.get("x1", 0),
                        "y1": img.get("bottom", 0)
                    },
                    "宽度": img.get("width", 0),
                    "高度": img.get("height", 0),
                    "类型": img.get("name", "未知")
                }
                page_info["图像详情"].append(img_info)
            
            # 提取矢量图形
            curves = page.curves
            page_info["曲线数"] = len(curves)
            
            lines = page.lines
            page_info["直线数"] = len(lines)
            
            rects = page.rects
            page_info["矩形数"] = len(rects)
            
            # 计算矢量图形总数
            page_info["矢量图形数"] = page_info["曲线数"] + page_info["直线数"] + page_info["矩形数"]
            
            # 添加页面信息
            analysis["页面信息"].append(page_info)
    
    return analysis

def print_analysis(analysis):
    """打印PDF分析结果"""
    print(f"\nPDF文件: {analysis['文件名']}")
    print(f"总页数: {analysis['页数']}")
    
    # 打印元数据
    if analysis["元数据"]:
        print("\n元数据:")
        for key, value in analysis["元数据"].items():
            print(f"  {key}: {value}")
    
    # 打印页面信息
    print("\n页面信息:")
    for page in analysis["页面信息"]:
        print(f"\n  第{page['页码']}页:")
        print(f"    尺寸: {page['宽度']} x {page['高度']} 点")
        print(f"    旋转: {page['旋转']}度")
        print(f"    文本字符数: {page['文本字符数']}")
        print(f"    图像数: {page['图像数']}")
        print(f"    矢量图形数: {page['矢量图形数']} (曲线: {page['曲线数']}, 直线: {page['直线数']}, 矩形: {page['矩形数']})")
        
        # 如果有图像，打印图像详情
        if page["图像数"] > 0:
            print("\n    图像详情:")
            for img in page["图像详情"]:
                print(f"      图像 #{img['索引']+1}:")
                print(f"        位置: ({img['位置']['x0']}, {img['位置']['y0']}) - ({img['位置']['x1']}, {img['位置']['y1']})")
                print(f"        尺寸: {img['宽度']} x {img['高度']}")
                print(f"        类型: {img['类型']}")
        
        # 如果有文本，打印文本摘要
        if page["文本字符数"] > 0:
            print(f"\n    文本摘要: {page['文本摘要']}")
    
    # 打印总结
    print("\n总结:")
    total_images = sum(page["图像数"] for page in analysis["页面信息"])
    total_vectors = sum(page["矢量图形数"] for page in analysis["页面信息"])
    total_text = sum(page["文本字符数"] for page in analysis["页面信息"])
    
    print(f"  总图像数: {total_images}")
    print(f"  总矢量图形数: {total_vectors}")
    print(f"  总文本字符数: {total_text}")
    
    # 判断PDF类型
    if total_vectors > 100 and total_text > 100:
        print("  PDF类型: 矢量PDF (CAD或矢量图形)")
    elif total_images > 0 and total_text > 100:
        print("  PDF类型: 数字PDF (包含文本和图像)")
    elif total_images > 0 and total_text < 100:
        print("  PDF类型: 扫描PDF或图像PDF (主要是图像)")
    else:
        print("  PDF类型: 文本PDF (主要是文本)")

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='分析PDF文件结构')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--json', '-j', help='将分析结果保存为JSON文件')
    
    args = parser.parse_args()
    
    try:
        # 分析PDF
        analysis = analyze_pdf(args.pdf_path)
        
        # 打印分析结果
        print_analysis(analysis)
        
        # 如果指定了JSON输出路径，保存为JSON
        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            print(f"\n分析结果已保存到: {args.json}")
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
