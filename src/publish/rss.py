from feedgen.feed import FeedGenerator

def build_feed(show, episodes, base_url):
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(show["title"]); fg.author({"name": show["author"]})
    fg.link(href=base_url, rel="alternate")
    fg.description(show["description"]); fg.language(show.get("language", "en-us"))
    fg.logo(f"{base_url}/{show['cover'].split('/')[-1]}")
    fg.podcast.itunes_author(show["author"])
    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["id"]); fe.title(ep["title"]); fe.description(ep["description"])
        fe.pubDate(ep["pub_date"])
        fe.enclosure(f"{base_url}/{ep['audio']}", str(ep["length_bytes"]), "audio/mpeg")
    return fg.rss_str(pretty=True).decode("utf-8")
