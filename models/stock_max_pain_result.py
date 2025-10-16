"""
Stock Max Pain Result Model

This module defines the SQLAlchemy model for the stock_max_pain_results table.
This table stores max pain calculation results from CSV data processing,
including stock close prices and additional market data.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create the declarative base
Base = declarative_base()

class StockMaxPainResult(Base):
    """
    SQLAlchemy model for stock_max_pain_results table
    
    Represents max pain calculation results from CSV data processing,
    including stock close prices and additional market statistics.
    """
    
    __tablename__ = 'stock_max_pain_results'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Stock identifier (e.g., 'SPY.US')
    stock_code = Column(String(20), nullable=False, index=True)
    
    # Option expiry date
    expiry_date = Column(Date, nullable=False, index=True)
    
    # Stock close price at the time of calculation
    stock_close_price = Column(Float, nullable=False)
    
    # Max pain price based on volume
    max_pain_price_volume = Column(Float, nullable=False)
    
    # Max pain price based on open interest
    max_pain_price_open_interest = Column(Float, nullable=False)
    
    # Total volume sum
    sum_volume = Column(Integer, nullable=False)
    
    # Volume standard deviation for current strike ± 3 strikes
    volume_std_deviation = Column(Float, nullable=True)
    
    # Total open interest sum
    sum_open_interest = Column(Integer, nullable=False)
    
    # Calculation timestamp
    calculated_at = Column(DateTime, default=datetime.now, nullable=False)
    
    def __repr__(self):
        """String representation of the model"""
        return f"<StockMaxPainResult(stock_code='{self.stock_code}', expiry_date='{self.expiry_date}', max_pain_volume={self.max_pain_price_volume})>"
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'expiry_date': self.expiry_date,
            'stock_close_price': self.stock_close_price,
            'max_pain_price_volume': self.max_pain_price_volume,
            'max_pain_price_open_interest': self.max_pain_price_open_interest,
            'sum_volume': self.sum_volume,
            'volume_std_deviation': self.volume_std_deviation,
            'sum_open_interest': self.sum_open_interest,
            'calculated_at': self.calculated_at
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
        print("✅ Stock Max Pain Results 数据库表创建成功")
    
    @classmethod
    def save_stock_max_pain_results(cls, results_list):
        """
        Save a list of stock max pain results to database
        
        Args:
            results_list: List of dictionaries containing max pain results
            
        Returns:
            int: Number of records saved
        """
        if not results_list:
            print("⚠️ 没有数据需要保存")
            return 0
        
        session = cls.get_session()
        saved_count = 0
        
        try:
            for result_data in results_list:
                # Check if record already exists
                existing_record = session.query(cls).filter(
                    cls.stock_code == result_data['stock_code'],
                    cls.expiry_date == result_data['expiry_date']
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.stock_close_price = result_data['stock_close_price']
                    existing_record.max_pain_price_volume = result_data['max_pain_price_volume']
                    existing_record.max_pain_price_open_interest = result_data['max_pain_price_open_interest']
                    existing_record.sum_volume = result_data['sum_volume']
                    existing_record.volume_std_deviation = result_data['volume_std_deviation']
                    existing_record.sum_open_interest = result_data['sum_open_interest']
                    existing_record.calculated_at = datetime.now()
                    print(f"📝 更新记录: {result_data['stock_code']} - {result_data['expiry_date']}")
                else:
                    # Create new record
                    new_record = cls(
                        stock_code=result_data['stock_code'],
                        expiry_date=result_data['expiry_date'],
                        stock_close_price=result_data['stock_close_price'],
                        max_pain_price_volume=result_data['max_pain_price_volume'],
                        max_pain_price_open_interest=result_data['max_pain_price_open_interest'],
                        sum_volume=result_data['sum_volume'],
                        volume_std_deviation=result_data['volume_std_deviation'],
                        sum_open_interest=result_data['sum_open_interest']
                    )
                    session.add(new_record)
                    saved_count += 1
                    print(f"💾 新增记录: {result_data['stock_code']} - {result_data['expiry_date']}")
            
            session.commit()
            print(f"✅ 成功保存 {saved_count} 条新记录到 stock_max_pain_results 表")
            return saved_count
            
        except Exception as e:
            session.rollback()
            print(f"❌ 保存数据失败: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def get_all_results(cls):
        """Get all stock max pain results from database"""
        session = cls.get_session()
        try:
            results = session.query(cls).all()
            return [result.to_dict() for result in results]
        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
            return []
        finally:
            session.close()
    
    @classmethod
    def get_results_by_stock(cls, stock_code):
        """Get stock max pain results by stock code"""
        session = cls.get_session()
        try:
            results = session.query(cls).filter(cls.stock_code == stock_code).all()
            return [result.to_dict() for result in results]
        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
            return []
        finally:
            session.close()
    
    @classmethod
    def get_results_by_expiry_date(cls, expiry_date):
        """Get stock max pain results by expiry date"""
        session = cls.get_session()
        try:
            results = session.query(cls).filter(cls.expiry_date == expiry_date).all()
            return [result.to_dict() for result in results]
        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
            return []
        finally:
            session.close()
    
    @classmethod
    def delete_all_results(cls):
        """Delete all stock max pain results"""
        session = cls.get_session()
        try:
            deleted_count = session.query(cls).delete()
            session.commit()
            print(f"🗑️ 删除了 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            session.rollback()
            print(f"❌ 删除数据失败: {e}")
            return 0
        finally:
            session.close()


if __name__ == "__main__":
    # Test the model
    print("🧪 测试 StockMaxPainResult 模型...")
    
    # Create tables
    StockMaxPainResult.create_tables()
    
    # Test data
    test_data = [{
        'stock_code': 'SPY.US',
        'expiry_date': datetime(2024, 1, 19).date(),
        'stock_close_price': 450.0,
        'max_pain_price_volume': 440.0,
        'max_pain_price_open_interest': 445.0,
        'sum_volume': 100000,
        'volume_std_deviation': 123.45,
        'sum_open_interest': 200000
    }]
    
    # Test save
    saved_count = StockMaxPainResult.save_stock_max_pain_results(test_data)
    print(f"保存了 {saved_count} 条测试记录")
    
    # Test query
    all_results = StockMaxPainResult.get_all_results()
    print(f"查询到 {len(all_results)} 条记录")
    
    print("✅ 模型测试完成!")
