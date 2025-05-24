#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF图片提取工具

使用PyMuPDF库从PDF文件中提取图片及其相关信息
"""

import os
import fitz  # PyMuPDF (注意：PyMuPDF在Python中的导入名称是fitz)
import json
import numpy as np
from PIL import Image, ImageChops
from io import BytesIO
import hashlib
from collections import defaultdict


def is_similar_image(img1, img2, threshold=0.9):
    """
    比较两个PIL图像是否相似
    
    参数:
        img1 (PIL.Image): 第一个图像
        img2 (PIL.Image): 第二个图像
        threshold (float): 相似度阈值，0-1之间，越高要求越严格
        
    返回:
        bool: 如果图像相似则返回True，否则返回False
    """
    # 确保两个图像大小相同
    if img1.size != img2.size:
        # 调整大小以便比较
        img2 = img2.resize(img1.size, Image.LANCZOS)
    
    # 转换为相同模式
    if img1.mode != img2.mode:
        if 'A' in img1.mode:
            img1 = img1.convert('RGBA')
            img2 = img2.convert('RGBA')
        else:
            img1 = img1.convert('RGB')
            img2 = img2.convert('RGB')
    
    # 计算差异
    diff = ImageChops.difference(img1, img2)
    
    # 计算差异程度
    diff_array = np.array(diff)
    non_zero = np.count_nonzero(diff_array)
    total_pixels = diff_array.size
    
    # 计算相似度 (0-1)
    similarity = 1 - (non_zero / total_pixels)
    
    return similarity >= threshold


def is_contained_in(rect1, rect2, tolerance=0.9):
    """
    检查矩形1是否基本包含在矩形2中
    
    参数:
        rect1 (tuple): 第一个矩形 (x0, y0, x1, y1)
        rect2 (tuple): 第二个矩形 (x0, y0, x1, y1)
        tolerance (float): 容差，0-1之间
        
    返回:
        bool: 如果矩形1基本包含在矩形2中则返回True，否则返回False
    """
    x0_1, y0_1, x1_1, y1_1 = rect1
    x0_2, y0_2, x1_2, y1_2 = rect2
    
    # 计算矩形1的面积
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    
    # 计算重叠区域
    overlap_x0 = max(x0_1, x0_2)
    overlap_y0 = max(y0_1, y0_2)
    overlap_x1 = min(x1_1, x1_2)
    overlap_y1 = min(y1_1, y1_2)
    
    # 检查是否有重叠
    if overlap_x0 >= overlap_x1 or overlap_y0 >= overlap_y1:
        return False
    
    # 计算重叠面积
    overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
    
    # 计算重叠比例
    overlap_ratio = overlap_area / area1
    
    return overlap_ratio >= tolerance


def extract_images_from_pdf(pdf_path, output_dir=None, save_images=False, group_by_page=False, 
                           filter_duplicates=True, filter_contained=True, min_size=100):
    """
    从PDF文件中提取所有图片及其信息
    
    参数:
        pdf_path (str): PDF文件的路径
        output_dir (str, 可选): 保存图片的目录，如果save_images为True则必须提供
        save_images (bool, 可选): 是否将图片保存到文件系统，默认为False
        group_by_page (bool, 可选): 是否按页码分组创建子文件夹保存图片，默认为False
    
    返回:
        list: 包含所有图片信息的列表，每个元素是一个字典，包含图片的页码、索引、尺寸、格式等信息
    """
    # 检查PDF文件是否存在
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 如果需要保存图片，检查输出目录
    if save_images:
        if not output_dir:
            raise ValueError("如果save_images为True，则必须提供output_dir参数")
        
        # 创建输出目录（如果不存在）
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取PDF文件名（不含扩展名），用于创建子文件夹
        pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 打开PDF文件
    doc = fitz.open(pdf_path)
    
    # 用于存储所有图片信息的列表
    all_images = []
    
    # 用于存储图像对象和矩形，用于过滤重叠图像
    page_images = defaultdict(list)
    
    # 遍历PDF的每一页
    for page_index in range(len(doc)):
        page = doc[page_index]
        
        # 获取页面上的图片列表
        image_list = page.get_images(full=True)
        
        # 遍历页面上的每个图片
        for img_index, img in enumerate(image_list):
            # 图片的基本信息
            xref = img[0]  # 图片的xref号
            base_image = doc.extract_image(xref)
            
            if base_image:
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 使用PIL打开图片以获取更多信息
                try:
                    with Image.open(BytesIO(image_bytes)) as pil_img:
                        width, height = pil_img.size
                        mode = pil_img.mode
                        format_desc = pil_img.format_description if hasattr(pil_img, 'format_description') else pil_img.format
                except Exception as e:
                    # 如果无法用PIL打开，使用PyMuPDF提供的信息
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    mode = "Unknown"
                    format_desc = image_ext.upper()
                
                # 计算图片哈希值，用于唯一标识
                img_hash = hashlib.md5(image_bytes).hexdigest()
                
                # 收集图片信息
                image_info = {
                    "page_index": page_index + 1,  # 页码（从1开始）
                    "img_index": img_index + 1,    # 图片在页面中的索引（从1开始）
                    "xref": xref,                  # 图片的xref号
                    "width": width,                # 宽度（像素）
                    "height": height,              # 高度（像素）
                    "format": image_ext,           # 格式（扩展名）
                    "format_description": format_desc,  # 格式描述
                    "color_mode": mode,            # 颜色模式
                    "size_bytes": len(image_bytes),  # 图片大小（字节）
                    "md5_hash": img_hash,          # MD5哈希值
                }
                
                # 如果需要保存图片
                if save_images and output_dir:
                    # 确定保存路径
                    if group_by_page:
                        # 按页码分组创建子文件夹
                        page_dir = os.path.join(output_dir, f"page_{page_index+1}")
                        os.makedirs(page_dir, exist_ok=True)
                        # 创建图片文件名
                        filename = f"img{img_index+1}_{img_hash[:8]}.{image_ext}"
                        filepath = os.path.join(page_dir, filename)
                    else:
                        # 不分组，直接保存到输出目录
                        filename = f"page{page_index+1}_img{img_index+1}_{img_hash[:8]}.{image_ext}"
                        filepath = os.path.join(output_dir, filename)
                    
                    # 保存图片
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    
                    # 添加文件路径到图片信息
                    image_info["saved_path"] = filepath
                
                # 检查图像大小是否符合最小要求
                if width * height < min_size:
                    continue
                    
                # 添加到结果列表
                all_images.append(image_info)
                
                # 保存图像对象和矩形信息，用于后续过滤
                try:
                    pil_img = Image.open(BytesIO(image_bytes))
                    # 获取图像在页面上的位置（如果有）
                    bbox = page.get_image_bbox(img)
                    if bbox:
                        x0, y0, x1, y1 = bbox
                        rect = (x0, y0, x1, y1)
                        page_images[page_index].append({
                            "image": pil_img,
                            "rect": rect,
                            "info": image_info
                        })
                except Exception as e:
                    print(f"警告: 无法处理图像进行过滤: {e}")
    
    # 关闭PDF文档
    doc.close()
    
    # 过滤重叠和包含关系的图像
    filtered_images = all_images
    
    if filter_duplicates or filter_contained:
        filtered_images = []
        processed_indices = set()
        
        # 按页面处理图像
        for page_idx, images in page_images.items():
            # 按面积从大到小排序图像
            images.sort(key=lambda x: x["rect"][2] * x["rect"][3] - x["rect"][0] * x["rect"][1], reverse=True)
            
            for i, img_data1 in enumerate(images):
                if i in processed_indices:
                    continue
                    
                img1 = img_data1["image"]
                rect1 = img_data1["rect"]
                info1 = img_data1["info"]
                
                # 标记为已处理
                processed_indices.add(i)
                
                # 检查是否与其他图像重叠或包含
                is_valid = True
                
                for j, img_data2 in enumerate(images):
                    if i == j or j in processed_indices:
                        continue
                        
                    img2 = img_data2["image"]
                    rect2 = img_data2["rect"]
                    
                    # 检查是否相似（如果启用了过滤重复）
                    if filter_duplicates and is_similar_image(img1, img2):
                        processed_indices.add(j)
                        continue
                    
                    # 检查是否包含（如果启用了过滤包含关系）
                    if filter_contained and is_contained_in(rect2, rect1):
                        processed_indices.add(j)
                        
                if is_valid:
                    filtered_images.append(info1)
    
    return filtered_images


def save_image_info_to_json(image_info, output_json_path):
    """
    将图片信息保存为JSON文件
    
    参数:
        image_info (list): 图片信息列表
        output_json_path (str): 输出JSON文件的路径
    """
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(image_info, f, ensure_ascii=False, indent=2)


def print_image_summary(image_info):
    """
    打印图片信息摘要并按页面分组统计
    
    参数:
        image_info (list): 图片信息列表
    """
    if not image_info:
        print("PDF中未找到图片")
        return
    
    print(f"共找到 {len(image_info)} 张图片")
    
    # 按页面分组统计
    pages_with_images = {}
    for img in image_info:
        page_idx = img["page_index"]
        if page_idx not in pages_with_images:
            pages_with_images[page_idx] = []
        pages_with_images[page_idx].append(img)
    
    print(f"包含图片的页面数: {len(pages_with_images)}")
    
    # 打印每页的图片数量
    print("\n每页图片数量:")
    for page, images in sorted(pages_with_images.items()):
        print(f"  - 第{page}页: {len(images)}张图片")
    
    # 统计图片格式
    formats = {}
    for img in image_info:
        fmt = img["format"].upper()
        formats[fmt] = formats.get(fmt, 0) + 1
    
    print("图片格式统计:")
    for fmt, count in formats.items():
        print(f"  - {fmt}: {count}张")
    
    # 打印前5张图片的详细信息
    print("\n前5张图片的详细信息:")
    for i, img in enumerate(image_info[:5]):
        print(f"\n图片 #{i+1}:")
        print(f"  页码: {img['page_index']}")
        print(f"  尺寸: {img['width']}x{img['height']}像素")
        print(f"  格式: {img['format']} ({img['format_description']})")
        print(f"  大小: {img['size_bytes']/1024:.2f} KB")
        if "saved_path" in img:
            print(f"  保存路径: {img['saved_path']}")


def main():
    """
    主函数，用于命令行调用
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='从PDF中提取图片')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', '-o', help='图片输出目录')
    parser.add_argument('--save-images', '-s', action='store_true', help='是否保存图片到文件系统')
    parser.add_argument('--group-by-page', '-g', action='store_true', help='是否按页码分组创建子文件夹保存图片')
    parser.add_argument('--json', '-j', help='将图片信息保存为JSON文件')
    parser.add_argument('--min-size', '-m', type=int, default=100, help='图像的最小像素数，默认为100')
    parser.add_argument('--no-filter-duplicates', '-d', action='store_true', help='不过滤重复图像')
    parser.add_argument('--no-filter-contained', '-c', action='store_true', help='不过滤被其他图像包含的小图像')
    
    args = parser.parse_args()
    
    try:
        # 提取图片
        image_info = extract_images_from_pdf(
            args.pdf_path, 
            output_dir=args.output_dir,
            save_images=args.save_images,
            group_by_page=args.group_by_page,
            filter_duplicates=not args.no_filter_duplicates,
            filter_contained=not args.no_filter_contained,
            min_size=args.min_size
        )
        
        # 打印摘要
        print_image_summary(image_info)
        
        # 如果指定了JSON输出路径，保存为JSON
        if args.json:
            save_image_info_to_json(image_info, args.json)
            print(f"\n图片信息已保存到: {args.json}")
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    # source venv/bin/activate && python pdf_image_extractor.py /Users/zhouxinlun/Downloads/IVR\ Drawing.pdf -o ./images -s -g
    sys.exit(main())
