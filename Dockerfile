FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PUID=1000 \
    PGID=1000 \
    TZ=Asia/Seoul

# TZ 환경변수가 동작하도록 tzdata 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN pip install requests PyYAML beautifulsoup4 tqdm

# /app 은 docker-compose 에서 볼륨으로 덮어쓰므로 코드는 /opt/smi 에 둡니다.
WORKDIR /opt/smi
COPY subs.py ./
COPY gdrive ./gdrive
COPY docker/entrypoint.sh /entrypoint.sh
# Windows 에서 체크아웃해 CRLF 가 들어가도 동작하도록 줄바꿈을 정리합니다.
RUN sed -i 's/\r$//' /entrypoint.sh \
 && chmod 0755 /entrypoint.sh \
 && chmod -R a+rX /opt/smi

# anime.yml 과 다운로드 폴더(download_path 기준 경로)는 작업 디렉터리 /app 에 위치
WORKDIR /app

# PUID/PGID 가 지정되면 해당 사용자 권한으로 실행 (NAS 파일 소유권 유지)
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "/opt/smi/subs.py"]