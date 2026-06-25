#!/usr/bin/env bash
# =============================================================================
# validate.sh — Mana Raithanna Foundation Website Content & Structure Validator
# Usage: bash validate.sh [path/to/index.html]
# Default target: index.html in the same directory as this script
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$SCRIPT_DIR/index.html}"

PASS=0
FAIL=0
WARN=0

# ANSI colours (disabled if not a terminal)
if [ -t 1 ]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  RESET='\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; CYAN=''; BOLD=''; RESET=''
fi

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
pass() {
  echo -e "  ${GREEN}[PASS]${RESET} $1"
  PASS=$((PASS + 1))
}

fail() {
  echo -e "  ${RED}[FAIL]${RESET} $1"
  FAIL=$((FAIL + 1))
}

warn() {
  echo -e "  ${YELLOW}[WARN]${RESET} $1"
  WARN=$((WARN + 1))
}

section() {
  echo ""
  echo -e "${CYAN}${BOLD}== $1 ==${RESET}"
}

# Count occurrences of a string (case-sensitive)
count_of() {
  grep -c "$1" "$TARGET" 2>/dev/null || echo 0
}

# Count occurrences of a string (case-insensitive)
count_of_i() {
  grep -ci "$1" "$TARGET" 2>/dev/null || echo 0
}

# Check if a string exists at least once
contains() {
  grep -q "$1" "$TARGET" 2>/dev/null
}

