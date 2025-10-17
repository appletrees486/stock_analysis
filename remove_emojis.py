#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_blog.py에서 이모지를 제거하는 스크립트
"""

import re
import os

def remove_emojis_from_file(file_path):
    """파일에서 이모지를 제거합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 이모지 패턴 (유니코드 범위)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
            "\U00002600-\U000026FF"  # miscellaneous symbols
            "\U0001F000-\U0001F02F"  # mahjong tiles
            "\U0001F0A0-\U0001F0FF"  # playing cards
            "]+", flags=re.UNICODE)
        
        # 이모지 제거
        content_without_emojis = emoji_pattern.sub('', content)
        
        # 백업 파일 생성
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 원본 파일에 이모지 제거된 내용 쓰기
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_without_emojis)
        
        print(f"OK: {file_path}에서 이모지 제거 완료")
        print(f"   백업 파일: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {file_path} 처리 실패: {e}")
        return False

def main():
    """메인 함수"""
    auto_blog_path = "blog_auto/auto_blog.py"
    
    if os.path.exists(auto_blog_path):
        print(f"{auto_blog_path}에서 이모지 제거 중...")
        remove_emojis_from_file(auto_blog_path)
    else:
        print(f"ERROR: 파일을 찾을 수 없습니다: {auto_blog_path}")

if __name__ == "__main__":
    main()
