-- daily_data 테이블 컬럼명 변경
-- shares_at_date -> outstanding_shares
-- market_cap_at_date -> market_cap

USE stock_analysis;

-- 1. shares_at_date 컬럼명을 outstanding_shares로 변경
ALTER TABLE daily_data CHANGE COLUMN shares_at_date outstanding_shares bigint;

-- 2. market_cap_at_date 컬럼명을 market_cap으로 변경  
ALTER TABLE daily_data CHANGE COLUMN market_cap_at_date market_cap decimal(20,2);

-- 3. 변경 결과 확인
DESCRIBE daily_data;
