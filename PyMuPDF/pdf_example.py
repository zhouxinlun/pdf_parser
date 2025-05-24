#!/usr/bin/env python3
"""
Basic PyMuPDF example script that demonstrates common PDF operations:
- Opening a PDF file
- Extracting text
- Extracting images
- Getting document metadata
- Creating a simple PDF
"""

import os
import fitz  # PyMuPDF
import tempfile
from PIL import Image
import io


def extract_text_from_pdf(pdf_path):
    """Extract text from all pages of a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    
    doc.close()
    return text


def extract_images_from_pdf(pdf_path, output_dir):
    """Extract images from all pages of a PDF file."""
    doc = fitz.open(pdf_path)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    image_count = 0
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Get image extension
            ext = base_image["ext"]
            
            # Save the image
            image_filename = f"{output_dir}/image_p{page_num + 1}_{img_index}.{ext}"
            with open(image_filename, "wb") as img_file:
                img_file.write(image_bytes)
                image_count += 1
    
    doc.close()
    return image_count


def get_pdf_metadata(pdf_path):
    """Get metadata from a PDF file."""
    doc = fitz.open(pdf_path)
    metadata = doc.metadata
    doc.close()
    return metadata


def create_simple_pdf(output_path):
    """Create a simple PDF with text and a rectangle."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size
    
    # Add text
    text_point = fitz.Point(50, 100)
    page.insert_text(text_point, "Hello from PyMuPDF!", fontsize=24)
    
    # Add a rectangle
    rect = fitz.Rect(50, 150, 550, 250)
    page.draw_rect(rect, color=(1, 0, 0), width=2)
    
    # Add more text
    page.insert_text(fitz.Point(50, 300), "This is a simple PDF created with PyMuPDF.", fontsize=12)
    
    # Save the PDF
    doc.save(output_path)
    doc.close()
    return output_path


def main():
    """Main function to demonstrate PyMuPDF functionality."""
    print("PyMuPDF Example Script")
    print("=====================")
    
    # Create a simple PDF for demonstration
    temp_dir = tempfile.gettempdir()
    sample_pdf_path = os.path.join(temp_dir, "sample.pdf")
    create_simple_pdf(sample_pdf_path)
    print(f"\nCreated sample PDF at: {sample_pdf_path}")
    
    # Extract text
    print("\nExtracting text from the PDF:")
    text = extract_text_from_pdf(sample_pdf_path)
    print(text[:150] + "..." if len(text) > 150 else text)
    
    # Extract images (likely none in our simple PDF)
    images_dir = os.path.join(temp_dir, "pdf_images")
    print(f"\nExtracting images to: {images_dir}")
    image_count = extract_images_from_pdf(sample_pdf_path, images_dir)
    print(f"Extracted {image_count} images")
    
    # Get metadata
    print("\nPDF Metadata:")
    metadata = get_pdf_metadata(sample_pdf_path)
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
