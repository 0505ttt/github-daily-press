#!/usr/bin/env python3
"""解析 GitHub Trending 页面 HTML（支持实时页与 Wayback 快照页）为 JSON。

用法:
    parse_trending.py <trending.html 路径> [--top 10]
依赖: bs4（用 tools/.venv/bin/python 运行）
"""
import argparse
import json
import re
import sys

from bs4 import BeautifulSoup

REPO_HREF = re.compile(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:[/?#]|$)')
REPO_PATH = re.compile(r'^/?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:[/?#]|$)')


def extract_repo_name(href: str) -> str:
    """从 href 中提取 owner/repo，兼容 Wayback 重写后的绝对/相对链接。"""
    if not href:
        return ''
    m = REPO_HREF.search(href)
    if m:
        return m.group(1)
    m = REPO_PATH.match(href)
    if m:
        return m.group(1)
    return ''


def parse_trending(html: str, top: int = 10):
    if top < 1:
        raise ValueError('收录数量必须大于零')
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.find_all('article', class_='Box-row')
    projects, seen = [], set()
    for i, art in enumerate(articles[:top]):
        name = ''
        h2 = art.find('h2')
        if h2:
            a = h2.find('a')
            if a:
                name = extract_repo_name(a.get('href', ''))

        p = art.find('p')
        desc = p.get_text(' ', strip=True) if p else ''

        lang_span = art.find('span', itemprop='programmingLanguage')
        lang = lang_span.get_text(strip=True) if lang_span else ''

        today_stars = ''
        today_span = art.select_one('span.float-sm-right')
        if today_span:
            today_stars = today_span.get_text(strip=True)

        total_stars = ''
        star_link = art.find('a', href=re.compile(r'/stargazers'))
        if star_link:
            total_stars = star_link.get_text(strip=True)

        total_forks = ''
        fork_link = art.find('a', href=re.compile(r'/forks'))
        if fork_link:
            total_forks = fork_link.get_text(strip=True)

        if not name or name in seen:
            continue
        seen.add(name)
        projects.append({
            # 不用有效行数重排名，避免坏行把后续仓库名次前移。
            'rank': i + 1,
            'name': name,
            'desc': desc,
            'lang': lang or '未标注',
            'total_stars': total_stars or '暂未获取',
            'today_stars': today_stars or '暂未获取',
            'total_forks': total_forks or '暂未获取',
            'url': f'https://github.com/{name}',
        })
    return projects


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html_file', help='trending 页面 HTML 文件路径')
    ap.add_argument('--top', type=int, default=10)
    args = ap.parse_args()
    with open(args.html_file, encoding='utf-8', errors='replace') as f:
        html = f.read()
    projects = parse_trending(html, args.top)
    if not projects:
        print('警告: 未解析到任何项目，页面结构可能已变化', file=sys.stderr)
        sys.exit(2)
    print(json.dumps(projects, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
