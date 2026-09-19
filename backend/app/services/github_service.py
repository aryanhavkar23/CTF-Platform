import base64
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import encrypt_secret, decrypt_secret
from app.models.challenge import Challenge
from app.models.github_integration import GitHubIntegration, GitHubSubmissionSync
from app.models.solution import UserWriteup
from app.models.solve import Solve
from app.models.submission import Submission
from app.models.user import User
from app.schemas.github import (
    GitHubIntegrationStatusResponse,
    GitHubRepoItem,
    GitHubSyncResponse,
)

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Converts a string into a clean URL/filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "challenge"


class GitHubService:
    """Authoritative service for GitHub OAuth, repository configuration, and automated solution commit sync."""

    @staticmethod
    def get_auth_url(user_id: UUID) -> str:
        """Generates the GitHub OAuth authorization URL."""
        state_payload = {"user_id": str(user_id), "ts": int(datetime.now(timezone.utc).timestamp())}
        state = base64.urlsafe_b64encode(json.dumps(state_payload).encode("utf-8")).decode("utf-8")

        if settings.GITHUB_CLIENT_ID:
            params = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
                "scope": "repo,read:user",
                "state": state,
                "allow_signup": "true",
            }
            return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        else:
            # Fallback simulated URL for development / testing without live OAuth app
            return f"{settings.GITHUB_REDIRECT_URI}?mock=true&state={state}"

    @staticmethod
    def exchange_oauth_code(
        db: Session,
        user: User,
        code: Optional[str] = None,
        mock_username: Optional[str] = None
    ) -> GitHubIntegration:
        """Exchanges an OAuth code or completes simulated dev connection."""
        is_mock = (
            not settings.GITHUB_CLIENT_ID
            or not settings.GITHUB_CLIENT_SECRET
            or code == "mock"
            or mock_username is not None
        )

        if is_mock:
            username = (mock_username or user.github_username or user.username).strip()
            github_user_id = f"gh_sim_{username}"
            profile_url = f"https://github.com/{username}"
            access_token = f"simulated_token_{username}"
        else:
            if not code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing GitHub authorization code."
                )

            # 1. Exchange code for access token with GitHub
            token_url = "https://github.com/login/oauth/access_token"
            token_payload = json.dumps({
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            }).encode("utf-8")

            req = urllib.request.Request(
                token_url,
                data=token_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "OWASP-CTF-Platform"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    token_data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.error(f"GitHub token exchange network error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub token exchange network error: {str(e)}"
                )

            if "error" in token_data:
                err_desc = token_data.get("error_description", token_data.get("error"))
                logger.error(f"GitHub OAuth error: {err_desc}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GitHub OAuth error: {err_desc}"
                )

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub."
                )

            # 2. Retrieve user identity from GitHub
            user_req = urllib.request.Request(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "OWASP-CTF-Platform"
                }
            )

            try:
                with urllib.request.urlopen(user_req, timeout=10) as resp:
                    gh_user = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to fetch GitHub profile: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch GitHub profile: {str(e)}"
                )

            username = gh_user.get("login")
            github_user_id = str(gh_user.get("id"))
            profile_url = gh_user.get("html_url") or f"https://github.com/{username}"

        # 3. Encrypt access token at rest
        encrypted_token = encrypt_secret(access_token)

        # 4. Upsert integration record
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user.id).first()
        if not integration:
            integration = GitHubIntegration(
                user_id=user.id,
                github_user_id=github_user_id,
                github_username=username,
                github_profile_url=profile_url,
                encrypted_access_token=encrypted_token,
                token_type="bearer",
                scope="repo,read:user",
                is_connected=True,
                last_sync_status="connected",
            )
            db.add(integration)
        else:
            integration.github_user_id = github_user_id
            integration.github_username = username
            integration.github_profile_url = profile_url
            integration.encrypted_access_token = encrypted_token
            integration.is_connected = True
            integration.last_sync_status = "connected"
            integration.last_sync_error = None

        # Also update user table profile attributes
        user.github_username = username
        user.github_profile_url = profile_url

        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def get_status(db: Session, user_id: UUID) -> GitHubIntegrationStatusResponse:
        """Retrieves public connection status, repository config, and sync statistics."""
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user_id).first()
        if not integration or not integration.is_connected:
            return GitHubIntegrationStatusResponse(
                is_connected=False,
                github_username=None,
                selected_repository=None,
                synced_count=0
            )

        synced_count = db.query(GitHubSubmissionSync)\
            .filter(GitHubSubmissionSync.user_id == user_id, GitHubSubmissionSync.status == "synced")\
            .count()

        return GitHubIntegrationStatusResponse(
            is_connected=True,
            github_username=integration.github_username,
            github_profile_url=integration.github_profile_url,
            selected_repository=integration.selected_repository,
            repository_url=integration.repository_url,
            last_sync_at=integration.last_sync_at,
            last_sync_status=integration.last_sync_status,
            last_sync_error=integration.last_sync_error,
            last_commit_sha=integration.last_commit_sha,
            last_commit_url=integration.last_commit_url,
            synced_count=synced_count
        )

    @staticmethod
    def list_user_repositories(db: Session, user_id: UUID) -> List[GitHubRepoItem]:
        """Fetches repositories accessible by the user."""
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user_id).first()
        if not integration or not integration.is_connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account is not connected."
            )

        raw_token = decrypt_secret(integration.encrypted_access_token)
        if not raw_token:
            integration.is_connected = False
            integration.last_sync_error = "Decryption failure. Please reconnect GitHub."
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Stored GitHub credentials could not be decrypted. Please reconnect."
            )

        if raw_token.startswith("simulated_token_"):
            # Provide development mock repository choices
            user_gh = integration.github_username
            return [
                GitHubRepoItem(
                    full_name=f"{user_gh}/ctf-solutions",
                    name="ctf-solutions",
                    html_url=f"https://github.com/{user_gh}/ctf-solutions",
                    private=False,
                    description="Verified student CTF solutions and tactical writeups",
                    has_push_access=True
                ),
                GitHubRepoItem(
                    full_name=f"{user_gh}/owasp-student-defense",
                    name="owasp-student-defense",
                    html_url=f"https://github.com/{user_gh}/owasp-student-defense",
                    private=True,
                    description="Collegiate cyber defense laboratory notes",
                    has_push_access=True
                ),
                GitHubRepoItem(
                    full_name=f"{user_gh}/cybersecurity-portfolio",
                    name="cybersecurity-portfolio",
                    html_url=f"https://github.com/{user_gh}/cybersecurity-portfolio",
                    private=False,
                    description="Public security researcher writeups and methodology",
                    has_push_access=True
                )
            ]

        # Real GitHub API call
        req = urllib.request.Request(
            "https://api.github.com/user/repos?per_page=100&sort=updated&type=all",
            headers={
                "Authorization": f"Bearer {raw_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OWASP-CTF-Platform"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                repos_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                integration.is_connected = False
                integration.last_sync_status = "error"
                integration.last_sync_error = "GitHub authorization expired or revoked. Please reconnect."
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="GitHub authorization has expired or was revoked. Please reconnect."
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API error fetching repositories: {e.reason}"
            )
        except Exception as e:
            logger.error(f"Error fetching user repositories: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to query GitHub repositories: {str(e)}"
            )

        results = []
        for r in repos_data:
            perms = r.get("permissions", {})
            can_push = perms.get("push", True)  # If permissions key is absent, assume writable for owned repos
            results.append(
                GitHubRepoItem(
                    full_name=r.get("full_name"),
                    name=r.get("name"),
                    html_url=r.get("html_url"),
                    private=r.get("private", False),
                    description=r.get("description"),
                    has_push_access=can_push
                )
            )
        return results

    @staticmethod
    def configure_repository(
        db: Session,
        user_id: UUID,
        repository_name: str,
        auto_create: bool = False
    ) -> GitHubIntegration:
        """Configures and verifies repository write access."""
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user_id).first()
        if not integration or not integration.is_connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account is not connected."
            )

        clean_repo = repository_name.strip()
        if "/" not in clean_repo:
            clean_repo = f"{integration.github_username}/{clean_repo}"

        raw_token = decrypt_secret(integration.encrypted_access_token)
        if not raw_token:
            raise HTTPException(status_code=401, detail="Authentication token could not be decrypted.")

        # If mock mode, skip external GitHub call and accept configuration
        if raw_token.startswith("simulated_token_"):
            integration.selected_repository = clean_repo
            integration.repository_url = f"https://github.com/{clean_repo}"
            integration.last_sync_status = "verified"
            integration.last_sync_error = None
            db.commit()
            db.refresh(integration)
            return integration

        owner, repo = clean_repo.split("/", 1)

        # Verify access via GitHub API
        verify_url = f"https://api.github.com/repos/{owner}/{repo}"
        req = urllib.request.Request(
            verify_url,
            headers={
                "Authorization": f"Bearer {raw_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OWASP-CTF-Platform"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                repo_info = json.loads(resp.read().decode("utf-8"))
                perms = repo_info.get("permissions", {})
                if not perms.get("push", True):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You do not have write/push permissions to '{clean_repo}'."
                    )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                if auto_create and owner.lower() == integration.github_username.lower():
                    # Attempt to create the repository
                    create_url = "https://api.github.com/user/repos"
                    create_payload = json.dumps({
                        "name": repo,
                        "description": "OWASP CTF Platform — Verified Student Solves & Tactical Writeups",
                        "private": False,
                        "auto_init": True
                    }).encode("utf-8")
                    create_req = urllib.request.Request(
                        create_url,
                        data=create_payload,
                        headers={
                            "Authorization": f"Bearer {raw_token}",
                            "Content-Type": "application/json",
                            "Accept": "application/vnd.github+json",
                            "User-Agent": "OWASP-CTF-Platform"
                        },
                        method="POST"
                    )
                    try:
                        with urllib.request.urlopen(create_req, timeout=10) as create_resp:
                            repo_info = json.loads(create_resp.read().decode("utf-8"))
                    except Exception as create_err:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to auto-create repository '{clean_repo}': {str(create_err)}"
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Repository '{clean_repo}' not found or access is denied."
                    )
            elif e.code == 401:
                integration.is_connected = False
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="GitHub credentials expired or revoked. Please reconnect."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub verification failed: {e.reason}"
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating repository: {str(e)}"
            )

        integration.selected_repository = clean_repo
        integration.repository_url = f"https://github.com/{clean_repo}"
        integration.last_sync_status = "verified"
        integration.last_sync_error = None
        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def sync_solve_to_github(
        db: Session,
        user_id: UUID,
        challenge: Challenge,
        solve: Solve,
        submission: Submission,
        points_awarded: int
    ) -> Optional[GitHubSubmissionSync]:
        """Automatically commits an accepted challenge solve to the student's designated repository.

        Strict Security Guarantee: The actual flag is NEVER exposed in the commit message or body.
        Duplicate Prevention: If (user_id, challenge_id) has already been synced, returns existing record.
        """
        # 1. Prevent duplicate commits
        existing = db.query(GitHubSubmissionSync).filter(
            GitHubSubmissionSync.user_id == user_id,
            GitHubSubmissionSync.challenge_id == challenge.id,
            GitHubSubmissionSync.status == "synced"
        ).first()
        if existing:
            return existing

        # 2. Check active GitHub connection & configured repository
        integration = db.query(GitHubIntegration).filter(
            GitHubIntegration.user_id == user_id,
            GitHubIntegration.is_connected == True
        ).first()
        if not integration or not integration.selected_repository:
            return None

        # 3. Decrypt token
        raw_token = decrypt_secret(integration.encrypted_access_token)
        if not raw_token:
            integration.last_sync_status = "error"
            integration.last_sync_error = "Access token decryption failure."
            db.commit()
            return None

        # 4. Check for student's attached solution/writeup
        writeup = db.query(UserWriteup).filter(
            UserWriteup.user_id == user_id,
            UserWriteup.challenge_id == challenge.id,
            UserWriteup.is_published == True
        ).first()

        category_name = challenge.category.name if challenge.category else "Specialized Vector"
        difficulty = challenge.difficulty.value.upper() if challenge.difficulty else "STANDARD"
        solve_time = solve.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if solve.created_at else "Verified"
        challenge_slug = slugify(challenge.title)
        file_path = f"ctf-solutions/{challenge_slug}/README.md"

        # 5. Build solution markdown document (NEVER exposing flag)
        doc_lines = [
            f"# {challenge.title}",
            "",
            f"- **Domain / Category:** {category_name}",
            f"- **Exploit Tier:** {difficulty}",
            f"- **Points Awarded:** {points_awarded} PTS",
            f"- **Solved At:** {solve_time}",
            "- **Platform:** OWASP CTF Student Defense Ops",
            "",
            "## Tactical Briefing",
            challenge.description or "No briefing parameters recorded.",
            "",
        ]

        if writeup and writeup.content:
            doc_lines.extend([
                "## Operative Solution & Methodology",
                f"### {writeup.title}",
                writeup.content,
                ""
            ])
            if writeup.tags:
                doc_lines.extend([
                    f"**Vector Tags:** `{writeup.tags}`",
                    ""
                ])
        else:
            doc_lines.extend([
                "## Solution Methodology",
                "*Flag successfully neutralized and validated by automated judging engine.*",
                "",
                "> [!NOTE]",
                "> Full tactical writeup can be appended through the OWASP CTF Academy writeup terminal.",
                ""
            ])

        doc_lines.extend([
            "---",
            "*Verified CTF Solve via OWASP CTF Student Defense Ops platform. Flag is cryptographically sanitized and omitted.*"
        ])

        markdown_content = "\n".join(doc_lines)
        commit_message = f"Solve: {challenge.title} ({category_name}) [+{points_awarded} PTS]"

        # 6. Execute commit via GitHub API or simulation
        owner, repo = integration.selected_repository.split("/", 1)

        if raw_token.startswith("simulated_token_"):
            # Simulated environment commit response
            sim_sha = f"sim_{challenge_slug[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
            sim_url = f"{integration.repository_url}/blob/main/{file_path}"
            sync_rec = GitHubSubmissionSync(
                user_id=user_id,
                challenge_id=challenge.id,
                submission_id=submission.id,
                solve_id=solve.id,
                file_path=file_path,
                commit_sha=sim_sha,
                commit_url=sim_url,
                status="synced",
                synced_at=datetime.now(timezone.utc)
            )
            db.add(sync_rec)
            integration.last_sync_at = datetime.now(timezone.utc)
            integration.last_sync_status = "success"
            integration.last_sync_error = None
            integration.last_commit_sha = sim_sha
            integration.last_commit_url = sim_url
            db.commit()
            db.refresh(sync_rec)
            return sync_rec

        # Real GitHub API Commit execution
        encoded_content = base64.b64encode(markdown_content.encode("utf-8")).decode("utf-8")
        api_path = urllib.parse.quote(file_path)
        content_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{api_path}"

        # Check if file already exists on GitHub to obtain blob SHA
        existing_sha = None
        check_req = urllib.request.Request(
            content_url,
            headers={
                "Authorization": f"Bearer {raw_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OWASP-CTF-Platform"
            }
        )
        try:
            with urllib.request.urlopen(check_req, timeout=10) as resp:
                file_info = json.loads(resp.read().decode("utf-8"))
                existing_sha = file_info.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                logger.warning(f"Unexpected error checking existing file: {e}")
        except Exception:
            pass

        # Send PUT request to create or update file
        put_payload: Dict[str, Any] = {
            "message": commit_message,
            "content": encoded_content,
            "committer": {
                "name": "OWASP CTF Defense Bot",
                "email": "bot@owasp-ctf.local"
            }
        }
        if existing_sha:
            put_payload["sha"] = existing_sha

        put_req = urllib.request.Request(
            content_url,
            data=json.dumps(put_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {raw_token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OWASP-CTF-Platform"
            },
            method="PUT"
        )

        try:
            with urllib.request.urlopen(put_req, timeout=12) as put_resp:
                commit_res = json.loads(put_resp.read().decode("utf-8"))
                commit_sha = commit_res.get("commit", {}).get("sha")
                commit_html_url = commit_res.get("commit", {}).get("html_url") or commit_res.get("content", {}).get("html_url")
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.error(f"Failed to create GitHub commit for user {user_id}: {e.code} - {error_body}")
            integration.last_sync_status = "error"
            integration.last_sync_error = f"GitHub API error ({e.code}): {e.reason}"
            db.commit()
            return None
        except Exception as e:
            logger.error(f"Network error during GitHub commit: {e}")
            integration.last_sync_status = "error"
            integration.last_sync_error = f"Network failure: {str(e)}"
            db.commit()
            return None

        # 7. Record sync in database
        sync_rec = GitHubSubmissionSync(
            user_id=user_id,
            challenge_id=challenge.id,
            submission_id=submission.id,
            solve_id=solve.id,
            file_path=file_path,
            commit_sha=commit_sha,
            commit_url=commit_html_url,
            status="synced",
            synced_at=datetime.now(timezone.utc)
        )
        db.add(sync_rec)

        integration.last_sync_at = datetime.now(timezone.utc)
        integration.last_sync_status = "success"
        integration.last_sync_error = None
        integration.last_commit_sha = commit_sha
        integration.last_commit_url = commit_html_url
        db.commit()
        db.refresh(sync_rec)
        return sync_rec

    @staticmethod
    def sync_all_uncommitted_solves(db: Session, user_id: UUID) -> GitHubSyncResponse:
        """Back-fills commits for all solved challenges that have not yet been synced to GitHub."""
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user_id).first()
        if not integration or not integration.is_connected or not integration.selected_repository:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account is not connected or no repository has been configured."
            )

        solves = db.query(Solve).filter(Solve.user_id == user_id).all()
        synced_records = []
        details = []

        for s in solves:
            challenge = db.query(Challenge).filter(Challenge.id == s.challenge_id).first()
            if not challenge:
                continue

            sub = db.query(Submission).filter(Submission.id == s.submission_id).first() if s.submission_id else None
            if not sub:
                # Find any correct submission by this user for the challenge
                sub = db.query(Submission).filter(
                    Submission.user_id == user_id,
                    Submission.challenge_id == s.challenge_id,
                    Submission.is_correct == True
                ).first()

            if not sub:
                continue

            sync = GitHubService.sync_solve_to_github(
                db=db,
                user_id=user_id,
                challenge=challenge,
                solve=s,
                submission=sub,
                points_awarded=s.points_awarded
            )
            if sync:
                synced_records.append(sync)
                details.append({
                    "challenge_id": str(challenge.id),
                    "title": challenge.title,
                    "sha": sync.commit_sha,
                    "url": sync.commit_url
                })

        return GitHubSyncResponse(
            success=True,
            message=f"Synchronized {len(synced_records)} challenge solve(s) to {integration.selected_repository}.",
            synced_count=len(synced_records),
            details=details
        )

    @staticmethod
    def disconnect(db: Session, user_id: UUID) -> None:
        """Disconnects GitHub integration and cleans sensitive session tokens."""
        integration = db.query(GitHubIntegration).filter(GitHubIntegration.user_id == user_id).first()
        if integration:
            integration.is_connected = False
            integration.encrypted_access_token = encrypt_secret("revoked")
            integration.last_sync_status = "disconnected"
            integration.last_sync_error = None
            db.commit()
