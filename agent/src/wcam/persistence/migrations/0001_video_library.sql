create table if not exists videos (
    id text primary key,
    name text not null,
    file_name text not null,
    duration_seconds real not null,
    width integer not null,
    height integer not null,
    fps real not null,
    codec text not null,
    filmstrip_frames integer not null,
    added_order integer not null
);

create table if not exists clips (
    position integer primary key,
    id text not null,
    video_id text not null references videos (id) on delete cascade,
    in_seconds real not null,
    out_seconds real not null
);
