# Service Central pgvector SQL Patterns

## 1) Discover candidate tables/columns

```sql
select table_schema, table_name, column_name, udt_name
from information_schema.columns
where udt_name = 'vector'
order by 1,2,3;
```

## 2) Basic cosine similarity search

Replace placeholders:
- `service_central_docs`
- `embedding`
- `id`, `title`, `content`
- vector literal `'[ ... ]'::vector`

```sql
select
  id,
  title,
  left(content, 240) as snippet,
  1 - (embedding <=> '[0.01,0.02,0.03]'::vector) as similarity
from service_central_docs
order by embedding <=> '[0.01,0.02,0.03]'::vector
limit 8;
```

## 3) Alternative distance operators

- Cosine distance: `<=>` (recommended default)
- L2 distance: `<->`
- Inner product distance: `<#>`

## 4) Performance indexing

### HNSW (recommended for quality/speed balance)

```sql
create index if not exists idx_service_central_embedding_hnsw
on service_central_docs
using hnsw (embedding vector_cosine_ops);
```

### IVFFlat (needs list tuning)

```sql
create index if not exists idx_service_central_embedding_ivfflat
on service_central_docs
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

## 5) Sanity checks

```sql
select extname from pg_extension where extname='vector';
```

```sql
select count(*) as row_count from service_central_docs;
```

```sql
explain analyze
select id
from service_central_docs
order by embedding <=> '[0.01,0.02,0.03]'::vector
limit 8;
```
