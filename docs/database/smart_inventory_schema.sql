create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;
create extension if not exists citext;

create type user_status as enum ('invited', 'active', 'suspended', 'deleted');
create type po_status as enum ('draft', 'pending_approval', 'approved', 'ordered', 'received', 'cancelled');
create type movement_type as enum ('initial', 'purchase', 'sale', 'adjustment', 'waste', 'transfer', 'return');
create type notification_channel as enum ('in_app', 'email', 'sms', 'push', 'websocket');
create type subscription_status as enum ('trialing', 'active', 'past_due', 'cancelled', 'expired');

create table tenants (
  id uuid primary key default gen_random_uuid(),
  name varchar(160) not null,
  slug varchar(120) not null unique,
  plan_code varchar(80) not null default 'starter',
  status varchar(40) not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table organizations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  name varchar(180) not null,
  legal_name varchar(220),
  tax_id varchar(80),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, name)
);

create table restaurants (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  organization_id uuid not null references organizations(id),
  name varchar(180) not null,
  timezone varchar(80) not null default 'UTC',
  currency char(3) not null default 'USD',
  address jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, organization_id, name)
);

create table users (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  email citext not null,
  password_hash varchar(255) not null,
  first_name varchar(100) not null,
  last_name varchar(100) not null,
  phone_number varchar(32),
  status user_status not null default 'invited',
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, email)
);

create table roles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references tenants(id),
  code varchar(80) not null,
  name varchar(120) not null,
  description text,
  system_role boolean not null default false,
  unique (tenant_id, code)
);

create table permissions (
  id uuid primary key default gen_random_uuid(),
  code varchar(120) not null unique,
  description text
);

create table user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  role_id uuid not null references roles(id) on delete cascade,
  restaurant_id uuid references restaurants(id) on delete cascade,
  unique (user_id, role_id, restaurant_id)
);

create unique index idx_user_roles_tenant_wide
  on user_roles (user_id, role_id)
  where restaurant_id is null;

create table role_permissions (
  role_id uuid not null references roles(id) on delete cascade,
  permission_id uuid not null references permissions(id) on delete cascade,
  primary key (role_id, permission_id)
);

create table suppliers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid references restaurants(id),
  name varchar(180) not null,
  contact_name varchar(160),
  email citext,
  phone varchar(40),
  lead_time_days integer not null default 1 check (lead_time_days >= 0),
  minimum_order_amount numeric(12,2) not null default 0,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, restaurant_id, name)
);

create table categories (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid references restaurants(id),
  name varchar(120) not null,
  parent_id uuid references categories(id),
  unique (tenant_id, restaurant_id, name)
);

create table products (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  category_id uuid references categories(id),
  supplier_id uuid references suppliers(id),
  sku varchar(100),
  name varchar(180) not null,
  unit varchar(30) not null,
  purchase_unit varchar(30),
  unit_conversion_factor numeric(14,6) not null default 1,
  average_unit_cost numeric(12,4) not null default 0,
  shelf_life_days integer check (shelf_life_days is null or shelf_life_days >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, sku)
);

create table inventory_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid not null references restaurants(id),
  product_id uuid not null references products(id),
  batch_number varchar(100),
  quantity_on_hand numeric(14,4) not null default 0,
  reorder_point numeric(14,4) not null default 0,
  target_stock_level numeric(14,4) not null default 0,
  expires_at date,
  received_at date,
  location varchar(120),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, restaurant_id, product_id, batch_number, expires_at)
);

create table stock_movements (
  id uuid not null default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid not null references restaurants(id),
  inventory_item_id uuid not null references inventory_items(id),
  product_id uuid not null references products(id),
  movement_type movement_type not null,
  quantity numeric(14,4) not null check (quantity <> 0),
  unit_cost numeric(12,4),
  reason text,
  source_type varchar(80),
  source_id uuid,
  occurred_at timestamptz not null default now(),
  created_by_id uuid references users(id),
  created_at timestamptz not null default now(),
  primary key (id, occurred_at)
) partition by range (occurred_at);

