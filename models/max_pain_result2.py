"""
Max Pain Result Model

This module defines the SQLAlchemy model for the max_pain_results table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create the declarative base
Base = declarative_base()

class MaxPainResult2(Base):
    """
    SQLAlchemy model for max_pain_results2 table
    
    Represents max pain calculation results including stock code, expiry date,
    update time, max pain prices, volume statistics, and variance.
    """
    
    __tablename__ = 'max_pain_results2'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock identifier (e.g., 'SPY.US')
    stock_code = Column(String(20), nullable=False, index=True)
    
    # Option expiry date
    expiry_date = Column(Date, nullable=False, index=True)
    
    # Update timestamp
    update_time = Column(String(50), nullable=False, index=True)
    
    # Max pain price based on volume
    max_pain_price_volume = Column(Float, nullable=False)
    
    # Max pain price based on open interest
    max_pain_price_open_interest = Column(Float, nullable=False)
    
    # Total volume sum
    sum_volume = Column(Integer, nullable=False)
    
    # Total open interest sum
    sum_open_interest = Column(Integer, nullable=False)
    
    # Stock price at the time of calculation
    stock_price = Column(Float, nullable=False, default=0)

    # Volume strike price
    volume_strike_price = Column(Float, nullable=True, default=0)

    # Open interest strike price
    open_interest_strike_price = Column(Float, nullable=True, default=0)
    
    def __repr__(self):
        """String representation of the model"""
        return f"<MaxPainResult(stock_code='{self.stock_code}', expiry_date='{self.expiry_date}', max_pain_volume={self.max_pain_price_volume})>"
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'expiry_date': self.expiry_date,
            'update_time': self.update_time,
            'max_pain_price_volume': self.max_pain_price_volume,
            'max_pain_price_open_interest': self.max_pain_price_open_interest,
            'sum_volume': self.sum_volume,
            'sum_open_interest': self.sum_open_interest,
            'stock_price': self.stock_price,
            'volume_strike_price': self.volume_strike_price,
            'open_interest_strike_price': self.open_interest_strike_price,
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
    def get_session(cls):
        """Get SQLAlchemy session"""
        engine = cls.get_engine()
        Session = sessionmaker(bind=engine)
        return Session()
    
    @classmethod
    def create_tables(cls):
        """Create all tables"""
        engine = cls.get_engine()
        Base.metadata.create_all(engine)
        print("✅ Max Pain Results2 数据库表创建成功")
    
    @classmethod
    def save_max_pain_results2(cls, results_list):
        """
        Save a list of max pain results2 to database
        
        Args:
            results_list (list): List of max pain result dictionaries
            
        Returns:
            int: Number of records saved
        """
        if not results_list:
            return 0
            
        session = cls.get_session()
        try:
            saved_count = 0
            for result_data in results_list:
                # Check if record already exists (avoid duplicates)
                existing = (session.query(cls)
                           .filter(cls.stock_code == result_data['stock_code'])
                           .filter(cls.expiry_date == result_data['expiry_date'])
                           .filter(cls.update_time == result_data['update_time'])
                           .first())
                
                if not existing:
                    result_record = cls(**result_data)
                    session.add(result_record)
                    saved_count += 1
            
            session.commit()
            print(f"✅ 成功保存 {saved_count} 条最大痛点结果记录")
            return saved_count
        except Exception as e:
            session.rollback()
            print(f"❌ 保存最大痛点结果时出错: {e}")
            return 0
        finally:
            session.close()
    
    @classmethod
    def get_max_pain_results2(cls, stock_code=None, expiry_date=None, 
                            start_date=None, end_date=None, limit=None):
        """
        Query max pain results2 with optional filters
        
        Args:
            stock_code (str): Filter by specific stock code
            expiry_date (date): Filter by expiry date
            start_date (str): Filter by start date (YYYY-MM-DD format)
            end_date (str): Filter by end date (YYYY-MM-DD format)
            limit (int): Limit number of results
            
        Returns:
            list: List of MaxPainResult2 objects
        """
        session = cls.get_session()
        try:
            query = session.query(cls)
            
            if stock_code:
                query = query.filter(cls.stock_code == stock_code)
            
            if expiry_date:
                query = query.filter(cls.expiry_date == expiry_date)
            
            if start_date:
                query = query.filter(cls.update_time >= start_date)
            
            if end_date:
                query = query.filter(cls.update_time <= end_date)
            
            query = query.order_by(cls.stock_code, cls.expiry_date, cls.update_time)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        finally:
            session.close()
    
    @classmethod
    def get_latest_max_pain_results2(cls, stock_code, expiry_date=None):
        """
        Get the latest max pain results2 for a specific stock
        
        Args:
            stock_code (str): Stock code to query
            expiry_date (date): Optional expiry date filter
            
        Returns:
            list: List of latest MaxPainResult2 objects
        """
        session = cls.get_session()
        try:
            # Get the latest update_time for the stock
            latest_time_query = (session.query(cls.update_time)
                                .filter(cls.stock_code == stock_code))
            
            if expiry_date:
                latest_time_query = latest_time_query.filter(cls.expiry_date == expiry_date)
            
            latest_time = latest_time_query.order_by(cls.update_time.desc()).first()
            
            if not latest_time:
                return []
            
            # Get all max pain results for the latest update time
            query = (session.query(cls)
                    .filter(cls.stock_code == stock_code)
                    .filter(cls.update_time == latest_time[0]))
            
            if expiry_date:
                query = query.filter(cls.expiry_date == expiry_date)
            
            return query.order_by(cls.expiry_date).all()
        finally:
            session.close()
    
    @classmethod
    def get_stock_codes(cls):
        """
        Get all unique stock codes in the max pain results2 database
        
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
    def get_expiry_dates(cls, stock_code=None):
        """
        Get all unique expiry dates in the max pain results2 database
        
        Args:
            stock_code (str): Optional stock code filter
            
        Returns:
            list: List of unique expiry dates
        """
        session = cls.get_session()
        try:
            query = session.query(cls.expiry_date).distinct()
            if stock_code:
                query = query.filter(cls.stock_code == stock_code)
            
            result = query.order_by(cls.expiry_date).all()
            return [row[0] for row in result]
        finally:
            session.close()
    
    @classmethod
    def get_all_results(cls):
        """Get all max pain results2 from database"""
        session = cls.get_session()
        try:
            results = session.query(cls).all()
            return [result.to_dict() for result in results]
        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
            return []
        finally:
            session.close()


if __name__ == "__main__":
    # 演示 MaxPainResult2 类的各种方法
    print("🚀 执行 MaxPainResult2 类方法演示")
    print("=" * 50)
    
    # 1. 创建数据库表
    print("📊 创建数据库表:")
    MaxPainResult2.create_tables()
    print()
    
    # 2. 获取所有股票代码
    print("📊 获取所有最大痛点结果股票代码:")
    stock_codes = MaxPainResult2.get_stock_codes()
    print(f"   {stock_codes}")
    print()
    
    # 3. 获取所有到期日期
    print("📅 获取所有到期日期:")
    expiry_dates = MaxPainResult2.get_expiry_dates()
    print(f"   {expiry_dates}")
    print()
    
    print("✅ 演示完成！")
