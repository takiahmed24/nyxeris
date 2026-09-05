# CJdropshipping: Sourcing, Dropshipping & Fulfillment for Whop

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![Whop](https://img.shields.io/badge/Whop-App%20Store%20Ready-FF6243.svg?style=flat)](https://whop.com)
[![License](https://img.shields.io/badge/License-Proprietary-black.svg?style=flat)](#)

> **Developed by Taki**  
> A dedicated, multi-tenant fulfillment engine connecting Whop creators and merchants directly to CJ Dropshipping's global supply chain—eliminating Shopify's \/month platform fee.

---

## 🌟 Key Features

- **1-Click Product Listing**: Browse CJ Dropshipping's 400,000+ catalog or your saved products and list directly to your Whop store with custom profit margins.
- **Automated SKU Mapping**: Automatically translates Whop variant titles and SKUs to CJ Dropshipping product IDs with zero manual configuration.
- **Instant Order Dispatch**: Automatically captures customer orders from Whop webhooks and submits fulfillment orders directly to CJ's global warehouses.
- **Carrier Tracking Synchronization**: Syncs USPS, DHL, CJ Packet, and FedEx tracking numbers and marks orders as fulfilled inside Whop customer dashboards.
- **Multi-Tenant Architecture**: Each merchant connects their own private CJ API credentials securely with tenant isolation.
- **Zero Cold-Starts & Production Ready**: Native Dockerfile, Procfile, and cloud deployment ready for AWS App Runner, Railway, or Render.

---

## 🚀 Quick Start (Local Development)

1. **Clone the repository**:
   `ash
   git clone https://github.com/takiahmed24/cjdropshipping-whop.git
   cd cjdropshipping-whop
   `

2. **Install dependencies**:
   `ash
   pip install -r requirements.txt
   `

3. **Configure Environment Variables**:
   Copy .env.example to .env and fill in your credentials:
   `ash
   cp .env.example .env
   `

4. **Launch Server**:
   `ash
   # On Windows: Double-click start.bat
   # Or run via CLI:
   uvicorn main:app --host 0.0.0.0 --port 8090 --reload
   `
   Open http://localhost:8090 in your browser.

---

## 🧪 Verification & Testing

Run the automated 8-stage verification test suite:
`ash
python verify_cj_whop.py
`

---

## 🚢 Production Deployment

### Option A: AWS App Runner (Recommended)
1. Create a new service in AWS App Runner.
2. Select this GitHub repository (cjdropshipping-whop).
3. Set build provider to **Dockerfile** with port 8090.
4. Add environment variables (WHOP_APP_ID, WHOP_API_KEY).
5. Deploy to get your permanent SSL URL.

### Option B: Docker
`ash
docker build -t cjdropshipping-whop .
docker run -p 8090:8090 --env-file .env cjdropshipping-whop
`

---

## 📄 License & Attribution
Proprietary software. Developed by Taki for the Whop developer ecosystem.
