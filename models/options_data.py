"""
Options Data Model

This module defines the SQLAlchemy model for the options_data table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import os

# Create the declarative base
Base = declarative_base()

class OptionsData(Base):
    """
    SQLAlchemy model for options_data table
    
    Represents real-time options data including strike price, volume, turnover,
    open interest, implied volatility, and contract details.
    """
    
    __tablename__ = 'options_data'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock identifier (e.g., 'SPY.US')
    stock_code = Column(String(20), nullable=False, index=True)
    
    # Option expiry date
    expiry_date = Column(Date, nullable=False, index=True)
    
    # Option symbol
    symbol = Column(String(50), nullable=False, index=True)
    
    # Update timestamp
    update_time = Column(String(50), nullable=False, index=True)
    
    # Option type (call/put)
    type = Column(String(10), nullable=False, index=True)
    
    # Strike price
    strike_price = Column(Float, nullable=False)
    
    # Volume
    volume = Column(Integer, nullable=True)
    
    # Turnover
    turnover = Column(Float, nullable=True)
    
    # Open interest
    open_interest = Column(Integer, nullable=True)
    
    # Implied volatility
    implied_volatility = Column(Float, nullable=True)
    
    # Contract size
    contract_size = Column(Integer, nullable=True)
    
    def __repr__(self):
        """String representation of the model"""
        return f"<OptionsData(stock_code='{self.stock_code}', symbol='{self.symbol}', type='{self.type}', strike={self.strike_price})>"
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'expiry_date': self.expiry_date,
            'symbol': self.symbol,
            'update_time': self.update_time,
            'type': self.type,
            'strike_price': self.strike_price,
            'volume': self.volume,
            'turnover': self.turnover,
            'open_interest': self.open_interest,
            'implied_volatility': self.implied_volatility,
            'contract_size': self.contract_size
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
        print("✅ 数据库表创建成功")
    
    @classmethod
    def save_options_data(cls, options_list):
        """
        Save a list of options data to database
        
        Args:
            options_list (list): List of option data dictionaries
            
        Returns:
            int: Number of records saved
        """
        if not options_list:
            return 0
            
        session = cls.get_session()
        try:
            saved_count = 0
            for option_data in options_list:
                # Check if record already exists (avoid duplicates)
                existing = (session.query(cls)
                           .filter(cls.stock_code == option_data['stock_code'])
                           .filter(cls.symbol == option_data['symbol'])
                           .filter(cls.update_time == option_data['update_time'])
                           .first())
                
                if not existing:
                    option_record = cls(**option_data)
                    session.add(option_record)
                    saved_count += 1
            
            session.commit()
            print(f"✅ 成功保存 {saved_count} 条期权数据记录")
            return saved_count
        except Exception as e:
            session.rollback()
            print(f"❌ 保存期权数据时出错: {e}")
            return 0
        finally:
            session.close()
    
    @classmethod
    def get_options_data(cls, stock_code=None, expiry_date=None, option_type=None, 
                        update_time=None, start_date=None, end_date=None, limit=None):
        """
        Query options data with optional filters
        
        Args:
            stock_code (str): Filter by specific stock code
            expiry_date (date): Filter by expiry date
            option_type (str): Filter by option type (call/put)
            update_time (str): Filter by exact update time (YYYY-MM-DD HH:MM:SS format)
            start_date (str): Filter by start date (YYYY-MM-DD format)
            end_date (str): Filter by end date (YYYY-MM-DD format)
            limit (int): Limit number of results
            
        Returns:
            list: List of OptionsData objects
        """
        session = cls.get_session()
        try:
            query = session.query(cls)
            
            if stock_code:
                query = query.filter(cls.stock_code == stock_code)
            
            if expiry_date:
                query = query.filter(cls.expiry_date == expiry_date)
            
            if option_type:
                query = query.filter(cls.type == option_type)
            
            if update_time:
                query = query.filter(cls.update_time == update_time)
            
            if start_date:
                query = query.filter(cls.update_time >= start_date)
            
            if end_date:
                query = query.filter(cls.update_time <= end_date)
            
            query = query.order_by(cls.stock_code, cls.expiry_date, cls.strike_price, cls.type)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        finally:
            session.close()
    
    @classmethod
    def get_latest_options_data(cls, stock_code, expiry_date=None):
        """
        Get the latest options data for a specific stock
        
        Args:
            stock_code (str): Stock code to query
            expiry_date (date): Optional expiry date filter
            
        Returns:
            list: List of latest OptionsData objects
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
            
            # Get all options data for the latest update time
            query = (session.query(cls)
                    .filter(cls.stock_code == stock_code)
                    .filter(cls.update_time == latest_time[0]))
            
            if expiry_date:
                query = query.filter(cls.expiry_date == expiry_date)
            
            return query.order_by(cls.strike_price, cls.type).all()
        finally:
            session.close()
    
    @classmethod
    def get_stock_codes(cls):
        """
        Get all unique stock codes in the options database
        
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
        Get all unique expiry dates in the options database
        
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
    def get_strike_price_range(cls, stock_code, expiry_date):
        """
        Get strike price range for a specific stock and expiry date
        
        Args:
            stock_code (str): Stock code to query
            expiry_date (date): Expiry date
            
        Returns:
            dict: Dictionary with min_strike, max_strike, and strike_range
        """
        session = cls.get_session()
        try:
            result = (session.query(cls)
                     .filter(cls.stock_code == stock_code)
                     .filter(cls.expiry_date == expiry_date)
                     .all())
            
            if not result:
                return None
            
            strike_prices = [record.strike_price for record in result]
            min_strike = min(strike_prices)
            max_strike = max(strike_prices)
            strike_range = max_strike - min_strike
            
            return {
                'min_strike': min_strike,
                'max_strike': max_strike,
                'strike_range': strike_range,
                'records_count': len(result)
            }
        finally:
            session.close()
    
    @classmethod
    def delete_by_expiry_date(cls, expiry_date, stock_code=None):
        """
        Delete options data by expiry date
        
        Args:
            expiry_date (date): Expiry date to delete
            stock_code (str): Optional stock code filter
            
        Returns:
            int: Number of records deleted
        """
        session = cls.get_session()
        try:
            query = session.query(cls).filter(cls.expiry_date == expiry_date)
            
            if stock_code:
                query = query.filter(cls.stock_code == stock_code)
            
            # Count records before deletion
            count = query.count()
            
            # Delete records
            query.delete(synchronize_session=False)
            session.commit()
            
            print(f"✅ 成功删除 {count} 条到期日期为 {expiry_date} 的期权数据记录")
            return count
        except Exception as e:
            session.rollback()
            print(f"❌ 删除期权数据时出错: {e}")
            return 0
        finally:
            session.close()


if __name__ == "__main__":
    # 删除到期日期为 2025-12-17 的数据
    print("🗑️  删除到期日期为 2025-12-17 的期权数据")
    print("=" * 50)
    
    expiry_date_to_delete = date(2025, 12, 17)
    
    # 先查看有多少条记录
    records_before = OptionsData.get_options_data(expiry_date=expiry_date_to_delete)
    print(f"📊 找到 {len(records_before)} 条到期日期为 {expiry_date_to_delete} 的记录")
    
    if len(records_before) > 0:
        # 执行删除
        deleted_count = OptionsData.delete_by_expiry_date(expiry_date_to_delete)
        print(f"✅ 删除完成！共删除 {deleted_count} 条记录")
    else:
        print("ℹ️  没有找到需要删除的记录")
    
    print("=" * 50)