# Check if a string exists at least once (case-insensitive)
contains_i() {
  grep -qi "$1" "$TARGET" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Pre-flight: file existence
# ---------------------------------------------------------------------------
section "PRE-FLIGHT"

if [ ! -f "$TARGET" ]; then
  echo -e "${RED}${BOLD}FATAL: File not found: $TARGET${RESET}"
  echo "Usage: bash validate.sh [path/to/index.html]"
  exit 1
fi

pass "File exists: $TARGET"
FILE_SIZE=$(wc -c < "$TARGET")
echo "       File size: ${FILE_SIZE} bytes"
LINE_COUNT=$(wc -l < "$TARGET")
echo "       Line count: ${LINE_COUNT} lines"

# ---------------------------------------------------------------------------
# 1. HTML STRUCTURE
# ---------------------------------------------------------------------------
section "1. HTML STRUCTURE"

# Doctype
if contains '<!DOCTYPE html>'; then
  pass "H-01: <!DOCTYPE html> declaration present"
else
  fail "H-01: Missing <!DOCTYPE html> declaration"
fi

# Charset
if contains 'charset="UTF-8"' || contains "charset='UTF-8'" || contains_i 'charset=utf-8'; then
  pass "H-03: charset=UTF-8 meta tag present"
else
  fail "H-03: Missing charset=UTF-8 meta tag"
fi

# Viewport
if contains 'name="viewport"' || contains "name='viewport'"; then
  pass "H-04: viewport meta tag present"
else
  fail "H-04: Missing viewport meta tag"
fi

# Title
TITLE_COUNT=$(count_of '<title>')
if [ "$TITLE_COUNT" -gt 0 ]; then
  if contains_i 'Mana Raithanna' ; then
    pass "H-05: <title> present and contains foundation name"
  else
    warn "H-05: <title> present but may not contain 'Mana Raithanna'"
  fi
else
  fail "H-05: Missing <title> tag"
fi

# Semantic elements
for tag in header nav main footer section; do
  if contains "<${tag}"; then
    pass "H-0x: <${tag}> element present"
  else
    fail "H-0x: Missing <${tag}> element"
  fi
done

# lang attribute
if contains 'lang='; then
  pass "H-02: lang attribute present on <html>"
else
  warn "H-02: No lang attribute detected — add lang=\"en\" to <html>"
fi

# ---------------------------------------------------------------------------
# 2. IMAGES
# ---------------------------------------------------------------------------
section "2. IMAGES"

IMG_TOTAL=$(count_of '<img')
IMG_WITH_ALT=$(count_of 'alt=')
echo "       Total <img> tags found: ${IMG_TOTAL}"
echo "       Tags with alt= attribute: ${IMG_WITH_ALT}"

if [ "$IMG_TOTAL" -eq 0 ]; then
  warn "H-14: No <img> tags found — is the page complete?"
elif [ "$IMG_WITH_ALT" -ge "$IMG_TOTAL" ]; then
  pass "H-14: All <img> tags appear to have alt= attributes (${IMG_WITH_ALT}/${IMG_TOTAL})"
else
  fail "H-14: Some <img> tags are missing alt= (${IMG_WITH_ALT}/${IMG_TOTAL} have alt)"
fi

# Check all images use Unsplash CDN (no local paths)
LOCAL_IMGS=$(grep -c 'src="\.\.' "$TARGET" 2>/dev/null || true)
LOCAL_IMGS2=$(grep -c "src='\.\." "$TARGET" 2>/dev/null || true)
if [ "$LOCAL_IMGS" -gt 0 ] || [ "$LOCAL_IMGS2" -gt 0 ]; then
  fail "H-18: Local image paths detected (../) — all images should use Unsplash CDN"
else
  pass "H-18: No relative local image paths found"
fi

UNSPLASH_COUNT=$(count_of 'unsplash.com')
if [ "$UNSPLASH_COUNT" -gt 0 ]; then
  pass "P-01: Unsplash CDN images found (${UNSPLASH_COUNT} occurrences)"
else
  warn "P-01: No Unsplash CDN image URLs detected — verify image sources"
fi

# ---------------------------------------------------------------------------
# 3. LINKS
# ---------------------------------------------------------------------------
section "3. LINKS"

A_TOTAL=$(count_of '<a ')
A_WITH_HREF=$(count_of 'href=')
echo "       Total <a> tags: ${A_TOTAL}"
echo "       href= attributes: ${A_WITH_HREF}"

if [ "$A_TOTAL" -eq 0 ]; then
  warn "H-20: No <a> tags found"
elif [ "$A_WITH_HREF" -ge "$A_TOTAL" ]; then
  pass "H-20: All <a> tags appear to have href= (${A_WITH_HREF}/${A_TOTAL})"
else
  fail "H-20: Some <a> tags missing href= (${A_WITH_HREF}/${A_TOTAL} have href)"
fi

# mailto link
if contains 'mailto:'; then
  pass "H-24: mailto: link present"
else
  warn "H-24: No mailto: link found — add email contact link"
fi

# tel link
if contains 'tel:'; then
  pass "H-25: tel: link present"
else
  warn "H-25: No tel: link found — add phone contact link"
fi

# noopener on external links
if contains 'target="_blank"'; then
  if contains 'noopener'; then
    pass "H-23: External links with target=_blank include noopener"
  else
    fail "H-23: target=\"_blank\" found but no noopener rel — security risk"
  fi
fi

# ---------------------------------------------------------------------------
# 4. FORMS & INPUTS
# ---------------------------------------------------------------------------
section "4. FORMS & INPUTS"

FORM_COUNT=$(count_of '<form')
INPUT_COUNT=$(count_of '<input')
LABEL_COUNT=$(count_of '<label')
echo "       <form> elements: ${FORM_COUNT}"
echo "       <input> elements: ${INPUT_COUNT}"
echo "       <label> elements: ${LABEL_COUNT}"

if [ "$FORM_COUNT" -gt 0 ]; then
  pass "H-29: Contact form element present"
  if [ "$LABEL_COUNT" -ge "$INPUT_COUNT" ]; then
    pass "H-26: Label count (${LABEL_COUNT}) >= input count (${INPUT_COUNT})"
  else
    fail "H-26: Fewer labels (${LABEL_COUNT}) than inputs (${INPUT_COUNT}) — some inputs may be unlabelled"
  fi
  if contains 'type="email"' || contains "type='email'"; then
    pass "H-31: Email input type used"
  else
    warn "H-31: No type=\"email\" input found in form"
  fi
  if contains 'required'; then
    pass "H-32: required attribute used on at least one field"
  else
    warn "H-32: No required attribute found — form fields may lack validation"
  fi
else
  warn "H-29: No <form> element found — is the contact form present?"
fi

# ---------------------------------------------------------------------------
# 5. ACCESSIBILITY
# ---------------------------------------------------------------------------
section "5. ACCESSIBILITY"

# ARIA labels
ARIA_COUNT=$(count_of 'aria-label')
if [ "$ARIA_COUNT" -gt 0 ]; then
  pass "A-07/A-08: aria-label attributes present (${ARIA_COUNT} occurrences)"
else
  fail "A-07/A-08: No aria-label attributes found — ARIA labels required"
fi

# aria-expanded (hamburger)
if contains 'aria-expanded'; then
  pass "A-09: aria-expanded attribute present (hamburger menu)"
else
  warn "A-09: No aria-expanded attribute — hamburger button needs aria-expanded toggle"
fi

# Skip link
if contains_i 'skip' && (contains 'href="#' || contains "href='#"); then
  pass "A-16: Skip-to-content link pattern detected"
else
  warn "A-16: No skip-to-content link detected — add <a href=\"#main-content\" class=\"skip-link\">Skip to main content</a>"
fi

# Focus outline
if grep -q 'outline.*none' "$TARGET" 2>/dev/null; then
  warn "A-21: 'outline: none' detected — verify focus styles are replaced, not just removed"
else
  pass "A-21: No blanket 'outline: none' detected"
fi

# ---------------------------------------------------------------------------
# 6. CONTENT COMPLETENESS
# ---------------------------------------------------------------------------
section "6. CONTENT COMPLETENESS — Foundation Identity"

# Foundation name
FOUNDATION_NAME_COUNT=$(count_of_i 'Mana Raithanna')
if [ "$FOUNDATION_NAME_COUNT" -ge 2 ]; then
  pass "C-29: 'Mana Raithanna' appears ${FOUNDATION_NAME_COUNT} times (name used consistently)"
elif [ "$FOUNDATION_NAME_COUNT" -eq 1 ]; then
  warn "C-29: 'Mana Raithanna' appears only once — verify name used throughout"
else
  fail "C-29: 'Mana Raithanna' not found in HTML — foundation name missing"
fi

# Lorem ipsum check
if contains_i 'lorem ipsum'; then
  fail "C-28: Placeholder text 'Lorem ipsum' found — replace with real content"
else
  pass "C-28: No Lorem ipsum placeholder text found"
fi

section "6. CONTENT COMPLETENESS — Address"

# Address components
if contains 'D.No. 1-93' || contains 'D.No.1-93' || contains_i 'D No 1-93' || contains_i 'Edlurupadu'; then
  pass "C-13: Address / Edlurupadu Village reference found"
else
  fail "C-13: Address 'D.No. 1-93, Edlurupadu Village' NOT found — add contact address"
fi

if contains 'Edlurupadu'; then
  pass "C-13a: 'Edlurupadu' village name present"
else
  fail "C-13a: 'Edlurupadu' village name not found"
fi

if contains '523105'; then
  pass "C-14: PIN code 523105 present"
else
  fail "C-14: PIN code '523105' not found — add full address"
fi

if contains_i 'Andhra Pradesh' || contains 'A.P' || contains ', AP'; then
  pass "C-14b: State reference (Andhra Pradesh / AP) found"
else
  warn "C-14b: State 'Andhra Pradesh' not found in address"
fi

section "6. CONTENT COMPLETENESS — Committee (7 Members)"

COMMITTEE_SECTION=$(count_of_i 'committee')
if [ "$COMMITTEE_SECTION" -gt 0 ]; then
  pass "C-01/C-07: Committee section detected (${COMMITTEE_SECTION} occurrences of 'committee')"
else
  fail "C-01/C-07: No 'committee' section detected"
fi

# Count member card patterns — look for common card containers with role/designation
MEMBER_CARDS=$(count_of_i 'member\|committee-card\|team-card\|person-card' 2>/dev/null || grep -ci 'member\|committee-card' "$TARGET" 2>/dev/null || echo 0)
echo "       Rough committee card pattern matches: ${MEMBER_CARDS}"
if [ "$MEMBER_CARDS" -ge 7 ]; then
  pass "C-08: Likely 7+ committee member entries found"
elif [ "$MEMBER_CARDS" -ge 4 ]; then
  warn "C-08: Only ~${MEMBER_CARDS} committee card patterns found — expected 7"
else
  warn "C-08: Too few committee card patterns found — manually verify all 7 members present"
fi

section "6. CONTENT COMPLETENESS — Programs (3 Categories)"

PROGRAMS_SECTION=$(count_of_i 'program\|programme')
if [ "$PROGRAMS_SECTION" -gt 0 ]; then
  pass "C-09/C-11: Programs section detected (${PROGRAMS_SECTION} occurrences)"
else
  fail "C-09/C-11: No 'programs' or 'programme' section detected"
fi

section "6. CONTENT COMPLETENESS — Impact Stats"

COUNTER_COUNT=$(count_of_i 'counter\|stat\|impact')
if [ "$COUNTER_COUNT" -ge 3 ]; then
  pass "C-18: Impact/counter/stat section detected (${COUNTER_COUNT} occurrences)"
else
  warn "C-18: Few impact stat references found (${COUNTER_COUNT}) — verify counters present"
fi

section "6. CONTENT COMPLETENESS — Footer"

COPYRIGHT_COUNT=$(count_of_i 'copyright\|&copy;\|©')
if [ "$COPYRIGHT_COUNT" -gt 0 ]; then
  pass "C-21: Copyright notice found"
else
  fail "C-21: No copyright notice found in footer"
fi

REGISTRATION=$(count_of_i 'registr\|trust\|society\|ngo')
if [ "$REGISTRATION" -gt 0 ]; then
  pass "C-22: Registration/trust/NGO reference found (${REGISTRATION} occurrences)"
else
  warn "C-22: No registration number or trust reference found — add NGO registration details"
fi

# ---------------------------------------------------------------------------
# 7. JAVASCRIPT FEATURES
# ---------------------------------------------------------------------------
section "7. JAVASCRIPT FEATURES"

# AOS
if contains 'AOS.init' || contains 'aos.init'; then
  pass "J-15/J-16: AOS.init() call found"
else
  warn "J-15/J-16: AOS.init() not found — verify AOS library is initialised"
fi

AOS_CDN=$(count_of_i 'cdn.*aos\|aos.*cdn\|unpkg.*aos\|cdnjs.*aos\|aos.min.js\|animate.min.js')
if [ "$AOS_CDN" -gt 0 ] || contains_i 'aos@'; then
  pass "J-15: AOS CDN link detected"
else
  warn "J-15: AOS CDN link not clearly detected — verify library is loaded"
fi

# Hamburger menu
HAMBURGER=$(count_of_i 'hamburger\|menu-toggle\|nav-toggle\|navbar-toggle\|menu-btn')
if [ "$HAMBURGER" -gt 0 ]; then
  pass "J-05: Hamburger menu element detected (${HAMBURGER} occurrences)"
else
  warn "J-05: No hamburger/menu-toggle element clearly detected"
fi

# Smooth scroll
if contains 'scroll-behavior' || contains 'scrollBehavior' || contains 'scrollIntoView'; then
  pass "J-20: Smooth scroll implementation detected"
else
  warn "J-20: No smooth scroll implementation found — add scroll-behavior: smooth or scrollIntoView"
fi

# Intersection Observer (for counters / AOS)
if contains 'IntersectionObserver' || contains 'intersectionObserver'; then
  pass "J-11: IntersectionObserver used (good for counter animation)"
else
  warn "J-11: No IntersectionObserver found — counter animation may not be scroll-triggered"
fi

# ---------------------------------------------------------------------------
# 8. PERFORMANCE — CDN LIBRARIES
# ---------------------------------------------------------------------------
section "8. PERFORMANCE — CDN Libraries"

CDN_LINKS=$(count_of_i 'cdn\|unpkg\|cdnjs\|jsdelivr\|googleapis')
if [ "$CDN_LINKS" -gt 0 ]; then
  pass "P-02/P-03: CDN library links detected (${CDN_LINKS} occurrences)"
else
  warn "P-02/P-03: No CDN library links found — verify libraries load from CDN"
fi

# Google Fonts
if contains 'fonts.googleapis.com'; then
  pass "P-04/B-08: Google Fonts CDN link present"
  if contains 'display=swap'; then
    pass "B-08: font-display=swap used (prevents FOUT)"
  else
    warn "B-08: Google Fonts link lacks display=swap — add &display=swap to prevent text flash"
  fi
else
  warn "P-04: No Google Fonts CDN link found — verify font loading strategy"
fi

# ---------------------------------------------------------------------------
# 9. CSS CHECKS
# ---------------------------------------------------------------------------
section "9. CSS QUALITY"

# CSS variables
if contains '--' && contains ':root'; then
  pass "B-01: CSS custom properties (:root variables) detected"
else
  warn "B-01: No CSS :root custom properties detected"
fi

# Saffron / Indian flag colours
if contains_i '#FF9933\|saffron\|#ff9933'; then
  pass "B-03: Saffron colour (#FF9933) referenced in CSS"
else
  warn "B-03: Saffron (#FF9933) colour not found — verify brand colours defined"
fi

if contains_i '#138808\|#128807\|india.*green'; then
  pass "B-03: Indian Green colour (#138808) referenced"
else
  warn "B-03: Indian Green (#138808) not clearly found — verify brand colours"
fi

# Font family fallbacks
if contains_i "font-family.*,"; then
  pass "B-09: Font family stacks with fallbacks detected"
else
  warn "B-09: No font-family fallback stacks found — add system font fallbacks"
fi

# ---------------------------------------------------------------------------
# SUMMARY REPORT
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL + WARN))

