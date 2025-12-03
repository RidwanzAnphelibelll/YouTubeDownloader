#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import os
import sys
import json
import time
import glob
import atexit
import signal
import subprocess

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def install_package(package):
    try:
        __import__(package)
        
    except ImportError:
        clear_screen()
        print(f"Menginstall Packages {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = ['tqdm', 'requests', 'colorama']

for package in required_packages:
    install_package(package)

import requests
from tqdm import tqdm
from colorama import Fore, Style

def check_ytdlp():
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_ytdlp():
    try:
        clear_screen()
        print(f"{Fore.YELLOW}python-yt-dlp tidak ditemukan. Mencoba menginstall...{Style.RESET_ALL}")
        subprocess.run(['apt', 'install', '-y', 'python-yt-dlp'], check=True)
        print(f"{Fore.GREEN}python-yt-dlp berhasil diinstall!{Style.RESET_ALL}")
        time.sleep(1.5)
        return True
        
    except:
        print(f"{Fore.RED}Gagal menginstall python-yt-dlp. Silakan install manual.{Style.RESET_ALL}")
        return False

if not check_ytdlp():
    if not install_ytdlp():
        print(f"{Fore.RED}Program tidak dapat berfungsi tanpa python-yt-dlp!{Style.RESET_ALL}")
        sys.exit(0)

FOLDER_DOWNLOAD = '/sdcard/Download/YouTubeDownloader'
FOLDER_VIDEO = os.path.join(FOLDER_DOWNLOAD, 'Video')
FOLDER_AUDIO = os.path.join(FOLDER_DOWNLOAD, 'Audio')
COOKIE_FILE = os.path.expanduser('~/cookies.txt')
COOKIE_URL = 'https://file-uploaders-rs.vercel.app/uploaded/cookies.txt'

current_download_folder = None
current_download_title = None
current_process = None

def cleanup_partial_files():
    global current_download_folder, current_download_title
    
    if current_download_folder and current_download_title:
        try:
            files_to_delete = []
            
            for file in os.listdir(current_download_folder):
                if file.startswith(current_download_title):
                    if any(ext in file for ext in ['.ytdl', '.part', '.temp', '.f', '.download']):
                        files_to_delete.append(os.path.join(current_download_folder, file))
                        
                    elif file.endswith('.part-Frag') or '.part-Frag' in file:
                        files_to_delete.append(os.path.join(current_download_folder, file))
            
            for file_path in files_to_delete:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
                except Exception as e:
                    pass
                    
        except Exception as e:
            pass
    
    current_download_folder = None
    current_download_title = None

def signal_handler(signum, frame):
    global current_process
    
    if current_process:
        try:
            current_process.terminate()
            time.sleep(0.8)
            
            if current_process.poll() is None:
                current_process.kill()
        except:
            pass
    
    cleanup_partial_files()
    print(f'\n{Fore.YELLOW}Program Telah Dihentikan.{Style.RESET_ALL}')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTSTP, signal_handler)
atexit.register(cleanup_partial_files)

def ensure_download_folder(folder_path):
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path, exist_ok=True)
            print(f'{Fore.GREEN}Folder download berhasil dibuat: {folder_path}{Style.RESET_ALL}')
            
        except Exception as e:
            print(f'{Fore.RED}Gagal membuat folder download: {e}{Style.RESET_ALL}')
            return False
    return True

def trigger_media_scan(file_path):
    try:
        subprocess.run([
            'am', 'broadcast', 
            '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
            '-d', f'file://{file_path}'
        ], check=False, capture_output=True)
    except:
        pass
    
    try:
        subprocess.run([
            'am', 'broadcast',
            '-a', 'android.intent.action.MEDIA_MOUNTED',
            '-d', f'file://{os.path.dirname(file_path)}'
        ], check=False, capture_output=True)
    except:
        pass

def download_cookies():
    try:
        clear_screen()
        print(f'{Fore.YELLOW}Mengunduh cookies.txt...{Style.RESET_ALL}')
        response = requests.get(COOKIE_URL, timeout=10)
        response.raise_for_status()
        
        with open(COOKIE_FILE, 'w') as f:
            f.write(response.text)   
        
        print(f'{Fore.GREEN}cookies.txt berhasil diunduh!{Style.RESET_ALL}')
        time.sleep(1.5)
        
        return True
    except Exception as e:
        print(f'{Fore.RED}Gagal mengunduh cookies.txt: {e}{Style.RESET_ALL}')
        return False

