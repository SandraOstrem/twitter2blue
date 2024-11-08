import tweepy
from datetime import datetime, timezone
from atproto import Client
import re
import requests
import warnings
import sys

# Set default encoding to UTF-8 for Windows environments
sys.stdout.reconfigure(encoding='utf-8')

# Suppress warnings
warnings.filterwarnings("ignore")

# Retrieve sensitive information from environment variables
bearer_token = os.getenv("BEARER_TOKEN")           # Twitter Bearer Token
bluesky_username = os.getenv("BLUESKY_USERNAME")   # Bluesky Username
bluesky_password = os.getenv("BLUESKY_PASSWORD")   # Bluesky Password

# Target Twitter account to monitor
twitter_account = "valerengaoslo"
last_tweet_id_file = "last_tweet.txt"

# Connect to Twitter API using the Bearer Token
def get_twitter_client():
    print("[DEBUG] Initializing Twitter client...")
    return tweepy.Client(bearer_token=bearer_token)

# Authenticate with Bluesky
def authenticate_bluesky(username, password):
    print("[DEBUG] Authenticating with Bluesky...")
    client = Client()
    client.login(username, password)
    print("[DEBUG] Bluesky authentication successful.")
    return client

# Function to create a post on Bluesky
def post_to_bluesky(client, message):
    print("[DEBUG] Preparing to post to Bluesky...")
    post_data = {
        "repo": client.me.did,
        "collection": "app.bsky.feed.post",
        "record": {
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
    }
    try:
        response = client.com.atproto.repo.create_record(data=post_data)
        print("Posted to Bluesky:", response)
    except Exception as e:
        print("Failed to post to Bluesky:", e)

# Function to expand shortened t.co links in tweet text
def expand_tco_links(text):
    tco_links = re.findall(r'https://t.co/\w+', text)
    for tco_link in tco_links:
        try:
            response = requests.head(tco_link, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                expanded_url = response.url
                text = text.replace(tco_link, expanded_url)
        except requests.RequestException as e:
            print(f"Could not expand {tco_link}: {e}")
    return text

# Function to clean up tweet text for Bluesky
def clean_tweet_text(text):
    text = expand_tco_links(text)
    cleaned_text = re.sub(r'https://t.co/\w+', '', text).strip()
    if not cleaned_text:
        cleaned_text = "Posted a video or media content on Twitter."
    print(f"[DEBUG] Cleaned tweet text: '{cleaned_text}'")
    return cleaned_text

# Function to check for the latest tweet from the specified Twitter account
def get_latest_tweet(twitter_client, screen_name):
    print("[DEBUG] Fetching the latest tweet...")
    try:
        user = twitter_client.get_user(username=screen_name)
        user_id = user.data.id
        tweets = twitter_client.get_users_tweets(user_id, max_results=5, tweet_fields=["created_at", "text"])
        if tweets and tweets.data:
            tweet = tweets.data[0]
            print(f"[DEBUG] Latest tweet text: '{tweet.text}'")
            return tweet.text, tweet.id
    except Exception as e:
        print(f"Error fetching tweets: {e}")
    return None, None

# Function to read the last posted tweet ID from a file
def read_last_tweet_id():
    try:
        with open(last_tweet_id_file, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Function to save the last posted tweet ID to a file
def save_last_tweet_id(tweet_id):
    with open(last_tweet_id_file, "w") as file:
        file.write(str(tweet_id))

# Main function to monitor Twitter and repost on Bluesky
def monitor_twitter_and_repost():
    twitter_client = get_twitter_client()
    bluesky_client = authenticate_bluesky(bluesky_username, bluesky_password)
    last_checked_id = read_last_tweet_id()

    tweet_content, tweet_id = get_latest_tweet(twitter_client, twitter_account)
    if tweet_content and tweet_id != last_checked_id:
        cleaned_tweet_text = clean_tweet_text(tweet_content)
        print(f"New tweet found: {cleaned_tweet_text}")
        post_to_bluesky(bluesky_client, cleaned_tweet_text)
        save_last_tweet_id(tweet_id)
    else:
        print("No new tweets found or already posted.")

# Run the script
if __name__ == "__main__":
    monitor_twitter_and_repost()
