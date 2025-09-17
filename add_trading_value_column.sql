-- daily_data 테이블에 거래대금 컬럼 추가
-- 거래대금 = 거래량 × 종가

ALTER TABLE daily_data 
ADD COLUMN trading_value BIGINT NULL COMMENT '거래대금 (거래량 × 종가)' 
AFTER volume;

-- 기존 데이터에 거래대금 계산하여 업데이트
UPDATE daily_data 
SET trading_value = volume * close 
WHERE trading_value IS NULL;

-- 거래대금 컬럼에 인덱스 추가 (거래대금 랭킹 조회용)
CREATE INDEX idx_trading_value ON daily_data(trading_value DESC);

-- 컬럼 추가 확인
DESCRIBE daily_data;
