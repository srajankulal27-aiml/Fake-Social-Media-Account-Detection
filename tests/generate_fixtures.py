"""Script to generate test fixtures for FSMD screenshot testing.
Generates:
1. Real target fixtures: profile_genuine.png, profile_fake.png
2. 8 Synthetic fixtures covering different modes, layouts, and profile types.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path("tests/fixtures")
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def get_default_font(size=14):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def create_profile_fixture(
    filename: str,
    username: str,
    full_name: str,
    posts_str: str,
    followers_str: str,
    following_str: str,
    bio: str = "",
    dark_mode: bool = False,
    is_private: bool = False,
    custom_avatar: bool = True,
    number_above: bool = True,
    link: str = ""
):
    bg_color = (18, 18, 18) if dark_mode else (255, 255, 255)
    text_color = (245, 245, 245) if dark_mode else (20, 20, 20)
    subtext_color = (160, 160, 160) if dark_mode else (115, 115, 115)
    link_color = (56, 151, 240) if dark_mode else (0, 55, 107)

    w, h = 420, 500
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    f_user = get_default_font(18)
    f_num = get_default_font(17)
    f_lbl = get_default_font(12)
    f_body = get_default_font(14)

    # 1. Header: Username
    draw.text((25, 20), username, fill=text_color, font=f_user)

    # 2. Avatar Circle
    avatar_box = [25, 60, 115, 150]
    if custom_avatar:
        # Colorful custom avatar
        draw.ellipse(avatar_box, fill=(230, 75, 90), outline=(200, 200, 200), width=2)
        # Inner drawing
        draw.rectangle([50, 85, 90, 125], fill=(50, 140, 230))
    else:
        # Flat grey default silhouette
        draw.ellipse(avatar_box, fill=(180, 180, 180), outline=(150, 150, 150), width=1)
        draw.ellipse([50, 75, 90, 115], fill=(130, 130, 130))
        draw.ellipse([40, 110, 100, 150], fill=(130, 130, 130))

    # 3. Counts Block (Posts, Followers, Following)
    # Positions
    x_posts = 160
    x_followers = 240
    x_following = 330

    if number_above:
        # Number on top line (y=75), Label below (y=100)
        draw.text((x_posts, 75), posts_str, fill=text_color, font=f_num)
        draw.text((x_posts, 100), "posts", fill=subtext_color, font=f_lbl)

        draw.text((x_followers, 75), followers_str, fill=text_color, font=f_num)
        draw.text((x_followers, 100), "followers", fill=subtext_color, font=f_lbl)

        draw.text((x_following, 75), following_str, fill=text_color, font=f_num)
        draw.text((x_following, 100), "following", fill=subtext_color, font=f_lbl)
    else:
        # Number beside label: "120 posts", etc.
        draw.text((150, 80), f"{posts_str} posts", fill=text_color, font=f_body)
        draw.text((150, 105), f"{followers_str} followers", fill=text_color, font=f_body)
        draw.text((150, 130), f"{following_str} following", fill=text_color, font=f_body)

    # 4. Full Name & Bio
    y_cursor = 175
    if full_name:
        draw.text((25, y_cursor), full_name, fill=text_color, font=f_body)
        y_cursor += 24

    if bio:
        for line in bio.splitlines():
            draw.text((25, y_cursor), line, fill=text_color, font=f_body)
            y_cursor += 20

    if link:
        draw.text((25, y_cursor), link, fill=link_color, font=f_body)
        y_cursor += 24

    if is_private:
        y_cursor += 15
        draw.text((25, y_cursor), "This Account is Private", fill=subtext_color, font=f_body)

    out_path = FIXTURES_DIR / filename
    img.save(out_path, format="PNG")
    return out_path


def generate_all_fixtures():
    # 1. Real Fixture: profile_genuine.png
    # Expected: username srajankulal27, 120 posts, 800 followers, 400 following, full name "Srajan Kulal", custom picture, public.
    create_profile_fixture(
        filename="profile_genuine.png",
        username="srajankulal27",
        full_name="Srajan Kulal",
        posts_str="120",
        followers_str="800",
        following_str="400",
        bio="AI Engineer & Researcher\nBuilding open-source ML systems",
        custom_avatar=True,
        is_private=False,
        number_above=True,
        link="https://github.com/srajankulal27"
    )

    # 2. Real Fixture: profile_fake.png
    # Expected: username user12fake45, 0 posts, 5 followers, 3000 following, full name "User", default grey picture, public.
    create_profile_fixture(
        filename="profile_fake.png",
        username="user12fake45",
        full_name="User",
        posts_str="0",
        followers_str="5",
        following_str="3000",
        bio="",
        custom_avatar=False,
        is_private=False,
        number_above=True
    )

    # 3. 8 Synthetic Fixtures
    # 1. Dark Mode
    create_profile_fixture(
        filename="synthetic_dark_mode.png",
        username="night_coder_99",
        full_name="Night Coder",
        posts_str="45",
        followers_str="1200",
        following_str="310",
        bio="Coding under the moonlight",
        dark_mode=True,
        custom_avatar=True
    )

    # 2. Number Beside Label
    create_profile_fixture(
        filename="synthetic_beside_labels.png",
        username="beside_layout",
        full_name="Horizontal Layout",
        posts_str="88",
        followers_str="650",
        following_str="210",
        number_above=False
    )

    # 3. K and M Counts
    create_profile_fixture(
        filename="synthetic_km_counts.png",
        username="celebrity_star",
        full_name="Star Creator",
        posts_str="1.5K",
        followers_str="2.4M",
        following_str="120",
        bio="Official Creator Account",
        custom_avatar=True
    )

    # 4. Private Account
    create_profile_fixture(
        filename="synthetic_private_account.png",
        username="secret_agent_007",
        full_name="James Bond",
        posts_str="12",
        followers_str="95",
        following_str="80",
        is_private=True,
        custom_avatar=True
    )

    # 5. No Bio
    create_profile_fixture(
        filename="synthetic_no_bio.png",
        username="minimalist_user",
        full_name="Minimalist",
        posts_str="15",
        followers_str="200",
        following_str="180",
        bio="",
        custom_avatar=True
    )

    # 6. Long Bio with Link
    create_profile_fixture(
        filename="synthetic_long_bio_link.png",
        username="tech_publisher",
        full_name="Tech Publisher Daily",
        posts_str="350",
        followers_str="18500",
        following_str="420",
        bio="Daily AI and machine learning insights\nTutorials, code examples, reviews\nJoin our community of developers",
        link="https://techdaily.io/subscribe",
        custom_avatar=True
    )

    # 7. Default Grey Avatar
    create_profile_fixture(
        filename="synthetic_default_avatar.png",
        username="new_joiner_2026",
        full_name="New Joiner",
        posts_str="0",
        followers_str="2",
        following_str="45",
        custom_avatar=False
    )

    # 8. High digit ratio suspicious fake
    create_profile_fixture(
        filename="synthetic_bot_digits.png",
        username="bot_user_99887766",
        full_name="Bot 998877",
        posts_str="1",
        followers_str="8",
        following_str="4500",
        bio="Make $5000 a week work from home!",
        link="http://bit.ly/fastmoney",
        custom_avatar=False
    )


if __name__ == "__main__":
    generate_all_fixtures()
    print("Successfully generated all fixtures in tests/fixtures/")

