
"""
Code Smell Detection Web Application
Flask backend with GitHub integration and file upload support
"""
import os
import re
import json
import zipfile
import tempfile
import requests
from io import BytesIO
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from java_parser import JavaParser
from smell_detector import SmellDetector

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max


def fetch_github_repo(repo_url):
    """Fetch Java files from a GitHub repository archive."""
    clean_url = repo_url.strip().rstrip('/')
    match = re.search(r'github\.com/([^/]+)/([^/]+)', clean_url)
    if not match:
        return None, "Invalid GitHub URL format. Please use format: https://github.com/username/repository"

    owner = match.group(1)
    repo = match.group(2).replace('.git', '')

    # Try zipball download options from GitHub
    zip_urls = [
        f"https://github.com/{owner}/{repo}/archive/HEAD.zip",
        f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
        f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip",
        f"https://api.github.com/repos/{owner}/{repo}/zipball"
    ]

    java_files = []
    last_error = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for zip_url in zip_urls:
        try:
            resp = requests.get(zip_url, headers=headers, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                with zipfile.ZipFile(BytesIO(resp.content)) as z:
                    for name in z.namelist():
                        if name.endswith('.java') and not name.startswith('__MACOSX'):
                            # Strip root repository folder name from zip file structure
                            parts = name.split('/', 1)
                            norm_path = parts[1] if len(parts) > 1 and parts[1] else name
                            try:
                                content = z.read(name).decode('utf-8', errors='ignore')
                                java_files.append({
                                    'path': norm_path,
                                    'content': content
                                })
                            except Exception:
                                continue
                if java_files:
                    return java_files, None
            else:
                last_error = f"GitHub returned status code {resp.status_code}"
        except Exception as e:
            last_error = str(e)
            continue

    if not java_files:
        return None, last_error or "No Java files found in GitHub repository"

    return java_files, None



def process_files(file_list):
    """Process a list of Java files and detect smells."""
    parser = JavaParser()

    for file_info in file_list:
        try:
            parser.parse_file(file_info['path'], file_info['content'])
        except Exception as e:
            print(f"Error parsing {file_info['path']}: {e}")
            continue

    parser.calculate_cross_reference_metrics()

    detector = SmellDetector()
    classes = detector.detect_smells(parser.classes)

    return classes


def serialize_results(classes):
    """Convert results to JSON-serializable format."""
    results = []
    for cls in classes:
        class_data = {
            'name': cls.name,
            'package': cls.package,
            'parent': cls.parent_class,
            'startLine': cls.start_line,
            'metrics': {
                'LOC': cls.loc,
                'NOM': cls.nom,
                'NOPM': cls.nopm,
                'WMC': cls.wmc,
                'TCC': round(cls.tcc, 2),
                'WOC': round(cls.woc, 2),
                'NAS': cls.nas,
                'PNAS': round(cls.pnas, 2),
                'NProtM': cls.nprotm,
                'BUR': round(cls.bur, 2),
                'BOvR': round(cls.bovr, 2),
                'AMW': round(cls.amw, 2),
                'NOPA': cls.nopa,
                'NOAM': cls.noam
            },
            'methods': [],
            'smells': cls.smells
        }

        for method in cls.methods:
            class_data['methods'].append({
                'name': method.name,
                'returnType': method.return_type,
                'modifiers': method.modifiers,
                'startLine': method.start_line,
                'endLine': method.end_line,
                'metrics': {
                    'LOC': method.loc,
                    'CYCLO': method.cyclo,
                    'MAXNESTING': method.max_nesting,
                    'NOAV': method.noav,
                    'CINT': method.cint,
                    'CDISP': round(method.cdisp, 2),
                    'CM': method.cm,
                    'CC': method.cc,
                    'ATFD': method.atfd,
                    'FDP': method.fdp,
                    'LAA': round(method.laa, 2)
                }
            })

        results.append(class_data)

    return results


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze/github', methods=['POST'])
def analyze_github():
    data = request.get_json()
    repo_url = data.get('url', '')

    if not repo_url:
        return jsonify({'error': 'No URL provided'}), 400

    files, error = fetch_github_repo(repo_url)
    if error:
        return jsonify({'error': error}), 400

    if not files:
        return jsonify({'error': 'No Java files found in repository'}), 404

    classes = process_files(files)
    results = serialize_results(classes)

    # Also return file contents for display
    file_contents = {f['path']: f['content'] for f in files}

    return jsonify({
        'classes': results,
        'files': file_contents,
        'totalFiles': len(files),
        'totalClasses': len(classes),
        'totalSmells': sum(len(c['smells']) for c in results)
    })


@app.route('/api/analyze/upload', methods=['POST'])
def analyze_upload():
    files_data = []

    def extract_zip(file_bytes):
        extracted = []
        try:
            with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                for name in z.namelist():
                    if name.endswith('.java') and not name.startswith('__MACOSX'):
                        parts = name.split('/', 1)
                        norm_path = parts[1] if len(parts) > 1 and parts[1] else name
                        content = z.read(name).decode('utf-8', errors='ignore')
                        extracted.append({'path': norm_path, 'content': content})
        except Exception as e:
            print(f"Error unzipping uploaded file: {e}")
        return extracted

    # Collect files from all request.files keys
    for key in request.files:
        for file in request.files.getlist(key):
            fname = file.filename
            if not fname:
                continue
            file_bytes = file.read()
            if fname.lower().endswith('.zip'):
                files_data.extend(extract_zip(file_bytes))
            elif fname.lower().endswith('.java'):
                content = file_bytes.decode('utf-8', errors='ignore')
                files_data.append({'path': fname, 'content': content})

    if not files_data:
        return jsonify({'error': 'No Java files found in upload'}), 400

    classes = process_files(files_data)
    results = serialize_results(classes)

    file_contents = {f['path']: f['content'] for f in files_data}

    return jsonify({
        'classes': results,
        'files': file_contents,
        'totalFiles': len(files_data),
        'totalClasses': len(classes),
        'totalSmells': sum(len(c['smells']) for c in results)
    })



@app.route('/api/analyze/text', methods=['POST'])
def analyze_text():
    data = request.get_json()
    filename = data.get('filename', 'Main.java')
    content = data.get('content', '')

    if not content:
        return jsonify({'error': 'No content provided'}), 400

    files_data = [{'path': filename, 'content': content}]
    classes = process_files(files_data)
    results = serialize_results(classes)

    return jsonify({
        'classes': results,
        'files': {filename: content},
        'totalFiles': 1,
        'totalClasses': len(classes),
        'totalSmells': sum(len(c['smells']) for c in results)
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
