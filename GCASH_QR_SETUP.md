# GCash QR Code Setup Guide

## How to Add Your GCash QR Code

Your GCash payment modal will display your actual GCash QR code for customers to scan.

### Step 1: Save Your QR Code Image

1. **Download or save your GCash QR code image**
   - The image should be in PNG or JPG format
   - Make sure it's clear and scannable

2. **Save it to the `static` folder**
   - File name: `gcash-qr.png`
   - Full path: `static/gcash-qr.png`

### Step 2: Verify the Image

1. Make sure the file exists at: `static/gcash-qr.png`
2. The image should be readable and clear
3. Recommended size: At least 500x500 pixels for good quality

### Step 3: Test the Payment Flow

1. Start your server: `python start_server.py`
2. Place a test order with GCash payment
3. The QR code should appear in the payment modal

## Alternative: Using a Different File Name or URL

If you want to use a different file name or host the QR code elsewhere:

### Option 1: Environment Variable
Set the `GCASH_QR_CODE_URL` environment variable:
```bash
export GCASH_QR_CODE_URL="/static/my-custom-qr.png"
# or
export GCASH_QR_CODE_URL="https://example.com/my-qr-code.png"
```

### Option 2: Direct URL
If your QR code is hosted online, you can set the URL directly in the environment variable.

## Current Configuration

- **Default QR Code Path**: `/static/gcash-qr.png`
- **Backend**: Automatically includes QR code URL in payment response
- **Frontend**: Displays QR code in the GCash payment modal

## Troubleshooting

### QR Code Not Showing

1. **Check file exists**: Verify `static/gcash-qr.png` exists
2. **Check file permissions**: Make sure the file is readable
3. **Check browser console**: Look for 404 errors for the image
4. **Check server logs**: Verify the static files are being served

### QR Code Image is Blurry

- Use a higher resolution image (at least 500x500 pixels)
- Save as PNG for better quality
- Make sure the QR code is clear and not compressed too much

### QR Code Not Scannable

- Ensure the QR code is the official GCash QR code
- Make sure the image is not distorted or stretched
- Verify the QR code is valid and not expired

## Notes

- The QR code will be displayed in the GCash payment modal
- Customers can scan it directly with their GCash app
- The QR code is shown alongside the admin's GCash number and payment instructions
- If the QR code image fails to load, a fallback message will be shown