create table purchase_orders (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid not null references restaurants(id),
  supplier_id uuid not null references suppliers(id),
  order_number varchar(80) not null,
  status po_status not null default 'draft',
  expected_delivery_date date,
  approved_by_id uuid references users(id),
  approved_at timestamptz,
  subtotal numeric(12,2) not null default 0,
  tax_total numeric(12,2) not null default 0,
  total numeric(12,2) not null default 0,
  created_by_id uuid references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, order_number)
);

create table purchase_order_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  purchase_order_id uuid not null references purchase_orders(id) on delete cascade,
  product_id uuid not null references products(id),
  quantity numeric(14,4) not null check (quantity > 0),
  unit varchar(30) not null,
  unit_cost numeric(12,4) not null check (unit_cost >= 0),
  line_total numeric(12,2) not null check (line_total >= 0)
);

create table forecasts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid not null references restaurants(id),
  product_id uuid not null references products(id),
  forecast_date date not null,
  horizon_days integer not null check (horizon_days in (1, 7, 14, 30)),
  predicted_quantity numeric(14,4) not null,
  confidence_low numeric(14,4),
  confidence_high numeric(14,4),
  model_name varchar(120) not null,
  model_version varchar(80) not null,
  features jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (tenant_id, restaurant_id, product_id, forecast_date, horizon_days, model_version)
);

create table notifications (
  id uuid not null default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  restaurant_id uuid references restaurants(id),
  user_id uuid references users(id),
  channel notification_channel not null,
  title varchar(180) not null,
  body text not null,
  metadata jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  primary key (id, created_at)
) partition by range (created_at);

create table subscriptions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  provider varchar(60) not null,
  provider_customer_id varchar(160),
  provider_subscription_id varchar(160),
  plan_code varchar(80) not null,
  status subscription_status not null,
  current_period_start timestamptz,
  current_period_end timestamptz,
  restaurant_limit integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, provider)
);

create table audit_logs (
  id uuid not null default gen_random_uuid(),
  tenant_id uuid not null references tenants(id),
  actor_user_id uuid references users(id),
  action varchar(120) not null,
  entity_type varchar(120) not null,
  entity_id uuid,
  ip_address inet,
  user_agent text,
  changes jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (id, created_at)
) partition by range (created_at);

create index idx_organizations_tenant on organizations (tenant_id);
create index idx_restaurants_tenant_org on restaurants (tenant_id, organization_id);
create index idx_users_tenant_status on users (tenant_id, status);
create index idx_suppliers_tenant_restaurant on suppliers (tenant_id, restaurant_id);
create index idx_products_tenant_category on products (tenant_id, category_id);
create index idx_inventory_lookup on inventory_items (tenant_id, restaurant_id, product_id);
create index idx_inventory_expiration on inventory_items (tenant_id, restaurant_id, expires_at) where expires_at is not null;
create index idx_inventory_low_stock on inventory_items (tenant_id, restaurant_id, product_id) where quantity_on_hand <= reorder_point;
create index idx_stock_movements_time on stock_movements (tenant_id, restaurant_id, occurred_at desc);
create index idx_purchase_orders_status on purchase_orders (tenant_id, restaurant_id, status, created_at desc);
create index idx_forecasts_lookup on forecasts (tenant_id, restaurant_id, product_id, forecast_date);
create index idx_notifications_unread on notifications (tenant_id, user_id, created_at desc) where read_at is null;
create index idx_audit_entity on audit_logs (tenant_id, entity_type, entity_id, created_at desc);

create table stock_movements_2026_06 partition of stock_movements
  for values from ('2026-06-01') to ('2026-07-01');

create table notifications_2026_06 partition of notifications
  for values from ('2026-06-01') to ('2026-07-01');

create table audit_logs_2026_06 partition of audit_logs
  for values from ('2026-06-01') to ('2026-07-01');
