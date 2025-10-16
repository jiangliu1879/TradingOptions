"""
Stock Data Model

This module defines the SQLAlchemy model for the stock_data table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create the declarative base
Base = declarative_base()

class StockData(Base):
    """
    SQLAlchemy model for stock_data table
    
    Represents historical stock price data including OHLCV (Open, High, Low, Close, Volume)
    and additional metrics like turnover.
    """
    
    __tablename__ = 'stock_data'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock identifier (e.g., 'NVDA.US', 'SPY.US')
    stock_code = Column(String(20), nullable=False, index=True)
    
    # Timestamp of the data point
    timestamp = Column(String(50), nullable=False, index=True)
    
    # OHLC (Open, High, Low, Close) prices
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    
    # Volume and turnover
    volume = Column(Integer, nullable=False)
    turnover = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        """String representation of the model"""
        return f"<StockData(stock_code='{self.stock_code}', timestamp='{self.timestamp}', close={self.close})>"
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'turnover': self.turnover,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_database_url(cls):
        """Get database URL from environment or default"""
        db_path = os.getenv('DATABASE_URL', 'sqlite:///us_market_data.db')
        return db_path
    
    @classmethod
    def get_engine(cls):
        """Get SQLAlchemy engine"""
        database_url = cls.get_database_url()
        return create_engine(database_url, echo=False)
    
    @classmethod
    def create_tables(cls):
        """Create all tables"""
        engine = cls.get_engine()
        Base.metadata.create_all(engine)
        print("✅ 股票数据表创建成功")
    
    @classmethod
    def get_session(cls):
        """Get SQLAlchemy session"""
        engine = cls.get_engine()
        Session = sessionmaker(bind=engine)
        return Session()
    
    @classmethod
    def get_stock_data(cls, stock_code=None, start_date=None, end_date=None, limit=None):
        """
        Query stock data with optional filters
        
        Args:
            stock_code (str): Filter by specific stock code
            start_date (str): Filter by start date (YYYY-MM-DD format)
            end_date (str): Filter by end date (YYYY-MM-DD format)
            limit (int): Limit number of results
            
        Returns:
            list: List of StockData objects
        """
        session = cls.get_session()
        try:
            query = session.query(cls)
            
            if stock_code:
                query = query.filter(cls.stock_code == stock_code)
            
            if start_date:
                query = query.filter(cls.timestamp >= start_date)
            
            if end_date:
                query = query.filter(cls.timestamp <= end_date)
            
            query = query.order_by(cls.stock_code, cls.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        finally:
            session.close()
    
    @classmethod
    def get_latest_price(cls, stock_code):
        """
        Get the latest price for a specific stock
        
        Args:
            stock_code (str): Stock code to query
            
        Returns:
            StockData: Latest stock data record or None
        """
        session = cls.get_session()
        try:
            return (session.query(cls)
                    .filter(cls.stock_code == stock_code)
                    .order_by(cls.timestamp.desc())
                    .first())
        finally:
            session.close()
    
    @classmethod
    def get_stock_codes(cls):
        """
        Get all unique stock codes in the database
        
        Returns:
            list: List of unique stock codes
        """
        session = cls.get_session()
        try:
            result = session.query(cls.stock_code).distinct().all()
            return [row[0] for row in result]
        finally:
            session.close()
    
    @classmethod
    def get_price_range(cls, stock_code, start_date, end_date):
        """
        Get price range (min/max) for a stock in a date range
        
        Args:
            stock_code (str): Stock code to query
            start_date (str): Start date (YYYY-MM-DD format)
            end_date (str): End date (YYYY-MM-DD format)
            
        Returns:
            dict: Dictionary with min_price, max_price, and price_range
        """
        session = cls.get_session()
        try:
            result = (session.query(cls)
                     .filter(cls.stock_code == stock_code)
                     .filter(cls.timestamp >= start_date)
                     .filter(cls.timestamp <= end_date)
                     .all())
            
            if not result:
                return None
            
            prices = [record.close for record in result]
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price
            
            return {
                'min_price': min_price,
                'max_price': max_price,
                'price_range': price_range,
                'records_count': len(result)
            }
        finally:
            session.close()
    

if __name__ == "__main__":
    # 演示 StockData 类的各种方法
    print("🚀 执行 StockData 类方法演示")
    print("=" * 50)
    
    # 1. 获取所有股票代码
    print("📊 获取所有股票代码:")
    stock_codes = StockData.get_stock_codes()
    print(f"   {stock_codes}")
    print()
    
    # 2. 获取NVDA的最新价格
    print("📈 获取NVDA最新价格:")
    latest_nvda = StockData.get_latest_price('NVDA.US')
    if latest_nvda:
        print(f"   {latest_nvda.stock_code}: ${latest_nvda.close:.2f} ({latest_nvda.timestamp})")
    print()
    
    # 3. 获取SPY的最近5条数据
    print("📊 获取SPY最近5条数据:")
    spy_data = StockData.get_stock_data(stock_code='SPY.US', limit=5)
    for i, record in enumerate(spy_data):
        print(f"   {i+1}. {record.timestamp}: ${record.close:.2f}")
    print()
    
    # 4. 获取QQQ 2023年的价格区间
    print("📈 获取QQQ 2023年价格区间:")
    qqq_range = StockData.get_price_range('QQQ.US', '2023-01-01', '2023-12-31')
    if qqq_range:
        print(f"   最低价: ${qqq_range['min_price']:.2f}")
        print(f"   最高价: ${qqq_range['max_price']:.2f}")
        print(f"   价格区间: ${qqq_range['price_range']:.2f}")
        print(f"   记录数: {qqq_range['records_count']}")
    print()
    
    # 5. 显示所有股票的最新价格
    print("💰 所有股票最新价格:")
    for code in stock_codes:
        latest = StockData.get_latest_price(code)
        if latest:
            print(f"   {code}: ${latest.close:.2f}")
    
    print("\n✅ 演示完成！")
