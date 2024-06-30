-- DROP TABLE DEPT;
CREATE TABLE DEPT
       (DEPTNO INT PRIMARY KEY,
        DNAME VARCHAR(64),
        LOC VARCHAR(64) );

INSERT INTO DEPT VALUES (10, 'ACCOUNTING', 'TOKYO');
INSERT INTO DEPT VALUES (20, 'RESEARCH',   'POSTGRESQL');
INSERT INTO DEPT VALUES (30, 'SALES',      'BEIJING');
INSERT INTO DEPT VALUES (40, 'OPERATIONS', 'SEOUL');

CREATE EXTENSION  IF NOT EXISTS vector;

-- DROP TABLE docs;
CREATE TABLE docs (
    id bigserial PRIMARY KEY, 

    content text,
    summary text,
    translation text,
    summary_embed vector(1024),

    filename varchar(256),    
    path varchar(1024),    
    content_type varchar(256),
    region varchar(256),    

    application_name varchar(256),
    author varchar(256),
    creation_date varchar(256),    
    modified varchar(256),    
    other1 varchar(1024),    
    other2 varchar(1024),    
    other3 varchar(1024),    
    parsed_by varchar(256),    
    publisher varchar(256),
    source_type varchar(256)
);

-- DROP TABLE docs_chunck;
CREATE TABLE docs_chunck (
    id bigserial PRIMARY KEY, 
    doc_id bigint,
    fileblob BYTEA,
    content text,
    translation text,
    cohere_embed vector(1024),

    filename varchar(256),    
    path varchar(1024),    
    content_type varchar(256),
    region varchar(256),    
    page integer,
    char_start integer,
    char_end integer,
    summary text
);



