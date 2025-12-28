import httpx
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Assuming the table name is "players" - you may need to change this
TABLE_NAME = "players"  # Change this to your actual table name

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


async def get_usernames(WithScore=False):
    async with httpx.AsyncClient() as client:
        # Correct the URL to include the table name
        base_url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=cssbattle_profile_link,verified_ofppt,api_user_css"

        if WithScore:
            base_url += ",score"

        r = await client.get(base_url, headers=HEADERS)

        # Check if request was successful
        if r.status_code != 200:
            return []

        try:
            links = r.json()
        except Exception as e:
            return []

        # Handle case where response is an error object
        if isinstance(links, dict) and 'error' in links:
            return []

        if WithScore:
            usernames = []
            for item in links:
                if isinstance(item, dict):
                    # Fixed the URL replacement logic
                    profile_link = item.get('cssbattle_profile_link', '')
                    if profile_link:
                        username = profile_link.replace(
                            "https://cssbattle.dev/player/", "").strip()
                    else:
                        username = ""
                    usernames.append({
                        "username": username,
                        "cssbattle_profile": profile_link,  # Changed to match what the script expects
                        "verified_ofppt": item.get("verified_ofppt", False),
                        "api_user_css": item.get("api_user_css", None),
                        "score": item.get("score", 0)
                    })
        else:
            usernames = []
            for item in links:
                if isinstance(item, dict):
                    # Fixed the URL replacement logic
                    profile_link = item.get('cssbattle_profile_link', '')
                    if profile_link:
                        username = profile_link.replace(
                            "https://cssbattle.dev/player/", "").strip()
                    else:
                        username = ""
                    usernames.append({
                        "username": username,
                        "cssbattle_profile": profile_link,  # Changed to match what the script expects
                        "verified_ofppt": item.get("verified_ofppt", False),
                        "api_user_css": item.get("api_user_css", None)
                    })

        return usernames


async def update_unverified_ofppt(username, is_verified):
    payload = {"verified_ofppt": is_verified}
    # Fixed the URL - using proper Supabase REST API format
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?cssbattle_profile_link=eq.https://cssbattle.dev/player/{username}"

    async with httpx.AsyncClient() as client:
        r = await client.patch(url, headers=HEADERS, json=payload)
        if r.status_code in (200, 201, 204):
            return {"username": username, "verified_ofppt": is_verified, "status": "updated"}
        else:
            try:
                return r.json()
            except:
                return {"username": username, "status": "failed", "response": r.text}


async def update_score(username, score):
    payload = {"score": score}
    # Fixed the URL - using proper Supabase REST API format
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?cssbattle_profile_link=eq.https://cssbattle.dev/player/{username}"

    async with httpx.AsyncClient() as client:
        r = await client.patch(url, headers=HEADERS, json=payload)
        if r.status_code in (200, 201, 204):
            return {"username": username, "score": score, "status": "updated"}
        else:
            try:
                return r.json()
            except:
                return {"username": username, "status": "failed", "response": r.text}


async def update_api_user_css(username, api_endpoint):
    payload = {"api_user_css": api_endpoint}
    # Fixed the URL - using proper Supabase REST API format
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?cssbattle_profile_link=eq.https://cssbattle.dev/player/{username}"

    async with httpx.AsyncClient() as client:
        r = await client.patch(url, headers=HEADERS, json=payload)
        if r.status_code in (200, 201, 204):
            return {"username": username, "api_user_css": api_endpoint, "status": "updated"}
        else:
            try:
                return r.json()
            except:
                return {"username": username, "status": "failed", "response": r.text}