echo ""
echo -e "${BOLD}================================================================${RESET}"
echo -e "${BOLD}  VALIDATION SUMMARY — Mana Raithanna Foundation${RESET}"
echo -e "${BOLD}================================================================${RESET}"
echo -e "  File:   $TARGET"
echo -e "  Lines:  $LINE_COUNT  |  Size: ${FILE_SIZE} bytes"
echo ""
echo -e "  ${GREEN}PASS${RESET}:    $PASS"
echo -e "  ${RED}FAIL${RESET}:    $FAIL"
echo -e "  ${YELLOW}WARN${RESET}:    $WARN"
echo -e "  Total:  $TOTAL checks run"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}Result: ALL CHECKS PASSED (warnings may still need review)${RESET}"
  EXIT_CODE=0
else
  echo -e "  ${RED}${BOLD}Result: $FAIL CRITICAL CHECK(S) FAILED — review output above${RESET}"
  EXIT_CODE=1
fi

echo -e "${BOLD}================================================================${RESET}"
echo ""
echo "NOTE: This script checks string patterns only. Also run:"
echo "  - W3C Validator:  https://validator.w3.org"
echo "  - WAVE A11y:      https://wave.webaim.org"
echo "  - Lighthouse:     Chrome DevTools > Lighthouse tab"
echo ""

exit $EXIT_CODE
