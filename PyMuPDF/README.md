# PyMuPDF 环境

这是一个使用 PyMuPDF 处理 PDF 文件的 Python 环境。PyMuPDF 是一个强大的 PDF 处理库，可以用于提取文本、图像，获取元数据，以及创建和修改 PDF 文件。

## 环境设置

### 1. 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# 在 macOS/Linux 上:
source venv/bin/activate
# 在 Windows 上:
# venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 示例脚本

`pdf_example.py` 文件包含了一些基本的 PyMuPDF 功能演示：

- 打开 PDF 文件
- 提取文本
- 提取图像
- 获取文档元数据
- 创建简单的 PDF

## 运行示例

```bash
python pdf_example.py
```

## PyMuPDF 常用功能

### 打开 PDF

```python
import fitz  # PyMuPDF
doc = fitz.open("your_file.pdf")
```

### 提取文本

```python
page = doc.load_page(0)  # 第一页
text = page.get_text()
```

### 提取图像

```python
images = page.get_images(full=True)
for img in images:
    xref = img[0]
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]
    # 处理图像...
```

### 获取元数据

```python
metadata = doc.metadata
```

### 创建 PDF

```python
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 100), "Hello World!")
doc.save("output.pdf")
```

## 更多资源

- [PyMuPDF 官方文档](https://pymupdf.readthedocs.io/)
- [PyMuPDF GitHub](https://github.com/pymupdf/PyMuPDF)
