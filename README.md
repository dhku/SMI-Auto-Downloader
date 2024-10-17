# SMI-Auto-Downloader

![title](./img/title.png)

자막 릴리즈시 자막을 일괄로 다운받게 해주는 프로그램 입니다.



## 사용방법 

1. **anime.yml** 에서 받고싶은 자막의 애니메이션을 추가합니다.

   ![config](./img/config.png)

   * AnimeNo는 애니시아(https://anissia.net/anime) 애니메이션 목록에서 확인 가능합니다. 

   * download_path 미기입시 현재 디렉토리(Default)에 저장됩니다.

     * 경로 예시(시놀로지) : download_path: "/volume1/Anime/Downloads"
     
     

2. 다음 명령어를 통해 프로그램을 실행합니다.

   ```shell
   python3 subs.py
   ```

   ![build](./img/build.webp)

   (Optional) Crontab을 통한 설정 (NAS 추천)

   ``` bash
   */30 * * * * python3 /home/user/subs.py # 예시) 30분 간격으로 실행...
   ```



3. 프로그램 실행후 다음과 같은 경로가 생성됩니다.

   ![result](./img/result.png)

   * 생성경로 :  다운 받을 디렉토리 / 애니메이션 이름 / 회차 / 제작자 / ( *.zip or *.smi )

   * finish.txt : 정상적으로 파일 다운로드가 완료되면 생성되는 파일입니다. 

     finish.txt 에는 메타정보가 포함되어있으며 이후 finish.txt 존재시 해당 다운로드를 스킵합니다.

