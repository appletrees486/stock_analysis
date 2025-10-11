#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 관리 API 엔드포인트
4단계: 웹 인터페이스 구현
"""

from flask import Blueprint, request, jsonify, render_template
from typing import Dict, Any, Optional
import json
from datetime import datetime

# 프롬프트 관리자 import
try:
    from prompt_manager import PromptManager, UnifiedConfigManager
    from config import config
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False

# Blueprint 생성
prompt_bp = Blueprint('prompt', __name__, url_prefix='/api/prompts')

def get_config_manager():
    """설정 관리자 인스턴스 반환"""
    if not PROMPT_MANAGER_AVAILABLE:
        return None
    
    try:
        db_config = config.get_database_config()
        return UnifiedConfigManager(db_config)
    except Exception as e:
        print(f"❌ 설정 관리자 초기화 실패: {e}")
        return None

@prompt_bp.route('/', methods=['GET'])
def get_prompts():
    """모든 프롬프트 조회"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # 모든 차트 유형의 프롬프트 조회
        chart_types = ['일봉', '주봉', '월봉', '일봉 요약', '주봉 요약', '월봉 요약', '태그']
        prompts_data = {}
        
        for chart_type in chart_types:
            versions = config_manager.prompt_manager.get_prompt_versions(chart_type)
            prompts_data[chart_type] = versions
        
        return jsonify({
            "success": True,
            "prompts": prompts_data,
            "total_categories": len(chart_types)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/<chart_type>', methods=['GET'])
def get_prompt_by_type(chart_type):
    """특정 차트 유형의 프롬프트 조회"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # URL 디코딩 및 차트 타입 정규화
        from urllib.parse import unquote
        chart_type = unquote(chart_type)
        
        # 프롬프트 내용 조회
        prompt_content = config_manager.prompt_manager.get_prompt(chart_type)
        
        # 버전 정보 조회
        versions = config_manager.prompt_manager.get_prompt_versions(chart_type)
        
        return jsonify({
            "success": True,
            "chart_type": chart_type,
            "prompt_content": prompt_content,
            "versions": versions,
            "current_version": versions[0] if versions else None
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/<chart_type>', methods=['PUT'])
def update_prompt(chart_type):
    """프롬프트 업데이트"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # URL 디코딩 및 차트 타입 정규화
        from urllib.parse import unquote
        chart_type = unquote(chart_type)
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 없습니다."
            }), 400
        
        content = data.get('content')
        version = data.get('version')
        created_by = data.get('created_by', 'web_user')
        
        if not content:
            return jsonify({
                "success": False,
                "error": "프롬프트 내용이 필요합니다."
            }), 400
        
        # 프롬프트 업데이트
        success = config_manager.prompt_manager.update_prompt(
            chart_type, content, version, created_by
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": f"{chart_type} 프롬프트가 업데이트되었습니다.",
                "chart_type": chart_type,
                "version": version or "자동생성"
            })
        else:
            return jsonify({
                "success": False,
                "error": "프롬프트 업데이트에 실패했습니다."
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/<chart_type>/versions', methods=['GET'])
def get_prompt_versions(chart_type):
    """특정 차트 유형의 프롬프트 버전 목록 조회"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # URL 디코딩 및 차트 타입 정규화
        from urllib.parse import unquote
        chart_type = unquote(chart_type)
        
        versions = config_manager.prompt_manager.get_prompt_versions(chart_type)
        
        return jsonify({
            "success": True,
            "chart_type": chart_type,
            "versions": versions,
            "total_versions": len(versions)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/<chart_type>/versions/<int:version_id>', methods=['DELETE'])
def delete_prompt_version(chart_type, version_id):
    """프롬프트 버전 삭제 (비활성화)"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # URL 디코딩 및 차트 타입 정규화
        from urllib.parse import unquote
        chart_type = unquote(chart_type)
        
        success = config_manager.prompt_manager.delete_prompt_version(version_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"프롬프트 버전이 비활성화되었습니다.",
                "chart_type": chart_type,
                "version_id": version_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "프롬프트 버전 비활성화에 실패했습니다."
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/<chart_type>/preview', methods=['POST'])
def preview_prompt(chart_type):
    """프롬프트 미리보기 (실제 저장하지 않고 내용만 반환)"""
    try:
        # URL 디코딩 및 차트 타입 정규화
        from urllib.parse import unquote
        chart_type = unquote(chart_type)
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 없습니다."
            }), 400
        
        content = data.get('content')
        if not content:
            return jsonify({
                "success": False,
                "error": "프롬프트 내용이 필요합니다."
            }), 400
        
        # 미리보기용 응답 (실제 저장하지 않음)
        return jsonify({
            "success": True,
            "message": "프롬프트 미리보기",
            "chart_type": chart_type,
            "content_length": len(content),
            "preview": content[:200] + "..." if len(content) > 200 else content
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@prompt_bp.route('/categories', methods=['GET'])
def get_categories():
    """프롬프트 카테고리 목록 조회"""
    try:
        config_manager = get_config_manager()
        if not config_manager:
            return jsonify({
                "success": False, 
                "error": "프롬프트 관리자가 사용할 수 없습니다."
            }), 500
        
        # 카테고리 정보 조회
        categories = [
            {"name": "일봉", "description": "일봉 차트 분석용 프롬프트", "sort_order": 1},
            {"name": "주봉", "description": "주봉 차트 분석용 프롬프트", "sort_order": 2},
            {"name": "월봉", "description": "월봉 차트 분석용 프롬프트", "sort_order": 3},
            {"name": "일봉 요약", "description": "일봉 분석 결과 요약용 프롬프트", "sort_order": 4},
            {"name": "주봉 요약", "description": "주봉 분석 결과 요약용 프롬프트", "sort_order": 5},
            {"name": "월봉 요약", "description": "월봉 분석 결과 요약용 프롬프트", "sort_order": 6},
            {"name": "태그", "description": "태그 분석용 프롬프트", "sort_order": 7}
        ]
        
        return jsonify({
            "success": True,
            "categories": categories,
            "total_categories": len(categories)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500





# 에러 핸들러
@prompt_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "요청한 리소스를 찾을 수 없습니다."
    }), 404

@prompt_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "내부 서버 오류가 발생했습니다."
    }), 500
