from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# Global Parameters
config = {
    "tema_len": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
}

st_config = {
    "atr_len": 14,
    "atr_mult": 3.0,
    "atr_smooth": 2,
}

nifty150 = [
    "360ONE",
    "3MINDIA",
    "ACC",
    "AIAENG",
    "APLAPOLLO",
    "AUBANK",
    "AWL",
    "ABBOTINDIA",
    "ATGL",
    "ABCAPITAL",
    "AJANTPHARM",
    "ALKEM",
    "APARINDS",
    "APOLLOTYRE",
    "ASHOKLEY",
    "ASTRAL",
    "AUROPHARMA",
    "BSE",
    "BALKRISIND",
    "BANKINDIA",
    "MAHABANK",
    "BERGEPAINT",
    "BDL",
    "BHARATFORG",
    "BHEL",
    "BHARTIHEXA",
    "BIOCON",
    "BLUESTARCO",
    "CRISIL",
    "COCHINSHIP",
    "COFORGE",
    "COLPAL",
    "CONCOR",
    "COROMANDEL",
    "CUMMINSIND",
    "DABUR",
    "DALBHARAT",
    "DEEPAKNTR",
    "DIXON",
    "ENDURANCE",
    "ESCORTS",
    "EXIDEIND",
    "NYKAA",
    "FEDERALBNK",
    "FACT",
    "FORTIS",
    "GMRAIRPORT",
    "GICRE",
    "GLAXO",
    "GLENMARK",
    "MEDANTA",
    "GODFRYPHLP",
    "GODREJIND",
    "GODREJPROP",
    "FLUOROCHEM",
    "GUJGASLTD",
    "HDFCAMC",
    "HEROMOTOCO",
    "HEXT",
    "HINDPETRO",
    "POWERINDIA",
    "HONAUT",
    "HUDCO",
    "ICICIPRULI",
    "IDBI",
    "IDFCFIRSTB",
    "IRB",
    "ITCHOTELS",
    "INDIANB",
    "IOB",
    "IRCTC",
    "IREDA",
    "IGL",
    "INDUSTOWER",
    "INDUSINDBK",
    "IPCALAB",
    "JKCEMENT",
    "JSWINFRA",
    "JSL",
    "JUBLFOOD",
    "KPRMILL",
    "KEI",
    "KPITTECH",
    "KALYANKJIL",
    "LTF",
    "LTTS",
    "LICHSGFIN",
    "LINDEINDIA",
    "LLOYDSME",
    "LUPIN",
    "MRF",
    "MANKIND",
    "MARICO",
    "MFSL",
    "MOTILALOFS",
    "MPHASIS",
    "MUTHOOTFIN",
    "NHPC",
    "NLCINDIA",
    "NMDC",
    "NTPCGREEN",
    "NATIONALUM",
    "OBEROIRLTY",
    "PAYTM",
    "OFSS",
    "POLICYBZR",
    "PIIND",
    "PAGEIND",
    "PATANJALI",
    "PERSISTENT",
    "PETRONET",
    "PHOENIXLTD",
    "POLYCAB",
    "PREMIERENE",
    "PRESTIGE",
    "PGHH",
    "RVNL",
    "SBICARD",
    "SJVN",
    "SRF",
    "SCHAEFFLER",
    "SONACOMS",
    "SAIL",
    "SUNDARMFIN",
    "SUPREMEIND",
    "SUZLON",
    "SWIGGY",
    "SYNGENE",
    "TATACOMM",
    "TATAELXSI",
    "TATAINVEST",
    "TATATECH",
    "NIACL",
    "THERMAX",
    "TORNTPOWER",
    "TIINDIA",
    "UCOBANK",
    "UNOMINDA",
    "UPL",
    "UNIONBANK",
    "UBL",
    "VMM",
    "IDEA",
    "VOLTAS",
    "WAAREEENER",
    "YESBANK",
]

nifty50 = [
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "BHARTIARTL",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "ETERNAL",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "ITC",
    "INFY",
    "INDIGO",
    "JSWSTEEL",
    "JIOFIN",
    "KOTAKBANK",
    "LT",
    "M&M",
    "MARUTI",
    "MAXHEALTH",
    "NTPC",
    "NESTLEIND",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SHRIRAMFIN",
    "SBIN",
    "SUNPHARMA",
    "TCS",
    "TATACONSUM",
    "TMPV",
    "TATASTEEL",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
]