def check_cookie_file():
    if not os.path.exists(COOKIE_FILE):
        if not download_cookies():
            sys.exit(1)
    return True

def get_video_title(url):
    try:
        cmd = ['yt-dlp', '--get-filename', '-o', '%(title)s', url]
        
        if check_cookie_file():
            cmd.extend(['--cookies', COOKIE_FILE])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return None

def delete_existing_file(folder, title, extension):
    try:
        filename = f"{title}.{extension}"
        filepath = os.path.join(folder, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        
        for file in os.listdir(folder):
            if file.startswith(title) and file.endswith(f'.{extension}'):
                filepath = os.path.join(folder, file)
                os.remove(filepath)
                return True
                
    except:
        pass
    
    return False

def get_available_video_formats(url):
    try:
        print(f'{Fore.YELLOW}Mengambil informasi kualitas video...{Style.RESET_ALL}')
        cmd = ['yt-dlp', '-F', url]
        
        if check_cookie_file():
            cmd.extend(['--cookies', COOKIE_FILE])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_lines = result.stdout.split('\n')
        
        video_formats = {}
        
        for line in output_lines:
            if 'mp4' in line.lower():
                parts = line.split()
                if len(parts) > 0:
                    try:
                        format_id = parts[0]
                        
                        resolution_match = re.search(r'(\d+)x(\d+)', line)
                        if resolution_match:
                            width = int(resolution_match.group(1))
                            height = int(resolution_match.group(2))
                            
                            if 'video only' in line.lower() or 'audio only' in line.lower():
                                continue
                            
                            if '│' in line or 'premium' in line.lower():
                                continue
                            
                            if height >= 144 and height <= 4320:
                                if height not in video_formats:
                                
                                    video_formats[height] = {
                                        'format_id': format_id,
                                        'width': width,
                                        'height': height
                                    }
                    except:
                        continue
        
        if not video_formats:
            cmd = ['yt-dlp', '-J', url]
            if check_cookie_file():
                cmd.extend(['--cookies', COOKIE_FILE])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            data = json.loads(result.stdout)
            formats = data.get('formats', [])
            
            for fmt in formats:
                height = fmt.get('height')
                width = fmt.get('width')
                ext = fmt.get('ext')
                
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                
                if height and width and vcodec != 'none' and acodec != 'none' and ext == 'mp4':
                    if height >= 144 and height <= 4320:
                        if height not in video_formats:
                        
                            video_formats[height] = {
                                'format_id': fmt.get('format_id'),
                                'width': width,
                                'height': height
                            }
        
        return sorted(video_formats.keys())
        
    except Exception as e:
        print(f'{Fore.RED}Gagal mendapatkan informasi kualitas video: {e}{Style.RESET_ALL}')
        return []

def download_video(url, quality):
    global current_download_folder, current_download_title, current_process
    
    try:
        if not ensure_download_folder(FOLDER_VIDEO):
            return False
        
        title = get_video_title(url)
        if title:
            current_download_folder = FOLDER_VIDEO
            current_download_title = title
            delete_existing_file(FOLDER_VIDEO, title, 'mp4')
        
        print(f'{Fore.GREEN}Memulai mengunduh video {quality}p...{Style.RESET_ALL}')
        
        output_template = os.path.join(FOLDER_VIDEO, '%(title)s.%(ext)s')
        
        cmd = [
            'yt-dlp',
            '-f', f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best',
            '--merge-output-format', 'mp4',
            '-o', output_template,
            '--concurrent-fragments', '16',
            '--newline',
            url
        ]
        
        if check_cookie_file():
            cmd.extend(['--cookies', COOKIE_FILE])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        current_process = process
        
        pbar = None
        error_output = []
        filename_displayed = False
        current_filename = None
        download_completed = False
        
        try:
            for line in process.stdout:
                line = line.strip()
                error_output.append(line)
                
                if '[download] Destination:' in line:
                    filename = line.split('Destination:')[1].strip()
                    base_name = os.path.basename(filename)
                    
                    name_with_ext = os.path.splitext(base_name)[0]
                    current_filename = f"{name_with_ext}.mp4"
                    
                    if not filename_displayed:
                        print(f'{Fore.CYAN}File: {current_filename}{Style.RESET_ALL}')
                        filename_displayed = True
                
                if '[download] 100%' in line or '[download] 100.0%' in line:
                    download_completed = True
                
                if '[download]' in line and '%' in line:
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        percent = float(match.group(1))
                        
                        if pbar is None:
                            pbar = tqdm(total=100, unit='%', colour='green', desc='Downloading')
                        
                        if pbar:
                            pbar.n = percent
                            pbar.refresh()
        except (KeyboardInterrupt, SystemExit):
            if pbar:
                pbar.close()
            process.terminate()
            time.sleep(0.5)
            
            if process.poll() is None:
                process.kill()
                
            process.wait()
            cleanup_partial_files()
            current_process = None
            raise
        
        if pbar:
            pbar.close()
        
        process.wait()
        current_process = None
        
        if process.returncode == 0 or download_completed:
            print(f'{Fore.GREEN}Video Berhasil Diunduh!{Style.RESET_ALL}')
            print(f'{Fore.BLUE}Tersimpan Di: {FOLDER_VIDEO}{Style.RESET_ALL}')
            
            if os.path.exists(FOLDER_VIDEO):
                for file in os.listdir(FOLDER_VIDEO):
                    if file.endswith('.mp4'):
                        filepath = os.path.join(FOLDER_VIDEO, file)
                        trigger_media_scan(filepath)
            
            current_download_folder = None
            current_download_title = None
            input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
            return True
        else:
            cleanup_partial_files()
            print(f'{Fore.RED}Gagal mengunduh video{Style.RESET_ALL}')
            
            error_messages = []
            for line in error_output[-20:]:
                if 'ERROR' in line or 'error' in line or 'Error' in line:
                    error_messages.append(line)
            
            if error_messages:
                print(f'{Fore.YELLOW}Pesan Kesalahan:{Style.RESET_ALL}')
                for msg in error_messages:
                    print(f'{Fore.YELLOW}{msg}{Style.RESET_ALL}')
            else:
                print(f'{Fore.YELLOW}Tidak ada pesan kesalahan spesifik.{Style.RESET_ALL}')
            
            current_download_folder = None
            current_download_title = None
            input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
            return False
            
    except (KeyboardInterrupt, SystemExit):
        cleanup_partial_files()
        current_download_folder = None
        current_download_title = None
        current_process = None
        raise
        
    except Exception as e:
        cleanup_partial_files()
        print(f'{Fore.RED}Gagal mengunduh video{Style.RESET_ALL}')
        print(f'{Fore.YELLOW}Pesan Kesalahan: {str(e)}{Style.RESET_ALL}')
        
        current_download_folder = None
        current_download_title = None
        current_process = None
        input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        return False

def download_audio(url, quality, audio_format='mp3'):
    global current_download_folder, current_download_title, current_process
    
    try:
        if not ensure_download_folder(FOLDER_AUDIO):
            return False
        
        title = get_video_title(url)
        if title:
            current_download_folder = FOLDER_AUDIO
            current_download_title = title
            delete_existing_file(FOLDER_AUDIO, title, audio_format)
        
        if audio_format == 'flac':
            print(f'{Fore.GREEN}Memulai mengunduh audio FLAC (Lossless)...{Style.RESET_ALL}')
        else:
            print(f'{Fore.GREEN}Memulai mengunduh audio {quality}kbps...{Style.RESET_ALL}')
        
        output_template = os.path.join(FOLDER_AUDIO, '%(title)s.%(ext)s')
        
        cmd = [
            'yt-dlp',
            '-x',
            '--audio-format', audio_format,
            '-o', output_template,
            '--concurrent-fragments', '16',
            '--newline',
            url
        ]
        
        if audio_format != 'flac':
            cmd.extend(['--audio-quality', f'{quality}K'])
        
        if check_cookie_file():
            cmd.extend(['--cookies', COOKIE_FILE])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        current_process = process
        
        pbar = None
        error_output = []
        filename_displayed = False
        current_filename = None
        download_completed = False
        
        try:
            for line in process.stdout:
                line = line.strip()
                error_output.append(line)
                
                if '[download] Destination:' in line:
                    filename = line.split('Destination:')[1].strip()
                    base_name = os.path.basename(filename)
                    
                    name_with_ext = os.path.splitext(base_name)[0]
                    current_filename = f"{name_with_ext}.{audio_format}"
                    
                    if not filename_displayed:
                        print(f'{Fore.CYAN}File: {current_filename}{Style.RESET_ALL}')
                        filename_displayed = True
                
                if '[download] 100%' in line or '[download] 100.0%' in line:
                    download_completed = True
                
                if '[download]' in line and '%' in line:
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        percent = float(match.group(1))
                        
                        if pbar is None:
                            pbar = tqdm(total=100, unit='%', colour='green', desc='Downloading')
                        
                        if pbar:
                            pbar.n = percent
                            pbar.refresh()
        except (KeyboardInterrupt, SystemExit):
            if pbar:
                pbar.close()
            process.terminate()
            time.sleep(0.5)
            
            if process.poll() is None:
                process.kill()
                
            process.wait()
            cleanup_partial_files()
            current_process = None
            raise
        
        if pbar:
            pbar.close()
        
        process.wait()
        current_process = None
        
        if process.returncode == 0 or download_completed:
            print(f'{Fore.GREEN}Audio Berhasil Diunduh!{Style.RESET_ALL}')
            print(f'{Fore.BLUE}Tersimpan Di: {FOLDER_AUDIO}{Style.RESET_ALL}')
            
            if os.path.exists(FOLDER_AUDIO):
                for file in os.listdir(FOLDER_AUDIO):
                    if file.endswith(('.mp3', '.flac')):
                        filepath = os.path.join(FOLDER_AUDIO, file)
                        trigger_media_scan(filepath)
            
            current_download_folder = None
            current_download_title = None
            input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
            return True
        else:
            cleanup_partial_files()
            print(f'{Fore.RED}Gagal mengunduh audio{Style.RESET_ALL}')
            
            error_messages = []
            for line in error_output[-20:]:
                if 'ERROR' in line or 'error' in line or 'Error' in line:
                    error_messages.append(line)
            
            if error_messages:
                print(f'{Fore.YELLOW}Pesan Kesalahan:{Style.RESET_ALL}')
                for msg in error_messages:
                    print(f'{Fore.YELLOW}{msg}{Style.RESET_ALL}')
            else:
                print(f'{Fore.YELLOW}Tidak ada pesan kesalahan spesifik.{Style.RESET_ALL}')
            
            current_download_folder = None
            current_download_title = None
            input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
            return False
            
    except (KeyboardInterrupt, SystemExit):
        cleanup_partial_files()
        current_download_folder = None
        current_download_title = None
        current_process = None
        raise
        
    except Exception as e:
        cleanup_partial_files()
        print(f'{Fore.RED}Gagal mengunduh audio{Style.RESET_ALL}')
        print(f'{Fore.YELLOW}Pesan Kesalahan: {str(e)}{Style.RESET_ALL}')
        
        current_download_folder = None
        current_download_title = None
        current_process = None
        input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        return False

def is_valid_youtube_url(url):
    youtube_patterns = [
        r'^https?://(www\.)?(youtube\.com|youtu\.be)/.+',
        r'^https?://(www\.)?youtube\.com/watch\?v=.+',
        r'^https?://(www\.)?youtube\.com/shorts/.+',
        r'^https?://youtu\.be/.+'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

def main_menu():
    clear_screen()
    print('')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.WHITE}    • YOUTUBE DOWNLOADER MENU •      {Style.RESET_ALL}')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.GREEN}[1]{Style.RESET_ALL} Download Video')
    print(f'{Fore.GREEN}[2]{Style.RESET_ALL} Download Audio')
    print(f'{Fore.RED}[0]{Style.RESET_ALL} Keluar')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.YELLOW}      By: ©RSCoders        {Style.RESET_ALL}')
    print('')

