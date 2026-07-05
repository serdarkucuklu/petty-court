from feedgen.feed import FeedGenerator

def build_feed(show, episodes, base_url):
    fg = FeedGenerator()
    fg.load_extension("podcast")
    cover = f"{base_url}/{show['cover'].split('/')[-1]}"
    explicit = show.get("explicit", "no")
    fg.title(show["title"])
    fg.author({"name": show["author"], "email": show.get("email", "")})
    fg.link(href=base_url, rel="alternate")
    fg.description(show["description"])
    fg.language(show.get("language", "en-us"))
    fg.logo(cover)
    # --- iTunes / Apple Podcasts REQUIRED channel tags (feed is rejected without these) ---
    fg.podcast.itunes_author(show["author"])
    fg.podcast.itunes_summary(show["description"])
    fg.podcast.itunes_image(cover)
    fg.podcast.itunes_explicit(explicit)
    fg.podcast.itunes_category([{"cat": show.get("category", "Comedy")}])
    if show.get("email"):
        fg.podcast.itunes_owner(name=show["author"], email=show["email"])
    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["id"]); fe.title(ep["title"]); fe.description(ep["description"])
        fe.pubDate(ep["pub_date"])
        fe.enclosure(f"{base_url}/{ep['audio']}", str(ep["length_bytes"]), "audio/mpeg")
        fe.podcast.itunes_explicit(explicit)
    return fg.rss_str(pretty=True).decode("utf-8")
