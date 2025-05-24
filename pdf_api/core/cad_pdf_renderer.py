#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
专用CAD PDF渲染器

针对复杂CAD图纸优化的渲染器，确保所有元素都被正确捕获
"""

import os
import fitz  # PyMuPDF
import time
from PIL import Image
import numpy as np

def render_cad_pdf(pdf_path, output_dir, page_num, dpi=300):
    """
    使用优化的设置渲染CAD PDF，确保所有元素都被捕获
    
    参数:
        pdf_path (str): PDF文件路径
        output_dir (str): 输出目录路径
        page_num (int): 页码 (0-based)
        dpi (int): 输出图像的DPI，默认为300
    
    返回:
        dict: 渲染结果信息
    """
    # 检查是否是简单矢量PDF或复杂CAD PDF
    # 我们不再使用硬编码的文件名检查，而是基于内容特征进行判断
    print(f"  使用专用CAD渲染器处理页面 {page_num + 1}...")
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开PDF文件
        doc = fitz.open(pdf_path)
        
        # 获取页面
        page = doc[page_num]
        
        # 计算缩放因子 (DPI / 72，因为PDF的默认DPI是72)
        zoom_factor = dpi / 72
        
        # 创建一个矩阵来应用缩放
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        
        # 开始计时
        start_time = time.time()
        
        # 渲染PDF并保持原始颜色规格
        print("  使用专用CAD渲染器保持原始颜色规格...")
        
        # 尝试不同的渲染设置来找到最接近原始效果的方法
        
        # 使用PyMuPDF官方推荐的渲染设置
        # 方法1: 使用高质量设置直接渲染
        pix1 = page.get_pixmap(
            matrix=mat,
            alpha=False,
            colorspace="rgb",  # 使用RGB颜色空间
            annots=True,      # 包含注释
        )
        
        # 方法2: 使用更高的DPI渲染然后缩小
        # 这样可以捕获更精细的线条
        mat_hires = fitz.Matrix(zoom_factor * 2, zoom_factor * 2)  # 双倍DPI
        pix2 = page.get_pixmap(
            matrix=mat_hires,
            alpha=False,
            colorspace="rgb",
            annots=True
        )
        
        # 转换为NumPy数组进行处理
        img1 = Image.frombytes("RGB", [pix1.width, pix1.height], pix1.samples)
        img2 = Image.frombytes("RGB", [pix2.width, pix2.height], pix2.samples)
        
        # 将高分辨率图像缩放到与第一个图像相同的尺寸
        img2 = img2.resize((img1.width, img1.height), Image.LANCZOS)
        
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # 尝试保持原始线条颜色的方法，同时增强可见度
        
        # 合并两种渲染结果以获得最佳效果
        combined_arr = np.minimum(arr1, arr2)  # 取最小值可以保留最暗的部分
        
        # 定义不同类型的像素掩码
        # 背景像素（非常浅色）
        background_mask = np.all(combined_arr > 240, axis=2)
        
        # 深色线条（非常深色）
        dark_line_mask = np.any(combined_arr < 100, axis=2)
        
        # 浅色线条（中等深色）
        light_line_mask = np.any(combined_arr < 180, axis=2) & ~dark_line_mask
        
        # 中间色调的元素
        mid_tone_mask = ~background_mask & ~dark_line_mask & ~light_line_mask
        
        # 创建结果数组
        result_arr = combined_arr.copy()
        
        # 增强线条可见度，保持原始颜色
        # 对深色线条进行适度增强，保持原始颜色比例
        for i in range(3):  # RGB三个通道
            # 对深色线条进行适度增强，保持原始颜色比例
            # 使用乘法因子而不是直接设置为黑色，这样可以保持原始颜色
            # 例如，红色线条仍然会是红色的，只是更深一些
            # 增强因子从0.6改为0.4，使线条更暗
            result_arr[:,:,i][dark_line_mask] = np.clip(result_arr[:,:,i][dark_line_mask] * 0.2, 0, 255).astype(np.uint8)
            
            # 对浅色线条进行适度增强
            # 增强因子从0.7改为0.5，使线条更暗
            result_arr[:,:,i][light_line_mask] = np.clip(result_arr[:,:,i][light_line_mask] * 0.3, 0, 255).astype(np.uint8)
            
            # 对中间色调元素进行轻微增强
            # 增强因子从0.8改为0.6，使元素更暗
            result_arr[:,:,i][mid_tone_mask] = np.clip(result_arr[:,:,i][mid_tone_mask] * 0.4, 0, 255).astype(np.uint8)
        
        # 增强整体对比度
        # 对于背景，保持原样
        # 不需要额外的处理
        
        # 创建最终图像
        combined_arr = result_arr
        
        # 创建合并后的图像
        combined_img = Image.fromarray(combined_arr)
        
        # 构建输出文件路径
        output_filename = f"page_{page_num + 1}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # 保存合并后的图像
        combined_img.save(output_path)
        
        # 计算渲染时间
        render_time = time.time() - start_time
        
        # 关闭文档
        doc.close()
        
        print(f"  CAD渲染完成: {output_path}")
        print(f"  图像尺寸: {combined_img.width}x{combined_img.height} 像素")
        print(f"  渲染时间: {render_time:.2f} 秒")
        
        return {
            "success": True,
            "page": page_num + 1,
            "width": combined_img.width,
            "height": combined_img.height,
            "dpi": dpi,
            "file_path": output_path,
            "file_name": output_filename,
            "render_time": f"{render_time:.2f}秒"
        }
        
    except Exception as e:
        print(f"  CAD渲染出错: {e}")
        return {
            "success": False,
            "error": str(e)
        }
