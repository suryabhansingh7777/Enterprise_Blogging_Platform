"""Generate a static HTML site from the Django blog database."""
import sqlite3
import os
import shutil
from datetime import datetime

OUTPUT_DIR = "dist"

def get_db():
    conn = sqlite3.connect("db.sqlite3")
    conn.row_factory = sqlite3.Row
    return conn

def time_since(date_str):
    dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - dt
    days = diff.days
    if days >= 365:
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''}"
    elif days >= 30:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''}"
    elif days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    else:
        hours = diff.seconds // 3600
        if hours >= 1:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"

def truncatewords(text, count):
    words = text.split()
    if len(words) <= count:
        return text
    return " ".join(words[:count]) + " ..."

def load_data(conn):
    categories = [dict(r) for r in conn.execute("SELECT * FROM blogs_category ORDER BY id").fetchall()]
    blogs = [dict(r) for r in conn.execute(
        "SELECT b.*, u.username, u.first_name, u.last_name, c.category_name "
        "FROM blogs_blog b "
        "JOIN auth_user u ON b.author_id = u.id "
        "JOIN blogs_category c ON b.category_id = c.id "
        "WHERE b.status = 'Published' "
        "ORDER BY b.created_at DESC"
    ).fetchall()]
    comments = [dict(r) for r in conn.execute(
        "SELECT c.*, u.username FROM blogs_comment c JOIN auth_user u ON c.user_id = u.id ORDER BY c.created_at"
    ).fetchall()]
    about = conn.execute("SELECT * FROM assignments_about LIMIT 1").fetchone()
    about = dict(about) if about else None
    social_links = [dict(r) for r in conn.execute("SELECT * FROM assignments_sociallink").fetchall()]
    return categories, blogs, comments, about, social_links

def category_nav(categories):
    items = ""
    for cat in categories:
        items += f'<a class="p-2 text-muted" href="/category/{cat["id"]}/">{cat["category_name"]}</a>\n'
    return items

