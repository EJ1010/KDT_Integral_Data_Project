from pathlib import Path
import copy, hashlib, io, contextlib, sys
import nbformat
from nbclient import NotebookClient

source = Path(r'C:\Users\jaena\OneDrive\Desktop\data.project\KDT_Integral_Data_Project\02_csv\01_youtube\3. code\04. youtube_EDA_v2.ipynb')
work = Path.cwd() / 'youtube_v2_cleanup'
work.mkdir(exist_ok=True)
raw = source.read_bytes()
(work / '04. youtube_EDA_v2.before_cleanup.ipynb').write_bytes(raw)
nb = nbformat.reads(raw.decode('utf-8-sig'), as_version=4)
original = copy.deepcopy(nb)
c = nb.cells
c[0].source = '''### 치이카와 유튜브 EDA v2

제목 기준 9개 소비·콘텐츠 유형의 다중 라벨 분석으로 콘텐츠 생산, 유형별 반응, 연도별 변화와 동시 출현을 탐색한다. 키워드 언급량, 캐릭터·작품명, 전체 시계열과 채널 구조를 함께 살펴본다.

v1의 6종 분류를 9종 다중 라벨 분류로 개편했다. 과거 분류와 결과는 v1에서 확인할 수 있다. 원본 CSV와 v1은 변경하지 않으며 파생 열은 분석용 복사본에만 추가한다.

분석 대상은 제목에 한글이 있고 히라가나·가타카나가 없는 영상이다. 이는 제목 언어에 따른 국내 생산의 대리 지표이며 한국인 제작자나 한국 시청자를 보장하지 않는다.

입력은 현재 프로젝트의 `youtube_analysis_merged.csv`와 `youtube_relevance_audit_merged.csv`다.'''
s = c[2].source
start = s.index('V1_ROOT =')
end = s.index('for path in (ANALYSIS_CSV, AUDIT_CSV):')
c[2].source = s[:start] + s[end:]
c[9].source = '''## 국내 제목 부분집합

수집은 한국 시간 연도와 `regionCode=KR`을 사용했지만 일본어 제목도 포함된다. 이하 분석은 제목에 한글이 있고 히라가나·가타카나가 없는 영상에 적용한다.'''
c[11].source = '''## 제목 단어 분포

콘텐츠 유형은 제목만 사용한다. 설명의 성우 크레딧 때문에 본편 영상을 더빙 창작으로 분류하지 않기 위한 기준이다. 캐릭터·작품명은 제목, 설명, 태그를 합친 `search_text`를 사용한다.

Kiwi 형태소 분석이 아니라 `[가-힣]{2,}`로 두 글자 이상 연속된 한글 문자열을 추출한다. 출현 횟수는 같은 제목 안의 반복도 센다. 언급 영상 수는 영상별 동일 단어를 한 번만 센다.

문자열 출현 횟수, 단어별 고유 영상 수, 사전 키워드 매칭, 유형별 OR 집계를 구분한다.'''
c[13].source = '''## 캐릭터·작품명 분류

11종 캐릭터와 2종 작품명을 제목·설명·태그에서 판별한다. 캐릭터는 복수 언급을 허용한다. `시사(?!리즈)`, `파자마\\s*파티즈|파자마즈`, `(?<![가-힣])카니(?![가-힣])`의 구분 규칙을 유지한다.

`치이카와`와 `먼작귀`는 작품명으로 집계하며 개별 캐릭터 선호로 해석하지 않는다.'''
s = c[14].source
s = s[s.index('CHARACTER_RULES ='):]
start = s.index('for name, keywords in CONTENT_RULES:')
end = s.index('for name, pattern in CHARACTER_RULES:')
s = s[:start] + '''def join_labels(row, columns, labels):
    return "|".join(label for column, label in zip(columns, labels) if row[column])

''' + s[end:]
start = s.index('for name, keywords in CONTENT_RULES:')
end = s.index('for name, pattern in CHARACTER_RULES:', start)
s = s[:start] + s[end:]
s = '\n'.join(line for line in s.splitlines() if 'df_kr["content_type"]' not in line and 'primary_content_type' not in line)
c[14].source = s
c[16].source = '\n'.join(line for line in c[16].source.splitlines() if '인형계' not in line)
c[19].source = c[19].source.replace('분석 3.', '분석 2.')
c[21].source = c[21].source.replace('분석 4.', '분석 3.')
c[23].source = c[23].source.split('\n기존 6종에만 있는')[0].replace('## 신규 9종 다중 라벨', '## 분석 4. 9종 소비·콘텐츠 유형의 다중 라벨 분류')
c[27].source = '''## 9종별 규모와 이용자 반응

비율의 분모는 전체 분석 대상 영상 수다. 한 영상에 여러 유형이 붙으므로 유형별 비율의 합은 100%를 넘을 수 있다.

조회수 평균은 일부 상위 영상에 영향을 받으므로 중앙값을 함께 본다. 좋아요·댓글이 결측이면 참여율은 계산하지 않는다. 반응 차이를 인기의 원인으로 단정하지 않는다.'''
c[28].source = '\n'.join(line for line in c[28].source.splitlines() if 'type_인형계·상황극' not in line)
c[37].source = '''## 원본 무결성과 집계 검증

로드 직후와 분석 후 원본 데이터프레임의 크기, 영상 ID 순서, 좋아요·댓글 결측 수를 비교한다. 영상 ID 고유성, 유형 내부 중복, 미분류 수 및 라벨 수 합계의 일치를 검증한다.'''
s = c[38].source
start = s.index('snapshot =')
end = s.index('assert df["video_id"].is_unique', start)
c[38].source = s[:start] + s[end:]
nb.cells = [cell for i, cell in enumerate(c) if i not in {1, 17, 18, 32, 33}]
for cell in nb.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
        compile(cell.source, '<cell>', 'exec')
