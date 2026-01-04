-- auto-generated definition
create table songs
(
    id               varchar(50)  not null
        primary key,
    title            varchar(255) not null,
    artist           varchar(255) not null,
    lyrics           text,
    segmented_lyrics text,
    review_text      text,
    review_vector    vector(1024),
    tfidf_vector     jsonb,
    album_cover      varchar(500),
    created_at       timestamp,
    is_duplicate     boolean   default false,
    vibe_tags        jsonb,
    vibe_scores      jsonb,
    recommend_scene  text,
    updated_at       timestamp default CURRENT_TIMESTAMP
);

comment on column songs.id is '网易云音乐歌曲ID';

comment on column songs.title is '歌曲标题';

comment on column songs.artist is '歌手';

comment on column songs.lyrics is '原始歌词';

comment on column songs.segmented_lyrics is '分词后的歌词 (用于 TF-IDF)';

comment on column songs.review_text is 'LLM 生成的情感评语';

comment on column songs.review_vector is '评语 Embedding 向量';

comment on column songs.tfidf_vector is 'TF-IDF 向量 (JSON)';

comment on column songs.album_cover is '专辑封面 URL';

comment on column songs.created_at is '创建时间';

comment on column songs.is_duplicate is '是否为重复歌曲';

comment on column songs.vibe_tags is 'LLM 提取的氛围标签 (JSONB 数组)';

comment on column songs.vibe_scores is '情感维度评分 (JSONB)';

comment on column songs.recommend_scene is 'LLM 建议的听歌场景';

comment on column songs.updated_at is '最后更新时间';

alter table songs
    owner to root;

