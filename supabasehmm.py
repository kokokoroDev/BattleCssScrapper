import httpx
import asyncio
import os

SUPABASE_URL= os.getenv("SUPABASE_URL")
SUPABASE_KEY= os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


async def get_usernames(IsFiltered=False, WithScore=False):
    async with httpx.AsyncClient() as client:
        base_url = f"{SUPABASE_URL}?select=cssbattle_profile_link,verified_ofppt"
        if IsFiltered:
            base_url += "&verified_ofppt=eq.false"

        if WithScore:
            base_url += ",score"

        r = await client.get(base_url, headers=HEADERS)
        links = r.json()

        if WithScore:
            usernames = [
                {
                    "username": ((item.get('cssbattle_profile_link') or '').replace("https://cssbattle.dev/player/", "")).strip(),
                    "verified_ofppt": item.get("verified_ofppt", False),
                    "score": item.get("score", 0)
                }
                for item in links
            ]
        else:
            usernames = [
                {
                    "username": ((item.get('cssbattle_profile_link') or '').replace("https://cssbattle.dev/player/", "")).strip(),
                    "verified_ofppt": item.get("verified_ofppt", False)
                }
                for item in links
            ]

        return usernames
    
        


async def update_unverified_ofppt(username,is_verified):

    payload = {"verified_ofppt": is_verified}
    url = f"{SUPABASE_URL}?cssbattle_profile_link=eq.https://cssbattle.dev/player/{username}"

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
    url = f"{SUPABASE_URL}?cssbattle_profile_link=eq.https://cssbattle.dev/player/{username}"

    async with httpx.AsyncClient() as client:
        r = await client.patch(url, headers=HEADERS, json=payload)
        if r.status_code in (200, 201, 204):
            return {"username": username, "score": score, "status": "updated"}
        else:
            try:
                return r.json()
            except:
                return {"username": username, "status": "failed", "response": r.text}

async def update_all_scores(results: dict):



    originale = await get_usernames(WithScore=True)
    


    changed_users = [
    {**user, 'score': results[user['username']]['score']}
    for user in originale
    if user['score'] != results[user['username']]['score']
]



    tasks = [update_score(user['username'], user["score"]) for user in changed_users]
    return await asyncio.gather(*tasks)

async def update_all_unverified_ofppt(results: dict):

    False_Users = await get_usernames(IsFiltered=True)
    false_usernames = {u["username"] for u in False_Users}
    changed_users = [{"user" : u, "ofppt" : d.get("ofppt")} for u, d in results.items() if d.get("ofppt") is True and u in false_usernames and d.get('ofppt') == True]

    tasks = [update_unverified_ofppt(user['user'], user["ofppt"]) for user in changed_users]
    return await asyncio.gather(*tasks)


async def main():
    usernames = await get_usernames(WithScore=True)
    print(usernames)

if __name__ == "__main__":
    asyncio.run(main())