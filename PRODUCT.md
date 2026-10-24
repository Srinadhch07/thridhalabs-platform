# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary users (four audiences):**
1. **Potential clients** - Businesses looking for custom software, websites, AI solutions, and digital product development.
2. **Prospective Lab Members** - Freshers, developers, designers, researchers, and aspiring product professionals who want to join the lab, explore opportunities, and contribute to projects.
3. **Existing Lab Members** - Members who need a professional portal to manage their profiles, showcase their work, document projects, and apply for work-specific certification.
4. **General visitors** - People exploring Thridha Labs' identity, experiments, products, research, and technical work.

The primary public website goal is to communicate that Thridha Labs is an AI-first experimentation and product-building lab, not a conventional web development agency. Help potential clients understand capabilities while making it easy for prospective members to discover opportunities and join the lab. The member portal should prioritize productivity, intuitive navigation, work showcasing, and certification workflows.

## Product Purpose

Thridha Labs is an AI-first technology and experimentation lab that explores emerging technologies, experiments with AI, and turns ideas into practical software, intelligent applications, and digital products.

Its work has three interconnected areas:
- **AI & R&D:** Experiment with AI, agentic systems, emerging technologies, and new software concepts.
- **Product & Software Development:** Build useful digital products, intelligent applications, and platforms that solve real-world problems.
- **Client Solutions:** Design and develop websites, custom platforms, and AI-powered solutions for businesses.

The core idea is to experiment, build, and ship meaningful technology. Client projects provide real-world impact, while independent experiments and products push the lab to explore what's possible with AI and software.

## Positioning

Thridha Labs is an evolving technology lab, not merely a web development agency. It emphasizes curiosity, technical depth, experimentation, and building practical solutions - combining client work with independent R&D to push boundaries with AI and software.

## Operating Context

- **Public website** (in progress) - communicates lab identity, showcases work/projects/activities, clients, testimonials, careers
- **Admin panel** (in progress) - manages content (clients, projects, testimonials), settings/branding, media, certifications, members, activities
- **Member portal** (in progress) - member profiles, work showcasing, certifications, contributions, activities
- **Content management** - Full CRUD APIs for content entities (clients, projects, testimonials) with publishing rules, media management via storage abstraction
- **Authentication** - Role-based admin auth (owner/admin/editor), member auth separate; cookie-based JWT + CSRF protection
- **Media pipeline** - Image uploads processed to WebP variants, stored via local/S3 providers, content-addressed

## Capabilities and Constraints

**Capabilities:**
- FastAPI backend with MongoDB, async/await
- React 19 + TypeScript + Vite frontend
- Storage abstraction (local disk, S3-compatible)
- Image processing pipeline (WebP conversion, EXIF stripping, variants)
- Content APIs for settings, branding, clients, projects, testimonials
- Admin auth with RBAC, CSRF protection, rate limiting
- SEO/sitemap/robots, OG sharing routes
- Member portal with activities, certifications, works showcase

**Constraints:**
- Web + mobile responsive (no native mobile apps currently planned)
- Secrets never in frontend code
- Publishing rules enforced server-side
- Media uploads only JPEG/PNG/WebP, size/pixel limits
- Public APIs never expose internal Mongo IDs or admin-only fields
- Visual redesign must not change the backend, APIs, authentication, or existing functionality

## Brand Commitments

- **Identity:** Thridha Labs - technology lab and digital company
- **Voice/positioning:** AI-first experimentation lab, not conventional web dev agency
- **Emphasis:** Curiosity, technical depth, experimentation, practical solutions
- **Color:** `#363199` must remain available within the branding system; existing admin-controlled theme presets are preserved
- **Visual direction:** not yet fixed - the current Swiss editorial homepage treatment is under review and must not be treated as a durable commitment. New direction is being explored before implementation.

## Evidence on Hand

- **Codebase:** Full-stack implementation in progress (Phases 1-4 complete per README)
- **Documentation:** Architecture docs, frontend UI/UX audit, certificates, activities, member contributions, social sharing, work showcase docs
- **Frontend:** React app with public pages (Home, About, Projects, Clients, Testimonials, Activities, Careers, Contact), admin pages, member pages
- **Backend:** FastAPI with modules for auth, media, settings, branding, clients, projects, testimonials, members, activities, etc.
- **Design prototype:** Visual reference at separate location (not imported)
- **Assets:** Media upload system in place

## Product Principles

1. **Experiment to ship** - Balance R&D exploration with practical, usable solutions
2. **Lab identity first** - Present as AI-first experimentation lab, distinct from agency positioning
3. **Multi-audience coherence** - Serve clients, members, and visitors with clear paths without homepage clutter
4. **Technical rigor** - Security-first (auth, CSRF, validation), content safety, proper abstractions
5. **Member-centric growth** - Support members' work showcase, learning, and certification

## Accessibility & Inclusion

- prefers-reduced-motion support in styles
- Semantic HTML structure
- Image alt text handling needed for accessibility (to be ensured in implementation)
