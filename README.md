# PDF解析器

一个智能PDF图像提取工具，能够自动识别PDF类型并使用最合适的方法提取图像。

## 功能特点

- 自动识别PDF类型（矢量PDF、扫描PDF、数字PDF、文本PDF）
- 根据PDF类型选择最合适的提取方法
- 支持过滤重复图像和重叠图像
- 提供整页渲染和图像对象提取两种模式
- 支持跳过只包含文字的页面，只提取包含图像的页面
- 专门优化的CAD图纸渲染器，确保所有元素都被正确捕获

## 项目结构

```
pdf_parser/
├── pdf_api/                  # API服务
│   ├── api/                  # API路由
│   ├── core/                 # 核心功能
│   │   ├── cad_pdf_renderer.py   # CAD PDF渲染器
│   │   ├── pdf_analyzer.py       # PDF分析器
│   │   └── pdf_image_extractor.py # PDF图像提取器
│   ├── static/               # 静态文件
│   ├── templates/            # 模板文件
│   ├── venv/                 # 虚拟环境
│   └── app.py                # 应用入口
```

## 安装

1. 克隆仓库
```bash
git clone https://github.com/yourusername/pdf_parser.git
cd pdf_parser
```

2. 创建虚拟环境并安装依赖
```bash
cd pdf_api
python -m venv venv
source venv/bin/activate  # 在Windows上使用 venv\Scripts\activate
pip install -r requirements.txt
```

## 使用方法

1. 启动API服务
```bash
python app.py
```

2. 访问Web界面
在浏览器中打开 http://localhost:8888

3. 上传PDF文件并选择提取选项
   - 选择是否过滤重复图像
   - 选择是否过滤重叠图像
   - 设置重叠阈值
   - 选择是否跳过只包含文字的页面

## 支持的PDF类型

- **矢量PDF**：如CAD图纸、矢量图形
- **扫描PDF**：扫描的文档或图像
- **数字PDF**：包含文本和图像的混合PDF
- **文本PDF**：仅包含文本的PDF

## 技术栈

- **后端**：Python, Flask
- **PDF处理**：PyMuPDF (fitz), pdfplumber
- **图像处理**：Pillow, NumPy
