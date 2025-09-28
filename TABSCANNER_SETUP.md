# 🧾 MealSplit OCR Setup with Tabscanner

This guide shows you how to set up **real receipt processing** using the Tabscanner API.

## Quick Start

### 1. Get Your API Key

1. Sign up at [tabscanner.com](https://tabscanner.com)
2. Get your free API key (200 credits/month)
3. Set the environment variable:

```bash
export TABSCANNER_API_KEY="your_api_key_here"
```

### 2. Test the Integration

```bash
# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Test with sample data
python3 test_ocr.py --create-samples

# Test different formats
python3 test_ocr.py                    # Mock data
python3 test_ocr.py sample_receipt.txt # Text parsing
python3 test_ocr.py sample_receipt.json # JSON parsing

# Test with real receipt image (requires API key)
python3 test_ocr.py /path/to/receipt.jpg
```

## 📸 How to Process Your First Receipt

### Step 1: Take a Photo
- Use your phone to take a clear photo of your grocery receipt
- Ensure good lighting and the receipt is flat
- Save as JPG or PNG

### Step 2: Set API Key
```bash
# Add to your .env file
echo "TABSCANNER_API_KEY=your_key_here" >> .env

# Or export temporarily
export TABSCANNER_API_KEY="your_key_here"
```

### Step 3: Process the Receipt
```bash
python3 test_ocr.py /path/to/your/receipt.jpg
```

Expected output:
```
🧾 Testing MealSplit OCR Service
==================================================
API Key: ✅ Set
Supported formats: ['.jpg', '.jpeg', '.png', '.pdf', '.txt', '.json']

📸 Processing file: receipt.jpg
File size: 1234567 bytes

📋 OCR Result:
------------------------------
Store: Tesco
Date: 2025-01-27T14:30:00
Currency: GBP
Total: GBP25.47
OCR Engine: tabscanner

🛒 Items (8):
   1. Tesco Bananas
      6 pack - £1.50 (confidence: 98.0%)
   2. Semi Skimmed Milk
      2 pint - £2.20 (confidence: 95.0%)
   [... more items ...]

💰 Total calculated: £25.47
```

## 🔧 Development Features

The OCR service supports multiple input formats for flexible development:

### 1. Real API Processing (.jpg, .png)
- Uses Tabscanner API when `TABSCANNER_API_KEY` is set
- Supports UK grocery stores (Tesco, Sainsbury's, ASDA, etc.)
- Returns real extracted line items with prices

### 2. JSON Sidecar Files (.json)
Perfect for testing without API calls:
```json
{
  "store_name": "Tesco",
  "purchase_date": "2025-01-27T10:30:00",
  "currency": "GBP",
  "total_amount": 15.47,
  "items": [
    {
      "name": "Bananas 6 pack",
      "quantity": 1,
      "unit": "pack",
      "unit_price": 1.50,
      "total_price": 1.50,
      "confidence": 0.98
    }
  ]
}
```

### 3. Text File Parsing (.txt)
Simple line-based format:
```
Tesco Bananas 6 pack 1.50
Whole Milk 2 pint 2.20
Organic Eggs 12 pack 3.99
Total 8.74
```

### 4. Mock Data Fallback
When no API key is set, returns sample data for development.

## 📊 API Response Format

All processing methods return a standardized format:

```python
{
    "store_name": "Tesco",
    "purchase_date": "2025-01-27T10:30:00",
    "currency": "GBP",
    "total_amount": 25.47,
    "items": [
        {
            "name": "Cleaned Item Name",
            "quantity": 1.0,
            "unit": "pack",
            "unit_price": 1.50,
            "total_price": 1.50,
            "confidence": 0.95
        }
    ],
    "metadata": {
        "ocr_engine": "tabscanner",
        "confidence_avg": 0.95,
        "items_processed": 8
    }
}
```

## 🛠 Integration with MealSplit API

The OCR service integrates with the receipt upload endpoint:

```bash
# Upload a receipt via API
curl -X POST "http://localhost:8000/api/v1/receipts/" \
  -H "Authorization: Bearer your_jwt_token" \
  -F "file=@receipt.jpg" \
  -F "household_id=1" \
  -F "store_name=Tesco"
```

The system will:
1. Save the uploaded image
2. Process it with Tabscanner OCR
3. Store extracted line items in the database
4. Make them available for ingredient matching

## 🚨 Error Handling

The service handles common OCR edge cases:

- **Blurry images**: Falls back to mock data with logging
- **API timeouts**: Retries with exponential backoff
- **Malformed responses**: Robust parsing with fallbacks
- **Missing line items**: Graceful degradation
- **Currency/price parsing**: Multiple format support

## 💰 Cost Management

**Free Tier**: 200 credits/month
- 1 credit = 1 receipt processed
- Enough for ~200 grocery receipts
- Perfect for household use

**Paid Plans**: Start at $24/month for 300 credits

## 🔍 Debugging

Enable debug logging:
```python
import logging
logging.getLogger("app.services.ocr_service").setLevel(logging.DEBUG)
```

Common issues:
- **"No API key configured"**: Set `TABSCANNER_API_KEY`
- **"Upload failed"**: Check image format and file size
- **"OCR processing timed out"**: Try smaller/clearer image

## Next Steps

1. ✅ **Phase 1 Complete**: Real OCR integration with Tabscanner
2. 🚧 **Phase 2**: Build ingredient matching algorithm
3. 📋 **Phase 3**: Settlement calculation and Splitwise integration

You're now ready to process real receipts! 🎉