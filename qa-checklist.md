# QA Checklist & Test Plan — Mana Raithanna Foundation Website
**File under test:** `index.html`  
**Date prepared:** 2026-05-12  
**Tester:** _______________  
**Pass threshold:** All CRITICAL items must pass. MAJOR items must be >= 90% pass rate.

---

## Legend
- [ ] Unchecked
- [P] PASS
- [F] FAIL — note finding beside item
- **[CRITICAL]** — blocks release
- **[MAJOR]** — should fix before release
- **[MINOR]** — nice to fix, low risk

---

## 1. HTML Structure Validation

### 1.1 Semantic Document Structure
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| H-01 | `<!DOCTYPE html>` declaration present on line 1 | CRITICAL | [ ] | |
| H-02 | `<html lang="en">` (or `lang="te"` for Telugu) attribute set | MAJOR | [ ] | |
| H-03 | `<head>` contains `<meta charset="UTF-8">` | CRITICAL | [ ] | |
| H-04 | `<meta name="viewport" content="width=device-width, initial-scale=1.0">` present | CRITICAL | [ ] | |
| H-05 | `<title>` tag is non-empty and references the foundation name | MAJOR | [ ] | |
| H-06 | `<meta name="description">` present with relevant content | MINOR | [ ] | |
| H-07 | `<header>` element wraps the site header/navbar area | MAJOR | [ ] | |
| H-08 | `<nav>` element wraps navigation links | MAJOR | [ ] | |
| H-09 | `<main>` element wraps the primary page content | MAJOR | [ ] | |
| H-10 | `<footer>` element wraps the site footer | MAJOR | [ ] | |
| H-11 | At least one `<section>` used per major content block (hero, about, programs, committee, contact) | MAJOR | [ ] | |
| H-12 | Heading hierarchy is logical: one `<h1>`, `<h2>` for sections, `<h3>` for sub-items — no skipped levels | MAJOR | [ ] | |
| H-13 | `<article>` or `<section>` used for committee member cards (not bare `<div>`) | MINOR | [ ] | |

### 1.2 Images
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| H-14 | Every `<img>` tag has an `alt` attribute (even if empty string for decorative) | CRITICAL | [ ] | |
| H-15 | Alt text is descriptive for content images (not just "image" or filename) | MAJOR | [ ] | |
| H-16 | Hero/banner images have meaningful alt text | MAJOR | [ ] | |
| H-17 | All Unsplash `<img>` `src` values begin with `https://images.unsplash.com` | MAJOR | [ ] | |
| H-18 | No `<img>` references a local file path (no `./`, `../`, or bare filename) | CRITICAL | [ ] | |
| H-19 | `width` and `height` attributes set on `<img>` tags to prevent layout shift | MINOR | [ ] | |

### 1.3 Links
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| H-20 | Every `<a>` tag has an `href` attribute | CRITICAL | [ ] | |
| H-21 | No `href="#"` used as a placeholder on visible nav links without a `data-` fallback | MAJOR | [ ] | |
| H-22 | Internal anchor links (`href="#section-id"`) match actual element `id` attributes | CRITICAL | [ ] | |
| H-23 | External links open in `_blank` and include `rel="noopener noreferrer"` | MAJOR | [ ] | |
| H-24 | Email `mailto:` links are properly formed | MAJOR | [ ] | |
| H-25 | Phone `tel:` links are properly formed with country code (+91) | MINOR | [ ] | |

### 1.4 Forms & Inputs
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| H-26 | Every `<input>` has an associated `<label>` (via `for`/`id` pair or wrapping label) | CRITICAL | [ ] | |
| H-27 | Every `<textarea>` has a `<label>` | CRITICAL | [ ] | |
| H-28 | Every `<select>` has a `<label>` | MAJOR | [ ] | |
| H-29 | Contact form has `name`, `email`, and `message` fields | MAJOR | [ ] | |
| H-30 | Submit button has descriptive text (not just "Submit") | MINOR | [ ] | |
| H-31 | Form `<input type="email">` used for email fields (enables native validation) | MAJOR | [ ] | |
| H-32 | `required` attribute set on mandatory fields | MAJOR | [ ] | |

