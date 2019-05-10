-- version 3.1.0 update 2019/1/25
alter table bg_user add column phone varchar(11);
alter table bg_user add column name varchar(20);
alter table bg_user add column rights varchar(1) default '1';
alter table bg_user add column time integer;
alter table bg_user add column uid uuid DEFAULT uuid_generate_v4();

alter table bg_user alter column password type varchar(60);
update bg_user set rights = '0' where username = 'admin';

alter table bg_user drop constraint username;
alter table bg_user add CONSTRAINT uid PRIMARY key (uid);
alter table bg_user add CONSTRAINT phone UNIQUE (phone);

-- version 3.4.0 update 2019/3/12

CREATE TABLE bg_banner (
  "id"      character varying(20) primary key,
  "image"   character varying(50) not null,
  "state"   character varying(1) DEFAULT '1',
  "time"    integer not NULL
);