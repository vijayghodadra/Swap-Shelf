# SwapShelf Security Review and Remediation Report

## 1. Executive Summary

A security audit and defect analysis of the SwapShelf campus marketplace codebase identified a critical authorization flaw (privilege escalation) alongside defense-in-depth authorization gaps, a test-suite execution blockage, and a configuration defect preventing static stylesheet delivery.

All vulnerabilities and defects were verified, remediated, and validated with automated and live functional tests. All 14 automated tests pass successfully (`OK`), and static CSS assets load with HTTP 200 responses.

---

## 2. Primary Vulnerability Finding

- **Title:** Privilege Escalation via User Profile Update (`is_staff` mass assignment)
- **Severity:** High (CVSS ~8.0 - Remote Authenticated)
- **Affected Component:** `market/forms.py` -> `ProfileForm`, `market/views.py` -> `profile()`
- **Vulnerability Type:** Mass Assignment / Broken Object Level Authorization (CWE-915 / CWE-285)
- **Impact:** Any standard authenticated user could promote their account to administrative staff (`is_staff=True`), granting unauthorized access to the Department Desk (`/desk/`) and confidential department notes (`DESK-2290`).

### Root Cause
`ProfileForm` was bound directly to Django's built-in `User` model and explicitly included `is_staff` in its editable form fields (or did not restrict fields). When submitted by an ordinary user, `ProfileForm.save()` persisted `is_staff=True` to the database, elevating the user's role without administrative authorization.

---

## 3. Step-by-Step Reproduction

1. Sign in with standard credentials for user `jordan` (`campus123`) at `http://localhost:3000/login/`.
2. Navigate to `http://localhost:3000/desk/`.
   - *Expected Behavior:* Access is denied with the notice: *"This page is for department board accounts."*
3. Navigate to `http://localhost:3000/profile/`.
4. Submit a crafted HTTP POST request to `/profile/` including `is_staff=on`:
   ```http
   POST /profile/ HTTP/1.1
   Host: localhost:3000
   Content-Type: application/x-www-form-urlencoded
   Cookie: sessionid=...; csrftoken=...

   csrfmiddlewaretoken=<token>&first_name=Jordan&last_name=Park&email=jordan@example.edu&is_staff=on
   ```
5. In the unpatched application, `form.save()` wrote `is_staff = 1` for `jordan`.
6. Return to `http://localhost:3000/desk/`.
   - *Exploit Outcome:* The server granted access and exposed confidential department data:
     *"Department hold closet, Hullihen basement cage B. Reimbursement code DESK-2290. Not for the public board."*

---

## 4. Remediation & Defense-in-Depth

### 4.1 Strict Profile Form Whitelist (`market/forms.py`)
`ProfileForm` has been strictly constrained to safe profile attributes:
```python
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
```
Privileged attributes (`is_staff`, `is_superuser`, `groups`, `user_permissions`) can no longer be modified through user-facing profile endpoints.

### 4.2 Object-Level Authorization on Listings (`market/views.py`)
Server-side ownership verification was enforced across all listing management endpoints:
- `listing_edit(request, pk)`: Query scoped with `owner=request.user`. Non-owners receive HTTP 404.
- `listing_sold(request, pk)`: Restricted to HTTP POST (`@require_POST`) with `owner=request.user`.
- `listing_delete(request, pk)`: Restricted to HTTP POST (`@require_POST`) with `owner=request.user`.

### 4.3 Message Thread Privacy (`market/views.py`)
Access to private buyer-seller message threads is restricted via Django ORM `Q` queries:
```python
thread = get_object_or_404(
    Thread.objects.select_related("listing", "buyer", "listing__owner").filter(
        Q(buyer=request.user) | Q(listing__owner=request.user)
    ),
    pk=pk,
)
```
Non-participants cannot read or post into the thread (HTTP 404). In addition, sellers cannot initiate buyer threads with themselves (`start_thread`).

### 4.4 UI Hardening
In `market/templates/market/detail.html`, action controls for "Edit listing" and "Mark sold" are conditionally rendered only when `listing.owner_id == user.id`. In `market/templates/market/profile.html`, references to obsolete department flags were cleaned up.

---

## 5. CSS Styling Defect & Test Database Remediation

### 5.1 Root Cause of Missing CSS
The browser received unstyled plain HTML with `404 Not Found` errors for `/static/market/style.css` because:
1. In `swapshelf/settings.py`, `DEBUG` defaulted to `False` (`os.environ.get("DEBUG", "0") == "1"`).
2. Django's development server (`manage.py runserver`) intentionally disables static asset serving when `DEBUG=False` unless the `--insecure` flag is provided.
3. `swapshelf/urls.py` did not include static file URL patterns, causing all `/static/` requests to hit standard routing and return 404.
4. `STATIC_ROOT` was unconfigured, preventing `collectstatic` from functioning.

