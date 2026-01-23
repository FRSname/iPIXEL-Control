"""
Stock API Client for iPIXEL Controller
"""

from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger()


class StockAPI:
    """Handles interaction with Yahoo Finance API via yfinance"""
    
    def __init__(self):
        """Initialize Stock API client"""
        self._yf = None
        
    def _get_yf(self):
        """Lazy initialization of yfinance"""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                logger.error("yfinance not installed")
                raise ImportError("yfinance library not installed. Please run: pip install yfinance")
        return self._yf

    def get_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch current stock data
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Dictionary containing ticker, name, price, change, change_percent, and previous_close
        """
        yf = self._get_yf()
        logger.info(f"Fetching stock data for: {ticker}")
        
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            # Get current price and change
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            
            if current_price is None:
                logger.warning(f"Could not fetch data for ticker: {ticker}")
                raise ValueError(f"Could not fetch data for {ticker}. Check ticker symbol.")
                
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            result = {
                'ticker': ticker.upper(),
                'name': info.get('shortName', ticker.upper()),
                'price': current_price,
                'change': change,
                'change_percent': change_percent,
                'previous_close': previous_close
            }
            
            logger.info(f"Successfully fetched stock data for {result['name']}")
            return result
            
        except Exception as e:
            logger.error(f"Stock data fetch failed for {ticker}: {e}")
            raise
