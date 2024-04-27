DUMMY_LAST_TWEET = {
    "entryId": "tweet-1783529954258350367",
    "sortIndex": "1" + "0" * 18,
    "content": {
        "entryType": "TimelineTimelineItem",
        "__typename": "TimelineTimelineItem",
        "itemContent": {
            "itemType": "TimelineTweet",
            "__typename": "TimelineTweet",
            "tweet_results": {
                "result": {
                    "__typename": "Tweet",
                    "rest_id": "1783529954258350367",
                    "has_birdwatch_notes": False,
                    "core": {
                        "user_results": {
                            "result": {
                                "__typename": "User",
                                "id": "VXNlcjoxNTUwODk1NTgzNDc2NDQ5Mjgw",
                                "rest_id": "1550895583476449280",
                                "affiliates_highlighted_label": {},
                                "has_graduated_access": True,
                                "is_blue_verified": True,
                                "profile_image_shape": "Circle",
                                "legacy": {
                                    "can_dm": False,
                                    "can_media_tag": False,
                                    "created_at": "Sat Jul 23 17:28:45 +0000 2022",
                                    "default_profile": True,
                                    "default_profile_image": False,
                                    "description": "",
                                    "entities": {
                                        "description": {
                                            "urls": [
                                                {
                                                    "display_url": "u24.gov.ua/seababy",
                                                    "expanded_url": "https://u24.gov.ua/seababy",
                                                    "url": "https://t.co/gS20c3pfA6",
                                                    "indices": [121, 144],
                                                }
                                            ]
                                        },
                                        "url": {
                                            "urls": [
                                                {
                                                    "display_url": "united24media.com",
                                                    "expanded_url": "http://united24media.com",
                                                    "url": "https://t.co/BmMM4DaogH",
                                                    "indices": [0, 23],
                                                }
                                            ]
                                        },
                                    },
                                    "fast_followers_count": 0,
                                    "favourites_count": 4384,
                                    "followers_count": 54940,
                                    "friends_count": 293,
                                    "has_custom_timelines": True,
                                    "is_translator": False,
                                    "listed_count": 659,
                                    "location": "Ukraine",
                                    "media_count": 4172,
                                    "name": "UNITED24 Media",
                                    "normal_followers_count": 54940,
                                    "pinned_tweet_ids_str": ["1783889921645613264"],
                                    "possibly_sensitive": False,
                                    "profile_banner_url": "https://pbs.twimg.com/profile_banners/1550895583476449280/1705505529",
                                    "profile_image_url_https": "https://pbs.twimg.com/profile_images/1550895772195033092/mhj-eC-N_normal.jpg",
                                    "profile_interstitial_type": "",
                                    "screen_name": "United24media",
                                    "statuses_count": 8545,
                                    "translator_type": "none",
                                    "url": "https://t.co/BmMM4DaogH",
                                    "verified": False,
                                    "want_retweets": False,
                                    "withheld_in_countries": [],
                                },
                                "professional": {
                                    "rest_id": "1563193825853870081",
                                    "professional_type": "Business",
                                    "category": [{"id": 579, "name": "", "icon_name": "IconBriefcaseStroke"}],
                                },
                                "tipjar_settings": {},
                            }
                        }
                    },
                    "unmention_data": {},
                    "edit_control": {
                        "edit_tweet_ids": ["1783529954258350367"],
                        "editable_until_msecs": "1714065252000",
                        "is_edit_eligible": True,
                        "edits_remaining": "5",
                    },
                    "is_translatable": True,
                    "views": {"count": "7111", "state": "EnabledWithCount"},
                    "source": '<a href="https://mobile.twitter.com" rel="nofollow">Twitter Web App</a>',
                    "legacy": {
                        "bookmark_count": 9,
                        "bookmarked": False,
                        "created_at": "Thu Apr 25 16:14:12 +0000 2024",
                        "conversation_id_str": "1783529954258350367",
                        "display_text_range": [0, 259],
                        "entities": {"hashtags": [], "symbols": [], "timestamps": [], "urls": [], "user_mentions": []},
                        "favorite_count": 183,
                        "favorited": False,
                        "full_text": "",
                        "is_quote_status": False,
                        "lang": "en",
                        "quote_count": 4,
                        "reply_count": 5,
                        "retweet_count": 106,
                        "retweeted": False,
                        "user_id_str": "1550895583476449280",
                        "id_str": "1783529954258350367",
                    },
                    "quick_promote_eligibility": {"eligibility": "IneligibleNotProfessional"},
                }
            },
            "tweetDisplayType": "Tweet",
            "hasModeratedReplies": False,
        },
    },
}
DUMMY_TWEE_ID = DUMMY_LAST_TWEET["entryId"].split("-")[-1]  # type: ignore[attr-defined]

__all__ = [
    "DUMMY_TWEE_ID",
    "DUMMY_LAST_TWEET",
]
