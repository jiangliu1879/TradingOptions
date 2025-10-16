# Service 模块使用说明

## 📁 文件说明

### 1. `get_realtime_options_data.py`
**实时期权数据获取服务**
- 从 LongPort API 获取实时期权数据
- 自动保存到数据库
- 支持美东时间获取
- 包含完整的错误处理

**使用方法:**
```bash
python3 service/get_realtime_options_data.py
```

### 2. `calculate_max_pain_from_db.py`
**从数据库计算最大痛点价格**
- 从 `options_data` 表读取期权数据
- 按 `stock_code`、`expiry_date`、`update_time` 分组
- 计算每个分组的最大痛点价格
- 参考 `utils/calculate_max_pain.py` 的逻辑

**使用方法:**
```bash
python3 service/calculate_max_pain_from_db.py
```

**输出文件:**
- `/data/result/max_pain_results_from_db.csv`

### 3. `analyze_max_pain.py`
**最大痛点分析工具**
- 分析最大痛点计算结果
- 与CSV文件结果进行比较
- 提供详细的期权数据统计

**使用方法:**
```bash
python3 service/analyze_max_pain.py
```

## 🔄 工作流程

### 完整的数据处理流程:

1. **获取实时期权数据**
   ```bash
   python3 service/get_realtime_options_data.py
   ```

2. **计算最大痛点价格**
   ```bash
   python3 service/calculate_max_pain_from_db.py
   ```

3. **分析结果**
   ```bash
   python3 service/analyze_max_pain.py
   ```

## 📊 输出数据格式

### 最大痛点结果 CSV 格式:
```csv
stock_code,expiry_date,update_time,max_pain_price_volume,max_pain_price_open_interest,min_earn_volume,min_earn_open_interest,options_count
SPY.US,2025-10-13,2025-10-14 09:23:52,500.0,660.0,0,92548,127
```

### 字段说明:
- `stock_code`: 股票代码
- `expiry_date`: 到期日期
- `update_time`: 数据更新时间
- `max_pain_price_volume`: 基于成交量的最大痛点价格
- `max_pain_price_open_interest`: 基于持仓量的最大痛点价格
- `min_earn_volume`: 最小成交量收益
- `min_earn_open_interest`: 最小持仓量收益
- `options_count`: 期权数量

## 🎯 最大痛点计算逻辑

### 算法说明:
1. **数据分组**: 按股票代码、到期日期、更新时间分组
2. **遍历行权价**: 假设股价在每个行权价到期
3. **计算卖方收益**:
   - Put期权卖方收益 = 高于当前价格的Put期权持仓量
   - Call期权卖方收益 = 低于当前价格的Call期权持仓量
4. **找最大痛点**: 卖方收益最小的价格点

### 两种计算方式:
- **基于成交量**: 使用 `volume` 字段计算
- **基于持仓量**: 使用 `open_interest` 字段计算

## 📈 实际运行结果示例

```
🚀 开始从数据库计算最大痛点价格
============================================================
📊 从数据库获取期权数据...
✅ 成功获取 508 条期权数据记录
🔄 处理期权数据，按股票代码、到期日、更新时间分组...
✅ 数据分组完成，共 1 个股票代码
🧮 开始计算最大痛点价格...

期权数据按股票代码、到期日、更新时间分组:

股票代码: SPY.US
  到期日: 2025-10-13
    更新时间: 2025-10-14 09:23:52
    期权数量: 127
      基于Volume - 最小收益: 0, 最大痛点价格: $500
      基于Open Interest - 最小收益: 92,548, 最大痛点价格: $660
      ----------------------------------------

✅ 最大痛点结果已保存到: /data/result/max_pain_results_from_db.csv
📊 共处理 2 个数据分组

📈 统计信息:
   - 涉及股票代码: 1
   - 涉及到期日期: 1
   - 涉及更新时间: 2
   - Volume最大痛点价格范围: $500 - $500
   - Open Interest最大痛点价格范围: $660 - $660
```

## 🔧 配置说明

### 数据库配置:
- 数据库文件: `us_market_data.db`
- 期权数据表: `options_data`
- 自动创建表结构

### API 配置:
- 使用 LongPort API
- 需要配置环境变量
- 支持美股期权数据

## 🚨 注意事项

1. **数据依赖**: 确保数据库中有期权数据
2. **时间格式**: 使用美东时间
3. **文件路径**: 确保输出目录存在
4. **API限制**: 注意API调用频率限制

## 🔄 扩展功能

### 可以添加的功能:
1. **定时任务**: 自动获取数据和计算最大痛点
2. **多股票支持**: 支持多个股票代码
3. **历史分析**: 分析最大痛点变化趋势
4. **预警系统**: 当最大痛点变化时发送通知
5. **可视化**: 生成最大痛点图表
