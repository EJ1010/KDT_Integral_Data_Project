from pathlib import Path
import nbformat, hashlib, io, contextlib, base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=Path(r'C:\Users\jaena\OneDrive\Desktop\data.project\KDT_Integral_Data_Project\02_csv\01_youtube\3. code\04. youtube_EDA_v2.ipynb')
w=Path.cwd()/'youtube_v2_cleanup'
raw=p.read_bytes()
(w/'04. youtube_EDA_v2.before_channel_review.ipynb').write_bytes(raw)
n=nbformat.reads(raw.decode('utf-8'),as_version=4)
md='''## 채널 ID 기반 관련성 검토와 제외

채널명 검색 실패는 삭제·무관 판정의 근거가 아니다. 수집 시점의 채널 ID와 영상 ID로 직접 확인 링크를 생성한다. 아래 3개 채널은 사용자가 무관하다고 확인한 대상으로, 그 판단을 출처로 기록해 분석에서 제외한다. 코드가 영상 내용을 자동 검증한 것은 아니다.

원본 CSV는 보존한다. 제외 영상은 `channel_review_videos`, 제외 전 후보 집합은 `df_before_channel_review`에 남긴다. `APPLY_CHANNEL_EXCLUSIONS=False`로 바꾸면 비교용으로 제외 전 분석을 실행할 수 있다. 링크의 현재 접근 가능 여부와 실제 영상 내용은 별도 확인이 필요하다.

제목 본문·해시태그·설명·태그별 명칭 매칭을 구분한다. 본문 매칭 여부만으로 관련성을 자동 확정하지 않는다.'''
code='''APPLY_CHANNEL_EXCLUSIONS = True
CHANNEL_REVIEW = {
    "UC_bq6EA8U2xCcBgMjshCh0Q": "Antistress Toys",
    "UCDtDKN4I6SS6rCiUi7lPyXg": "NekYos",
    "UCiHMmtaCy2vIcs17gFqC4fQ": "Favorite Toys",
}
df_before_channel_review = df.copy()
channel_review_videos = df.loc[df["channel_id"].isin(CHANNEL_REVIEW)].copy()
channel_review_videos["channel_url"] = "https://www.youtube.com/channel/" + channel_review_videos["channel_id"]
channel_review_videos["video_url"] = "https://www.youtube.com/watch?v=" + channel_review_videos["video_id"]
channel_review_videos["title_hashtags"] = channel_review_videos["title"].fillna("").str.findall(r"[#＃][^\\s#＃]+").str.join(" ")
channel_review_videos["title_body"] = channel_review_videos["title"].fillna("").str.replace(r"[#＃][^\\s#＃]+", " ", regex=True).str.strip()
name_pattern = r"치이카와|먼작귀|ちいかわ|chiikawa"
for field in ["title_body", "title_hashtags", "description", "tags"]:
    channel_review_videos[f"match_{field}"] = channel_review_videos[field].fillna("").str.replace(r"\\s+", "", regex=True).str.contains(name_pattern, case=False, regex=True)
channel_review_videos["review_source"] = "사용자 확인: 치이카와 무관 채널"
channel_review_videos["availability_status"] = "미확인: 검색 실패로 삭제 여부를 판단하지 않음"
channel_review_summary = channel_review_videos.groupby(["channel_id", "channel"]).agg(
    영상수=("video_id", "size"), 누적조회수=("view_count", "sum"),
    제목본문매칭=("match_title_body", "sum"), 제목해시태그매칭=("match_title_hashtags", "sum"),
).reset_index()
channel_review_summary["채널직접링크"] = "https://www.youtube.com/channel/" + channel_review_summary["channel_id"]
print(channel_review_summary.to_string(index=False))
print("\\n수집된 영상 직접 확인 목록")
print(channel_review_videos[["channel", "title", "title_body", "match_title_body", "match_title_hashtags", "match_description", "match_tags", "video_url"]].to_string(index=False))
missing_ids = set(CHANNEL_REVIEW) - set(channel_review_videos["channel_id"])
print("수집 데이터에 없는 대상 채널 ID:", sorted(missing_ids))
if APPLY_CHANNEL_EXCLUSIONS:
    df = df_before_channel_review.loc[~df_before_channel_review["channel_id"].isin(CHANNEL_REVIEW)].copy()
else:
    df = df_before_channel_review.copy()
print("\\n제외 적용:", APPLY_CHANNEL_EXCLUSIONS, "/ 제외 전:", len(df_before_channel_review), "/ 제외 후:", len(df))
if APPLY_CHANNEL_EXCLUSIONS:
    assert len(df_before_channel_review) == len(df) + len(channel_review_videos)
    assert not df["channel_id"].isin(CHANNEL_REVIEW).any()
assert df["video_id"].is_unique
'''
n.cells[8:8]=[nbformat.v4.new_markdown_cell(md),nbformat.v4.new_code_cell(code)]
for c in n.cells:
    if c.cell_type=='code':
        c.source=c.source.replace('rename("전체 relevant")','rename("관련성 검토 후 전체")').replace('["전체 relevant"]','["관련성 검토 후 전체"]').replace('"전체 relevant",','"관련성 검토 후 전체",')
    elif '## 해석을 읽는 기준' in c.source:
        c.source=c.source[:c.source.index('추가 확인이 필요한 것')]+'''추가 확인이 필요한 것

- 짧은 키워드의 오탐은 위 경계 사례의 현재 출력값을 기준으로 검토한다.
- 제외된 채널의 상태는 사용자 확인에 근거하며, 검색 가능 여부나 영상 내용을 코드로 검증한 것은 아니다.
- 캐릭터 시사의 시사회 오탐과 혼합 언어 제목 범위는 별도 검토 과제로 남아 있다.
- 인기 예측이나 실제 구매·방문으로 해석하려면 다른 자료와 추가 검증이 필요하다.'''
ns={}; count=0
for c in n.cells:
    if c.cell_type!='code':continue
    count+=1;c.execution_count=count;c.outputs=[];buf=io.StringIO()
    def flush():
        if buf.getvalue():c.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=buf.getvalue()));buf.seek(0);buf.truncate(0)
    def show():
        flush()
        for num in plt.get_fignums():
            pic=io.BytesIO();plt.figure(num).savefig(pic,format='png',bbox_inches='tight')
            c.outputs.append(nbformat.v4.new_output('display_data',data={'image/png':base64.b64encode(pic.getvalue()).decode()}))
        plt.close('all')
    plt.show=show
    with contextlib.redirect_stdout(buf):exec(compile(c.source,'<cell>','exec'),ns)
    flush()
nbformat.validate(n)
nbformat.write(n,w/p.name)
ns['channel_review_videos'].to_csv(w/'channel_review_videos.csv',index=False,encoding='utf-8-sig')
(w/'source.sha256').write_text(hashlib.sha256(raw).hexdigest())
print('PASS',len(ns['channel_review_videos']),'excluded; scope',ns['N_KR'],'; all cells executed')
