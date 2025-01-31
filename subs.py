import requests
import json
import sys
import re
import os
import io
import gdrive
import yaml
import traceback
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
# Version: 1.5
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

def requestMultipleAnimeSMI():
    global smiDir,isDownloadError,AnimeName,AnimeNO

    with open('anime.yml', encoding='UTF8') as f:
        global outpath
        config = yaml.load(f, Loader=yaml.FullLoader)

        if config['download_path'] != "":
            outpath = config['download_path'] + "/"

        animelist = json.loads(config['anime_list'])

        print("다운경로: "+outpath)
        print("================================================================")
        
        for k in animelist:
            AnimeName = k['Anime']
            AnimeNO = k['AnimeNo']

            response = requests.get("https://api.anissia.net/anime/caption/animeNo/" + str(AnimeNO))
            #print(response.status_code)
            datas = json.loads(response.text)
            json_data = datas["data"]

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

        if os.path.isfile(outpath + smiDir + "finish.txt"):
            print("[=] 이전에 생성된 finish.txt가 발견되어 과정이 스킵되었습니다.")
            print("================================================================")
            continue;

        if regrex1.match(website):
            print("[+] naver 검출.")
            download_naver(website)
        elif regrex2.match(website):
            print("[+] blogspot 검출.")
            download_blogspot(website)
        elif regrex3.match(website):
            print("[+] tistory 검출.")
            download_tistory(website)
        else:
            print("[-] 해당 조건에 부합하는 링크가 존재하지 않습니다.")
            isDownloadError = 1;
        
        if isDownloadError == 0:
            text_to_file( json.dumps(k) , outpath + smiDir + "finish.txt");
            print("[+] finish.txt가 생성되었습니다.")
        else:
            print("[-] finish.txt가 생성되지 않았습니다.")

        print("================================================================")


# 내부 로직 구현

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
        #p_attached_file = re.compile(r"\s*.*aPostFiles\[1\] = \[(.*?)\]", re.IGNORECASE | re.DOTALL)
        p_attached_file = re.compile(r"\s*.*aPostFiles\[1\] = JSON.parse\(\'\[(.*?)\]", re.IGNORECASE | re.DOTALL)
        result = p_attached_file.match(url_source).group(1)
        if result:
            # convert to JSON style
            data = "[" + result.replace('\\\'', '\"') + "]"
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

            # find 'NBlogWlwLayout.nhn'
            if url_source.find("NBlogWlwLayout.naver") == -1:
                print("\n[-] It is not a NAVER Blog")
                sys.exit(0)

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

    #text_to_file(get_url_source_tistory( "https://harnenim.github.io/WinPNG/Viewer.html?url=" + url), "hello.html");

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

def run():
    requestMultipleAnimeSMI()

if __name__ == "__main__":
    run()