text = '\n'.join(cell.source for cell in nb.cells)
for obsolete in ['CONTENT_RULES', 'CONTENT_PRIORITY', 'primary_content_type', 'type_인형계·상황극', 'old_new', 'snapshot_table', 'MNT_V1']:
    assert obsolete not in text, obsolete
nbformat.validate(nb)

# Run both versions without notebook output to compare retained computations.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.show = lambda: plt.close('all')
def run(book):
    namespace = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for index, cell in enumerate(book.cells):
            if cell.cell_type == 'code':
                print('Checking cell', index, file=sys.stderr, flush=True)
                exec(compile(cell.source, '<cell>', 'exec'), namespace)
    return namespace
before = run(original)
after = run(nb)
import pandas as pd
checks = ['token_counts', 'token_video_counts', 'char_summary', 'channel_stats', 'yearly', 'monthly', 'keyword_mention', 'v2_summary', 'length_summary', 'yearly_type_count', 'yearly_type_share', 'monthly_type', 'keyword_year', 'co']
for key in checks:
    pd.testing.assert_frame_equal(before[key], after[key])
assert before['N_KR'] == after['N_KR']
print('Comparison passed. Refreshing notebook outputs.', flush=True)

# Refresh all displayed outputs in a fresh notebook kernel.
import base64
namespace = {}
execution_count = 0
for cell in nb.cells:
    if cell.cell_type != 'code':
        continue
    execution_count += 1
    cell.execution_count = execution_count
    capture = io.StringIO()
    def flush_text():
        value = capture.getvalue()
        if value:
            cell.outputs.append(nbformat.v4.new_output('stream', name='stdout', text=value))
            capture.seek(0)
            capture.truncate(0)
    def show_figures():
        flush_text()
        for number in plt.get_fignums():
            buffer = io.BytesIO()
            plt.figure(number).savefig(buffer, format='png', bbox_inches='tight')
            cell.outputs.append(nbformat.v4.new_output('display_data', data={'image/png': base64.b64encode(buffer.getvalue()).decode('ascii')}, metadata={}))
        plt.close('all')
    plt.show = show_figures
    with contextlib.redirect_stdout(capture):
        exec(compile(cell.source, '<cell>', 'exec'), namespace)
    flush_text()
nbformat.validate(nb)
output = work / source.name
nbformat.write(nb, output)
(work / 'source.sha256').write_text(hashlib.sha256(raw).hexdigest(), encoding='ascii')
print(f'PASS: {len(checks)} retained tables unchanged; {len(original.cells)} -> {len(nb.cells)} cells; all cells executed.')
print(output)