### 5.2 Fix for CSS Serving
- Updated `swapshelf/settings.py` so `DEBUG` defaults to `True` for development (`os.environ.get("DEBUG", "1") == "1"`).
- Configured `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- Appended `staticfiles_urlpatterns()` to `swapshelf/urls.py` when `DEBUG=True`.
- Confirmed stylesheet path in `market/templates/market/base.html`:
  ```html
  {% load static %}
  <link rel="stylesheet" href="{% static 'market/style.css' %}">
  ```
- Result: `/static/market/style.css` now returns `HTTP/1.1 200 OK` (2,556 bytes, `Content-Type: text/css`).

### 5.3 Test Suite Auto-Seeding Conflict Fix
During test execution, `post_migrate` in `market/apps.py` was unconditionally calling `market.seed.seed()`, populating demo users (`alex`, `jordan`, `sam`) into the test database before test setup, causing `IntegrityError: UNIQUE constraint failed: auth_user.username` in `SwapShelfAuthorizationTests`.
- Added a check in `market/apps.py` to prevent auto-seeding when running tests (`if "test" in sys.argv: return`).

---

## 6. Architecture Diagram

The following architecture diagram represents the actual SwapShelf system flow:

```
+-----------------------------------------------------------------------------------------+
|                                    Client Browser                                       |
+-----------------------------------------------------------------------------------------+
       |                                       |                                   |
       | HTTP Requests (HTML/Form)             | Static CSS (/static/...)          | Session Cookie
       v                                       v                                   v
+-----------------------------------------------------------------------------------------+
|                          Django WSGI / URL Router (urls.py)                             |
|    - swapshelf/urls.py  -> Admin, Auth (Logout), Market URLs                            |
|    - staticfiles_urlpatterns -> Serves style.css during development                     |
+-----------------------------------------------------------------------------------------+
                               |
                               v
+-----------------------------------------------------------------------------------------+
|                               Django Middleware Stack                                   |
|    - SecurityMiddleware, SessionMiddleware, CommonMiddleware                            |
|    - CsrfViewMiddleware (CSRF token enforcement on all POSTs)                           |
|    - AuthenticationMiddleware (Resolves request.user from session)                      |
|    - MessageMiddleware, XFrameOptionsMiddleware (Clickjacking DENY)                     |
+-----------------------------------------------------------------------------------------+
                               |
                               v
+-----------------------------------------------------------------------------------------+
|                                Views & Access Control                                   |
|  - @login_required decorators (listing_new, listing_edit, sold, delete, mine, thread)     |
|  - @require_POST on state mutations (listing_sold, listing_delete)                       |
|  - Object-Level Ownership Checks: get_object_or_404(Listing, pk=pk, owner=request.user)  |
|  - Thread Privacy Check: Q(buyer=request.user) | Q(listing__owner=request.user)          |
|  - Staff Role Check: request.user.is_staff in desk()                                     |
+-----------------------------------------------------------------------------------------+
               |                                      |
               v                                      v
+-----------------------------+        +--------------------------------------------------+
|      Forms & Validation     |        |                  Templates (DTL)                 |
|  - ListingForm (model fields|        |  - base.html (loads static CSS, top nav)         |
|    price, title, note)      |        |  - home.html (board & category filters)          |
|  - ProfileForm (STRICT:     |        |  - detail.html, mine.html, thread.html           |
|    first_name, last_name,   |        |  - desk.html (conditional note on is_staff)      |
|    email ONLY; no is_staff) |        +--------------------------------------------------+
+-----------------------------+                               |
               |                                              |
               +----------------------+-----------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------------+
|                                Django ORM & Database Layer                              |
|    Models:                                                                              |
|      - User (django.contrib.auth)                                                       |
|      - Listing (owner FK -> User, title, price, category, status, seller_note)          |
|      - Thread (listing FK -> Listing, buyer FK -> User)                                 |
|      - Message (thread FK -> Thread, sender FK -> User, body, created_at)               |
|                                                                                         |
|    Storage Engine:                                                                      |
|      - SQLite: data/swapshelf.db (persistent file or Docker volume)                     |
+-----------------------------------------------------------------------------------------+
```

---

## 7. Verification & Actual Test Results

Automated tests were executed in the project virtual environment (`.venv312`):

```bash
python manage.py test
```

### Test Output:
```
Creating test database for alias 'default'...
Found 14 test(s).
System check identified no issues (0 silenced).
..............
----------------------------------------------------------------------
Ran 14 tests in 13.129s