def base_html(categories, content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Django Blogs</title>
    <link href="https://getbootstrap.com/docs/4.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Playfair+Display:700,900" rel="stylesheet">
    <link href="/css/blog.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
</head>
<body>
    <div class="container">
      <header class="blog-header py-3">
        <div class="row flex-nowrap justify-content-between align-items-center">
          <div class="col-4 pt-1">
            <a class="blog-header-logo text-dark" href="/">Django Blog</a>
          </div>
          <div class="col-4">
            <form action="/search/" method="GET">
              <div class="input-group">
                <input class="form-control" type="text" name="keyword" placeholder="Enter search term..." aria-label="Enter search term..." aria-describedby="button-search" />
                <button type="submit" class="btn btn-warning" id="button-search">Go!</button>
              </div>
            </form>
          </div>
          <div class="col-4 d-flex justify-content-end align-items-center">
          </div>
        </div>
      </header>

      <div class="nav-scroller py-1 mb-2">
        <nav class="nav d-flex justify-content-between">
          {category_nav(categories)}
        </nav>
      </div>

{content}

<footer class="blog-footer">
    <p>Django blog built with &#x1F496; by <a href="#">Rathan Kumar</a></p>
</footer>
</div>
</body>
</html>"""

def home_page(categories, blogs, about, social_links):
    featured = [b for b in blogs if b["is_featured"]]

    # Hero section
    hero = ""
    if featured:
        post = featured[0]
        hero = f"""<div class="jumbotron p-3 p-md-5 text-white rounded bg-dark" style="background-image: url(/media/{post['featured_image']});background-blend-mode: overlay;background-size:cover;">
      <div class="col-md-8 px-0">
        <h1 class="display-4 font-italic">{post['title']}</h1>
        <p class="lead my-3">{truncatewords(post['short_description'], 25)}</p>
        <p class="lead mb-0"><a href="/blogs/{post['slug']}/" class="text-white font-weight-bold">Continue reading...</a></p>
      </div>
    </div>"""

    # Featured posts cards
    featured_cards = ""
    for post in featured[1:]:
        featured_cards += f"""<div class="col-md-6">
      <div class="card border-0">
        <div class="card-body">
          <h3><a href="/blogs/{post['slug']}/" class="text-dark">{post['title']}</a></h3>
          <small class="mb-1 text-muted">{time_since(post['created_at'])} ago | {post['username']}</small>
          <p class="card-text">{truncatewords(post['short_description'], 25)}</p>
        </div>
      </div>
    </div>"""

    # Recent articles
    recent_cards = ""
    for post in blogs:
        recent_cards += f"""<div class="card border-0">
          <div class="card-body">
            <h3><a href="/blogs/{post['slug']}/" class="text-dark">{post['title']}</a></h3>
            <small class="mb-1 text-muted">{time_since(post['created_at'])} ago | {post['username']}</small>
            <p class="card-text">{truncatewords(post['short_description'], 25)}</p>
          </div>
        </div>"""

    # About sidebar
    about_html = ""
    if about:
        about_html = f"""<div class="p-3 mb-3 bg-light rounded">
          <h4 class="font-italic">{about['about_heading']}</h4>
          <p class="mb-0">{about['about_description']}</p>
        </div>"""

    # Social links sidebar
    social_html = ""
    if social_links:
        links = ""
        for s in social_links:
            links += f'<li><a href="{s["link"]}" target="_blank">{s["platform"]}</a></li>\n'
        social_html = f"""<div class="p-3">
          <h4 class="font-italic">Follow Us</h4>
          <ol class="list-unstyled">
            {links}
          </ol>
        </div>"""

    content = f"""{hero}

  <h3 class="text-uppercase text-warning" style="letter-spacing: 2px;">Featured Posts</h3>
  <div class="row mb-2">
    {featured_cards}
  </div>

  <h3 class="text-uppercase text-warning" style="letter-spacing: 2px;">Recent Articles</h3>
  <main role="main" class="container p-0">
    <div class="row">
      <div class="col-md-8 blog-main">
        {recent_cards}
      </div>
      <aside class="col-md-4 blog-sidebar">
        {about_html}
        {social_html}
      </aside>
    </div>
  </main>
</div>"""
    return base_html(categories, content)

def blog_page(categories, blog, comments_list, social_links):
    blog_comments = [c for c in comments_list if c["blog_id"] == blog["id"]]
    count = len(blog_comments)

    comments_html = ""
    if blog_comments:
        for c in blog_comments:
            comments_html += f"""<div class="card mt-1">
                <div class="card-body">
                    <p class="card-text mb-0">{c['comment']}</p>
                    <span>
                        <small>By {c['username']}</small>
                        <small>| {time_since(c['created_at'])} ago</small>
                    </span>
                </div>
            </div>"""
    else:
        comments_html = "No comments yet."

    # Categories sidebar
    cat_links = ""
    for cat in categories:
        cat_links += f'<li><a href="/category/{cat["id"]}/">{cat["category_name"]}</a></li>\n'

    # Social links sidebar
    social_html = ""
    if social_links:
        links = ""
        for s in social_links:
            links += f'<li><a href="{s["link"]}" target="_blank">{s["platform"]}</a></li>\n'
        social_html = f"""<div class="card mb-4 p-3">
                <h4 class="font-italic">Follow Us</h4>
                <ol class="list-unstyled">
                    {links}
                </ol>
            </div>"""

    # Convert newlines in blog body to paragraphs
    body = blog["blog_body"].replace("\r\n\r\n", "</p><p class='fs-5 mb-4'>").replace("\r\n", "<br>")

    content = f"""<div class="container mt-5">
    <div class="row">
        <div class="col-lg-8">
            <article>
                <header class="mb-4">
                    <h1 class="fw-bolder mb-1">{blog['title']}</h1>
                    <div class="text-muted fst-italic mb-2">Posted on {blog['created_at'][:10]} by {blog['username']}</div>
                    <a class="badge bg-warning text-decoration-none text-light" href="/category/{blog['category_id']}/">{blog['category_name']}</a>
                </header>
                <figure class="mb-4"><img class="img-fluid rounded" src="/media/{blog['featured_image']}" alt="{blog['title']}" /></figure>
                <section class="mb-5">
                    <p class="fs-5 mb-4">{blog['short_description']}</p>
                    <p class="fs-5 mb-4">{body}</p>

                    <h4>Comments ({count})</h4>
                    {comments_html}
                </section>
            </article>
        </div>
        <div class="col-lg-4">
            <div class="card mb-4 p-3">
                <h4 class="font-italic">Categories</h4>
                <div class="card-body">
                    <div class="row">
                        <div class="col-sm-6">
                            <ul class="list-unstyled mb-0">
                                {cat_links}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            {social_html}
        </div>
    </div>
</div>"""
    return base_html(categories, content)

def category_page(categories, category, posts):
    cards = ""
    if posts:
        for post in posts:
            cards += f"""<div class="col-md-6">
      <div class="card border-0">
        <div class="card-body">
          <h3><a href="/blogs/{post['slug']}/" class="text-dark">{post['title']}</a></h3>
          <small class="mb-1 text-muted">{time_since(post['created_at'])} ago | {post['username']}</small>
          <p class="card-text">{truncatewords(post['short_description'], 25)}</p>
        </div>
      </div>
    </div>"""
    else:
        cards = "<p>No posts found</p>"

    content = f"""<h3 class="text-uppercase text-warning" style="letter-spacing: 2px;">Category - {category['category_name']}</h3>
  <div class="row mb-2">
    {cards}
  </div>
</div>"""
    return base_html(categories, content)

def search_page_html(categories):
    """Generate a search page with client-side JS search."""
    content = """<h3 class="text-warning" style="letter-spacing: 2px;">Search Term - <span id="search-term"></span></h3>
<div class="row mb-2" id="search-results">
  <p>Enter a search term above to find posts.</p>
</div>
<script>
var posts = POSTS_JSON;
var params = new URLSearchParams(window.location.search);
var keyword = params.get('keyword') || '';
document.getElementById('search-term').textContent = keyword;
if (keyword) {
    document.querySelector('input[name="keyword"]').value = keyword;
}
var results = document.getElementById('search-results');
if (keyword) {
    var kw = keyword.toLowerCase();
    var matches = posts.filter(function(p) {
        return p.title.toLowerCase().indexOf(kw) !== -1 ||
               p.short_description.toLowerCase().indexOf(kw) !== -1 ||
               p.blog_body.toLowerCase().indexOf(kw) !== -1;
    });
    if (matches.length > 0) {
        var html = '';
        matches.forEach(function(p) {
            var words = p.short_description.split(' ').slice(0, 25).join(' ');
            if (p.short_description.split(' ').length > 25) words += ' ...';
            html += '<div class="col-md-6"><div class="card border-0"><div class="card-body">' +
                '<h3><a href="/blogs/' + p.slug + '/" class="text-dark">' + p.title + '</a></h3>' +
                '<small class="mb-1 text-muted">' + p.time_since + ' ago | ' + p.author + '</small>' +
                '<p class="card-text">' + words + '</p>' +
                '</div></div></div>';
        });
        results.innerHTML = html;
    } else {
        results.innerHTML = '<p>No posts found</p>';
    }
}
</script>
</div>"""
    return base_html(categories, content)

def not_found_page(categories):
    content = """<div class="text-center mt-5 mb-5">
    <h1>404</h1>
    <p>The page you are looking for does not exist.</p>
    <a href="/" class="btn btn-warning">Go Home</a>
</div>"""
    return base_html(categories, content)

def main():
    conn = get_db()
    categories, blogs, comments, about, social_links = load_data(conn)

    # Clean and create output dir
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Copy static assets
    os.makedirs(f"{OUTPUT_DIR}/css", exist_ok=True)
    shutil.copy("blog_main/static/css/blog.css", f"{OUTPUT_DIR}/css/blog.css")
    if os.path.exists("blog_main/static/images"):
        shutil.copytree("blog_main/static/images", f"{OUTPUT_DIR}/images")

    # Copy media files
    if os.path.exists("media"):
        shutil.copytree("media", f"{OUTPUT_DIR}/media")

    # Generate index.html (home page)
    with open(f"{OUTPUT_DIR}/index.html", "w") as f:
        f.write(home_page(categories, blogs, about, social_links))
    print("Generated: index.html")

    # Generate individual blog pages
    os.makedirs(f"{OUTPUT_DIR}/blogs", exist_ok=True)
    for blog in blogs:
        blog_dir = f"{OUTPUT_DIR}/blogs/{blog['slug']}"
        os.makedirs(blog_dir, exist_ok=True)
        with open(f"{blog_dir}/index.html", "w") as f:
            f.write(blog_page(categories, blog, comments, social_links))
        print(f"Generated: blogs/{blog['slug']}/index.html")

    # Generate category pages
    os.makedirs(f"{OUTPUT_DIR}/category", exist_ok=True)
    for cat in categories:
        cat_dir = f"{OUTPUT_DIR}/category/{cat['id']}"
        os.makedirs(cat_dir, exist_ok=True)
        cat_posts = [b for b in blogs if b["category_id"] == cat["id"]]
        with open(f"{cat_dir}/index.html", "w") as f:
            f.write(category_page(categories, cat, cat_posts))
        print(f"Generated: category/{cat['id']}/index.html")

    # Generate search page with client-side JS search
    import json
    posts_json = json.dumps([{
        "title": b["title"],
        "slug": b["slug"],
        "short_description": b["short_description"],
        "blog_body": b["blog_body"],
        "author": b["username"],
        "time_since": time_since(b["created_at"])
    } for b in blogs])

    os.makedirs(f"{OUTPUT_DIR}/search", exist_ok=True)
    search_html = search_page_html(categories)
    search_html = search_html.replace("POSTS_JSON", posts_json)
    with open(f"{OUTPUT_DIR}/search/index.html", "w") as f:
        f.write(search_html)
    print("Generated: search/index.html")

    # Generate 404 page
    with open(f"{OUTPUT_DIR}/404.html", "w") as f:
        f.write(not_found_page(categories))
    print("Generated: 404.html")

    conn.close()
    print(f"\nStatic site generated in '{OUTPUT_DIR}/' directory")

if __name__ == "__main__":
    main()
