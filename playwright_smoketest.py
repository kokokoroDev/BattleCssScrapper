import asyncio
from playwright.async_api import async_playwright
import supabasehmm

# CHECK IF USER EXISTS
async def verify_url(page):
    try: 
        await page.wait_for_load_state("domcontentloaded", timeout = 5000)
        await page.wait_for_timeout(1000)

        panel = await page.query_selector(
            "[style*='text-align:center;min-height:calc(100vh - 15rem);display:grid;place-content:center']"
        )


        if panel :
            return False
        return True

    except Exception as e:
        return False
    

# get Total Score
async def get_total_score(page):
    try:

        element = await page.wait_for_selector("text=Total score",timeout=10000)
        if not element:
            return 0.0
        


        parent = await element.evaluate_handle("el => el.closest('div')")
        text = (await parent.inner_text()).strip()

        # Extract the number and remove , if there is
        score_text = text.replace("Total score", "").strip()
        score_text = score_text.replace(",", "")

        return float(score_text) if score_text else 0.0

    except Exception as e:
        return None 
        
    

    # verify if he is in OFPPT
async def verify_ofppt(page):
    try:
        
        panels = await page.query_selector_all(".user-details__main")


        for panel in panels:
            text = (await panel.text_content()).strip()
            if text and "OFPPT" in text.upper() :
                return True

            return False    

    except Exception as e:
        print(f"Error verify_ofppt: {e}")
        return None
    


async def get_score_verify_ofppt(page, username):
    try:
        await page.goto(f"https://cssbattle.dev/player/{username}", wait_until="domcontentloaded", timeout=20000)

        isFound = await verify_url(page)

        score = None
        ofppt = None

        if isFound:
            score = await get_total_score(page)
            ofppt = await verify_ofppt(page)
            isFound = False

        
        return score, ofppt

    except Exception as e:
        print(f"Error Get score and verify ofppt: {e}")
        return None


async def main():
    usernames = await supabasehmm.get_usernames()  

    results = {}
    semaphore = asyncio.Semaphore(5)  


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=200)

        async def fetch(username):
            async with semaphore:
                page = await browser.new_page()
                try:
                    score, ofppt = await get_score_verify_ofppt(page, username)
                    results[username] = {
                        "score": score,
                        "ofppt": ofppt
                    }
                except Exception as e:
                    print(f"Error fetching {username}: {e}")
                    results[username] = {
                        "score": None,
                        "ofppt": None
                    }
                finally:
                    await page.close()


        # runs for each username the function fetch
        tasks = [asyncio.create_task(fetch(user['username'])) for user in usernames]
        await asyncio.gather(*tasks)

        await browser.close()
        filtered_results = {
                user: info for user, info in results.items()
                if not (info['score'] is None and info['ofppt'] is None)
            }
        

        await supabasehmm.update_all_scores(results=filtered_results)
        await supabasehmm.update_all_unverified_ofppt(results=filtered_results)
        

asyncio.run(main())
