import sys
import os

# Flask 애플리케이션의 루트 디렉토리
project_home = '/var/www/html/your_flask_app'

# 프로젝트 홈 디렉토리가 sys.path에 없으면 추가
if project_home not in sys.path:
    sys.path.insert(0, project_home) # 리스트의 맨 앞에 추가

# Note: activate_this.py를 사용하는 대신, mod_wsgi의 WSGIDaemonProcess 설정에서
# python-home 및 python-path를 통해 가상 환경을 지정합니다.
# 따라서 여기서 별도로 가상 환경을 활성화할 필요가 없습니다.

# Flask 애플리케이션 인스턴스 임포트
# 'application'은 mod_wsgi가 기대하는 기본 이름입니다.
from app import app as application
