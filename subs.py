import requests
import json
import sys
import re
import os
import io
import ssl
import gdrive
import yaml
import traceback
import datetime
import urllib.error
from http import client
from urllib import request
from urllib.request import urlopen
from urllib.parse import unquote
from urllib.parse import quote
from urllib.parse import urlparse
from bs4 import BeautifulSoup

#pip install requests
#pip install PyYAML
#pip install beautifulsoup4

#시놀로지(헤놀로지)
# wget https://bootstrap.pypa.io/get-pip.py
# python3 get-pip.py
# python3 -m pip install {package name}
# python3 -m pip install 'urllib3<2.0'

# =================================================
# Title: SMI AUTO DOWNLOADER
# Author: KUDONG
# Version: 1.5.6
# Url: https://github.com/dhku/SMI-Auto-Downloader
# =================================================

AnimeNO = -1
AnimeName = "None"
outpath = os.path.abspath('.') + "/"
smiDir = ""
isDownloadError = 0

p_extension = re.compile(r"^.*\.(zip|ass|smi|7z)$", re.IGNORECASE)
regrex1 = re.compile(r".*(naver).*")
regrex2 = re.compile(r".*(blogspot).*")
regrex3 = re.compile(r".*(tistory).*")

p_google = re.compile(r"(.*(https://drive.google.com/file/d/).*)")
p_google_2_1 = re.compile(r"(.*(https://docs.google.com/uc).*)")
p_google_2_2 = re.compile(r"(.*(https://drive.google.com/uc).*)")
p_google_3 = re.compile(r"(.*(https://drive.usercontent.google.com/download).*)")
p_google_drive = re.compile(r"^https?://(drive|docs)\.google\.com/", re.IGNORECASE)
p_google_folder = re.compile(r"^https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([\w-]+)", re.IGNORECASE)
p_google_file_id = re.compile(r"^https?://(?:drive|docs)\.google\.com/.*?(?:/d/|[?&]id=)([\w-]+)", re.IGNORECASE)

p_harne = re.compile(r"(.*(https://harne1.tistory.com).*)")

def download(url, file_name = None):
    with open(file_name, "wb") as file:  
        response = requests.get(url)              
        file.write(response.content)      

def text_to_file(txt, file_name):
    f = open(file_name, 'w',encoding="UTF-8")
    f.write(txt)
    f.close()

# 요청함수
def requestAnimeSMI(AnimeNo):
    global smiDir,isDownloadError

    print("다운경로: "+outpath)
    print("================================================================")

    response = requests.get("https://api.anissia.net/anime/caption/animeNo/" + str(AnimeNo))

    #print(response.status_code)

    datas = json.loads(response.text)
    json_data = datas["data"]

    _requestAnimeSMI(AnimeNo,json_data)

CONFIG_FILE = 'anime.yml'
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} \
    | {"COM%d" % i for i in range(1, 10)} | {"LPT%d" % i for i in range(1, 10)}

# 폴더명으로 사용할 수 없는 문자를 제거
def sanitize_folder_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', str(name))
    name = re.sub(r'\s+', ' ', name).strip().rstrip('. ')
    if name.upper() in _WINDOWS_RESERVED_NAMES:
        name = "_" + name
    return name

# 작품 정보(제목 + 자막 목록) 요청
def requestAnimeInfo(AnimeNo):
    response = requests.get("https://api.anissia.net/anime/animeNo/" + str(AnimeNo))
    datas = json.loads(response.text)
    if datas.get("code") != "ok" or not datas.get("data"):
        return None
    return datas["data"]

# anime.yml 저장 (anime_list는 기존과 같은 JSON 문자열 형식 유지)
def save_config(download_path, animelist):
    entries = []
    for item in animelist:
        lines = ['      %s:%s' % (json.dumps(key, ensure_ascii=False), json.dumps(value, ensure_ascii=False))
                 for key, value in item.items()]
        entries.append("    {\n" + ",\n".join(lines) + "\n    }")

    anime_list_str = "[\n" + ",\n".join(entries) + ("\n" if entries else "") + "    ]"
    anime_list_str = anime_list_str.replace("'", "''")  # YAML 작은따옴표 이스케이프

    with open(CONFIG_FILE, 'w', encoding='UTF8') as f:
        f.write("download_path: " + json.dumps(download_path, ensure_ascii=False) + "\n")
        f.write("anime_list: '" + anime_list_str + "'\n")

