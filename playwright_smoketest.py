import asyncio
import time
import re
from datetime import datetime
from playwright.async_api import async_playwright
import supabasehmm
import sys


# ============================================================================
# OUTPUT FORMATTING FUNCTIONS
# ============================================================================

def print_header(title, width=80):
    """Print a formatted header"""
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_table(headers, rows, width=80):
    """Print a formatted table"""
    if not rows:
        return

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Add padding
    col_widths = [w + 2 for w in col_widths]
    total_width = sum(col_widths) + len(headers) - 1

    # Print header
    header_row = "|".join([str(h).center(w)
                          for h, w in zip(headers, col_widths)])
    print("+" + "-" * (total_width - 2) + "+")
    print("|" + header_row + "|")
    print("+" + "-" * (total_width - 2) + "+")

    # Print rows
    for row in rows:
        row_str = "|".join([str(cell).ljust(w)
                           for cell, w in zip(row, col_widths)])
        print("|" + row_str + "|")

    print("+" + "-" * (total_width - 2) + "+")
    print()


def print_summary_box(title, items, width=80):
    """Print a summary box with key-value pairs"""
    print("+" + "-" * (width - 2) + "+")
    print(f"| {title.center(width - 4)} |")
    print("+" + "-" * (width - 2) + "+")
    for key, value in items:
        print(f"| {str(key).ljust(30)} : {str(value).rjust(width - 38)} |")
    print("+" + "-" * (width - 2) + "+")
    print()


def print_progress_bar(current, total, width=50):
    """Print a progress bar"""
    if total == 0:
        return
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = (current / total) * 100
    print(f"  [{bar}] {current}/{total} ({percent:.1f}%)", end='\r')
    if current == total:
        print()  # New line when complete


async def verify_url(page):
    try:
        # Reduced timeout for faster failure detection
        await page.wait_for_load_state("domcontentloaded", timeout=5000)
        # Reduced wait time
        await page.wait_for_timeout(300)

        panel = await page.query_selector(
            "[style*='text-align:center;min-height:calc(100vh - 15rem);display:grid;place-content:center']"
        )

        # If panel exists, user profile does NOT exist
        # If panel does not exist, user profile DOES exist
        if panel:
            return False  # User profile does not exist
        return True  # User profile exists

    except Exception as e:
        return False


