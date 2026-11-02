from pathlib import Path
import nbformat, hashlib, io, contextlib, base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(r'C:\Users\jaena\OneDrive\Desktop\data.project\KDT_Integral_Data_Project\02_csv\01_youtube\3. code\04. youtube_EDA_v2.ipynb')
w=Path.cwd()/'youtube_v2_cleanup'
raw=p.read_bytes(); (w/'04. youtube_EDA_v2.before_pattern_review.ipynb').write_bytes(raw)
n=nbformat.reads(raw.decode('utf-8'),as_version=4)
code=r'''# 자동 판정은 관련성 확정이 아니라 검토 우선순위다. df_kr는 변경하지 않는다.
pattern_audit = df_kr.copy()
pt = pattern_audit["title"].fillna("")
pattern_audit["title_body"] = pt.str.replace(r"[#＃][^\s#＃]+", " ", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
tag_lists = pt.str.findall(r"[#＃]([^\s#＃]+)")
pattern_audit["title_hashtags"] = tag_lists.str.join(" ")
pattern_audit["hashtag_signature"] = tag_lists.map(lambda xs: "|".join(sorted(set(x.casefold() for x in xs))))
pattern_audit["hashtag_count"] = tag_lists.map(len)
for field in ["title_body", "title_hashtags", "description", "tags"]:
    pattern_audit[f"name_in_{field}"] = pattern_audit[field].fillna("").str.replace(r"\s+", "", regex=True).str.contains(r"치이카와|먼작귀|ちいかわ|chiikawa", case=False, regex=True)
no_body_name = ~pattern_audit["name_in_title_body"]
pattern_audit["flag_hashtag_only_title"] = no_body_name & pattern_audit["name_in_title_hashtags"]
pattern_audit["flag_no_hangul_body"] = ~pattern_audit["title_body"].str.contains(r"[가-힣]")
pattern_audit["same_signature_in_channel"] = pattern_audit.groupby(["channel_id", "hashtag_signature"])["video_id"].transform("size")
pattern_audit["flag_repeated_hashtags"] = pattern_audit["hashtag_count"].ge(3) & pattern_audit["same_signature_in_channel"].ge(3)
# 앞서 발견한 해시태그 묶음의 동시 등장. 단독 키워드는 무관 근거가 아니다.
pattern_audit["flag_known_tag_bundle"] = tag_lists.map(lambda xs: {"치이카와", "인형계", "감기", "조이"}.issubset(set(xs)))
# 예시 사전은 비포괄적이며, 콜라보/여러 IP 소개도 검출할 수 있다.
OTHER_TOPIC_PATTERN = r"rainbow\s*friends|레인보우\s*프렌즈|mcqueen|맥퀸|skibidi|스키비디|poppy\s*playtime|huggy\s*wuggy|허기워기|m\s*&\s*m"
pattern_audit["flag_other_topic_body"] = pattern_audit["title_body"].str.contains(OTHER_TOPIC_PATTERN, case=False, regex=True)
pattern_audit["flag_metadata_only"] = no_body_name & ~pattern_audit["name_in_title_hashtags"] & (pattern_audit["name_in_description"] | pattern_audit["name_in_tags"])
pattern_audit["is_doll_keyword"] = pt.str.contains("인형계", regex=False)
high = no_body_name & (pattern_audit["flag_known_tag_bundle"] | pattern_audit["flag_other_topic_body"] | (pattern_audit["name_in_title_hashtags"] & pattern_audit["flag_no_hangul_body"]))
medium = pattern_audit["flag_hashtag_only_title"] | pattern_audit["flag_metadata_only"]
low = pattern_audit["flag_repeated_hashtags"]
pattern_audit["review_priority"] = np.select([high, medium, low], ["1_우선 확인", "2_문맥 확인", "3_반복 패턴 참고"], default="패턴 미검출")
pattern_audit["review_status"] = "미검토"
pattern_audit["review_decision"] = ""
pattern_audit["review_evidence"] = ""
pattern_audit["video_url"] = "https://www.youtube.com/watch?v=" + pattern_audit["video_id"]
pattern_audit["channel_url"] = "https://www.youtube.com/channel/" + pattern_audit["channel_id"]
reason_columns = {
    "flag_hashtag_only_title": "제목 본문 명칭 없음·해시태그에 있음",
    "flag_no_hangul_body": "제목 본문 한글 없음",
    "flag_repeated_hashtags": "채널 내 동일 해시태그 묶음 3편 이상",
    "flag_known_tag_bundle": "치이카와·인형계·감기·조이 묶음",
    "flag_other_topic_body": "다른 콘텐츠명 후보",
    "flag_metadata_only": "설명·태그에만 관련 명칭",
}
pattern_audit["review_reasons"] = pattern_audit.apply(lambda row: " / ".join(label for col, label in reason_columns.items() if row[col]), axis=1)
review_candidates = pattern_audit.loc[pattern_audit["review_priority"] != "패턴 미검출"].sort_values(["review_priority", "view_count"], ascending=[True, False]).copy()
pattern_channel_summary = review_candidates.groupby(["channel_id", "channel"]).agg(
    검토후보수=("video_id", "size"), 후보누적조회수=("view_count", "sum"),
    우선확인수=("review_priority", lambda s: s.eq("1_우선 확인").sum()),
    인형계후보수=("is_doll_keyword", "sum"),
).reset_index()
channel_totals = pattern_audit.groupby("channel_id").size()
pattern_channel_summary["채널전체영상수"] = pattern_channel_summary["channel_id"].map(channel_totals)
pattern_channel_summary["후보비율"] = pattern_channel_summary["검토후보수"] / pattern_channel_summary["채널전체영상수"]
pattern_channel_summary["channel_url"] = "https://www.youtube.com/channel/" + pattern_channel_summary["channel_id"]
pattern_channel_summary = pattern_channel_summary.sort_values("후보누적조회수", ascending=False)
print("검토 우선순위별 영상 수")
print(pattern_audit["review_priority"].value_counts().to_string())
print("\n후보 조회수 영향 상위 20채널: 무관 판정 목록이 아님")
print(pattern_channel_summary.head(20).to_string(index=False))
print("\n우선 확인 영상 상위 30편")
print(review_candidates.loc[review_candidates["review_priority"].eq("1_우선 확인"), ["channel", "title", "view_count", "review_reasons", "video_url"]].head(30).to_string(index=False))
print("\n남은 인형계 영상의 검토 우선순위")
print(pattern_audit.loc[pattern_audit["is_doll_keyword"]].groupby("review_priority").agg(영상수=("video_id", "size"), 누적조회수=("view_count", "sum")).to_string())
assert pattern_audit["video_id"].is_unique
assert len(pattern_audit) == len(df_kr) == N_KR
assert not pattern_audit["channel_id"].isin(CHANNEL_REVIEW).any() if APPLY_CHANNEL_EXCLUSIONS else True
'''
md='''## 추가 관련성 검토 패턴 — 자동 제외하지 않음

이미 제외한 세 채널을 뺀 현재 분석 집합에서 검토 후보를 찾는다. 제목 본문과 해시태그를 분리하고, 명칭의 등장 위치·본문 언어·채널 내 반복 해시태그·앞서 발견한 묶음·다른 콘텐츠명 후보를 기록한다.

1순위는 제목 본문에 관련 명칭이 없으면서 알려진 태그 묶음, 다른 콘텐츠명 후보 또는 본문에 한글 없이 관련 해시태그만 있는 경우다. 2순위는 관련 명칭이 제목 해시태그/설명/태그에만 있는 경우, 3순위는 반복 해시태그 참고 대상이다. 동일 묶음 3편 기준은 검토 편의를 위한 기준이며 무관성을 입증하지 않는다.

관련 작품의 공식 영상, 캐릭터 이름만 쓴 제목, 콜라보도 검출될 수 있다. 후보 조회수는 오염된 조회수로 확정하지 않는다. 패턴 미검출도 관련성 확인을 뜻하지 않는다. 직접 링크로 내용을 확인하고 `review_decision`, `review_evidence`에 근거를 기록한 뒤 제외 여부를 결정한다. 이 코드는 현재 분석 표본 밖의 영상이나 온라인 접속 상태를 점검하지 않는다.'''
idx=next(i for i,c in enumerate(n.cells) if c.cell_type=='code' and 'N_KR = len(df_kr)' in c.source)+1
n.cells[idx:idx]=[nbformat.v4.new_markdown_cell(md),nbformat.v4.new_code_cell(code)]
# Execute all cells, refresh text and figure outputs, and validate existing assertions.
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
nbformat.validate(n);nbformat.write(n,w/p.name)
cols=['channel_id','channel','video_id','title','title_body','title_hashtags','view_count','review_priority','review_reasons','is_doll_keyword','video_url','channel_url','review_status','review_decision','review_evidence']
ns['review_candidates'][cols].to_csv(w/'additional_review_videos.csv',index=False,encoding='utf-8-sig')
ns['pattern_channel_summary'].to_csv(w/'additional_review_channels.csv',index=False,encoding='utf-8-sig')
(w/'source.sha256').write_text(hashlib.sha256(raw).hexdigest())
print(ns['pattern_audit']['review_priority'].value_counts().to_string())
print(ns['pattern_channel_summary'].head(12).to_string(index=False))
print('DOLL PRIORITIES')
print(ns['pattern_audit'].loc[ns['pattern_audit'].is_doll_keyword].groupby('review_priority').agg(n=('video_id','size'),views=('view_count','sum')).to_string())
print('HIGH PRIORITY CHANNELS')
print(ns['review_candidates'].query('review_priority == "1_우선 확인"').groupby('channel').agg(n=('video_id','size'),views=('view_count','sum')).sort_values('views',ascending=False).head(12).to_string())
