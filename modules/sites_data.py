# Sherlock-совместимая база сайтов.
# Каждая запись: (name, url_template, error_type, error_value, regex_check)
# error_type:
#   "status_code"  — сайт отдаёт 200 если найден, 404 если нет
#   "message"      — сайт всегда 200, но содержит текст ошибки если НЕ найден
#   "response_url" — сайт редиректит на другой URL если не найден
# regex_check: None или строка-паттерн для валидации username

SITES: list[dict] = [
    # ── Разработка / код ──────────────────────────────────────────────
    {"name": "GitHub",         "url": "https://github.com/{}",                              "error_type": "status_code", "error_value": 404, "regex": r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"},
    {"name": "GitLab",         "url": "https://gitlab.com/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Bitbucket",      "url": "https://bitbucket.org/{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "SourceForge",    "url": "https://sourceforge.net/u/{}/profile",               "error_type": "status_code", "error_value": 404},
    {"name": "CodePen",        "url": "https://codepen.io/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Replit",         "url": "https://replit.com/@{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "JSFiddle",       "url": "https://jsfiddle.net/{}/",                           "error_type": "status_code", "error_value": 404},
    {"name": "Kaggle",         "url": "https://www.kaggle.com/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "HackerEarth",    "url": "https://www.hackerearth.com/@{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "HackerRank",     "url": "https://www.hackerrank.com/{}",                      "error_type": "status_code", "error_value": 404},
    {"name": "LeetCode",       "url": "https://leetcode.com/{}",                            "error_type": "status_code", "error_value": 404},
    {"name": "Codewars",       "url": "https://www.codewars.com/users/{}",                  "error_type": "status_code", "error_value": 404},
    {"name": "CodinGame",      "url": "https://www.codingame.com/profile/{}",               "error_type": "status_code", "error_value": 404},
    {"name": "npm",            "url": "https://www.npmjs.com/~{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "PyPI",           "url": "https://pypi.org/user/{}/",                          "error_type": "status_code", "error_value": 404},
    {"name": "DockerHub",      "url": "https://hub.docker.com/u/{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "RubyGems",       "url": "https://rubygems.org/profiles/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "crates.io",      "url": "https://crates.io/users/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "Packagist",      "url": "https://packagist.org/users/{}",                     "error_type": "status_code", "error_value": 404},
    {"name": "Gitea",          "url": "https://gitea.com/{}",                               "error_type": "status_code", "error_value": 404},
    {"name": "Stack Overflow", "url": "https://stackoverflow.com/users/{}",                 "error_type": "status_code", "error_value": 404, "regex": r"^\d+$"},

    # ── Социальные сети ───────────────────────────────────────────────
    {"name": "Twitter/X",      "url": "https://x.com/{}",                                   "error_type": "status_code", "error_value": 404, "regex": r"^[A-Za-z0-9_]{1,15}$"},
    {"name": "Instagram",      "url": "https://www.instagram.com/{}/",                      "error_type": "message",     "error_value": "Sorry, this page isn't available"},
    {"name": "Facebook",       "url": "https://www.facebook.com/{}",                        "error_type": "message",     "error_value": "The page you requested was not found"},
    {"name": "TikTok",         "url": "https://www.tiktok.com/@{}",                         "error_type": "message",     "error_value": "Couldn't find this account"},
    {"name": "Pinterest",      "url": "https://www.pinterest.com/{}/",                      "error_type": "message",     "error_value": "Sorry! We couldn\\'t find that page"},
    {"name": "Reddit",         "url": "https://www.reddit.com/user/{}/about.json",          "error_type": "status_code", "error_value": 404, "regex": r"^[A-Za-z0-9_-]{3,20}$"},
    {"name": "Tumblr",         "url": "https://{}.tumblr.com/",                             "error_type": "status_code", "error_value": 404},
    {"name": "VK",             "url": "https://vk.com/{}",                                  "error_type": "message",     "error_value": "This page does not exist"},
    {"name": "OK.ru",          "url": "https://ok.ru/{}",                                   "error_type": "message",     "error_value": "not found"},
    {"name": "Mastodon",       "url": "https://mastodon.social/@{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Telegram",       "url": "https://t.me/{}",                                    "error_type": "message",     "error_value": "tgme_page_title"},
    {"name": "LinkedIn",       "url": "https://www.linkedin.com/in/{}/",                    "error_type": "status_code", "error_value": 404},
    {"name": "Snapchat",       "url": "https://www.snapchat.com/add/{}",                    "error_type": "message",     "error_value": "Sorry, we couldn"},
    {"name": "Discord",        "url": "https://discord.com/users/{}",                       "error_type": "status_code", "error_value": 404, "regex": r"^\d{17,19}$"},
    {"name": "Clubhouse",      "url": "https://www.clubhouse.com/@{}",                      "error_type": "status_code", "error_value": 404},
    {"name": "MeWe",           "url": "https://mewe.com/i/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Minds",          "url": "https://www.minds.com/{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "Gab",            "url": "https://gab.com/{}",                                 "error_type": "status_code", "error_value": 404},
    {"name": "Parler",         "url": "https://parler.com/{}",                              "error_type": "status_code", "error_value": 404},

    # ── Видео / стриминг ──────────────────────────────────────────────
    {"name": "YouTube",        "url": "https://www.youtube.com/@{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Twitch",         "url": "https://www.twitch.tv/{}",                           "error_type": "status_code", "error_value": 404, "regex": r"^[a-zA-Z0-9_]{4,25}$"},
    {"name": "Vimeo",          "url": "https://vimeo.com/{}",                               "error_type": "status_code", "error_value": 404},
    {"name": "DailyMotion",    "url": "https://www.dailymotion.com/{}",                     "error_type": "status_code", "error_value": 404},
    {"name": "Trovo",          "url": "https://trovo.live/s/{}",                            "error_type": "status_code", "error_value": 404},
    {"name": "Odysee",         "url": "https://odysee.com/@{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "Rumble",         "url": "https://rumble.com/user/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "Kick",           "url": "https://kick.com/{}",                                "error_type": "status_code", "error_value": 404},
    {"name": "PeerTube",       "url": "https://video.hardlimit.com/accounts/{}",            "error_type": "status_code", "error_value": 404},

    # ── Музыка / аудио ────────────────────────────────────────────────
    {"name": "SoundCloud",     "url": "https://soundcloud.com/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "Spotify",        "url": "https://open.spotify.com/user/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "Last.fm",        "url": "https://www.last.fm/user/{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Bandcamp",       "url": "https://bandcamp.com/{}",                            "error_type": "status_code", "error_value": 404},
    {"name": "Mixcloud",       "url": "https://www.mixcloud.com/{}/",                       "error_type": "status_code", "error_value": 404},
    {"name": "ReverbNation",   "url": "https://www.reverbnation.com/{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "Audiomack",      "url": "https://audiomack.com/{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "Tidal",          "url": "https://tidal.com/browse/user/{}",                   "error_type": "status_code", "error_value": 404},

    # ── Игры ─────────────────────────────────────────────────────────
    {"name": "Steam",          "url": "https://steamcommunity.com/id/{}",                   "error_type": "message",     "error_value": "The specified profile could not be found"},
    {"name": "Chess.com",      "url": "https://www.chess.com/member/{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "Lichess",        "url": "https://lichess.org/@/{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "Roblox",         "url": "https://www.roblox.com/user.aspx?username={}",       "error_type": "status_code", "error_value": 404},
    {"name": "Minecraft",      "url": "https://api.mojang.com/users/profiles/minecraft/{}", "error_type": "status_code", "error_value": 404},
    {"name": "Battlenet",      "url": "https://us.battle.net/forums/en/d3/profile/{}",      "error_type": "status_code", "error_value": 404},
    {"name": "Kongregate",     "url": "https://www.kongregate.com/accounts/{}",             "error_type": "status_code", "error_value": 404},
    {"name": "Newgrounds",     "url": "https://{}.newgrounds.com/",                         "error_type": "message",     "error_value": "Error 404"},
    {"name": "Itch.io",        "url": "https://itch.io/profile/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "GameBanana",     "url": "https://gamebanana.com/members/{}",                  "error_type": "status_code", "error_value": 404, "regex": r"^\d+$"},
    {"name": "SpeedRunsLive",  "url": "http://www.speedrunslive.com/profiles/#!/{}",        "error_type": "status_code", "error_value": 404},
    {"name": "Speedrun.com",   "url": "https://www.speedrun.com/user/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "Faceit",         "url": "https://www.faceit.com/en/players/{}",               "error_type": "status_code", "error_value": 404},

    # ── Фото / арт / дизайн ───────────────────────────────────────────
    {"name": "Flickr",         "url": "https://www.flickr.com/people/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "500px",          "url": "https://500px.com/p/{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "Behance",        "url": "https://www.behance.net/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "Dribbble",       "url": "https://dribbble.com/{}",                            "error_type": "status_code", "error_value": 404},
    {"name": "DeviantArt",     "url": "https://{}.deviantart.com/",                         "error_type": "message",     "error_value": "The page you're looking for can't be found"},
    {"name": "ArtStation",     "url": "https://www.artstation.com/{}",                      "error_type": "status_code", "error_value": 404},
    {"name": "Unsplash",       "url": "https://unsplash.com/@{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "PixelFed",       "url": "https://pixelfed.social/@{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Imgur",          "url": "https://imgur.com/user/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "GuruShots",      "url": "https://gurushots.com/{}/photos",                    "error_type": "status_code", "error_value": 404},
    {"name": "Wattpad",        "url": "https://www.wattpad.com/user/{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "Fur Affinity",   "url": "https://www.furaffinity.net/user/{}/",               "error_type": "message",     "error_value": "System Message"},
    {"name": "Cara",           "url": "https://cara.app/{}",                                "error_type": "status_code", "error_value": 404},

    # ── Блоги / контент ───────────────────────────────────────────────
    {"name": "Medium",         "url": "https://medium.com/@{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "Dev.to",         "url": "https://dev.to/{}",                                  "error_type": "status_code", "error_value": 404},
    {"name": "Hashnode",       "url": "https://hashnode.com/@{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "Substack",       "url": "https://{}.substack.com/",                           "error_type": "status_code", "error_value": 404},
    {"name": "WordPress",      "url": "https://{}.wordpress.com/",                          "error_type": "status_code", "error_value": 404},
    {"name": "Ghost",          "url": "https://{}.ghost.io/",                               "error_type": "status_code", "error_value": 404},
    {"name": "Blogger",        "url": "https://{}.blogspot.com/",                           "error_type": "status_code", "error_value": 404},
    {"name": "Livejournal",    "url": "https://{}.livejournal.com/",                        "error_type": "status_code", "error_value": 404},
    {"name": "Quora",          "url": "https://www.quora.com/profile/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "HackerNews",     "url": "https://hacker-news.firebaseio.com/v0/user/{}.json", "error_type": "message",     "error_value": "null"},
    {"name": "Lobsters",       "url": "https://lobste.rs/u/{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "Lemmy",          "url": "https://lemmy.world/u/{}",                           "error_type": "status_code", "error_value": 404},
    {"name": "Hubpages",       "url": "https://hubpages.com/@{}",                           "error_type": "status_code", "error_value": 404},

    # ── Продуктивность / бизнес ───────────────────────────────────────
    {"name": "ProductHunt",    "url": "https://www.producthunt.com/@{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "AngelList",      "url": "https://angel.co/u/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Crunchbase",     "url": "https://www.crunchbase.com/person/{}",               "error_type": "status_code", "error_value": 404},
    {"name": "Wellfound",      "url": "https://wellfound.com/u/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "Indie Hackers",  "url": "https://www.indiehackers.com/{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "Freelancer",     "url": "https://www.freelancer.com/u/{}",                    "error_type": "status_code", "error_value": 404},
    {"name": "Fiverr",         "url": "https://www.fiverr.com/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "Upwork",         "url": "https://www.upwork.com/freelancers/~{}",             "error_type": "status_code", "error_value": 404},
    {"name": "Guru",           "url": "https://www.guru.com/freelancers/{}",                "error_type": "status_code", "error_value": 404},
    {"name": "PeoplePerHour",  "url": "https://www.peopleperhour.com/freelancer/{}",        "error_type": "status_code", "error_value": 404},
    {"name": "Toptal",         "url": "https://www.toptal.com/resume/{}",                   "error_type": "status_code", "error_value": 404},

    # ── Identity / универсальные профили ─────────────────────────────
    {"name": "Keybase",        "url": "https://keybase.io/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Gravatar",       "url": "https://en.gravatar.com/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "About.me",       "url": "https://about.me/{}",                                "error_type": "status_code", "error_value": 404},
    {"name": "Linktree",       "url": "https://linktr.ee/{}",                               "error_type": "status_code", "error_value": 404},
    {"name": "Carrd",          "url": "https://{}.carrd.co/",                               "error_type": "status_code", "error_value": 404},
    {"name": "Bento",          "url": "https://bento.me/{}",                                "error_type": "status_code", "error_value": 404},
    {"name": "Beacons",        "url": "https://beacons.ai/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Bio.link",       "url": "https://bio.link/{}",                                "error_type": "status_code", "error_value": 404},
    {"name": "Biolinks",       "url": "https://biolinks.io/{}",                             "error_type": "status_code", "error_value": 404},
    {"name": "Patreon",        "url": "https://www.patreon.com/{}",                         "error_type": "status_code", "error_value": 404},
    {"name": "Ko-fi",          "url": "https://ko-fi.com/{}",                               "error_type": "status_code", "error_value": 404},
    {"name": "Buy Me a Coffee","url": "https://buymeacoffee.com/{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Gumroad",        "url": "https://gumroad.com/{}",                             "error_type": "status_code", "error_value": 404},

    # ── Форумы / сообщества ───────────────────────────────────────────
    {"name": "Disqus",         "url": "https://disqus.com/by/{}/",                          "error_type": "status_code", "error_value": 404},
    {"name": "Pastebin",       "url": "https://pastebin.com/u/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "Foursquare",     "url": "https://foursquare.com/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "Tripadvisor",    "url": "https://www.tripadvisor.com/members/{}",             "error_type": "status_code", "error_value": 404},
    {"name": "Yelp",           "url": "https://www.yelp.com/user_details?userid={}",        "error_type": "status_code", "error_value": 404},
    {"name": "Etsy",           "url": "https://www.etsy.com/shop/{}",                       "error_type": "status_code", "error_value": 404},
    {"name": "Ebay",           "url": "https://www.ebay.com/usr/{}",                        "error_type": "status_code", "error_value": 404},

    # ── Спорт / здоровье ──────────────────────────────────────────────
    {"name": "Strava",         "url": "https://www.strava.com/athletes/{}",                 "error_type": "status_code", "error_value": 404, "regex": r"^\d+$"},
    {"name": "Garmin",         "url": "https://connect.garmin.com/modern/profile/{}",       "error_type": "status_code", "error_value": 404},
    {"name": "Nike+",          "url": "https://www.nike.com/member/profile/{}",             "error_type": "status_code", "error_value": 404},
    {"name": "Geocaching",     "url": "https://www.geocaching.com/p/default.aspx?u={}",    "error_type": "status_code", "error_value": 404},

    # ── Путешествия / карты ───────────────────────────────────────────
    {"name": "Polarsteps",     "url": "https://www.polarsteps.com/{}",                      "error_type": "status_code", "error_value": 404},
    {"name": "Maps.me",        "url": "https://maps.me/user/{}/",                           "error_type": "status_code", "error_value": 404},

    # ── Новости / Q&A ─────────────────────────────────────────────────
    {"name": "Wikidot",        "url": "http://{}.wikidot.com/",                             "error_type": "status_code", "error_value": 404},
    {"name": "Fandom",         "url": "https://www.fandom.com/u/{}",                        "error_type": "status_code", "error_value": 404},
    {"name": "Instructables",  "url": "https://www.instructables.com/member/{}/",           "error_type": "status_code", "error_value": 404},
    {"name": "WikiTree",       "url": "https://www.wikitree.com/wiki/{}",                   "error_type": "status_code", "error_value": 404},
    {"name": "GoodReads",      "url": "https://www.goodreads.com/user/show/{}",             "error_type": "status_code", "error_value": 404, "regex": r"^\d+$"},
    {"name": "LibraryThing",   "url": "https://www.librarything.com/profile/{}",            "error_type": "status_code", "error_value": 404},
    {"name": "Letterboxd",     "url": "https://letterboxd.com/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "Trakt",          "url": "https://trakt.tv/users/{}",                          "error_type": "status_code", "error_value": 404},
    {"name": "MyAnimeList",    "url": "https://myanimelist.net/profile/{}",                 "error_type": "status_code", "error_value": 404},
    {"name": "AniList",        "url": "https://anilist.co/user/{}",                         "error_type": "status_code", "error_value": 404},

    # ── Крипто / Web3 ─────────────────────────────────────────────────
    {"name": "Bitcointalk",    "url": "https://bitcointalk.org/index.php?action=profile;u={}", "error_type": "status_code", "error_value": 404, "regex": r"^\d+$"},
    {"name": "Opensea",        "url": "https://opensea.io/{}",                              "error_type": "status_code", "error_value": 404},
    {"name": "Etherscan",      "url": "https://etherscan.io/address/{}",                    "error_type": "status_code", "error_value": 404},

    # ── Email / безопасность ──────────────────────────────────────────
    {"name": "HaveIBeenPwned", "url": "https://haveibeenpwned.com/account/{}",              "error_type": "status_code", "error_value": 404},
    {"name": "Keyoxide",       "url": "https://keyoxide.org/{}",                            "error_type": "status_code", "error_value": 404},
    {"name": "PGP",            "url": "https://keys.openpgp.org/search?q={}",              "error_type": "status_code", "error_value": 404},
]