def requestMultipleAnimeSMI():
    global smiDir,isDownloadError,AnimeName,AnimeNO,outpath

    with open(CONFIG_FILE, encoding='UTF8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    download_path = config.get('download_path') or ""
    if download_path != "":
        outpath = download_path + "/"

    animelist = json.loads(config['anime_list'])

    print("다운경로: "+outpath)
    print("================================================================")

    # 1. 작품 정보 조회 및 Anime(폴더명) 항목 채우기
    targets = []
    isConfigChanged = False

    for i, k in enumerate(animelist):
        AnimeNO = k['AnimeNo']

        try:
            info = requestAnimeInfo(AnimeNO)
        except Exception as e:
            print("[-] 작품 정보 요청 실패 (AnimeNo: %s) : %s" % (AnimeNO, e))
            continue

        if info is None:
            print("[-] 작품 정보를 찾을 수 없습니다. (AnimeNo: %s)" % AnimeNO)
            continue

        name = str(k.get('Anime') or "").strip()

        if name == "":
            name = sanitize_folder_name(info.get('subject') or "")
            if name == "":
                name = str(AnimeNO)
            # "Anime" 항목을 맨 앞에 두고 나머지 항목은 유지
            animelist[i] = {"Anime": name, **{key: v for key, v in k.items() if key != 'Anime'}}
            isConfigChanged = True
            print("[+] 작품명 추가: %s => %s" % (AnimeNO, name))

        targets.append((name, AnimeNO, info.get('captions') or []))

    if isConfigChanged:
        save_config(download_path, animelist)
        print("[+] %s에 작품명이 저장되었습니다." % CONFIG_FILE)
        print("================================================================")

    # 2. 자막 다운로드
    for AnimeName, AnimeNO, json_data in targets:
        _requestAnimeSMI(AnimeNO,json_data)


def _requestAnimeSMI(AnimeNo,json_data):
    global smiDir,isDownloadError

    for k in json_data:

        isDownloadError = 0;

        name = k['name']
        episode = k['episode']
        updDt = k['updDt']
        website = unquote(k['website'])

        smiDir = AnimeName + "/" + episode + "화/" + name + "/"

        print("ANIME SMI AUTO DOWNLOADER - Target => <"+AnimeName+">")    
        print("================================================================")
        print("> 제작자: " + name)
        print("> 회차: " + episode+"화")
        print("> 업데이트: " + updDt)
        print("> 주소: " + website)

        finish_path = outpath + smiDir + "finish.txt"

        if os.path.isfile(finish_path):
            print("[=] 이전에 생성된 finish.txt가 발견되어 과정이 스킵되었습니다.")
            print_finish_detail(finish_path, updDt)
            print("================================================================")
            continue;

        if p_google_drive.match(website):
            print("[+] 구글 드라이브 검출.")
            download_google_drive(website)
        elif regrex1.match(website):
            print("[+] naver 검출.")
            download_naver(website)
        elif regrex2.match(website):
            print("[+] blogspot 검출.")
            download_blogspot(website)
        elif regrex3.match(website):
            print("[+] tistory 검출.")
            download_tistory(website)
        elif website == "":
            print("[=] 자막 사이트가 검출되지 않았습니다.")
            isDownloadError = 1;
        else:
            print("[+] 일반 웹사이트 검출.")
            download_website(website)
        
        if isDownloadError == 0:
            text_to_file( build_finish_content(AnimeNo, k, website, finish_path) , finish_path);
            print("[+] finish.txt가 생성되었습니다.")
            print_finish_detail(finish_path)
        else:
            print("[-] 다운로드 중 오류가 있어 finish.txt가 생성되지 않았습니다. (다음 실행 시 다시 시도합니다)")
            print("    - 대상 폴더: " + os.path.normpath(outpath + smiDir))

        print("================================================================")


# finish.txt 관련 상세 로그

def _format_size(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return ("%d %s" % (size, unit)) if unit == "B" else ("%.1f %s" % (size, unit))
        size /= 1024.0

def _list_folder_files(folder):
    """폴더 안의 파일(finish.txt 제외)을 (파일명, 바이트 크기) 목록으로 돌려준다."""
    try:
        names = sorted(f for f in os.listdir(folder)
                       if f != "finish.txt" and os.path.isfile(os.path.join(folder, f)))
    except OSError:
        return []
    files = []
    for f in names:
        try:
            size = os.path.getsize(os.path.join(folder, f))
        except OSError:
            size = None
        files.append((f, size))
    return files

def build_finish_content(AnimeNo, caption, website, finish_path):
    """finish.txt에 저장할 내용(JSON)을 만든다.

    스킵 시 비교에 쓰는 updDt는 기존과 같이 최상위에 둔다.
    """
    folder = os.path.dirname(finish_path)
    files = _list_folder_files(folder)
    info = {
        "Anime": AnimeName,
        "AnimeNo": str(AnimeNo),
        "episode": caption.get('episode'),
        "name": caption.get('name'),
        "updDt": caption.get('updDt'),
        "website": website,
        "finishedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "path": os.path.normpath(folder),
        "fileCount": len(files),
        "files": [{"name": f, "size": size, "sizeText": _format_size(size) if size is not None else "?"}
                  for f, size in files],
        "caption": caption,
    }
    return json.dumps(info, ensure_ascii=False, indent=2) + "\n"

def print_finish_detail(finish_path, current_updDt=None):
    """finish.txt 경로, 생성 시각, 폴더 안의 자막 파일 목록을 출력한다.

    current_updDt가 주어지면(스킵 시) finish.txt에 기록된 업데이트 날짜와 비교한다.
    """
    folder = os.path.dirname(finish_path)
    print("    - 경로: " + os.path.normpath(finish_path))

    try:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(finish_path))
        print("    - 생성 시각: " + mtime.strftime("%Y-%m-%d %H:%M:%S"))
    except OSError:
        pass

    if current_updDt is not None:
        try:
            with open(finish_path, encoding="UTF-8") as f:
                recorded_updDt = json.load(f).get("updDt")
        except Exception:
            recorded_updDt = None
        if recorded_updDt:
            print("    - 기록된 업데이트: " + str(recorded_updDt))
            if str(recorded_updDt) != str(current_updDt):
                print("    [!] 자막이 갱신되었습니다. (%s => %s) 다시 받으려면 finish.txt를 삭제하세요." % (recorded_updDt, current_updDt))

    files = _list_folder_files(folder)
    print("    - 폴더 내 파일: %d개" % len(files))
    for f, size in files:
        print("      * %s (%s)" % (f, _format_size(size) if size is not None else "?"))


# 내부 로직 구현

def _download_drive_file(view_url):
    """https://drive.google.com/file/d/.../view 하나를 저장한다.

    확장자가 자막/압축이 아니면 False. 저장했으면 True.
    """
    start_index = view_url.find("/d/") + 3
    end_index = view_url.rfind("/view")
    key = view_url[start_index:end_index]
    uc_url = "https://drive.google.com/uc?id=" + key

    remotefile = urlopen(uc_url)
    file_name = remotefile.headers.get_filename()

    if file_name is not None:
        file_name = file_name.encode('ISO-8859-1').decode('UTF-8')
    else:
        parsed_url = urlparse(uc_url)
        file_name = unquote(os.path.basename(parsed_url.path))

    if file_name == "uc":
        file_name = gdrive.get_file_name(uc_url)

    if not p_extension.match(file_name):
        return False

    print("[=] 다운로드 시작 => " + file_name)

    path = outpath + smiDir
    if not os.path.exists(path):
        os.makedirs(path)

    gdrive.download(uc_url, path + file_name, quiet=False)
    print("[+] 파일 다운로드가 완료 되었습니다. ")
    return True

def _list_drive_files(folder_id, depth=0):
    """공유 폴더(하위 폴더 포함)의 모든 파일을 (파일 ID, 파일명) 목록으로 돌려준다."""
    res = requests.get("https://drive.google.com/embeddedfolderview?id=" + folder_id, headers=HEADERS, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, 'html.parser')

    files = []
    for entry in soup.select("div.flip-entry"):
        link = entry.find("a")
        title = entry.select_one(".flip-entry-title")
        if link is None or title is None:
            continue
        href = link.get("href", "")
        file_name = re.sub(r'[\\/:*?"<>|]', "", title.get_text().strip())

        sub_folder = p_google_folder.match(href)
        if sub_folder:
            if depth < 3:
                files += _list_drive_files(sub_folder.group(1), depth + 1)
            continue

        file_id = p_google_file_id.match(href)
        if file_id and file_name:
            files.append((file_id.group(1), file_name))
    return files

def download_google_drive(url):
    global isDownloadError
    folder = p_google_folder.match(url)

    if folder is None:
        file_id = p_google_file_id.match(url)
        if file_id is None:
            print("[-] 구글 드라이브 파일 ID를 찾을 수 없습니다.")
            isDownloadError = 1
            return
        try:
            if not _download_drive_file("https://drive.google.com/file/d/" + file_id.group(1) + "/view"):
                isDownloadError = 1
        except Exception as e:
            print("[-] Error : %s" % e)
            print(traceback.format_exc())
            isDownloadError = 1
        return

    try:
        files = _list_drive_files(folder.group(1))
    except Exception as e:
        print("[-] 구글 드라이브 폴더를 읽을 수 없습니다. : %s" % e)
        isDownloadError = 1
        return

    if not files:
        print("[-] 구글 드라이브 폴더에서 파일을 찾지 못했습니다.")
        isDownloadError = 1
        return

    path = outpath + smiDir
    if not os.path.exists(path):
        os.makedirs(path)

    saved_any = False
    for file_id, file_name in files:
        try:
            print("[=] 다운로드 시작 => " + file_name)
            gdrive.download("https://drive.google.com/uc?id=" + file_id, path + file_name, quiet=False)
            print("[+] 파일 다운로드가 완료 되었습니다. ")
            saved_any = True
        except Exception as e:
            print("[-] Error : %s" % e)
    if not saved_any:
        isDownloadError = 1

def download_naver(url):
    global isDownloadError
    #URL source를 긁어옵니다.
    url_source = get_url_source_naver(url);

    if url_source is None:
        isDownloadError = 1;
        return
    
    # find 't.static.blog.naver.net'
    if url_source.find("t.static.blog/mylog") == -1:
        print("\n[-] It is not a NAVER Blog")
        isDownloadError = 1;
        return 

    try:
        # find 'aPostFiles'
        # 캡쳐 그룹 \[ \] 사이 - 따로 [ ] 감싸줘야함
        # p_attached_file = re.compile(r"\s*.*aPostFiles\[1\] = JSON.parse\(\'\[(.*?)\]", re.IGNORECASE | re.DOTALL)
        # 캡쳐 그룹 ( ) 사이 - 따로 [ ] 안해도됨
        p_attached_file = re.compile(r"\s*.*aPostFiles\[1\]\s*=\s*JSON\.parse\('(\[.*?\])'\s*\.replace", re.IGNORECASE | re.DOTALL)
        result = p_attached_file.match(url_source).group(1)
        if result != '[]':
            # convert to JSON style
            # data = "[" + result.replace('\\\'', '\"') + "]"
            data = result.replace('\\\'', '\"')
            json_data = json.loads(data)

            for each_file in json_data:       
                try:
                    print("* File : %s, Size : %s Bytes" % (each_file["encodedAttachFileName"], each_file["attachFileSize"]))
                    print("  Link : %s" % each_file["encodedAttachFileUrl"])
                    # File Download
                    print("[=] 다운로드 시작 => "+each_file["encodedAttachFileName"])

                    path = outpath + smiDir
                    if not os.path.exists(path):
                        os.makedirs(path)

                    download(each_file["encodedAttachFileUrl"], path + each_file["encodedAttachFileName"])
                    print("[+] 파일 다운로드가 완료 되었습니다. ")
                except Exception as e:
                    print("[-] Error : %s" % e)
                    isDownloadError = 1;
        else:
            soup = BeautifulSoup(url_source, 'html.parser')
            temps = soup.find('div',class_="se-main-container")    

            if(temps is None):
                temps = soup.find('div', {'class': 'se-main-container'})

            links = temps.find_all("a")
            file_found = 0;

            p_attach = re.compile(r"(.*(googleusercontent).*)")
            p_google = re.compile(r"(.*(https://drive.google.com/file/d/).*)")

            for a in links:
                if a.get('href') == None:
                    continue;
                each_file = a.attrs['href']
                # print("href = "+each_file)
                try:
                    each_file = each_file.replace('&amp;','&');

                    # 구글 드라이브 주소가 검출되었을때
                    if bool(p_google.match(each_file)):

                        start_index = each_file.find("/d/") + 3;
                        end_index =  each_file.rfind("/view");

                        key = each_file[start_index:end_index]
                        each_file = "https://drive.google.com/uc?id="+key

                        remotefile = urlopen(each_file)
                        fileName = remotefile.headers.get_filename();

                        if fileName is not None:
                            fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                        else:
                            parsed_url = urlparse(each_file)
                            fileName = os.path.basename(parsed_url.path)
                            fileName = unquote(fileName)

                        path = outpath + smiDir

                        if fileName == "uc":
                            fileName = gdrive.get_file_name(each_file)

                        if(not p_extension.match(fileName)):
                            continue;

                        print("[=] 다운로드 시작 => "+ fileName)

                        if not os.path.exists(path):
                            os.makedirs(path)

                        gdrive.download(each_file, path + fileName, quiet=False)
                        print("[+] 파일 다운로드가 완료 되었습니다. ")

                        file_found = 1;

                    # 일반 다운로드 주소가 검출되었을때
                    elif bool(p_attach.match(each_file)) == False:
                        print("  Link : %s" % each_file)
                        remotefile = urlopen(each_file)
                        fileName = remotefile.headers.get_filename();

                        if fileName is not None:
                            fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                        else:
                            parsed_url = urlparse(each_file)
                            fileName = os.path.basename(parsed_url.path)
                            fileName = unquote(fileName)

                        print("[=] 다운로드 시작 => "+fileName)

                        path = outpath + smiDir
                        if not os.path.exists(path):
                            os.makedirs(path)

                        download(each_file, path + fileName);
                        file_found = 1;
                        print("[+] 파일 다운로드가 완료 되었습니다. ")
                        
                except urllib.error.HTTPError as e:
                    print("[=] 해당 URL은 스킵되었습니다. : %s" % e)                     
                except Exception as e:
                    print("[-] Error : %s" % e)
            
            if(file_found == 0):
                print("[-] Attached File not found !!")
                isDownloadError = 1;
    except Exception as e:
        print("[-] Error : %s" % e)
        isDownloadError = 1;

def get_url_source_naver(url):
    global isDownloadError
    try:
        while url.find("PostView.naver") == -1 and url.find("PostList.naver") == -1:
            f = request.urlopen(url)
            url_info = f.info()
            url_charset = client.HTTPMessage.get_charsets(url_info)[0]
            url_source = f.read().decode(url_charset)

            # get frame src
            p_frame = re.compile(r"\s*.*?<iframe.*?mainFrame.*?(.*)", re.IGNORECASE | re.DOTALL)
            p_src_url = re.compile(r"\s*.*?src=[\'\"](.+?)[\'\"]", re.IGNORECASE | re.DOTALL)
            src_url = p_src_url.match(p_frame.match(url_source).group(1)).group(1)
            url = src_url

        if url.find("http://blog.naver.com") == -1:
            last_url = "http://blog.naver.com" + url
        else:
            last_url = url

        print("   => Last URL : %s\n" % last_url)
        f = request.urlopen(last_url)
        url_info = f.info()
        url_charset = client.HTTPMessage.get_charsets(url_info)[0]
        url_source = f.read().decode(url_charset)

        return url_source

    except Exception as e:
        print("[-] Error : %s" % e)
        isDownloadError = 1;
        return None;

def download_tistory(url):
    global isDownloadError
    url_source = get_url_source_tistory(url)

    if url_source is None:
        return

    # find 's1.daumcdn.net/cfs.tistory'
    if url_source.find("t1.daumcdn.net/tistory") == -1:
        print("[-] It is not a Tistory Blog")
        isDownloadError = 1;
        return;

    # if bool(p_harne.match(url)):

    try:
        # find all 'attach file link'
        p_attach = re.compile(r"href=[\'\"](\S+?/attachment/.*?)[\'\"]\s*.*?/> (.*?)</", re.IGNORECASE | re.DOTALL)
        result = p_attach.findall(url_source)

        if result:
            
            for each_file in result:
                file_url = each_file[0]
                if each_file[1] == "":
                    file_name = file_url[file_url.rfind('/') + 1:]
                else:
                    file_name = each_file[1]
                print("* File : %s" % file_name)
                print("  Link : %s" % file_url)
                print("[=] 다운로드 시작 => "+file_name)

                path = outpath + smiDir
                if not os.path.exists(path):
                    os.makedirs(path)

                download(file_url, path + file_name)
                print("[+] 파일 다운로드가 완료 되었습니다. ")

        else:
            soup = BeautifulSoup(url_source, 'html.parser')
            temps = soup.find('div',class_="tt_article_useless_p_margin contents_style")    
        
            if(temps is None):
                temps = soup.find('div', {'class': 'contents_style'})

            links = temps.find_all("a")
            file_found = 0;

            p_attach = re.compile(r"(.*(googleusercontent).*)")
            p_google = re.compile(r"(.*(https://drive.google.com/file/d/).*)")

            for a in links:
                if a.get('href') == None:
                    continue;
                each_file = a.attrs['href']
                # print("href = "+each_file)
                try:
                    each_file = each_file.replace('&amp;','&');

                    # 구글 드라이브 주소가 검출되었을때
                    if bool(p_google.match(each_file)):

                        start_index = each_file.find("/d/") + 3;
                        end_index =  each_file.rfind("/view");

                        key = each_file[start_index:end_index]
                        each_file = "https://drive.google.com/uc?id="+key

                        remotefile = urlopen(each_file)
                        fileName = remotefile.headers.get_filename();

                        if fileName is not None:
                            fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                        else:
                            parsed_url = urlparse(each_file)
                            fileName = os.path.basename(parsed_url.path)
                            fileName = unquote(fileName)

                        path = outpath + smiDir

                        if fileName == "uc":
                            fileName = gdrive.get_file_name(each_file)
                    
                        if(not p_extension.match(fileName)):
                            continue;

                        print("[=] 다운로드 시작 => "+ fileName)

                        if not os.path.exists(path):
                            os.makedirs(path)

                        gdrive.download(each_file, path + fileName, quiet=False)
                        print("[+] 파일 다운로드가 완료 되었습니다. ")

                        file_found = 1;

                    # 일반 다운로드 주소가 검출되었을때
                    elif bool(p_attach.match(each_file)) == False:
                        print("  Link : %s" % each_file)

                        remotefile = urlopen(each_file)
                        fileName = remotefile.headers.get_filename();

                        if fileName is not None:
                            fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                        else:
                            parsed_url = urlparse(each_file)
                            fileName = os.path.basename(parsed_url.path)
                            fileName = unquote(fileName)

                        print("[=] 다운로드 시작 => "+fileName)

                        path = outpath + smiDir
                        if not os.path.exists(path):
                            os.makedirs(path)

                        download(each_file, path + fileName);
                        file_found = 1;
                        print("[+] 파일 다운로드가 완료 되었습니다. ")

                except urllib.error.HTTPError as e:
                    print("[=] 해당 URL은 스킵되었습니다. : %s" % e)
                except Exception as e:
                    print("[-] Error : %s" % e)
                    print(traceback.format_exc())
            
            if(file_found == 0):
                print("[-] Attached File not found !!")
                isDownloadError = 1;
    
    except Exception as e:
        print("[-] Error : %s" % e)
        print(traceback.format_exc())
        isDownloadError = 1;   

def get_url_source_tistory(url):
    global isDownloadError
    try:
        try:
            f = request.urlopen(url)
        except Exception as e:
            # 한글 URL 검출시 quote로 감싸야됨
            # 'ascii' codec can't encode characters in position 11-13: ordinal not in range(128) 방지
            last_slash_index = url.rfind('/')
            body = url[:last_slash_index]
            query = quote(url[last_slash_index:])
            #print("출력=> "+body + query)
            f = request.urlopen(body + query)

        url_info = f.info()
        url_charset = client.HTTPMessage.get_charsets(url_info)[0]
        url_source = f.read().decode(url_charset)
        return url_source
    except Exception as e:
        print("[-] Error : %s" % e)
        print(traceback.format_exc())
        isDownloadError = 1;
        return None;

def download_blogspot(url):
    global isDownloadError
    url_source = get_url_source_blogspot(url)

    if url_source is None:
        return

    # p_attach = re.compile(r"<div class=\'post-body.*?\'[^>]*>((?:(?:(?!<div[^>]*>|</div>).)+|<div[^>]*>([\s\S]*?)</div>)*)</div>", re.IGNORECASE | re.DOTALL)   
    # result = p_attach.findall(url_source)

    soup = BeautifulSoup(url_source, 'html.parser')
    temps = soup.find('div',class_="post-body")

    links = temps.find_all("a")

    p_attach = re.compile(r"(.*(googleusercontent).*)")
    p_google = re.compile(r"(.*(https://drive.google.com/file/d/).*)")
    p_google_2 = re.compile(r"(.*(https://docs.google.com/uc).*)")
    p_google_3 = re.compile(r"(.*(https://drive.usercontent.google.com/download).*)")

    isDownloaded = 0;

    for a in links:
        each_file = a.attrs['href']
        # print("href = "+each_file)
        try:
            each_file = each_file.replace('&amp;','&');

            if bool(p_google_2.match(each_file)):
                start_index = each_file.find("&id=") + 4;
                end_index =  each_file.rfind("&confirm");
                each_file = "https://drive.google.com/file/d/" + each_file[start_index:end_index] + "/view"
            
            if bool(p_google_3.match(each_file)):
                start_index = each_file.find("?id=") + 4;
                end_index =  each_file.rfind("&export");
                each_file = "https://drive.google.com/file/d/" + each_file[start_index:end_index] + "/view"            

            # 구글 드라이브 주소가 검출되었을때
            if bool(p_google.match(each_file)):

                start_index = each_file.find("/d/") + 3;
                end_index =  each_file.rfind("/view");

                key = each_file[start_index:end_index]
                each_file = "https://drive.google.com/uc?id="+key

                remotefile = urlopen(each_file)
                fileName = remotefile.headers.get_filename();

                if fileName is not None:
                    fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                else:
                    parsed_url = urlparse(each_file)
                    fileName = os.path.basename(parsed_url.path)
                    fileName = unquote(fileName)

                path = outpath + smiDir

                if fileName == "uc":
                    fileName = gdrive.get_file_name(each_file)

                if(not p_extension.match(fileName)):
                    continue;

                print("[=] 다운로드 시작 => "+ fileName)

                if not os.path.exists(path):
                    os.makedirs(path)

                gdrive.download(each_file, path + fileName, quiet=False)
                print("[+] 파일 다운로드가 완료 되었습니다. ")
                    
                isDownloaded = 1;

            # 일반 다운로드 주소가 검출되었을때
            elif bool(p_attach.match(each_file)) == False:
                print("  Link : %s" % each_file)
                remotefile = urlopen(each_file)
                fileName = remotefile.headers.get_filename();

                if fileName is not None:
                    try:
                        fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                    except Exception as e:
                        fileName = fileName.encode('UTF-8').decode('ISO-8859-1');
                        fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                else:
                    parsed_url = urlparse(each_file)
                    fileName = os.path.basename(parsed_url.path)
                    fileName = unquote(fileName)

                print("[=] 다운로드 시작 => "+fileName)

                path = outpath + smiDir
                if not os.path.exists(path):
                    os.makedirs(path)

                download(each_file, path + fileName);
                isDownloaded = 1;
                print("[+] 파일 다운로드가 완료 되었습니다. ")

        except urllib.error.HTTPError as e:
            print("[=] 해당 URL은 스킵되었습니다. : %s" % e)            
        except Exception as e:
            print("[-] Error : %s" % e)
            print(traceback.format_exc())

    if isDownloaded == 0:
        isDownloadError = 1;

def get_url_source_blogspot(url):
    global isDownloadError
    try:
        try:
            f = request.urlopen(url)
        except Exception as e:
            # 한글 URL 검출시 quote로 감싸야됨
            # 'ascii' codec can't encode characters in position 11-13: ordinal not in range(128) 방지
            last_slash_index = url.rfind('/')
            body = url[:last_slash_index]
            query = quote(url[last_slash_index:])
            #print("출력=> "+body + query)
            f = request.urlopen(body + query)
        url_info = f.info()
        url_charset = client.HTTPMessage.get_charsets(url_info)[0]
        url_source = f.read().decode(url_charset)
        return url_source
    except Exception as e:
        print("[-] Error : %s" % e)
        isDownloadError = 1;
        return None;

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

def extract_csrf_token(html, url_source=None):
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
    return match.group(1) if match else None

def download_website(url):
    global isDownloadError
    url_source = get_url_source_website(url)

    if url_source is None:
        return

    soup = BeautifulSoup(url_source, 'html.parser')
    temps = soup.find('div')

    isDownloaded = 0;
    isDownloaded = find_blog_standard(temps)

    if isDownloaded == 0:
        isDownloadError = 1;

def find_blog_standard(temps):

    links = temps.find_all("a")

    for a in links:
        each_file = a.attrs['href']
        #print("href = "+each_file)

        try:
            each_file = each_file.replace('&amp;','&');

            if bool(p_google_2_1.match(each_file)):
                start_index = each_file.find("&id=") + 4;
                end_index =  each_file.rfind("&confirm");
                each_file = "https://drive.google.com/file/d/" + each_file[start_index:end_index] + "/view"

            if bool(p_google_2_2.match(each_file)):
                start_index = each_file.find("&id=") + 4;
                end_index =  len(each_file);
                each_file = "https://drive.google.com/file/d/" + each_file[start_index:end_index] + "/view"

            if bool(p_google_3.match(each_file)):
                start_index = each_file.find("?id=") + 4;
                end_index =  each_file.rfind("&export");
                each_file = "https://drive.google.com/file/d/" + each_file[start_index:end_index] + "/view"

            # 구글 드라이브 주소가 검출되었을때
            if bool(p_google.match(each_file)):

                start_index = each_file.find("/d/") + 3;
                end_index =  each_file.rfind("/view");

                key = each_file[start_index:end_index]
                each_file = "https://drive.google.com/uc?id="+key

                remotefile = urlopen(each_file)
                fileName = remotefile.headers.get_filename();

                if fileName is not None:
                    fileName = fileName.encode('ISO-8859-1').decode('UTF-8');
                else:
                    parsed_url = urlparse(each_file)
                    fileName = os.path.basename(parsed_url.path)
                    fileName = unquote(fileName)

                path = outpath + smiDir

                if fileName == "uc":
                    fileName = gdrive.get_file_name(each_file)

                #print(fileName);

                if(not p_extension.match(fileName)):
                    continue;

                print("[=] 다운로드 시작 => "+ fileName)

                if not os.path.exists(path):
                    os.makedirs(path)

                gdrive.download(each_file, path + fileName, quiet=False)
                print("[+] 파일 다운로드가 완료 되었습니다. ")
                    
                return 1;
        except urllib.error.HTTPError as e:
            print("[=] 해당 URL은 스킵되었습니다. : %s" % e)
            return 0;
        except Exception as e:
            print("[-] Error : %s" % e)
            print(traceback.format_exc())
            return 0;
    return 0;

def get_url_source_website(url):
    global isDownloadError
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    ssl_context = ssl._create_unverified_context()
    try:
        try:
            req = request.Request(url, headers=headers)
            f = request.urlopen(req, context=ssl_context)
        except Exception as e:
            # 한글 URL 검출시 quote로 감싸야됨
            # 'ascii' codec can't encode characters in position 11-13: ordinal not in range(128) 방지
            last_slash_index = url.rfind('/')
            body = url[:last_slash_index]
            query = quote(url[last_slash_index:])
            #print_log("출력=> "+body + query)
            f = request.urlopen(body + query)
        url_info = f.info()
        url_charset = client.HTTPMessage.get_charsets(url_info)[0]
        url_source = f.read().decode(url_charset)
        return url_source
    except Exception as e:
        print("[-] Error : %s" % e)
        isDownloadError = 1;
        return None;


def run():
    requestMultipleAnimeSMI()

if __name__ == "__main__":
    run()