### 1.5 Tag Closure
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| H-33 | No unclosed `<div>`, `<section>`, `<nav>`, `<ul>`, or `<li>` tags (validate with W3C validator) | CRITICAL | [ ] | |
| H-34 | Self-closing tags (`<img>`, `<input>`, `<br>`, `<hr>`, `<meta>`, `<link>`) do not have mismatched closers | MAJOR | [ ] | |
| H-35 | HTML validates at https://validator.w3.org with 0 errors | CRITICAL | [ ] | |

---

## 2. Accessibility

### 2.1 Color Contrast
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| A-01 | Saffron (#FF9933) text on white (#FFFFFF) background: check WCAG AA (4.5:1 for normal text, 3:1 for large) — expected ratio ~2.4:1 for normal text; use large/bold only | CRITICAL | [ ] | Saffron on white fails AA for small text; verify only used for large/bold headings |
| A-02 | Green (#138808) text on cream/white background: ratio ~4.5:1 — verify passes WCAG AA | CRITICAL | [ ] | |
| A-03 | Dark text on saffron button background: check contrast | MAJOR | [ ] | |
| A-04 | White text on dark/green background: check contrast | MAJOR | [ ] | |
| A-05 | Footer text color on footer background passes 4.5:1 | MAJOR | [ ] | |
| A-06 | Use https://webaim.org/resources/contrastchecker/ for each color pair | MAJOR | [ ] | |

### 2.2 ARIA & Semantics
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| A-07 | `<nav>` has `aria-label="Main navigation"` or similar | MAJOR | [ ] | |
| A-08 | Hamburger menu button has `aria-label="Toggle navigation"` | CRITICAL | [ ] | |
| A-09 | Hamburger button has `aria-expanded` toggled via JS (true/false) | MAJOR | [ ] | |
| A-10 | Mobile nav menu has `aria-hidden` toggled when collapsed/expanded | MAJOR | [ ] | |
| A-11 | Carousel/slider (if present) has `aria-live` region or pause control | MAJOR | [ ] | |
| A-12 | Social media icon links have `aria-label` describing destination | MAJOR | [ ] | |
| A-13 | Form has `role="form"` or is a `<form>` element (not `<div>`) | MAJOR | [ ] | |
| A-14 | Loading/animated elements have `aria-hidden="true"` if decorative | MINOR | [ ] | |
| A-15 | Counter section heading announces intent (e.g., "Our Impact") | MINOR | [ ] | |

### 2.3 Keyboard Navigation
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| A-16 | Skip-to-content link present as first focusable element: `<a href="#main-content" class="skip-link">Skip to main content</a>` | CRITICAL | [ ] | |
| A-17 | Skip link becomes visible on focus (not permanently hidden) | MAJOR | [ ] | |
| A-18 | All interactive elements reachable via Tab key in logical order | CRITICAL | [ ] | |
| A-19 | No keyboard traps — Esc or Tab always exits modal/menu | CRITICAL | [ ] | |
| A-20 | Focus order follows visual reading order (top-to-bottom, left-to-right) | MAJOR | [ ] | |

### 2.4 Focus Styles
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| A-21 | Focus ring is visible on all focusable elements (not `outline: none` globally) | CRITICAL | [ ] | |
| A-22 | Focus style has sufficient contrast against surrounding background | MAJOR | [ ] | |
| A-23 | Custom focus style used (if default removed) that is at least as visible as browser default | MAJOR | [ ] | |
| A-24 | Buttons and links show distinct focus state on keyboard navigation | MAJOR | [ ] | |

---

## 3. Responsive Design Checkpoints

### 3.1 Mobile — 375px (iPhone SE / most budget Android)
Open DevTools > Toggle device toolbar > set width to 375px.

| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| R-01 | Navbar collapses to hamburger icon at 375px — desktop links hidden | CRITICAL | [ ] | |
| R-02 | Hamburger icon is visible and tappable (min 44x44px touch target) | CRITICAL | [ ] | |
| R-03 | Hero section text is readable (no overflow, font >= 18px) | MAJOR | [ ] | |
| R-04 | Hero image does not obscure text | MAJOR | [ ] | |
| R-05 | Cards (programs, committee) stack vertically (1-column layout) | MAJOR | [ ] | |
| R-06 | No horizontal scroll bar visible | CRITICAL | [ ] | |
| R-07 | Contact form fields are full-width and usable | MAJOR | [ ] | |
| R-08 | Footer columns stack vertically | MAJOR | [ ] | |
| R-09 | All text is >= 14px (body), headings proportionally larger | MAJOR | [ ] | |
| R-10 | Impact counter numbers are legible | MINOR | [ ] | |

### 3.2 Tablet — 768px (iPad portrait / Android tablet)
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| R-11 | Layout transitions to 2-column grid for cards at 768px | MAJOR | [ ] | |
| R-12 | Navbar may show links directly (not hamburger) — verify breakpoint decision | MAJOR | [ ] | |
| R-13 | Fonts are readable — body text ~16px, headings proportional | MAJOR | [ ] | |
| R-14 | Hero section uses available width effectively | MINOR | [ ] | |
| R-15 | Committee member cards align in 2-column grid without orphan alignment issues | MINOR | [ ] | |
| R-16 | Images scale without distortion (object-fit: cover used) | MAJOR | [ ] | |

### 3.3 Desktop — 1280px
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| R-17 | Full navbar links visible horizontally | CRITICAL | [ ] | |
| R-18 | Multi-column grid layout for programs and committee cards | MAJOR | [ ] | |
| R-19 | Content is centered with appropriate max-width (e.g., 1200px container) | MAJOR | [ ] | |
| R-20 | Hero spans full viewport width with appropriate padding | MAJOR | [ ] | |
| R-21 | No elements exceeding viewport width | MAJOR | [ ] | |
| R-22 | Hover states on buttons/links are visible | MAJOR | [ ] | |
| R-23 | Whitespace between sections is balanced (~80-120px padding) | MINOR | [ ] | |

---

## 4. JavaScript Features

### 4.1 Navbar Scroll Behavior
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| J-01 | Navbar has transparent/initial state at top of page | MINOR | [ ] | |
| J-02 | Navbar changes style (e.g., adds background, shadow) after scrolling ~50-100px | MAJOR | [ ] | |
| J-03 | Active nav link updates as user scrolls to corresponding section (scrollspy) | MINOR | [ ] | |
| J-04 | Navbar remains fixed/sticky at top during scroll | MAJOR | [ ] | |

### 4.2 Hamburger Menu
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| J-05 | Clicking hamburger icon opens mobile nav menu | CRITICAL | [ ] | |
| J-06 | Clicking hamburger again (or X) closes the menu | CRITICAL | [ ] | |
| J-07 | Clicking a nav link closes the menu and scrolls to section | MAJOR | [ ] | |
| J-08 | Menu closes when clicking outside of it (optional but good UX) | MINOR | [ ] | |
| J-09 | `aria-expanded` on button toggles between `"true"` and `"false"` | MAJOR | [ ] | |

### 4.3 Counter Animation
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| J-10 | Counters start at 0 on page load (not at final value) | MAJOR | [ ] | |
| J-11 | Counter animation triggers when impact section enters viewport (IntersectionObserver or scroll event) | MAJOR | [ ] | |
| J-12 | Animation counts up smoothly to target value | MAJOR | [ ] | |
| J-13 | Counter does not re-animate on every scroll pass (runs once) | MINOR | [ ] | |
| J-14 | Counter animation respects `prefers-reduced-motion` media query | MINOR | [ ] | |

### 4.4 AOS (Animate On Scroll) Library
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| J-15 | AOS library CDN link present in `<head>` or before `</body>` | MAJOR | [ ] | |
| J-16 | `AOS.init()` called in script | MAJOR | [ ] | |
| J-17 | Elements with `data-aos` attributes animate when scrolled into view | MAJOR | [ ] | |
| J-18 | AOS does not cause flash of invisible content on initial load | MAJOR | [ ] | |
| J-19 | AOS animations work correctly at 375px mobile width | MINOR | [ ] | |

### 4.5 Smooth Scroll
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| J-20 | Clicking nav links scrolls smoothly to target section (no jump) | MAJOR | [ ] | |
| J-21 | `scroll-behavior: smooth` in CSS or `scrollIntoView({behavior: 'smooth'})` in JS used | MAJOR | [ ] | |
| J-22 | Scroll offset accounts for fixed navbar height (section not hidden behind nav) | CRITICAL | [ ] | |
| J-23 | Back-to-top button (if present) smoothly scrolls to top | MINOR | [ ] | |

---

## 5. Content Completeness

### 5.1 Committee Members (7 Required)
Verify all 7 members appear in the HTML by name:

| ID | Member Name | Section | Result | Notes |
|----|-------------|---------|--------|-------|
| C-01 | Member 1 name visible in committee section | CRITICAL | [ ] | Add actual name |
| C-02 | Member 2 name visible in committee section | CRITICAL | [ ] | |
| C-03 | Member 3 name visible in committee section | CRITICAL | [ ] | |
| C-04 | Member 4 name visible in committee section | CRITICAL | [ ] | |
| C-05 | Member 5 name visible in committee section | CRITICAL | [ ] | |
| C-06 | Member 6 name visible in committee section | CRITICAL | [ ] | |
| C-07 | Member 7 name visible in committee section | CRITICAL | [ ] | |
| C-08 | Each member card shows name, role/designation, and photo | MAJOR | [ ] | |

### 5.2 Programs Section (3 Categories Required)
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| C-09 | Category 1 (e.g., Agriculture / Farming Support) present with title and items | CRITICAL | [ ] | |
| C-10 | Category 2 (e.g., Education / Scholarships) present with title and items | CRITICAL | [ ] | |
| C-11 | Category 3 (e.g., Community Development / Welfare) present with title and items | CRITICAL | [ ] | |
| C-12 | Each category has at least 2-3 program items listed | MAJOR | [ ] | |

### 5.3 Contact Details
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| C-13 | Full address present: "D.No. 1-93, Edlurupadu Village" | CRITICAL | [ ] | |
| C-14 | State and PIN: "Andhra Pradesh" and "523105" | CRITICAL | [ ] | |
| C-15 | Phone number visible and linked with `tel:` | MAJOR | [ ] | |
| C-16 | Email address visible and linked with `mailto:` | MAJOR | [ ] | |
| C-17 | Google Maps embed or link to location (optional but valuable) | MINOR | [ ] | |

### 5.4 Impact Statistics
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| C-18 | At least 3 impact stat counters visible (e.g., Farmers Helped, Villages, Years) | MAJOR | [ ] | |
| C-19 | Each stat has a label and a numeric value | MAJOR | [ ] | |
| C-20 | Stats section has a heading (e.g., "Our Impact" / "మా ప్రభావం") | MINOR | [ ] | |

### 5.5 Footer Content
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| C-21 | Copyright text present, e.g., "© 2024 Mana Raithanna Foundation" | MAJOR | [ ] | |
| C-22 | NGO registration number / trust deed reference text present | MAJOR | [ ] | |
| C-23 | Footer includes at minimum: address, contact, quick links | MAJOR | [ ] | |
| C-24 | Foundation logo or name appears in footer | MINOR | [ ] | |
| C-25 | Social media links in footer (if applicable) | MINOR | [ ] | |

### 5.6 General Content
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| C-26 | Hero section has a clear headline and sub-headline | MAJOR | [ ] | |
| C-27 | About section describes the foundation's mission | MAJOR | [ ] | |
| C-28 | No placeholder text ("Lorem ipsum") anywhere on page | CRITICAL | [ ] | |
| C-29 | Foundation name "Mana Raithanna Foundation" appears correctly spelled throughout | CRITICAL | [ ] | |

---

## 6. Performance

### 6.1 Assets & CDN
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| P-01 | All images sourced from Unsplash CDN (`images.unsplash.com`) — no local image files | CRITICAL | [ ] | |
| P-02 | AOS library loaded from CDN (not bundled locally) | MAJOR | [ ] | |
| P-03 | Font Awesome / icon library loaded from CDN | MAJOR | [ ] | |
| P-04 | Google Fonts loaded via `<link>` from `fonts.googleapis.com` | MINOR | [ ] | |
| P-05 | No JavaScript files stored locally (or documented if intentional) | MINOR | [ ] | |
| P-06 | No CSS files stored locally (or documented if intentional) | MINOR | [ ] | |

### 6.2 Console & Errors
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| P-07 | Browser DevTools console shows 0 errors on page load | CRITICAL | [ ] | |
| P-08 | No 404 errors in Network tab for any resource | CRITICAL | [ ] | |
| P-09 | No mixed content warnings (HTTP resources on HTTPS page) | MAJOR | [ ] | |
| P-10 | No "Failed to load resource" messages in console | CRITICAL | [ ] | |

### 6.3 Loading Performance (Subjective)
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| P-11 | Page appears visually complete within 3 seconds on broadband | MAJOR | [ ] | |
| P-12 | No visible layout shift (CLS) after images load | MINOR | [ ] | |
| P-13 | Fonts do not cause large text flash (FOUT) | MINOR | [ ] | |
| P-14 | Unsplash images use appropriately sized variants (not 4K for thumbnails) | MINOR | [ ] | Check `?w=400` or similar params |

---

## 7. Cross-Browser Compatibility

### 7.1 CSS Custom Properties
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| B-01 | CSS custom properties (`--variable-name`) defined in `:root {}` | MAJOR | [ ] | |
| B-02 | Fallback values provided where critical: `color: saffron; color: var(--saffron)` | MINOR | [ ] | IE11 not a target, but good practice |
| B-03 | Saffron (#FF9933), Green (#138808), and White (#FFFFFF) defined as CSS variables | MINOR | [ ] | |

### 7.2 Flexbox & Grid
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| B-04 | Flexbox used correctly (no deprecated `flex-flow: row wrap` issues) | MAJOR | [ ] | |
| B-05 | CSS Grid used with `grid-template-columns` and appropriate `gap` | MAJOR | [ ] | |
| B-06 | Grid degrades gracefully if not supported (fallback to flex/block) | MINOR | [ ] | |
| B-07 | `gap` property used (not `grid-gap` which is deprecated) | MINOR | [ ] | |

### 7.3 Font Loading
| ID | Check | Severity | Result | Notes |
|----|-------|----------|--------|-------|
| B-08 | Google Fonts `<link>` includes `display=swap` parameter | MAJOR | [ ] | |
| B-09 | Font stacks include system fallbacks: `font-family: 'Roboto', Arial, sans-serif` | MAJOR | [ ] | |
| B-10 | Telugu/Devanagari characters (if any) render correctly with fallback font | MINOR | [ ] | |

### 7.4 Browser Test Matrix
Test in each browser and note pass/fail:

| Browser | Version | Layout OK | JS Works | Fonts Load | Result |
|---------|---------|-----------|----------|------------|--------|
| Chrome | Latest | [ ] | [ ] | [ ] | |
| Firefox | Latest | [ ] | [ ] | [ ] | |
| Safari | Latest | [ ] | [ ] | [ ] | |
| Edge | Latest | [ ] | [ ] | [ ] | |
| Chrome Mobile | Android | [ ] | [ ] | [ ] | |
| Safari Mobile | iOS | [ ] | [ ] | [ ] | |

---

## 8. Final Sign-Off

| Category | Total Checks | Passed | Failed | Pass % |
|----------|-------------|--------|--------|--------|
| HTML Structure | 35 | | | |
| Accessibility | 24 | | | |
| Responsive Design | 23 | | | |
| JavaScript Features | 23 | | | |
| Content Completeness | 29 | | | |
| Performance | 14 | | | |
| Cross-Browser | 14 | | | |
| **TOTAL** | **162** | | | |

**CRITICAL items failed:** ___  
**Release decision:** [ ] GO &nbsp;&nbsp; [ ] NO-GO &nbsp;&nbsp; [ ] GO with conditions: _______________

**Tester sign-off:** _______________ &nbsp;&nbsp; **Date:** _______________

---

## Appendix A — Useful Validation Tools

| Tool | URL | Purpose |
|------|-----|---------|
| W3C HTML Validator | https://validator.w3.org | HTML syntax validation |
| WAVE Accessibility | https://wave.webaim.org | Accessibility audit |
| Colour Contrast Checker | https://webaim.org/resources/contrastchecker/ | WCAG contrast ratio |
| Google Lighthouse | DevTools > Lighthouse tab | Performance, A11y, SEO, Best Practices |
| axe DevTools | Browser extension | Detailed accessibility errors |
| BrowserStack | https://browserstack.com | Cross-browser live testing |
| Responsive Tester | https://responsivedesignchecker.com | Multi-device preview |

## Appendix B — Key String Reference for Validate Script

The `validate.sh` script checks for these exact strings in `index.html`:

- `Mana Raithanna Foundation` — foundation name
- `Edlurupadu` — village name in address
- `523105` — PIN code
- `<!DOCTYPE html>` — doctype declaration
- `<header` — header element
- `<nav` — nav element
- `<main` — main element
- `<footer` — footer element
- `alt=` — image alt attributes
- `aria-label` — ARIA labels
- `skip` — skip-to-content link (class or id containing "skip")
- `AOS.init` — AOS initialization call
- `hamburger` OR `menu-toggle` OR `nav-toggle` — hamburger button identifier
- `unsplash.com` — Unsplash CDN usage
