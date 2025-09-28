#!/usr/bin/env python3
"""
Test script for OCR service with Tabscanner API.

This script tests the OCR service with different input types:
1. Mock data (when no API key is set)
2. Text file parsing
3. Real Tabscanner API (when API key is provided)

Usage:
    # Test with fallback data
    python test_ocr.py

    # Test with text file
    echo "Bananas 2 lb @ 1.99 = 3.98" > test_receipt.txt
    python test_ocr.py test_receipt.txt

    # Test with real API (set TABSCANNER_API_KEY environment variable)
    export TABSCANNER_API_KEY="your_api_key_here"
    python test_ocr.py path/to/receipt_image.jpg
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.ocr_service import OCRService


async def test_ocr_service(image_path: str = None):
    """Test the OCR service with different inputs."""
    ocr_service = OCRService()

    print("🧾 Testing MealSplit OCR Service")
    print("=" * 50)

    # Show configuration
    api_key_status = "✅ Set" if ocr_service.api_key else "❌ Not set"
    print(f"API Key: {api_key_status}")
    print(f"Supported formats: {ocr_service.supported_formats}")
    print()

    if image_path:
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return

        print(f"📸 Processing file: {image_path}")
        print(f"File size: {os.path.getsize(image_path)} bytes")

        try:
            result = await ocr_service.process_receipt_image(image_path)
            print_result(result)

        except Exception as e:
            print(f"❌ Error processing receipt: {e}")

    else:
        # Test with fallback data
        print("🎭 Testing with fallback data...")
        try:
            result = await ocr_service._get_fallback_result()
            print_result(result)
        except Exception as e:
            print(f"❌ Error with fallback data: {e}")


def print_result(result: dict):
    """Pretty print OCR result."""
    print("\n📋 OCR Result:")
    print("-" * 30)
    print(f"Store: {result.get('store_name')}")
    print(f"Date: {result.get('purchase_date')}")
    print(f"Currency: {result.get('currency')}")
    print(f"Total: {result.get('currency', '$')}{result.get('total_amount', 0):.2f}")
    print(f"OCR Engine: {result.get('metadata', {}).get('ocr_engine', 'unknown')}")

    items = result.get('items', [])
    print(f"\n🛒 Items ({len(items)}):")
    for i, item in enumerate(items, 1):
        qty = item.get('quantity', 1)
        unit = item.get('unit', 'unit')
        name = item.get('name', 'Unknown')
        price = item.get('total_price', 0)
        confidence = item.get('confidence', 0)

        print(f"  {i:2d}. {name}")
        print(f"      {qty} {unit} - ${price:.2f} (confidence: {confidence:.1%})")

    print(f"\n💰 Total calculated: ${sum(item.get('total_price', 0) for item in items):.2f}")


def create_sample_files():
    """Create sample test files for demonstration."""

    # Create a sample text receipt
    sample_txt = """Tesco Bananas 6 pack 1.50
Whole Milk 2 pint 2.20
Organic Eggs 12 pack 3.99
White Bread 800g 1.05
Total 8.74"""

    with open("sample_receipt.txt", "w") as f:
        f.write(sample_txt)

    # Create a sample JSON receipt (simulating OCR results)
    sample_json = {
        "store_name": "Sainsbury's",
        "purchase_date": "2025-01-27T10:30:00",
        "currency": "GBP",
        "total_amount": 15.47,
        "items": [
            {
                "name": "Tesco Finest Bananas",
                "quantity": 6,
                "unit": "pack",
                "unit_price": 0.25,
                "total_price": 1.50,
                "confidence": 0.98
            },
            {
                "name": "Semi Skimmed Milk 2 Pint",
                "quantity": 1,
                "unit": "bottle",
                "unit_price": 2.20,
                "total_price": 2.20,
                "confidence": 0.95
            },
            {
                "name": "Free Range Eggs Large 12 Pack",
                "quantity": 1,
                "unit": "pack",
                "unit_price": 3.99,
                "total_price": 3.99,
                "confidence": 0.97
            }
        ],
        "metadata": {
            "ocr_engine": "tabscanner-sample",
            "confidence_avg": 0.97
        }
    }

    with open("sample_receipt.json", "w") as f:
        json.dump(sample_json, f, indent=2)

    print("📁 Created sample files:")
    print("  - sample_receipt.txt (text format)")
    print("  - sample_receipt.json (JSON format)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-samples":
        create_sample_files()
        sys.exit(0)

    file_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("🧪 MealSplit OCR Test")
    print("Usage tips:")
    print("  • Set TABSCANNER_API_KEY for real OCR processing")
    print("  • Use --create-samples to generate test files")
    print("  • Test with .txt, .json, or image files")
    print()

    try:
        asyncio.run(test_ocr_service(file_path))
    except KeyboardInterrupt:
        print("\n👋 Test cancelled")