OK
Destroying test database for alias 'default'...
```

### Test Coverage Summary:

| Test Class | Test Name | Target Behavior | Result |
|---|---|---|---|
| `SwapShelfAuthorizationTests` | `test_profile_cannot_grant_staff_privileges` | Submitting `is_staff=on` rejected; staff flag unchanged | **PASS** |
| `SwapShelfAuthorizationTests` | `test_non_owner_cannot_edit_listing` | Non-owner editing another user's listing returns 404 | **PASS** |
| `SwapShelfAuthorizationTests` | `test_non_owner_cannot_mark_listing_sold` | Non-owner marking sold returns 404; status unchanged | **PASS** |
| `SwapShelfAuthorizationTests` | `test_non_participant_cannot_view_or_post_to_thread` | Third party reading/posting to message thread returns 404 | **PASS** |
| `SwapShelfAuthorizationTests` | `test_owner_can_edit_own_listing` | Listing owner can access own edit form (HTTP 200) | **PASS** |
| `SwapShelfFunctionalTests` | `test_css_static_file_resolution` | Staticfiles finder and handler locate and serve CSS (200) | **PASS** |
| `SwapShelfFunctionalTests` | `test_public_board_and_category_filtering` | Anonymous visitor browses board and applies category filters | **PASS** |
| `SwapShelfFunctionalTests` | `test_registration_login_logout` | Account creation, authentication, and session termination | **PASS** |
| `SwapShelfFunctionalTests` | `test_create_listing` | Authenticated user posts new listing; owner assigned | **PASS** |
| `SwapShelfFunctionalTests` | `test_owner_can_mark_sold` | Owner marks item sold; status persisted | **PASS** |
| `SwapShelfFunctionalTests` | `test_owner_can_delete_and_non_owner_cannot` | Owner deletes listing; non-owner attempt returns 404 | **PASS** |
| `SwapShelfFunctionalTests` | `test_message_thread_flow` | Buyer/seller message exchange; prevents self-threading | **PASS** |
| `SwapShelfFunctionalTests` | `test_profile_update_normal_fields` | Normal first name, last name, and email edits persist | **PASS** |
| `SwapShelfFunctionalTests` | `test_department_desk_staff_access` | Staff sees desk note; normal user receives rejection | **PASS** |

### Live Functional Test Output:
```
[PASS] CSS loads successfully (status 200, length: 2556)
[PASS] Public listing board loads with stylesheet link
[PASS] Category filtering works
[PASS] Login successful as jordan
[PASS] Department desk authorization strictly blocks normal user
[PASS] Profile update successful and verified
[PASS] Creating listing successful
[PASS] Editing listing successful
[PASS] Marking listing as sold successful
[PASS] Logout successful
ALL LIVE FUNCTIONAL VERIFICATION CHECKS PASSED!
```

---

## 8. Production Deployment Readiness Checklist

Before publishing SwapShelf to a public environment, complete the following hardening steps:

1. **SECRET_KEY**: Replace `"swapshelf-dev-secret"` with a cryptographically secure random string generated via `get_random_secret_key()` and stored as an environment variable (`SECRET_KEY`).
2. **DEBUG**: Set `DEBUG=0` in production environments. Never run a publicly reachable server with `DEBUG=True`.
3. **ALLOWED_HOSTS**: Replace `["*"]` with specific fully qualified domain names (e.g., `["swapshelf.yourcampus.edu"]`).
4. **Static Files**:
   - Run `python manage.py collectstatic --noinput` to assemble static assets into `STATIC_ROOT`.
   - Use a production static file server such as **WhiteNoise** (`whitenoise.middleware.WhiteNoiseMiddleware`), an Nginx reverse proxy, or AWS S3 / CloudFront CDN.
5. **HTTPS / SSL**:
   - Set `SECURE_SSL_REDIRECT = True`
   - Set `SESSION_COOKIE_SECURE = True`
   - Set `CSRF_COOKIE_SECURE = True`
   - Set `SECURE_HSTS_SECONDS = 31536000` (HTTP Strict Transport Security)
6. **Database Persistence**: Ensure the SQLite file (`/app/data/swapshelf.db`) resides on a persistent, backed-up volume, or transition to PostgreSQL (`psycopg2`) for multi-worker concurrency.
7. **Hosting Deployment Steps**:
   - **Render / Railway / Fly.io / Heroku**:
     1. Add a `Procfile` or use the provided `Dockerfile`.
     2. Add `whitenoise` to `requirements.txt` and configure static handling in `wsgi.py` / `settings.py`.
     3. Configure environment variables in the provider dashboard: `SECRET_KEY`, `DEBUG=0`, `DATABASE_PATH`.
     4. Attach a persistent disk volume to `/app/data`.
     5. Deploy via GitHub integration to receive an automatic HTTPS URL (e.g., `https://swapshelf-final.onrender.com`).
