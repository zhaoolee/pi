# 将 _posts 里面的.md文件中的http图片路径替换为本地路径,
# 比如将 _posts/2025-12-21-13-46-18-more-safe.md 文件中的图片下载保存到 _posts/2025-12-21-13-46-18-more-safe.assets 里面
# 将.md文件里面的图片路径转为相对路径 ./2025-12-21-13-46-18-more-safe.assets/imagename.ext

import argparse
import hashlib
import mimetypes
import os
import re
import urllib.parse

import requests

POSTS_DIR = "_posts"

HTTP_IMAGE_PATTERN = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<inner>[^)]+)\)')


def iter_md_files(path):
    if os.path.isfile(path):
        if path.lower().endswith(".md"):
            yield path
        return
    for root, _, files in os.walk(path):
        for name in files:
            if name.lower().endswith(".md"):
                yield os.path.join(root, name)


def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9._-]+', "_", name)


def guess_extension(url, content_type):
    path = urllib.parse.urlparse(url).path
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in (".octet-stream", ""):
        ext = ""
    if ext:
        return ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".bin"


def build_local_path(url, used_names, content_type=None):
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path) or "image"
    base = safe_filename(base)
    name, ext = os.path.splitext(base)
    if not ext or ext == ".octet-stream":
        ext = guess_extension(url, content_type)
    filename = f"{name}{ext}"
    if filename in used_names:
        suffix = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        filename = f"{name}-{suffix}{ext}"
    used_names.add(filename)
    return filename


def download_image(url, assets_dir, used_names, session, max_retries=3):
    last_exc = None
    response = None
    for _ in range(max_retries):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
    if last_exc is not None or response is None:
        return None

    content_type = response.headers.get("Content-Type", "")
    filename = build_local_path(url, used_names, content_type=content_type)
    local_path = os.path.join(assets_dir, filename)
    if not os.path.exists(local_path):
        with open(local_path, "wb") as f:
            f.write(response.content)
    return filename


def replace_http_images(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    md_dir = os.path.dirname(md_path)
    md_base = os.path.splitext(os.path.basename(md_path))[0]
    assets_dir_name = f"{md_base}.assets"
    assets_dir = os.path.join(md_dir, assets_dir_name)
    os.makedirs(assets_dir, exist_ok=True)

    url_to_local = {}
    failed_urls = []
    failed_seen = set()
    used_names = set()
    session = requests.Session()

    def get_local_url(url):
        if url in url_to_local:
            return url_to_local[url]
        filename = download_image(url, assets_dir, used_names, session)
        if not filename:
            if url not in failed_seen:
                failed_urls.append(url)
                failed_seen.add(url)
            return None
        local_url = f"./{assets_dir_name}/{filename}"
        url_to_local[url] = local_url
        return local_url

    def replace_markdown(match):
        inner = match.group("inner")
        if not inner:
            return match.group(0)
        inner_match = re.match(r"\s*(\S+)(.*)", inner, flags=re.DOTALL)
        if not inner_match:
            return match.group(0)
        url = inner_match.group(1)
        rest = inner_match.group(2)
        if not url.startswith(("http://", "https://")):
            return match.group(0)
        local_url = get_local_url(url)
        if not local_url:
            return match.group(0)
        alt = match.group("alt")
        return f"![{alt}]({local_url}{rest})"

    new_content = HTTP_IMAGE_PATTERN.sub(replace_markdown, content)

    if new_content != content:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"已处理: {md_path}")
    else:
        print(f"无需处理: {md_path}")
    return failed_urls


def main():
    parser = argparse.ArgumentParser(description="将Markdown中的http图片下载到本地并替换为相对路径")
    parser.add_argument("path", nargs="?", default=POSTS_DIR, help=f"Markdown文件或目录，默认 {POSTS_DIR}")
    args = parser.parse_args()

    target_path = args.path
    all_failed = []
    all_failed_seen = set()
    for md_path in iter_md_files(target_path):
        failed_urls = replace_http_images(md_path)
        for url in failed_urls:
            if url not in all_failed_seen:
                all_failed.append(url)
                all_failed_seen.add(url)
    if all_failed:
        print("下载失败的图片URL:")
        for url in all_failed:
            print(url)


if __name__ == "__main__":
    main()
