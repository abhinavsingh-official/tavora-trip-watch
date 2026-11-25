# Known Issues & What's Needed for Production

Plain-language version: what's not quite right today, and what would need to change before this
could be a real product people pay for - written so the "why" makes sense even if you don't know
the tech by name.

## Known issues

**The cache and rate-limiter only remember things for one running copy of the app.** We keep a
short-term memory ("cache") so we don't hammer Hotelbeds with repeat calls, and a counter that stops
us from calling it too often ("rate limiter"). Both live in the memory of whichever single copy of
the backend is currently running. That's fine today, because there's only one copy running. If we
ever ran several copies at once to handle more traffic, each copy would have its own separate memory
instead of sharing one - so two copies could accidentally go over the shared quota together without
either one noticing. Not a problem at this project's scale, but worth knowing about.

**The free hosting plan sleeps after 15 minutes of no traffic.** We're hosting on Render's free
tier. If nobody visits for 15 minutes, the backend shuts itself down to save resources, and the next
visitor waits 30-60 seconds for it to wake back up. This is a hosting limitation, not a code defect.

**Visual polish was deliberately left for last.** We prioritized correctness (right prices, no
duplicate bookings, proper failure handling) over making every screen look finished, since the
assignment itself says that's what should matter most.

A full review of the whole app also found and fixed 11 separate real bugs along the way - most
notably a cancelled trip that could somehow still be booked, and a test tool (the Simulation price
override) that didn't behave the same way twice. All 11 are fixed and have tests guarding against
them coming back.

### Fixed during review (previously listed here as known issues)

**"Provisional" status wasn't reachable.** Every real price check only ever came back fully
complete or fully failed - the half-finished `provisional` status existed in the schema but never
actually fired. Fixed by adding a genuine "supplier timeout" lever to the Simulation page's Price
check scenarios (distinct from a booking timeout): arm it on one component, and the next price
check comes back `provisional` for real - some prices known, one still missing. Covered by
`backend/tests/test_provisional_status.py`.

**Euro-to-Rupee conversion used one fixed number.** Hotelbeds gives hotel prices in Euros; we were
converting with one rate written into the code. Now `app/exchange_rate.py` fetches the real daily
rate from a free FX API (Frankfurter, backed by the European Central Bank), cached for an hour, with
the old fixed rate kept only as a fallback if that API is ever unreachable. Covered by
`backend/tests/test_exchange_rate.py`.

**One shared 2-minute hold instead of three separate ones.** Flights, hotels, and cabs now each get
their own hold duration (`app/monitoring.py`'s `COMPONENT_HOLD_MINUTES`: flight 2 min, hotel 3 min,
cab 5 min - flight fares move fastest in the real world, cab fares are closest to a flat rate) and
`book()` reports specifically which component's hold expired, instead of one shared timer and a
generic message. Covered by `backend/tests/test_component_holds.py`.

