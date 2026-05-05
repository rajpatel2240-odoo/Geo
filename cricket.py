import urllib.request
import re

def fetch_and_clean_m3u(url, output_filename):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
    
    cleaned_content = re.sub(r'<script[\s\S]*?</script>\n*', '', content)
    
    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(cleaned_content.strip())

if __name__ == "__main__":
    target_url = "https://raw.githubusercontent.com/rkdyiptv/Playlist/refs/heads/main/Playlist/Cricket.m3u/index.html"
    fetch_and_clean_m3u(target_url, "Cricket.m3u")
