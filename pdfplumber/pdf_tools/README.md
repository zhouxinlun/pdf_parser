# PDF工具集

这个工具集提供了一系列用于处理PDF文件的工具，特别是针对不同类型PDF的图像提取。

## 功能特点

- 自动识别PDF类型（矢量PDF、扫描PDF、数字PDF、文本PDF）
- 根据PDF类型选择最合适的图像提取方法
- 支持过滤重复图像和重叠图像
- 支持整页渲染和图像对象提取两种模式
- 提供详细的PDF分析信息

## 工具说明

### 1. PDF分析器 (`pdf_analyzer.py`)

用于分析PDF文件的类型和结构，能够自动识别PDF类型。

```bash
python pdf_analyzer.py <pdf文件路径>
```

### 2. PDF图像提取器 (`pdf_image_extractor.py`)

根据PDF类型自动选择最合适的方法提取图像。

```bash
python pdf_image_extractor.py <pdf文件路径> [选项]
```

#### 选项说明

- `--output-dir`, `-o`: 输出目录路径
- `--min-size`, `-m`: 最小图像尺寸（像素），默认为100
- `--no-filter-duplicates`, `-d`: 不过滤重复图像
- `--no-filter-contained`, `-c`: 不过滤被包含的小图像
- `--overlap-threshold`, `-t`: 重叠面积比例阈值（0-1之间），默认为0.8
- `--force-vector-mode`, `-v`: 强制使用矢量PDF提取模式（整页渲染）
- `--force-scanned-mode`, `-s`: 强制使用扫描PDF提取模式（整页渲染）
- `--force-digital-mode`, `-g`: 强制使用数字PDF提取模式（图像对象提取）
- `--dpi`, `-p`: 输出图像的DPI（适用于整页渲染模式），默认为300

## PDF类型说明

1. **矢量PDF (Vector PDF)**
   - 特点：主要包含矢量图形（曲线、直线、矩形等）
   - 典型来源：CAD软件、矢量绘图软件
   - 提取方法：整页渲染为图像

2. **扫描PDF (Scanned PDF)**
   - 特点：主要是扫描的图像，几乎没有可选择的文本
   - 典型来源：扫描仪、手机拍照转PDF
   - 提取方法：整页渲染为图像

3. **数字PDF (Digital PDF)**
   - 特点：包含文本和嵌入的图像
   - 典型来源：Word、PowerPoint等办公软件导出
   - 提取方法：提取嵌入的图像对象

4. **文本PDF (Text PDF)**
   - 特点：主要是文本内容，很少或没有图像
   - 典型来源：纯文本编辑器、电子书
   - 提取方法：如果需要，使用整页渲染

## 使用示例

### 分析PDF类型

```bash
python pdf_analyzer.py 文档.pdf
```

### 自动提取图像

```bash
python pdf_image_extractor.py 文档.pdf -o ./输出目录
```

### 强制使用整页渲染模式（适用于CAD图纸或扫描文档）

```bash
python pdf_image_extractor.py 文档.pdf -o ./输出目录 -v
```

### 提取高分辨率图像

```bash
python pdf_image_extractor.py 文档.pdf -o ./输出目录 -p 600
```

## 依赖库

- pdfplumber
- PyMuPDF (fitz)
- Pillow (PIL)