# verify if he is in OFPPT
async def verify_ofppt(page):
    """Check if user profile contains OFPPT information with username exclusion"""
    try:
        # Wait for page to be fully loaded
        await page.wait_for_timeout(2000)

        # First, get ALL text from the page to check comprehensively
        all_page_text = ""
        try:
            all_page_text = await page.inner_text("body")
        except:
            pass

        # Try to find user details panels (this is the main profile content area)
        panels = []
        try:
            # Wait for selector with a reasonable timeout
            await page.wait_for_selector(".user-details__main", timeout=5000)
            panels = await page.query_selector_all(".user-details__main")
        except:
            # Selector not found or timeout - try alternative selectors
            try:
                # Try other possible selectors for user profile content
                panels = await page.query_selector_all("[class*='user'], [class*='profile'], [class*='bio'], [class*='info'], [class*='about']")
            except:
                pass

        # Check panels first - this is the most reliable way
        if panels and len(panels) > 0:
            for panel in panels:
                try:
                    text = (await panel.text_content()).strip()
                    if text:
                        # IMPORTANT: Exclude username from check (usernames might contain "ofppt")
                        # The username appears as @username, so we need to exclude anything immediately after @
                        text_upper = text.upper()

                        # First, check for full OFPPT name variations (these are never in usernames)
                        if "OFFICE DE FORMATION PROFESSIONNELLE ET DE PROMOTION DU TRAVAIL" in text_upper:
                            return True
                        if "OFFICE DE FORMATION PROFESSIONNELLE" in text_upper:
                            return True

                        # Now check for "OFPPT" but exclude if it's part of username
                        # Find all @ symbols and their positions
                        at_positions = [i for i, char in enumerate(
                            text_upper) if char == '@']

                        # Find all OFPPT occurrences
                        ofppt_positions = []
                        start = 0
                        while True:
                            pos = text_upper.find("OFPPT", start)
                            if pos == -1:
                                break
                            ofppt_positions.append(pos)
                            start = pos + 1

                        # Check each OFPPT occurrence
                        for ofppt_pos in ofppt_positions:
                            # Check if this OFPPT is part of a username (immediately after @)
                            is_in_username = False
                            for at_pos in at_positions:
                                # If @ is before OFPPT, check the distance and context
                                if at_pos < ofppt_pos:
                                    distance = ofppt_pos - at_pos
                                    # Get the text between @ and OFPPT
                                    between_text = text_upper[at_pos+1:ofppt_pos]

                                    # If OFPPT appears after @, check if it's part of a continuous username
                                    # A username is typically: @username (no spaces, just alphanumeric/underscore)
                                    # If the text between @ and OFPPT has no spaces and is alphanumeric, it's likely username
                                    if distance < 50:  # Check up to 50 chars after @
                                        # Check if there are spaces, newlines, or other word delimiters between @ and OFPPT
                                        # If no spaces and all alphanumeric/underscore/hyphen, it's part of username
                                        if ' ' not in between_text and '\n' not in between_text:
                                            # Check if it's all one word (alphanumeric/underscore/hyphen only)
                                            if between_text.replace("_", "").replace("-", "").isalnum():
                                                # This is part of username
                                                is_in_username = True
                                                break

                            if not is_in_username:
                                # OFPPT is not in username, it's valid
                                return True
                except:
                    continue

        # Fallback: check main content area (not entire body to avoid false positives)
        try:
            # Try to get content from main profile area only
            main_content = await page.query_selector("main, [role='main'], .profile, .user-profile")
            if main_content:
                content_text = await main_content.inner_text()
                if content_text:
                    text_upper = content_text.upper()
                    # Check for OFPPT but exclude username patterns
                    # First check for full OFPPT name (always valid)
                    if "OFFICE DE FORMATION PROFESSIONNELLE ET DE PROMOTION DU TRAVAIL" in text_upper:
                        return True
                    if "OFFICE DE FORMATION PROFESSIONNELLE" in text_upper:
                        return True

                    # Now check for "OFPPT" as a word
                    ofppt_pattern = r'\bOFPPT\b'
                    matches = list(re.finditer(ofppt_pattern, text_upper))

                    for match in matches:
                        ofppt_pos = match.start()
                        # Check if it's in a username context
                        # Look for @ before OFPPT
                        before_text = text_upper[max(
                            0, ofppt_pos-50):ofppt_pos]
                        at_pos = before_text.rfind("@")

                        if at_pos == -1:
                            # No @ found before, it's valid
                            return True

                        # @ found, check distance and context
                        actual_at_pos = ofppt_pos - len(before_text) + at_pos
                        distance = ofppt_pos - actual_at_pos
                        between_text = text_upper[actual_at_pos+1:ofppt_pos]

                        # Check if OFPPT is part of username (continuous word after @)
                        # If there are spaces or newlines between @ and OFPPT, it's not in username
                        if distance < 50:
                            if ' ' in between_text or '\n' in between_text:
                                # Has spaces, not in username - it's valid
                                return True
                            elif between_text.replace("_", "").replace("-", "").isalnum():
                                # No spaces, all alphanumeric - it's in username, skip
                                continue

                        # If we get here, OFPPT is not in username context
                        return True
        except:
            pass

        # Last fallback: check entire body text more thoroughly
        try:
            if all_page_text and len(all_page_text) > 100:
                text_upper = all_page_text.upper()

                # First check for full OFPPT name variations (always valid)
                if "OFFICE DE FORMATION PROFESSIONNELLE ET DE PROMOTION DU TRAVAIL" in text_upper:
                    return True
                if "OFFICE DE FORMATION PROFESSIONNELLE" in text_upper:
                    return True

                # Look for OFPPT as a word boundary (not part of username)
                ofppt_pattern = r'\bOFPPT\b'
                matches = list(re.finditer(ofppt_pattern, text_upper))

                for match in matches:
                    ofppt_index = match.start()
                    # Check surrounding context (300 chars before and after for better detection)
                    start = max(0, ofppt_index - 300)
                    end = min(len(text_upper), ofppt_index + 300)
                    context = text_upper[start:end]

                    # Check if it's in a username context (@username)
                    is_in_username = False
                    # Find all @ symbols in context
                    at_positions_in_context = [
                        i for i, char in enumerate(context) if char == '@']
                    ofppt_pos_in_context = ofppt_index - start

                    for at_pos in at_positions_in_context:
                        if at_pos < ofppt_pos_in_context:
                            distance = ofppt_pos_in_context - at_pos
                            between_text = context[at_pos +
                                                   1:ofppt_pos_in_context]
                            # If @ is close and no spaces between @ and OFPPT, it's in username
                            if distance < 50 and ' ' not in between_text and '\n' not in between_text:
                                if between_text.replace("_", "").replace("-", "").isalnum():
                                    is_in_username = True
                                    break

                    if not is_in_username:
                        # OFPPT is not in username, check if it's in relevant context
                        relevant_keywords = ["FORMATION", "EDUCATION", "INSTITUTION",
                                             "ECOLE", "ETABLISSEMENT", "ETUDIANT", "MOROCCO", "MAROC"]
                        if any(keyword in context for keyword in relevant_keywords):
                            return True
                        # If OFPPT appears with spaces around it (not in username), it's likely valid
                        # Check if there's a space before or after OFPPT in the original text
                        if ofppt_index > 0 and ofppt_index + 5 < len(text_upper):
                            char_before = text_upper[ofppt_index -
                                                     1] if ofppt_index > 0 else ' '
                            char_after = text_upper[ofppt_index +
                                                    5] if ofppt_index + 5 < len(text_upper) else ' '
                            if char_before in [' ', '\n', '\t', '.', ',', ':', ';'] or char_after in [' ', '\n', '\t', '.', ',', ':', ';']:
                                # OFPPT has word boundaries, it's valid
                                return True
        except:
            pass

        # If we got here, OFPPT was not found in the profile
        return False

    except Exception as e:
        # Return None to indicate error occurred
        return None