def display_video_quality_menu(available_qualities):
    clear_screen()
    print('')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.WHITE}      • PILIH KUALITAS VIDEO •       {Style.RESET_ALL}')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    
    quality_map = {}
    index = 1
    
    for quality in available_qualities:
        quality_label = f'{quality}p'
        if quality >= 2160:
            quality_label += ' (4K)'
            
        elif quality >= 1440:
            quality_label += ' (2K)'
            
        elif quality >= 1080:
            quality_label += ' (Full HD)'
            
        elif quality >= 720:
            quality_label += ' (HD)'
        
        print(f'{Fore.GREEN}[{index}]{Style.RESET_ALL} {quality_label}')
        quality_map[str(index)] = quality
        index += 1
    
    print(f'{Fore.RED}[0]{Style.RESET_ALL} Kembali')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    
    return quality_map

def display_audio_quality_menu():
    clear_screen()
    print('')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    print(f'{Fore.WHITE}      • PILIH KUALITAS AUDIO •       {Style.RESET_ALL}')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    
    quality_map = {
        '1': {'quality': 128, 'format': 'mp3'},
        '2': {'quality': 256, 'format': 'mp3'},
        '3': {'quality': 320, 'format': 'mp3'},
        '4': {'quality': None, 'format': 'flac'}
    }
    
    print(f'{Fore.GREEN}[1]{Style.RESET_ALL} 128kbps (MP3)')
    print(f'{Fore.GREEN}[2]{Style.RESET_ALL} 256kbps (MP3)')
    print(f'{Fore.GREEN}[3]{Style.RESET_ALL} 320kbps (MP3)')
    print(f'{Fore.GREEN}[4]{Style.RESET_ALL} FLAC (Lossless)')
    print(f'{Fore.RED}[0]{Style.RESET_ALL} Kembali')
    print(f'{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}')
    
    return quality_map

