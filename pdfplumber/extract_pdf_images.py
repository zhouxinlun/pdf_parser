#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF图像提取工具 (结合PyMuPDF和pdfplumber)

从PDF文件中提取图像，并过滤重叠图像，只保留最全面的图像
"""

import os
import sys
import fitz  # PyMuPDF
import argparse
from PIL import Image
import hashlib
from io import BytesIO
from collections import defaultdict
import numpy as np

def extract_images(pdf_path, output_dir, min_size=100, overlap_threshold=0.6, save_images=True):
    """
    从PDF中提取图像，并过滤重叠图像
    
    参数:
        pdf_path (str): PDF文件路径
        output_dir (str): 输出目录
        min_size (int): 最小图像尺寸（像素）
        overlap_threshold (float): 重叠阈值，0-1之间
        save_images (bool): 是否保存图像
    
    返回:
        list: 提取的图像信息列表
    """
    # 确保输出目录存在
    if save_images and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 打开PDF文件
    doc = fitz.open(pdf_path)
    
    # 存储图像信息
    all_images = []
    # 存储每页的图像矩形信息
    page_rects = defaultdict(list)
    
    # 遍历每一页
    for page_idx, page in enumerate(doc):
        print(f"处理第 {page_idx + 1} 页...")
        
        # 创建页面子目录
        if save_images:
            page_dir = os.path.join(output_dir, f"page_{page_idx + 1}")
            if not os.path.exists(page_dir):
                os.makedirs(page_dir)
        
        # 获取页面上的所有图像
        image_list = page.get_images(full=True)
        
        # 处理每个图像
        for img_idx, img in enumerate(image_list):
            try:
                # 获取图像xref
                xref = img[0]
                
                # 提取图像
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 使用PIL打开图像
                pil_image = Image.open(BytesIO(image_bytes))
                width, height = pil_image.size
                
                # 跳过太小的图像
                if width * height < min_size:
                    continue
                
                # 计算图像哈希值
                img_hash = hashlib.md5(image_bytes).hexdigest()
                
                # 获取图像在页面上的位置
                try:
                    # 尝试获取图像的边界框
                    bbox = page.get_image_bbox(img)
                    if bbox:
                        x0, y0, x1, y1 = bbox
                    else:
                        # 如果无法获取边界框，使用默认值
                        x0, y0 = 0, 0
                        x1, y1 = width, height
                except Exception as e:
                    print(f"  警告: 无法获取图像边界框: {e}")
                    x0, y0 = 0, 0
                    x1, y1 = width, height
                
                # 创建图像信息
                image_info = {
                    "page_index": page_idx + 1,
                    "image_index": img_idx + 1,
                    "width": width,
                    "height": height,
                    "format": image_ext.upper(),
                    "size_bytes": len(image_bytes),
                    "hash": img_hash,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1
                }
                
                # 保存图像
                if save_images:
                    output_filename = f"img{img_idx+1}_{img_hash[:8]}.{image_ext}"
                    output_path = os.path.join(page_dir, output_filename)
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    image_info["saved_path"] = output_path
                
                # 添加到结果列表
                all_images.append(image_info)
                
                # 保存矩形信息
                page_rects[page_idx].append({
                    "rect": (x0, y0, x1, y1),
                    "area": (x1 - x0) * (y1 - y0),
                    "index": len(all_images) - 1
                })
                
            except Exception as e:
                print(f"  警告: 提取图像 #{img_idx} 时出错: {e}")
    
    # 过滤重叠图像
    if overlap_threshold < 1.0:
        # 存储要保留的图像索引
        indices_to_keep = set()
        
        # 按页面处理
        for page_idx, rects in page_rects.items():
            # 按面积从大到小排序
            sorted_rects = sorted(rects, key=lambda x: x["area"], reverse=True)
            
            # 处理每个矩形
            for i, rect1 in enumerate(sorted_rects):
                # 如果已经决定保留这个图像，跳过进一步检查
                if rect1["index"] in indices_to_keep:
                    continue
                    
                # 默认保留这个图像
                keep = True
                
                # 检查这个矩形是否与已保留的任何矩形有显著重叠
                for kept_idx in indices_to_keep:
                    # 找到已保留矩形的信息
                    kept_rect_info = next((r for r in sorted_rects if r["index"] == kept_idx), None)
                    if not kept_rect_info:
                        continue
                        
                    # 获取两个矩形的坐标
                    x0_1, y0_1, x1_1, y1_1 = rect1["rect"]
                    x0_2, y0_2, x1_2, y1_2 = kept_rect_info["rect"]
                    
                    # 计算重叠区域
                    overlap_x0 = max(x0_1, x0_2)
                    overlap_y0 = max(y0_1, y0_2)
                    overlap_x1 = min(x1_1, x1_2)
                    overlap_y1 = min(y1_1, y1_2)
                    
                    # 检查是否有重叠
                    if overlap_x0 < overlap_x1 and overlap_y0 < overlap_y1:
                        # 计算重叠面积
                        overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
                        
                        # 计算当前矩形的面积
                        rect1_area = rect1["area"]
                        
                        # 如果重叠面积占当前矩形的比例超过阈值，则不保留当前矩形
                        if overlap_area / rect1_area > overlap_threshold:
                            keep = False
                            break
                
                # 如果决定保留这个图像
                if keep:
                    indices_to_keep.add(rect1["index"])
        
        # 只保留选定的图像
        filtered_images = [img for i, img in enumerate(all_images) if i in indices_to_keep]
        all_images = filtered_images
    
    # 关闭PDF文档
    doc.close()
    
    return all_images

def print_summary(images):
    """打印提取图像的摘要信息"""
    if not images:
        print("\nPDF中未找到图像")
        return
    
    print(f"\n成功提取 {len(images)} 张图像")
    
    # 按页面统计
    pages_count = {}
    for img in images:
        page = img["page_index"]
        pages_count[page] = pages_count.get(page, 0) + 1
    
    print(f"包含图像的页面数: {len(pages_count)}")
    
    # 打印每页的图像数量
    print("\n每页图像数量:")
    for page, count in sorted(pages_count.items()):
        print(f"  - 第{page}页: {count}张图像")
    
    # 统计图像格式
    formats = {}
    for img in images:
        fmt = img["format"]
        formats[fmt] = formats.get(fmt, 0) + 1
    
    print("\n图像格式统计:")
    for fmt, count in formats.items():
        print(f"  - {fmt}: {count}张")
    
    # 统计图像尺寸分布
    sizes = {
        "小图 (<10KB)": 0,
        "中图 (10KB-100KB)": 0,
        "大图 (>100KB)": 0
    }
    
    for img in images:
        size_kb = img["size_bytes"] / 1024
        if size_kb < 10:
            sizes["小图 (<10KB)"] += 1
        elif size_kb < 100:
            sizes["中图 (10KB-100KB)"] += 1
        else:
            sizes["大图 (>100KB)"] += 1
    
    print("\n图像尺寸统计:")
    for size_cat, count in sizes.items():
        print(f"  - {size_cat}: {count}张")
    
    # 打印前5张图像的详细信息
    print("\n前5张图像的详细信息:")
    for i, img in enumerate(images[:5]):
        print(f"\n图像 #{i+1}:")
        print(f"  页码: {img['page_index']}")
        print(f"  尺寸: {img['width']}x{img['height']}像素")
        print(f"  格式: {img['format']}")
        print(f"  大小: {img['size_bytes']/1024:.2f} KB")
        if "saved_path" in img:
            print(f"  保存路径: {img['saved_path']}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从PDF中提取图像并过滤重叠图像')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='图像输出目录', default='./extracted_images')
    parser.add_argument('--min-size', '-m', type=int, default=100, help='图像的最小像素数，默认为100')
    parser.add_argument('--overlap-threshold', '-t', type=float, default=0.6, 
                        help='重叠面积比例阈值，默认为0.6，范围0-1之间')
    parser.add_argument('--no-save', '-n', action='store_true', help='不保存图像到文件系统')
    
    args = parser.parse_args()
    
    try:
        print(f"开始处理PDF: {args.pdf_path}")
        
        # 提取图像
        extracted_images = extract_images(
            args.pdf_path,
            args.output_dir,
            min_size=args.min_size,
            overlap_threshold=args.overlap_threshold,
            save_images=not args.no_save
        )
        
        # 打印摘要
        print_summary(extracted_images)
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
