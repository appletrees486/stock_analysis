#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수집 프로세스 재시작
"""

import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("🔄 수정된 코드로 수집을 재시작합니다...")
logging.info("💡 이전 프로세스는 수동으로 중단해주세요 (Ctrl+C)")
logging.info("")
logging.info("🚀 새로운 수집 시작:")

# 새로운 수집 시작
subprocess.run([sys.executable, "-c", "from stock_data_collector import StockDataCollector; collector = StockDataCollector(); collector.collect_all_stocks()"])

