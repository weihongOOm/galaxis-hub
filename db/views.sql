-- galaxis-hub MCP server views.
-- Run once in the Supabase SQL editor. Idempotent.

-- 1) Latest generated output per (project, section).
create or replace view public.v_latest_project_output as
select distinct on (project_id, section)
       project_id,
       section,
       content,
       created_at
  from public.generated_outputs
 order by project_id, section, created_at desc;

-- 2) Projects lookup view (only the columns the server needs).
create or replace view public.v_projects as
select id, client_name, website
  from public.projects;

-- 3) Tighten grants. Adjust the role name if your project uses a
--    non-default name for the service role.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    revoke all on public.v_latest_project_output from public;
    grant select on public.v_latest_project_output to service_role;

    revoke all on public.v_projects from public;
    grant select on public.v_projects to service_role;
  else
    raise notice 'service_role does not exist; skipping grant step. Update this file with the correct role name and re-run.';
  end if;
end
$$;
