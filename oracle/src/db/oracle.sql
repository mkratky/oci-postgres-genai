create user vector identified by &1;
grant unlimited tablespace to vector;
grant resource to vector;

-- DROP TABLE docs;
CREATE TABLE vector.docs (
    id NUMBER GENERATED by default on null as IDENTITY,
    content CLOB,
    summary CLOB,
    translation CLOB,
    summary_embed vector(1024),
    filename varchar2(256),    
    path varchar2(1024),    
    content_type varchar2(256),
    region varchar2(256),    
    application_name varchar2(256),
    author varchar2(256),
    creation_date varchar2(256),    
    modified varchar2(256),    
    other1 varchar2(1024),    
    other2 varchar2(1024),    
    other3 varchar2(1024),    
    parsed_by varchar2(256),    
    publisher varchar2(256)
);

-- DROP TABLE docs_chunck;
CREATE TABLE vector.docs_chunck (
    id NUMBER GENERATED by default on null as IDENTITY,
    doc_id number,
    content CLOB,
    translation CLOB,
    cohere_embed vector(1024),
    filename varchar2(256),    
    path varchar2(1024),    
    content_type varchar2(256),
    region varchar2(256),    
    page integer,
    char_start integer,
    char_end integer,
    summary CLOB
);

create index vector.docs_index on vector.docs_chunck( content ) indextype is ctxsys.context;  

exit