async def find_user_id(page, username):
    """Find userId for a username by intercepting API calls and checking page content"""
    print(f"Finding userId for: {username}")

    user_id = None

    def on_response(response):
        nonlocal user_id
        url = response.url
        if 'getRank' in url and 'userId=' in url:
            # Extract userId from API call
            start = url.find('userId=') + 7
            end = url.find(
                '&', start) if '&' in url[start:] else len(url)
            user_id = url[start:end]
            print(f"  Found in API call: {user_id}")

    page.on('response', on_response)

    # Navigate to the user profile
    try:
        await page.goto(f"https://cssbattle.dev/player/{username}", timeout=20000)
        await page.wait_for_timeout(3000)  # Wait for API calls to happen

        # If not found in API calls, try to find in page content
        if not user_id:
            # Look for userId in the page content
            user_id = await page.evaluate('''() => {
                // Look for userId in the page
                const regex = /userId=([a-zA-Z0-9]{20,30})/g;
                const html = document.documentElement.outerHTML;
                const match = regex.exec(html);
                return match ? match[1] : null;
            }''')

            if user_id:
                print(f"  Found in page content: {user_id}")

    except Exception as e:
        print(f"  Error navigating to {username}: {str(e)}")
        return None

    return user_id


async def main():
    # Record start time
    start_time = time.time()
    start_datetime = datetime.now()

    print_header("CSSBattle User ID Scraper - API Endpoint Generator", 80)
    print(f"  Started: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        await run_main_logic()

        # Calculate execution time
        end_time = time.time()
        end_datetime = datetime.now()
        execution_time = end_time - start_time
        minutes = int(execution_time // 60)
        seconds = int(execution_time % 60)
        milliseconds = int((execution_time % 1) * 1000)

        print()
        print_summary_box("Execution Summary", [
            ("Execution Time", f"{minutes}m {seconds}s {milliseconds}ms"),
            ("Started", start_datetime.strftime('%Y-%m-%d %H:%M:%S')),
            ("Ended", end_datetime.strftime('%Y-%m-%d %H:%M:%S'))
        ])

    except Exception as e:
        # Calculate execution time even on error
        end_time = time.time()
        execution_time = end_time - start_time
        minutes = int(execution_time // 60)
        seconds = int(execution_time % 60)
        milliseconds = int((execution_time % 1) * 1000)

        print()
        print_summary_box("Execution Failed", [
            ("Error", str(e)[:70]),
            ("Execution Time", f"{minutes}m {seconds}s {milliseconds}ms")
        ])
        sys.exit(1)


async def run_main_logic():
    try:
        # Step 1: Fetch all players from the database
        print_header("STEP 1: Fetching all players from database", 80)
        all_players = await supabasehmm.get_usernames()

        # Filter out empty usernames
        valid_players = [player for player in all_players if player.get(
            'username') and player['username'].strip()]

        print_summary_box("Database Summary", [
            ("Total entries", len(all_players)),
            ("Valid players", len(valid_players)),
            ("Invalid entries", len(all_players) - len(valid_players))
        ])

        if not valid_players:
            print("  [ERROR] No valid players to process")
            return

        print(
            f"  [SUCCESS] Step 1 complete: {len(valid_players)} players ready for verification")
        print()

        # Step 2: Check each player's profile on the web for OFPPT verification
        print_header(
            "STEP 2: Checking OFPPT verification (fresh scrape, no cache)", 80)
        verified_players = []      # Temporary array for OFPPT verified players
        unverified_players = []    # Temporary array for players without OFPPT
        error_players = []         # Players with scraping errors

        semaphore = asyncio.Semaphore(8)  # Reduced concurrency for stability

        print(f"  Processing {len(valid_players)} players...")
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            async def check_ofppt_verification(player_data):
                username = player_data.get('username')
                if not username or not username.strip():
                    return None

                async with semaphore:
                    # Create a new context with no cache/storage for each player to ensure fresh data
                    context = await browser.new_context(
                        ignore_https_errors=True,
                        bypass_csp=True
                    )

                    # Clear all storage and cache for this context
                    await context.clear_cookies()

                    page = await context.new_page()
                    try:
                        ofppt_status = await verify_ofppt_for_player(page, username)
                        current_db_status = player_data.get(
                            'verified_ofppt', False)

                        if ofppt_status is True:
                            verified_players.append({
                                'username': username,
                                'current_ofppt_status': current_db_status
                            })
                        elif ofppt_status is False:
                            unverified_players.append({
                                'username': username,
                                'current_ofppt_status': current_db_status
                            })
                        else:
                            error_players.append({
                                'username': username,
                                'current_ofppt_status': current_db_status
                            })

                        return ofppt_status
                    except Exception as e:
                        print(f"  [ERR] {username}: Error - {str(e)[:50]}...")
                        return None
                    finally:
                        await page.close()
                        await context.close()

            async def verify_ofppt_for_player(page, username):
                # Retry logic for OFPPT verification with fresh scraping
                max_retries = 3
                target_url = f"https://cssbattle.dev/player/{username}"

                for attempt in range(max_retries):
                    try:
                        # Add cache-busting query parameter to ensure fresh fetch
                        cache_buster = int(time.time() * 1000)
                        fresh_url = f"{target_url}?_t={cache_buster}"

                        # Navigate to the profile URL with fresh request (no cache)
                        await page.goto(
                            fresh_url,
                            wait_until="domcontentloaded",
                            timeout=20000
                        )

                        # Wait for page to be fully loaded
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            # If networkidle times out, that's okay, continue with domcontentloaded
                            pass
                        await page.wait_for_timeout(1500)

                        userExists = await verify_url(page)
                        if not userExists:
                            print(f"  {username}: Profile does not exist")
                            return False

                        # Check OFPPT status with better error handling
                        ofppt_status = await verify_ofppt(page)

                        if ofppt_status is None:
                            # If verify_ofppt returned None, it means there was an error
                            # Try one more time with a longer wait
                            if attempt < max_retries - 1:
                                await page.wait_for_timeout(2000)
                                ofppt_status = await verify_ofppt(page)
                                if ofppt_status is not None:
                                    return ofppt_status
                            raise Exception(
                                "Failed to determine OFPPT status after retries")

                        return ofppt_status
                    except Exception as e:
                        if attempt < max_retries - 1:
                            # Silent retry - don't print unless it's the last attempt
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            # Only print error on final failure
                            return None

            # Check OFPPT verification for all players
            tasks = [check_ofppt_verification(player)
                     for player in valid_players]
            await asyncio.gather(*tasks, return_exceptions=True)

            await browser.close()

        # Display results in table format
        print()
        if verified_players:
            print_table(
                ["Username", "Status", "Database Status"],
                [[p['username'], "OFPPT Verified", "True" if p['current_ofppt_status'] else "False"]
                 for p in verified_players]
            )

        if unverified_players:
            print_table(
                ["Username", "Status", "Database Status"],
                [[p['username'], "Not Verified", "True -> False" if p['current_ofppt_status'] else "False (unchanged)"]
                 for p in unverified_players]
            )

        if error_players:
            print_table(
                ["Username", "Status"],
                [[p['username'], "Scraping Error"] for p in error_players]
            )

        print_summary_box("Step 2 Summary", [
            ("Total processed", len(valid_players)),
            ("OFPPT verified", len(verified_players)),
            ("Not verified", len(unverified_players)),
            ("Errors", len(error_players))
        ])

        # Step 3: Update database records for OFPPT verification status
        print_header(
            "STEP 3: Updating OFPPT verification status in database", 80)
        ofppt_updates = []
        update_success = []
        update_failed = []
        update_skipped = []

        # Update players who should have OFPPT verification = true
        for player in verified_players:
            username = player['username']
            current_db_status = player['current_ofppt_status']

            # Update database status to True
            if current_db_status != True:  # Only update if different
                try:
                    update_result = await supabasehmm.update_unverified_ofppt(username, True)
                    if update_result.get('status') == 'updated':
                        ofppt_updates.append(update_result)
                        update_success.append((username, "True", "Updated"))
                    else:
                        update_failed.append((username, "True", str(
                            update_result.get('status', 'failed'))))
                except Exception as e:
                    update_failed.append((username, "True", str(e)[:30]))
            else:
                update_skipped.append((username, "True", "Already correct"))

        # Update players who should have OFPPT verification = false
        # This is critical: if a player removed OFPPT from their profile, update DB to False
        if len(unverified_players) > 0:
            for player in unverified_players:
                username = player['username']
                current_db_status = player['current_ofppt_status']

                # Update database status to False
                if current_db_status != False:  # Only update if different
                    try:
                        update_result = await supabasehmm.update_unverified_ofppt(username, False)
                        if update_result.get('status') == 'updated':
                            ofppt_updates.append(update_result)
                            update_success.append(
                                (username, "False", "Updated"))
                        else:
                            update_failed.append((username, "False", str(
                                update_result.get('status', 'failed'))))
                    except Exception as e:
                        update_failed.append((username, "False", str(e)[:30]))
                else:
                    update_skipped.append(
                        (username, "False", "Already correct"))

        # Display update results in tables
        if update_success:
            print_table(
                ["Username", "New Status", "Result"],
                update_success
            )

        if update_failed:
            print_table(
                ["Username", "New Status", "Error"],
                update_failed
            )

        if update_skipped:
            print_table(
                ["Username", "Status", "Reason"],
                update_skipped
            )

        print_summary_box("Step 3 Summary", [
            ("Total updates", len(ofppt_updates)),
            ("Successful", len(update_success)),
            ("Failed", len(update_failed)),
            ("Skipped", len(update_skipped))
        ])

        # Step 4: Filter players who are OFPPT verified and don't have API value yet
        print_header(
            "STEP 4: Filtering OFPPT verified players for API scraping", 80)

        # Get fresh data after updating OFPPT status
        all_players_updated = await supabasehmm.get_usernames()

        # Filter players with CSSBattle profile links and OFPPT verification
        cssbattle_players = []
        for player in all_players_updated:
            # Check if player has a CSSBattle profile link and is OFPPT verified
            # Skip if they already have an API value in the api_user_css column
            if (player.get('cssbattle_profile') and  # has CSSBattle profile link
                player.get('verified_ofppt', False) and  # is OFPPT verified
                    not player.get('api_user_css')):  # doesn't already have API value
                cssbattle_players.append(player)

        print_summary_box("API Scraping Candidates", [
            ("Total players after OFPPT update", len(all_players_updated)),
            ("OFPPT verified", len(verified_players)),
            ("Ready for API scraping", len(cssbattle_players))
        ])

        if not cssbattle_players:
            print(
                "  [SUCCESS] No players need API scraping (all have existing API values or don't meet criteria)")
            return

        print(
            f"  [SUCCESS] Step 4 complete: {len(cssbattle_players)} players need API scraping")
        print()

        # Step 5: Scrape user IDs for OFPPT verified players with CSSBattle profiles
        print_header(
            "STEP 5: Scraping userIds for OFPPT verified players", 80)

        success_count = 0
        error_count = 0
        skipped_count = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            async def scrape_user_id(player_data):
                username = player_data.get('username')
                if not username or not username.strip():
                    return None

                async with semaphore:
                    # Create a new context with no cache/storage for each player to ensure fresh data
                    context = await browser.new_context(
                        ignore_https_errors=True,
                        bypass_csp=True
                    )

                    # Clear all storage and cache for this context
                    await context.clear_cookies()

                    page = await context.new_page()
                    try:
                        user_id = await find_user_id(page, username)

                        if user_id:
                            # Generate the API endpoint URL
                            api_endpoint = f"https://us-central1-cssbattleapp.cloudfunctions.net/getRank?userId={user_id}"

                            # Update the database with the API endpoint
                            try:
                                update_result = await supabasehmm.update_api_user_css(username, api_endpoint)
                                if update_result.get('status') == 'updated':
                                    print(f"  ✅ {username}: API saved to DB")
                                    return api_endpoint
                                else:
                                    print(f"  ❌ {username}: DB update failed")
                                    return None
                            except Exception as db_error:
                                print(
                                    f"  ❌ {username}: DB error - {str(db_error)[:50]}")
                                return None
                        else:
                            print(f"  ❌ {username}: No userId found")
                            return None
                    except Exception as e:
                        print(f"  ❌ {username}: Error - {str(e)[:50]}...")
                        return None
                    finally:
                        await page.close()
                        await context.close()

            # Scrape user IDs for all players
            tasks = [scrape_user_id(player) for player in cssbattle_players]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful and failed scrapes
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                elif result:
                    success_count += 1
                else:
                    error_count += 1

            await browser.close()

        # Display results in table format
        print()
        print_summary_box("Step 5 Summary", [
            ("Total processed", len(cssbattle_players)),
            ("Successful", success_count),
            ("Failed", error_count),
            ("Skipped", skipped_count)
        ])

        print_header("All steps completed successfully!", 80)

    except Exception as e:
        print(f"Error in main logic: {str(e)[:100]}...")


asyncio.run(main())
