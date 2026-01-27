
import os
import sys
from dotenv import load_dotenv
from github import Github, GithubException

def verify_access():
    print("--- Verifying Repository Code Access ---")
    
    # Load .env explicitly from audit_ease folder
    env_path = os.path.join(os.path.dirname(__file__), '../audit_ease/.env')
    load_dotenv(env_path)
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN not found in .env")
        return

    try:
        g = Github(token)
        user = g.get_user()
        print(f"Authenticated as: {user.login}")
        
        # Test Repo from logs
        repo_name = "alienhousenetworks/alienhouseemployment" 
        print(f"\nAttempting to access repo: {repo_name}")
        
        try:
            repo = g.get_repo(repo_name)
            print(f"✅ Repository Found: {repo.full_name}")
            print(f"   Private: {repo.private}")
            
            # Check Code Access (List Root)
            print("   Listing root contents...")
            contents = repo.get_contents("")
            print(f"✅ Success! Found {len(contents)} items:")
            for c in contents[:5]:
                print(f"   - {c.name} ({c.type})")
            if len(contents) > 5: print("   ... (more)")
                
        except GithubException as e:
            print(f"❌ Access Denied or Repo Not Found: {e}")
            if e.status == 404:
                print("   (404 can mean the repo doesn't exist OR the token lacks 'repo' scope)")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_access()