**Fast-forwarding time in Simulation affected the whole app.** Dragging the Simulation page's Clock
lever used to shift time for every user, including the real demo users A, B, and C. Users now carry
an `is_simulated` flag (true only for the Simulation page's own "Scenario" user), and the clock only
fast-forwards for that sandbox - real users always see real wall-clock time. Covered by
`backend/tests/test_sim_clock.py` and a dedicated test in `test_booking.py`.

## What would be needed for production

This project is a small, deliberately-scoped slice of what a real travel-booking product is. Below
is the rest of the iceberg - organized by concern, with the real-world technology a production team
would reach for in each spot, explained in plain terms.

### Real supplier relationships, not sandbox accounts

Flights and hotels right now come from real *test/sandbox* accounts (Sabre, Hotelbeds) - realistic,
but not actual bookable live prices or real inventory. Cabs are entirely made up (simulated), because
no cab company would give a one-week project real API access. A real product needs:

- Paid/production agreements with suppliers like Sabre and Hotelbeds (or alternatives: Amadeus,
  Travelport for flights; Booking.com's or Expedia's partner APIs for hotels).
- A real cab/transfer partner - Ola's or CabBazar's outstation-transfer APIs are the closest real fit
  found, but both require a business partnership to access, not just a signup.
- A real payment processor to actually charge someone (Razorpay or Stripe are the standard choices in
  India), plus PCI-DSS compliance handling around it - in practice, letting the processor's own hosted
  checkout handle card data so this app never touches it directly.

### Scaling the backend beyond one process

Right now, one single background process checks every trip's price every 5 minutes, one at a time
(**APScheduler** - a simple built-in scheduler living inside our one app process), and an in-memory
cache/rate-limiter that only one copy of the app knows about. That's fine for a handful of trips; it
doesn't survive real traffic. A production version would add:

- **Celery** (or a lighter alternative like **Dramatiq**) paired with **Redis** or **RabbitMQ** as the
  task queue, so price checks run across many worker machines instead of one process working through
  requests one at a time.
- That same **Redis** also becomes the shared cache and rate-limiter, so multiple running copies of
  the app coordinate instead of each guessing independently about Hotelbeds/Sabre's quota.
- A real database connection pooler (**PgBouncer**) in front of Postgres, since each new worker
  process opening its own raw connections doesn't scale past a few dozen.
- Running the API itself behind a load balancer across multiple container instances (e.g. on
  **AWS ECS/Fargate**, **Kubernetes**, or Render's own paid autoscaling tier), instead of one single
  instance.

### Real accounts, not a dropdown

Right now you just pick which demo person you are (User A, B, or C) from a dropdown - no password, no
session, no account recovery. A real product needs actual authentication: email/password or OAuth
login (Google/Apple sign-in), session tokens or JWTs, and a proper authorization layer so one user's
`user_id` in a URL can't be swapped for another's (this app only gets away with that because the
"users" are three fixed demo people, not the public).

### Real notifications, not just an in-app bell

Price-drop alerts only ever show up as a bell icon inside the app right now - if you're not looking at
the tab, you miss it, which defeats the point of a "watch this for me" product. A real version needs:

- **Email** (via SendGrid, Postmark, or AWS SES) for the actual price-drop alert.
- **Push notifications** (Firebase Cloud Messaging / APNs) if there's a mobile app, or web push if
  not.
- Possibly **SMS** (Twilio) for urgent "your hold is about to expire" nudges, since that's the one
  alert type where minutes genuinely matter.

### Observability - knowing what's actually happening in production

Today, "what happened" lives in the Simulation page's activity log and whatever's printed to stdout.
A real deployment needs to know this without a human needing to be watching:

- Structured logging (not print statements) shipped somewhere searchable - **Datadog**, **Better
  Stack**, or the ELK stack (Elasticsearch/Logstash/Kibana).
- Error tracking - **Sentry**, so a crash in production pages someone instead of silently failing.
- Metrics and dashboards - **Prometheus** + **Grafana**, to watch things like "how long is a price
  check taking" or "how many bookings failed today" over time, not just read about one at a time.
- Distributed tracing (**OpenTelemetry**) once there's more than one service, to see a single
  request's path across the API, the task queue, and the database.

### Security hardening beyond what a take-home needs

- A secrets manager (**AWS Secrets Manager**, **HashiCorp Vault**, or even Render's own secret env
  vars done properly) instead of a `.env` file, so API keys aren't sitting in a shell config.
- Rate limiting and basic bot protection at the edge (**Cloudflare**, or an API gateway like **Kong**),
  so the app itself isn't the first line of defense against abuse.
- Dependency and container vulnerability scanning in CI (**Dependabot**, **Trivy**), since this
  project's CI currently runs tests and a migration check, not a security scan.

### Everything else that "done" quietly assumes

- **A staging environment** - right now there's exactly one deployed copy (production), so every
  change goes live after CI passes. A real team tests against a separate, production-like environment
  first.
- **Database backups and point-in-time recovery**, not just Render's default snapshotting - knowing
  exactly how far back you could restore to after a bad migration.
- **A CDN** (**Cloudflare**, **AWS CloudFront**) in front of the frontend's static assets, rather than
  serving them straight from the one hosting instance.
- **Feature flags** (LaunchDarkly, or a simpler home-grown table) to ship a risky change to a few
  users before everyone, instead of every deploy being all-or-nothing.
- **Visual polish** - the one item we knowingly left for last, on purpose, since it's worth the least
  toward getting the core logic right, but a real product obviously needs a design pass this one
  didn't get.
