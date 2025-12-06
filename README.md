# CSSBattle Score Retriever & Institution Verifier

A Python web scraping module built to retrieve CSSBattle user scores, verify institutions, and integrate data into a leaderboard system. Developed as part of a team platform to track user performance.

## Description

This module automates extraction and verification of user data from CSSBattle. It collects scores, fetches user bio information, and verifies OFPPT affiliation, providing accurate data for leaderboard ranking.  
It is designed to **only update users whose score or verification status has changed**, ensuring minimal unnecessary writes to the database.

**Key Features:**
- Scrapes CSSBattle to collect user scores.  
- Retrieves additional bio data for the same user.  
- Checks for OFPPT affiliation and marks verified users.  
- Updates Supabase **only if the score or verified status has changed**.  
- Provides structured data ready for leaderboard integration.  

## How It Works

1. **Scrape CSSBattle Scores**  
   - Uses Python Playwright to navigate CSSBattle pages and extract user scores.  

2. **Retrieve User Data**  
   - Fetches user bio information using the same username.  

3. **Verify Institution**  
   - Checks if “OFPPT” appears in the bio to mark the user as verified.  

4. **Update Database**  
   - Updates Supabase **only for users with changed scores or verification status**.  

5. **Output for Leaderboard**  
   - Generates clean, verified data for leaderboard display.  

## Tech Stack

- **Language:** Python  
- **Libraries:** Playwright, asyncio, httpx, JSON  
- **Data Handling:** JSON or database integration  

## Usage

```bash
# Install dependencies
pip install requirements.txt

# Run scraper
python playwright_smoketest.py
````

## Example Output

```json

// update_all_scores
[
  {
    "username": "younes123",
    "score": 450,
    }
]
// update_all_unverified_ofppt
[
  {
    "username": "dev456",
    "ofppt": false
  }
]
```

## Contribution

This project was developed as part of a team. My role was focused on **web scraping and verification** using Python Playwright.

