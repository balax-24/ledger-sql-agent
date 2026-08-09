-- Run this once in the Supabase SQL editor for a fresh project.

create table if not exists customers (
  id serial primary key,
  name text not null,
  email text unique not null,
  region text not null,
  created_at timestamp not null default now()
);

create table if not exists products (
  id serial primary key,
  name text not null,
  category text not null,
  price numeric(10, 2) not null,
  cost numeric(10, 2) not null
);

create table if not exists orders (
  id serial primary key,
  customer_id integer not null references customers(id),
  order_date timestamp not null,
  status text not null check (status in ('pending', 'paid', 'shipped', 'delivered', 'cancelled'))
);

create table if not exists order_items (
  id serial primary key,
  order_id integer not null references orders(id),
  product_id integer not null references products(id),
  quantity integer not null check (quantity > 0),
  unit_price numeric(10, 2) not null
);

create index if not exists idx_orders_customer on orders(customer_id);
create index if not exists idx_orders_date on orders(order_date);
create index if not exists idx_order_items_order on order_items(order_id);
create index if not exists idx_order_items_product on order_items(product_id);

-- ---------------------------------------------------------------------
-- Read-only role. The agent connects as this role, never as the
-- Supabase owner/service role. Even if the SQL-safety check in the
-- run_sql_query tool has a bug, this role physically cannot write.
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (select from pg_roles where rolname = 'agent_readonly') then
    create role agent_readonly login password 'Mb5xcxCL8hoAygMr';
  end if;
end
$$;

grant usage on schema public to agent_readonly;
grant select on customers, products, orders, order_items to agent_readonly;

-- Make sure future tables in this schema stay readable but not writable
alter default privileges in schema public grant select on tables to agent_readonly;
