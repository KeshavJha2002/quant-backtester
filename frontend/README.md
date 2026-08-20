# Quantum Trading & Portfolio Terminal (100% Static Frontend App)

A modern, high-performance, 100% client-side React + TypeScript + Tailwind CSS web application for active portfolio management, multi-timeframe 4-state decisions (HOLD / ADD / TRIM / EXIT), holding-horizon position sizing, and quantitative stock screening.

---

## 🚀 Key Features

- **100% Static & Serverless**: Zero backend or database server needed. Deploy anywhere for free.
- **Client-Side Quantitative Engine**: Calculates Supertrend (10, 3.0), Triple Supertrend, Projection Cone Sigma (annualized log volatility), ATR(14), ADX, VCP compression, and institutional accumulation ratios directly in the browser.
- **Portfolio State Persistence**: Stores your positions, budget, and cash balance in browser `localStorage` with 1-click CSV/JSON export and import.
- **Pre-Loaded Holdings**: Comes pre-configured with all 11 current stock holdings.
- **Holding-Horizon Position Sizer**: Computes exact recommended shares based on volatility and selected horizon (`Swing 1-4w`, `Positional 1-6m`, `Long-Term >6m`).
- **Deterministic Tie-Breaker**: 5-Point structural comparison matrix between any two candidate stocks.

---

## 🛠 Local Development

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 📦 Production Build

```bash
cd frontend
npm run build
```
The compiled, production-ready static assets will be in `frontend/dist/`.

---

## 🌐 Instant Free Deployment

### 1. Deploy to Vercel (Recommended)
```bash
cd frontend
npx vercel
```
*Or connect your GitHub repository to Vercel and set the Root Directory to `frontend`.*

### 2. Deploy to Netlify
```bash
cd frontend
npx netlify deploy --prod --dir=dist
```
*Or drag and drop the `frontend/dist/` folder into [app.netlify.com/drop](https://app.netlify.com/drop).*

### 3. Deploy to GitHub Pages
Add the `base: '/<repo-name>/'` in `vite.config.ts` and push the `dist/` directory to the `gh-pages` branch.

### 4. Deploy to Cloudflare Pages
Connect your repo, set Build command to `npm run build` and Build output directory to `dist`.
