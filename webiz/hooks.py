import frappe
from werkzeug.wrappers import Response

app_name = "webiz"
app_title = "WeBiz"
app_publisher = "JYT AI"
app_description = "WeBiz"
app_email = "ktk@jyt.ai"
app_license = "Proprietary"

# Apps
# ------------------

required_apps = ["erpnext"]

fixtures = [
    {
        "dt": "Workspace",
        "filters": [["app", "in", ["webiz"]], ["label", "in", ["현장관리"]]]
    }
]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "webiz",
		"title": "WeBiz FM",
		"route": "/app/webiz",
		"has_permission": "webiz.api.permission.has_app_permission"
	}
]


# Installation
# ------------

# before_install = "webiz.install.before_install"
after_install = "webiz.install.after_install"


# Request hooks to inject global sidebar
after_request = ["webiz.hooks.inject_global_sidebar"]

def inject_global_sidebar(response=None, **kwargs):
    """Inject Occam global sidebar into all HTML responses"""
    if not response or not isinstance(response, Response):
        return

    # Only inject into HTML responses
    if not response.content_type or 'text/html' not in response.content_type:
        return

    # Skip if response is empty or not HTML
    if not response.data:
        return

    try:
        html_content = response.data.decode('utf-8')

        # Skip if not a proper HTML document
        if '<html' not in html_content.lower() or '<body' not in html_content.lower():
            return

        # Read sidebar CSS and JS
        sidebar_css = get_sidebar_css()
        sidebar_js = get_sidebar_js()

        if not sidebar_css or not sidebar_js:
            return

        # Create injection script
        injection_script = f"""
<!-- Occam Global Sidebar Injection -->
<style id="global-css">
{sidebar_css}
</style>
<script>
// Occam Global Sidebar - Injected via after_request hook
(function() {{
    'use strict';
    {sidebar_js}
}})();
</script>
<!-- End Occam Global Sidebar Injection -->
"""

        # Inject before closing body tag
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', injection_script + '\n</body>')
            response.data = html_content.encode('utf-8')
            response.content_length = len(response.data)

    except Exception as e:
        # Silently fail to avoid breaking the response
        frappe.log_error(f"Error injecting Global sidebar: {str(e)}")


def get_sidebar_css():
    """Get Global sidebar CSS content"""
    try:
        css_path = frappe.get_app_path("webiz", "public", "css", "global-sidebar.css")
        with open(css_path, 'r') as f:
            return f.read()
    except:
        return ""


def get_sidebar_js():
    """Get Global sidebar JavaScript content"""
    try:
        js_path = frappe.get_app_path("webiz", "public", "js", "global-sidebar.js")
        with open(js_path, 'r') as f:
            return f.read()
    except:
        return ""