nifty250 = [
    "ACMESOLAR",
    "AADHARHFC",
    "AARTIIND",
    "AAVAS",
    "ACE",
    "ABFRL",
    "ABLBL",
    "ABREL",
    "ABSLAMC",
    "AEGISLOG",
    "AEGISVOPAK",
    "AFCONS",
    "AFFLE",
    "AKUMS",
    "APLLTD",
    "ALKYLAMINE",
    "ALOKINDS",
    "ARE&M",
    "AMBER",
    "ANANDRATHI",
    "ANANTRAJ",
    "ANGELONE",
    "APTUS",
    "ASAHIINDIA",
    "ASTERDM",
    "ASTRAZEN",
    "ATHERENERG",
    "ATUL",
    "AIIL",
    "BASF",
    "BEML",
    "BLS",
    "BALRAMCHIN",
    "BANDHANBNK",
    "BATAINDIA",
    "BIKAJI",
    "BSOFT",
    "BLUEDART",
    "BLUEJET",
    "BBTC",
    "FIRSTCRY",
    "BRIGADE",
    "MAPMYINDIA",
    "CCL",
    "CESC",
    "CAMPUS",
    "CANFINHOME",
    "CAPLIPOINT",
    "CGCL",
    "CARBORUNIV",
    "CASTROLIND",
    "CEATLTD",
    "CENTRALBK",
    "CDSL",
    "CENTURYPLY",
    "CERA",
    "CHALET",
    "CHAMBLFERT",
    "CHENNPETRO",
    "CHOICEIN",
    "CHOLAHLDNG",
    "CUB",
    "CLEAN",
    "COHANCE",
    "CAMS",
    "CONCORDBIO",
    "CRAFTSMAN",
    "CREDITACC",
    "CROMPTON",
    "CYIENT",
    "DCMSHRIRAM",
    "DOMS",
    "DATAPATTNS",
    "DEEPAKFERT",
    "DELHIVERY",
    "DEVYANI",
    "AGARWALEYE",
    "LALPATHLAB",
    "EIDPARRY",
    "EIHOTEL",
    "ELECON",
    "ELGIEQUIP",
    "EMAMILTD",
    "EMCURE",
    "ENGINERSIN",
    "ERIS",
    "FINCABLES",
    "FINPIPE",
    "FSL",
    "FIVESTAR",
    "FORCEMOT",
    "GRSE",
    "GILLETTE",
    "GLAND",
    "GODIGIT",
    "GPIL",
    "GODREJAGRO",
    "GRANULES",
    "GRAPHITE",
    "GRAVITA",
    "GESHIP",
    "GMDCLTD",
    "GSPL",
    "HEG",
    "HBLENGINE",
    "HFCL",
    "HAPPSTMNDS",
    "HSCL",
    "HINDCOPPER",
    "HOMEFIRST",
    "HONASA",
    "IFCI",
    "IIFL",
    "INOXINDIA",
    "IRCON",
    "ITI",
    "INDGN",
    "INDIACEM",
    "INDIAMART",
    "IEX",
    "INOXWIND",
    "INTELLECT",
    "IGIL",
    "IKS",
    "JBCHEPHARM",
    "JBMA",
    "JKTYRE",
    "JSWCEMENT",
    "JPPOWER",
    "J&KBANK",
    "JINDALSAW",
    "JUBLINGREA",
    "JUBLPHARMA",
    "JWL",
    "JYOTHYLAB",
    "JYOTICNC",
    "KSB",
    "KAJARIACER",
    "KPIL",
    "KAYNES",
    "KEC",
    "KFINTECH",
    "KIRLOSBROS",
    "KIRLOSENG",
    "KIMS",
    "LTFOODS",
    "LATENTVIEW",
    "LAURUSLABS",
    "THELEELA",
    "MMTC",
    "MGL",
    "MAHSCOOTER",
    "MAHSEAMLES",
    "MANAPPURAM",
    "MRPL",
    "METROPOLIS",
    "MINDACORP",
    "MSUMI",
    "MCX",
    "NATCOPHARM",
    "NBCC",
    "NCC",
    "NSLNISP",
    "NH",
    "NAVA",
    "NAVINFLUOR",
    "NETWEB",
    "NEULANDLAB",
    "NEWGEN",
    "NIVABUPA",
    "NUVAMA",
    "NUVOCO",
    "OLAELEC",
    "OLECTRA",
    "ONESOURCE",
    "PCBL",
    "PGEL",
    "PNBHOUSING",
    "PTCIL",
    "PVRINOX",
    "PFIZER",
    "PPLPHARMA",
    "POLYMED",
    "POONAWALLA",
    "PRAJIND",
    "RRKABEL",
    "RBLBANK",
    "RHIM",
    "RITES",
    "RADICO",
    "RAILTEL",
    "RAINBOW",
    "RKFORGE",
    "RCF",
    "REDINGTON",
    "RPOWER",
    "SBFC",
    "SAGILITY",
    "SAILIFE",
    "SAMMAANCAP",
    "SAPPHIRE",
    "SARDAEN",
    "SAREGAMA",
    "SCHNEIDER",
    "SCI",
    "SHYAMMETL",
    "SIGNATURE",
    "SOBHA",
    "SONATSOFTW",
    "STARHEALTH",
    "SUMICHEM",
    "SUNTV",
    "SUNDRMFAST",
    "SWANCORP",
    "SYRMA",
    "TBOTEK",
    "TATACHEM",
    "TTML",
    "TECHNOE",
    "TEJASNET",
    "RAMCOCEM",
    "TIMKEN",
    "TITAGARH",
    "TARIL",
    "TRIDENT",
    "TRIVENI",
    "TRITURBINE",
    "UTIAMC",
    "USHAMART",
    "VGUARD",
    "VTL",
    "MANYAVAR",
    "VENTIVE",
    "VIJAYA",
    "WELCORP",
    "WELSPUNLIV",
    "WHIRLPOOL",
    "WOCKPHARMA",
    "ZFCVINDIA",
    "ZEEL",
    "ZENTEC",
    "ZENSARTECH",
    "ECLERX",
]