def handle_video_download():
    url = input(f'{Fore.BLUE}Masukkan URL YouTube: {Style.RESET_ALL}')
    
    if not is_valid_youtube_url(url):
        print(f'{Fore.RED}URL YouTube Tidak Valid.{Style.RESET_ALL}')
        input(f'{Fore.WHITE}Tekan Enter untuk kembali...{Style.RESET_ALL}')
        return
    
    available_video = get_available_video_formats(url)
    
    if not available_video:
        print(f'{Fore.RED}Tidak dapat mengambil informasi video atau tidak ada format yang tersedia.{Style.RESET_ALL}')
        input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
        return
    
    while True:
        quality_map = display_video_quality_menu(available_video)
        max_choice = len(quality_map)
        choice = input(f'Masukkan Pilihan [1-{max_choice}/0]: ')
        
        if choice == '0':
            break
        
        if choice in quality_map:
            quality = quality_map[choice]
            download_video(url, quality)
            break
        else:
            print(f'{Fore.RED}Pilihan Tidak Valid!{Style.RESET_ALL}')
            input(f'{Fore.WHITE}Tekan Enter untuk kembali...{Style.RESET_ALL}')

def handle_audio_download():
    url = input(f'{Fore.BLUE}Masukkan URL YouTube: {Style.RESET_ALL}')
    
    if not is_valid_youtube_url(url):
        print(f'{Fore.RED}URL YouTube Tidak Valid.{Style.RESET_ALL}')
        input(f'{Fore.WHITE}Tekan Enter untuk kembali...{Style.RESET_ALL}')
        return
    
    while True:
        quality_map = display_audio_quality_menu()
        choice = input(f'Masukkan Pilihan [1-4/0]: ')
        
        if choice == '0':
            break
        
        if choice in quality_map:
            audio_config = quality_map[choice]
            quality = audio_config['quality']
            audio_format = audio_config['format']
            
            if audio_format == 'flac':
                download_audio(url, None, 'flac')
            else:
                download_audio(url, quality, 'mp3')
            break
        else:
            print(f'{Fore.RED}Pilihan Tidak Valid!{Style.RESET_ALL}')
            input(f'{Fore.WHITE}Tekan Enter untuk kembali...{Style.RESET_ALL}')

def RSCoders():
    check_cookie_file()
    
    while True:
        try:
            main_menu()
            choice = input('Masukkan Pilihan [1-2/0]: ')
            
            if choice == '1':
                handle_video_download()
                
            elif choice == '2':
                handle_audio_download()
                    
            elif choice == '0':
                print(f'{Fore.BLUE}Keluar...{Style.RESET_ALL}')
                time.sleep(1.5)
                exit(0)
                
            else:
                print(f'{Fore.RED}Pilihan Tidak Valid!{Style.RESET_ALL}')
                input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')
                
        except KeyboardInterrupt:
            print(f'\n{Fore.YELLOW}Program Telah Dihentikan.{Style.RESET_ALL}')
            exit(0)
            
        except Exception as e:
            print(f'{Fore.RED}Terjadi Kesalahan: {e}{Style.RESET_ALL}')
            input(f'{Fore.WHITE}Tekan Enter untuk kembali ke menu...{Style.RESET_ALL}')

if __name__ == "__main__":
    RSCoders()