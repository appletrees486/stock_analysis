-- 블로그 자동 작성 기능을 위한 컬럼 추가
-- batch_schedules 테이블에 블로그 작성 상태 추적 컬럼 추가

USE stock_analysis;

-- 1. 블로그 작성 완료 여부
ALTER TABLE batch_schedules 
ADD COLUMN blog_written BOOLEAN DEFAULT FALSE COMMENT '블로그 작성 완료 여부';

-- 2. 블로그 작성 시간
ALTER TABLE batch_schedules 
ADD COLUMN blog_written_at DATETIME NULL COMMENT '블로그 작성 시간';

-- 3. 블로그 포스트 URL (선택사항)
ALTER TABLE batch_schedules 
ADD COLUMN blog_post_url VARCHAR(500) NULL COMMENT '작성된 블로그 포스트 URL';

-- 4. 블로그 작성 실패 사유 (선택사항)
ALTER TABLE batch_schedules 
ADD COLUMN blog_error_message TEXT NULL COMMENT '블로그 작성 실패 사유';

-- 인덱스 추가 (성능 최적화)
CREATE INDEX idx_blog_written ON batch_schedules(blog_written);
CREATE INDEX idx_blog_written_at ON batch_schedules(blog_written_at);

-- 기존 레코드 초기화
UPDATE batch_schedules 
SET blog_written = FALSE, 
    blog_written_at = NULL, 
    blog_post_url = NULL, 
    blog_error_message = NULL;

-- 변경사항 확인
SELECT 
    id, 
    schedule_name, 
    collection_completed, 
    ranking_extracted, 
    analysis_started,
    blog_written,
    blog_written_at
FROM batch_schedules 
ORDER BY id DESC 
LIMIT 5;