nifty150_ns = [f"{t}.NS" for t in nifty150]
nifty50_ns = [f"{t}.NS" for t in nifty50]
nifty250_ns = [f"{t}.NS" for t in nifty250]


def fetch_data(
    ticker: str,
    start: str = "1990-01-01",
    type: str = "W",
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    return default_data_store.fetch_data(ticker, start=start, type=type, refresh=refresh)


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    tr = np.full(len(close), np.nan)
    tr[0] = high[0] - low[0]

    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return tr


def rma(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full(len(series), np.nan)
    alpha = 1.0 / length

    valid = np.where(~np.isnan(series))[0]
    if len(valid) < length:
        return out

    start = valid[length - 1]
    out[start] = np.mean(series[valid[:length]])

    for i in range(start + 1, len(series)):
        out[i] = (
            out[i - 1] if np.isnan(series[i]) else out[i - 1] + alpha * (series[i] - out[i - 1])
        )

    return out


def sma(series: np.ndarray, length: int) -> np.ndarray:
    n = len(series)
    out = np.full(n, np.nan)

    for i in range(length - 1, n):
        window = series[i - length + 1 : i + 1]
        if not np.isnan(window).any():
            out[i] = window.mean()

    return out


def ema(candle_close: np.ndarray, length: int) -> np.ndarray:
    candle_close = np.asarray(candle_close, dtype=float).ravel()
    n = len(candle_close)

    out = np.full(n, np.nan)
    alpha = 2.0 / (length + 1)

    valid = np.where(~np.isnan(candle_close))[0]
    if len(valid) < length:
        return out

    start = valid[length - 1]
    out[start] = candle_close[valid[:length]].mean()

    for i in range(start + 1, n):
        out[i] = (
            out[i - 1]
            if np.isnan(candle_close[i])
            else (alpha * candle_close[i] + (1 - alpha) * out[i - 1])
        )

    return out


def rsi(data: pd.DataFrame, length: int = 14) -> np.ndarray:
    close = np.asarray(data["close"].values, dtype=float).ravel()
    delta = np.diff(close, prepend=np.nan)

    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)

    rs = avg_gain / avg_loss
    rsi_out = 100 - (100 / (1 + rs))

    return rsi_out


def compute_st_trend_from_config(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr_len: int,
    atr_mult: float,
    smooth_len: int,
) -> np.ndarray:
    source = ema(close, smooth_len) if smooth_len > 1 else close
    tr = true_range(high, low, close)
    atr = rma(tr, atr_len) * atr_mult

    n = len(close)
    supertrend = np.full(n, np.nan)
    trend = np.zeros(n, dtype=int)

    start = None
    for i in range(n):
        if not np.isnan(source[i]) and not np.isnan(atr[i]):
            supertrend[i] = source[i] - atr[i]
            trend[i] = 1
            start = i
            break
    if start is None:
        return trend

    for i in range(start + 1, n):
        if np.isnan(source[i]) or np.isnan(atr[i]):
            supertrend[i] = supertrend[i - 1]
            trend[i] = trend[i - 1]
            continue

        if trend[i - 1] == 1:
            if source[i] < supertrend[i - 1]:
                trend[i] = -1
                supertrend[i] = source[i] + atr[i]
            else:
                trend[i] = 1
                supertrend[i] = max(supertrend[i - 1], source[i] - atr[i])
        else:
            if source[i] > supertrend[i - 1]:
                trend[i] = 1
                supertrend[i] = source[i] - atr[i]
            else:
                trend[i] = -1
                supertrend[i] = min(supertrend[i - 1], source[i] + atr[i])

    return trend


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def ensure_output_dir(*parts: str) -> Path:
    path = PROJECT_ROOT.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


class MarketDataStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or ensure_output_dir("data_cache")

    def _cache_path(self, ticker: str, type: str) -> Path:
        interval_dir = self.base_dir / ("daily" if type == "D" else "weekly")
        interval_dir.mkdir(parents=True, exist_ok=True)
        safe_ticker = ticker.replace("/", "_")
        return interval_dir / f"{safe_ticker}.csv"

    def _read_cache(self, ticker: str, type: str) -> pd.DataFrame | None:
        cache_path = self._cache_path(ticker, type)
        if not cache_path.exists():
            return None

        df = pd.read_csv(cache_path, parse_dates=["time"])
        if df.empty:
            return None
        return df[["time", "open", "high", "low", "close", "volume"]]

    def _download(self, ticker: str, start: str, type: str) -> pd.DataFrame:
        df = yf.download(
            tickers=ticker,
            start=start,
            interval="1d" if type == "D" else "1wk",
            auto_adjust=False,
            progress=False,
        )

        if df.empty:
            raise ValueError(f"No data returned for ticker {ticker}")

        df = df.reset_index()
        df = df.rename(
            columns={
                "Date": "time",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return df[["time", "open", "high", "low", "close", "volume"]]

    def _write_cache(self, ticker: str, type: str, df: pd.DataFrame) -> None:
        cache_path = self._cache_path(ticker, type)
        df.to_csv(cache_path, index=False)

    def fetch_data(
        self,
        ticker: str,
        start: str = "1990-01-01",
        type: str = "W",
        *,
        refresh: bool = False,
    ) -> pd.DataFrame:
        cached = None if refresh else self._read_cache(ticker, type)
        if cached is None:
            cached = self._download(ticker, start, type)
            self._write_cache(ticker, type, cached)

        filtered = cached[cached["time"] >= pd.Timestamp(start)].copy()
        if filtered.empty:
            raise ValueError(f"No cached data returned for ticker {ticker} from {start}")
        return filtered.reset_index(drop=True)


default_data_store = MarketDataStore()


def get_fetch_data(
    *,
    refresh: bool = False,
    store: MarketDataStore | None = None,
) -> Callable[[str, str, str], pd.DataFrame]:
    active_store = store or default_data_store

    def _fetcher(ticker: str, start: str = "1990-01-01", type: str = "W") -> pd.DataFrame:
        return active_store.fetch_data(ticker, start=start, type=type, refresh=refresh)

    return _fetcher


def timestamped_output_path(strategy_name: str, suffix: str = ".txt") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ensure_output_dir(strategy_name, "outputs")
    return output_dir / f"{timestamp}{suffix}"


def latest_data_date(
    ticker: str,
    fetch_data_func=fetch_data,
    freq: str = "D",
) -> str:
    data = fetch_data_func(ticker, type=freq)
    last_value = pd.to_datetime(data["time"].iloc[-1])
    return last_value.strftime("%Y-%m-%d")


def shared_report_output_path(
    report_date: str,
    suffix: str = ".md",
) -> Path:
    output_dir = ensure_output_dir("reports")
    return output_dir / f"{report_date}{suffix}"


def initialize_shared_report(report_path: Path, title: str, generated_at: str) -> None:
    report = "\n".join(
        [
            f"# {title}",
            f"- Generated: `{generated_at}`",
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8")


def append_shared_report(report_path: Path, content: str) -> None:
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(content if content.endswith("\n") else f"{content}\n")
