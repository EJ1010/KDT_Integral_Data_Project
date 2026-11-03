# 캐릭터 IP별 description 키워드 동시출현 분석

## 확인된 원본 구조

`instagram_normalized_3nf_posts(1).csv`는 13,464행, 7열이며 컬럼은 다음과 같습니다.

```text
post_id, description, media_type_id, post_url, created_at, like_count, comment_count
```

- 분석 단위: `post_id` 기준 고유 게시글
- 분석 텍스트: `description`
- `description` 결측: 138건
- `post_id` 중복: 0건
- `post_url` 중복: 0건
- 공백만 정리한 동일 캡션 중복: 427건

스크립트는 URL·멘션·문자 폭·공백까지 정규화한 뒤 동일 캡션을 다시 판정하므로 실제 제거 수는 위의 단순 공백 기준 수보다 늘어날 수 있습니다. 기본값은 캡션 중복 제거이며 `--no-dedupe-text`로 끌 수 있습니다.

## 설치

PowerShell에서 다음을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements-ip-keyword.txt
```

## 실행

```powershell
python .\ip_keyword_cooccurrence.py `
  'C:\경로\instagram_normalized_3nf_posts(1).csv' `
  --output-dir .\ip_keyword_output `
  --min-keyword-df 10 `
  --min-co-count 3 `
  --top-n 25 `
  --save-post-map
```

현재 첨부 파일을 이 대화의 임시 경로에서 직접 실행하는 예시는 다음과 같습니다.

```powershell
python .\ip_keyword_cooccurrence.py `
  'C:\Users\user\AppData\Local\Temp\codex-file-preview-ozYBpC\instagram_normalized_3nf_posts(1).csv' `
  --output-dir .\ip_keyword_output
```

임시 첨부 경로는 대화가 끝난 뒤 사라질 수 있으므로 CSV를 프로젝트 폴더로 복사해 사용하는 편이 안전합니다.

## 주요 옵션

- `--ip-aliases aliases.json`: 기본 IP 별칭 사전을 사용자 JSON으로 교체합니다.
- `--stopwords stopwords.txt`: 한 줄에 하나씩 추가 불용어를 넣습니다.
- `--no-dedupe-text`: 동일 정규화 캡션을 별도 게시글로 유지합니다.
- `--tokenizer regex`: Kiwi 없이 파이프라인만 점검합니다. 최종 분석에는 기본값인 `kiwi`를 권장합니다.
- `--no-plots`: PNG 시각화를 만들지 않습니다.
- `--save-post-map`: 게시글별 탐지 IP와 키워드 목록을 저장합니다.

별칭 JSON 형식:

```json
{
  "치이카와": ["치이카와", "먼작귀", "ちいかわ", "chiikawa"],
  "산리오": ["산리오", "sanrio", "쿠로미", "시나모롤"]
}
```

## 저장 결과

- `analysis_audit.csv`: 원본/제외/중복 제거/최종 분석 행 수
- `ip_frequency.csv`: IP별 언급 게시글 수와 전체 대비 비율
- `keyword_frequency.csv`: 키워드별 고유 게시글 빈도와 비율
- `ip_keyword_cooccurrence.csv`: 빈도, IP 내 동시출현율, 전체 지지도, 기대빈도, lift
- `matrix_co_count.csv`, `matrix_co_rate_pct.csv`, `matrix_lift.csv`: 피벗 행렬
- `post_ip_keywords.csv`: `--save-post-map` 사용 시 게시글별 탐지 결과
- `plots/heatmap_co_rate.png`, `plots/heatmap_lift.png`: 비교 히트맵
- `plots/bar_*.png`: IP별 상위 키워드
- `plots/network_ip_keyword.png`: lift 1 이상인 IP-키워드 네트워크

## 지표 해석

- `co_count`: 해당 IP와 키워드가 함께 나온 고유 게시글 수
- `co_rate_pct`: `co_count / 해당 IP 게시글 수 × 100`
- `support_pct`: `co_count / 전체 분석 게시글 수 × 100`
- `lift`: `관측 동시출현 빈도 / 독립 가정하의 기대 빈도`
  - 1보다 큼: 전체 키워드 빈도에 비해 해당 IP에서 상대적으로 더 자주 등장
  - 1과 비슷: 전체 평균 수준
  - 1보다 작음: 해당 IP에서 상대적으로 덜 등장

표본이 매우 작은 IP의 lift는 불안정합니다. `ip_post_count`, `co_count`, `co_rate_pct`를 함께 보고, 필요하면 IP별 최소 게시글 수 기준을 추가해 해석해야 합니다.
