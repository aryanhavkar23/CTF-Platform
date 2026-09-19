"""
OWASP CTF Platform — Complete Demo Dataset Seeding Script
Populates a comprehensive, realistic, internally consistent, and idempotent demo dataset.

Usage:
    python scripts/seed_demo_data.py
"""

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.database import SessionLocal
from app.core.security import hash_password
from app.services.challenge_service import hash_flag
from app.models import (
    User,
    UserRole,
    Category,
    Challenge,
    ChallengeDifficulty,
    ChallengeType,
    InstanceMode,
    WriteupVisibility,
    ChallengeHint,
    ChallengeWriteup,
    ChallengeInstance,
    ChallengeInstanceStatus,
    Team,
    TeamMember,
    Event,
    EventStatus,
    event_challenges,
    EventRegistration,
    RegistrationType,
    Submission,
    Solve,
    HintUsage,
    UserActivity,
    ActivityType,
    Badge,
    UserBadge,
    Discussion,
    DiscussionComment,
    Notification,
    NotificationType,
    SecurityEvent,
    SecurityEventReview,
    SecurityEventType,
    SecurityEventSeverity,
    SecurityEventStatus,
)


DEMO_PASSWORD = "DemoPass2026!"


def utc_now():
    return datetime.now(timezone.utc)


def seed_demo_users(db: Session) -> dict[str, User]:
    print("[1/11] Seeding Demo Users...")
    hashed_pwd = hash_password(DEMO_PASSWORD)

    users_data = [
        {
            "username": "DEMO_ADMIN",
            "email": "demo_admin@owasp-ctf.org",
            "role": UserRole.ADMIN,
            "name": "SOC Commander Admin",
            "bio": "Lead CTF Administrator & Faculty Advisor for Collegiate Cyber Defense Ops.",
            "college": "PCCOE Cyber Operations Cell",
            "avatar_url": None,
        },
        {
            "username": "DEMO_STUDENT_01",
            "email": "demo_student_01@owasp-ctf.org",
            "role": UserRole.STUDENT,
            "name": "Alex '0xGhost' Mercer",
            "bio": "Top-tier red team enthusiast, binary exploitation & reverse engineering specialist.",
            "college": "PCCOE COE",
            "avatar_url": None,
        },
        {
            "username": "DEMO_STUDENT_02",
            "email": "demo_student_02@owasp-ctf.org",
            "role": UserRole.STUDENT,
            "name": "Maya 'Cipher' Lin",
            "bio": "Applied cryptography & web application security researcher. Team Alpha co-founder.",
            "college": "PCCOE COE",
            "avatar_url": None,
        },
        {
            "username": "DEMO_STUDENT_03",
            "email": "demo_student_03@owasp-ctf.org",
            "role": UserRole.STUDENT,
            "name": "Rohan 'ByteRookie' Patel",
            "bio": "Junior cybersecurity cadet learning OSINT, network forensics, and packet capture analysis.",
            "college": "MIT Cyber Club",
            "avatar_url": None,
        },
        {
            "username": "DEMO_STUDENT_04",
            "email": "demo_student_04@owasp-ctf.org",
            "role": UserRole.STUDENT,
            "name": "Sam 'ZeroState' Vance",
            "bio": "Newly enlisted cybersecurity student exploring introductory challenges.",
            "college": "COEP Security Lab",
            "avatar_url": None,
        },
    ]

    user_map = {}
    for u_info in users_data:
        user = db.query(User).filter(User.username == u_info["username"]).first()
        if not user:
            user = User(
                username=u_info["username"],
                email=u_info["email"],
                hashed_password=hashed_pwd,
                role=u_info["role"],
                name=u_info["name"],
                bio=u_info["bio"],
                college=u_info["college"],
                avatar_url=u_info["avatar_url"],
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"  + Created User: {user.username} ({user.role.value})")
        else:
            # Ensure attributes and password match
            user.email = u_info["email"]
            user.role = u_info["role"]
            user.name = u_info["name"]
            user.bio = u_info["bio"]
            user.college = u_info["college"]
            user.is_active = True
            user.is_verified = True
            user.hashed_password = hashed_pwd
            db.commit()
            db.refresh(user)
            print(f"  * Verified User: {user.username} ({user.role.value})")
        user_map[u_info["username"]] = user

    return user_map


def seed_demo_teams(db: Session, users: dict[str, User]) -> dict[str, Team]:
    print("[2/11] Seeding Demo Teams...")

    teams_data = [
        {
            "name": "DEMO_TEAM_ALPHA",
            "description": "Premier offensive security collegiate squad. Specializes in Web Exploitation & Pwn.",
            "owner": users["DEMO_STUDENT_01"],
            "college": "PCCOE COE",
            "members": [users["DEMO_STUDENT_01"], users["DEMO_STUDENT_02"]],
        },
        {
            "name": "DEMO_TEAM_BRAVO",
            "description": "Defensive security team focused on Forensics, Incident Response & OSINT.",
            "owner": users["DEMO_STUDENT_03"],
            "college": "MIT Cyber Club",
            "members": [users["DEMO_STUDENT_03"]],
        },
        {
            "name": "DEMO_TEAM_SPECTER",
            "description": "Elite underground research cell exploring zero-days and esoteric binary techniques.",
            "owner": users["DEMO_STUDENT_02"],
            "college": "PCCOE COE",
            "members": [users["DEMO_STUDENT_02"]],
        },
    ]

    team_map = {}
    for t_info in teams_data:
        team = db.query(Team).filter(Team.name == t_info["name"]).first()
        if not team:
            team = Team(
                name=t_info["name"],
                description=t_info["description"],
                owner_id=t_info["owner"].id,
                captain_id=t_info["owner"].id,
                college=t_info["college"],
                is_active=True,
                invite_code=uuid.uuid4().hex[:16],
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            print(f"  + Created Team: {team.name}")
        else:
            print(f"  * Verified Team: {team.name}")

        # Ensure memberships
        for member in t_info["members"]:
            membership = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == team.id, TeamMember.user_id == member.id)
                .first()
            )
            if not membership:
                membership = TeamMember(
                    team_id=team.id,
                    user_id=member.id,
                    role="captain" if member.id == team.owner_id else "member",
                    is_active=True,
                )
                db.add(membership)
                db.commit()
                print(f"    + Added Member: {member.username} to {team.name}")

        team_map[t_info["name"]] = team

    return team_map


def seed_demo_challenges(db: Session) -> dict[str, Challenge]:
    print("[3/11] Seeding Demo Challenges across all 8 categories...")

    # Fetch categories
    cats = {c.name: c for c in db.query(Category).all()}
    if not cats:
        raise RuntimeError("No categories found! Ensure Standard Categories are seeded.")

    challenges_spec = [
        # 1. Web Exploitation
        {
            "title": "DEMO_WEB_01 — Hidden Parameter",
            "category": "Web Exploitation",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 50,
            "flag": "OWASP_DEMO{web_hidden_parameter_01}",
            "description": (
                "An administrative portal leaks sensitive diagnostics through an unadvertised query parameter. "
                "Inspect the client-side JavaScript bundle, discover the debugging hook (`?debug_mode=`), and extract the operative credential flag."
            ),
            "hints": [
                {"title": "Inspect Page Scripts", "content": "Review the inline script tags and source maps in Developer Tools for developer flags.", "cost": 15},
                {"title": "Parameter Discovery", "content": "Try common testing parameters such as `?debug=true` or `?admin=1`.", "cost": 25},
            ],
            "writeup": {
                "title": "Hidden Parameter Walkthrough",
                "visibility": WriteupVisibility.AFTER_SOLVE,
                "content": (
                    "### Tactical Breakdown\n\n"
                    "1. Inspect the landing page source and locate the bundle `bundle.js`.\n"
                    "2. Searching for `fetch` reveals an API handler checking `window.location.search` for `?debug_token=trace_ops`.\n"
                    "3. Appending `?debug_token=trace_ops` returns the administrative banner containing `OWASP_DEMO{web_hidden_parameter_01}`."
                ),
            },
        },
        {
            "title": "DEMO_WEB_02 — Broken Authentication",
            "category": "Web Exploitation",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 80,
            "flag": "OWASP_DEMO{broken_auth_jwt_bypass_02}",
            "description": (
                "The target application relies on a custom JWT authorization header, but accepts an unsecured signature algorithm. "
                "Forge an administrative JWT claim using `alg: 'none'` to gain access to the restricted Operative Vault."
            ),
            "hints": [
                {"title": "Inspect JWT Header", "content": "Decode the JWT header in CyberChef. What algorithm is specified?", "cost": 20},
                {"title": "Algorithm Confusion", "content": "Some vulnerable JWT parsers accept `alg: 'none'` without signature validation.", "cost": 40},
            ],
            "writeup": {
                "title": "Exploiting Algorithm 'none' in JWT",
                "visibility": WriteupVisibility.PUBLIC,
                "content": (
                    "### Walkthrough\n\n"
                    "1. Intercept the `/api/vault` request in Burp Suite.\n"
                    "2. Change the header `alg` parameter from `HS256` to `none`.\n"
                    "3. Set the payload claim `\"role\": \"admin\"` and strip the signature section.\n"
                    "4. Replay the request to read the flag: `OWASP_DEMO{broken_auth_jwt_bypass_02}`."
                ),
            },
        },
        {
            "title": "DEMO_WEB_03 — SQL Injection Lab",
            "category": "Web Exploitation",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 160,
            "flag": "OWASP_DEMO{sql_injection_union_exfil_03}",
            "description": (
                "A legacy student ledger filter fails to parameterize user input on the course roster search. "
                "Perform a structured `UNION SELECT` attack against the SQLite/Postgres backend to extract confidential flags stored in `secret_vault`."
            ),
            "hints": [
                {"title": "Determine Column Count", "content": "Use `ORDER BY 1`, `ORDER BY 2`... to determine how many columns the query selects.", "cost": 30},
                {"title": "Extract Schema", "content": "Query `information_schema.tables` or `sqlite_master` to find hidden table names.", "cost": 50},
            ],
            "writeup": {
                "title": "Union-Based SQL Injection Walkthrough",
                "visibility": WriteupVisibility.AFTER_SOLVE,
                "content": (
                    "### Steps\n\n"
                    "1. Input: `' UNION SELECT 1, table_name, 3 FROM information_schema.tables--`\n"
                    "2. Discovered table `security_flags`.\n"
                    "3. Input: `' UNION SELECT 1, flag_value, 3 FROM security_flags--`\n"
                    "4. Flag revealed: `OWASP_DEMO{sql_injection_union_exfil_03}`."
                ),
            },
        },

        # 2. Cryptography
        {
            "title": "DEMO_CRYPTO_01 — Caesar's Shadow",
            "category": "Cryptography",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 30,
            "flag": "OWASP_DEMO{caesar_shadow_shift_13}",
            "description": (
                "An intercepted field transmission uses an ancient rotational substitution cipher. "
                "Ciphertext: `B J N F C _ Q R Z B { p n r f n e _ f u n q b j _ f u v s g _ 1 3 }` (ROT-13). "
                "Decrypt the operative directive to retrieve the flag."
            ),
            "hints": [
                {"title": "ROT Mechanics", "content": "Each character is rotated by 13 positions in the Latin alphabet.", "cost": 10},
            ],
            "writeup": {
                "title": "Caesar / ROT-13 Decryption",
                "visibility": WriteupVisibility.PUBLIC,
                "content": "Using standard ROT-13 decryption or CyberChef, rotating 13 positions restores `OWASP_DEMO{caesar_shadow_shift_13}`.",
            },
        },
        {
            "title": "DEMO_CRYPTO_02 — RSA Mistake",
            "category": "Cryptography",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 85,
            "flag": "OWASP_DEMO{rsa_small_exponent_cube_root_02}",
            "description": (
                "The operative key generator chose a public exponent of `e = 3` and did not pad the plaintext message (`m^3 < N`). "
                "Compute the direct integer cube root of ciphertext `c` to recover the secret message."
            ),
            "hints": [
                {"title": "Small Public Exponent", "content": "If `e = 3` and no padding is applied, the modular reduction may never wrap around `N`.", "cost": 25},
                {"title": "Cube Root in Python", "content": "Use `gmpy2.iroot(c, 3)` to extract the exact integer root.", "cost": 40},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_CRYPTO_03 — Broken Cipher",
            "category": "Cryptography",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 175,
            "flag": "OWASP_DEMO{aes_ecb_byte_at_a_time_oracle_03}",
            "description": (
                "A proprietary cryptographic service encrypts your input followed by a confidential flag under AES-128 in ECB mode. "
                "Leverage chosen-plaintext byte-at-a-time ECB decryption to deduce the secret flag character by character."
            ),
            "hints": [
                {"title": "Block Padding", "content": "Notice how identical 16-byte input blocks produce identical 16-byte ciphertexts.", "cost": 35},
                {"title": "One-Byte Shift", "content": "Send 15 bytes of padding so the first byte of the flag is pushed into the first block.", "cost": 60},
            ],
            "writeup": None,
        },

        # 3. Forensics
        {
            "title": "DEMO_FORENSICS_01 — Memory Fragment",
            "category": "Forensics",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 40,
            "flag": "OWASP_DEMO{memory_strings_dump_01}",
            "description": (
                "A compromised workstation memory dump was acquired during a security incident. "
                "Analyze the strings within the memory fragment using `strings -a mem.dmp | grep -i 'OWASP_'` to recover the credential."
            ),
            "hints": [
                {"title": "Basic Command Line", "content": "You don't need full Volatility for this fragment; simple string extraction will reveal the token.", "cost": 10},
            ],
            "writeup": {
                "title": "Memory Dump Quick Triage",
                "visibility": WriteupVisibility.PUBLIC,
                "content": "Run `strings mem.raw | grep 'OWASP_DEMO{'` to extract the plaintext flag directly from process cache memory.",
            },
        },
        {
            "title": "DEMO_FORENSICS_02 — Network Trail",
            "category": "Forensics",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 70,
            "flag": "OWASP_DEMO{wireshark_http_stream_exfil_02}",
            "description": (
                "Analyze the provided PCAP packet capture file (`suspect_traffic.pcap`). "
                "Filter on HTTP stream sequences (`http.request.method == 'POST'`) to reconstruct the attacker's data exfiltration payload."
            ),
            "hints": [
                {"title": "Follow TCP Stream", "content": "In Wireshark, right-click on the POST request to `/upload` and choose 'Follow > TCP Stream'.", "cost": 25},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_FORENSICS_03 — Disk Evidence",
            "category": "Forensics",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 140,
            "flag": "OWASP_DEMO{forensics_ext4_inode_recovery_03}",
            "description": (
                "An attacker attempted to wipe their footprints by unlinking files on an ext4 disk image. "
                "Use `fls` and `icat` from The Sleuth Kit (TSK) to carve deleted inode records and extract the confidential research note."
            ),
            "hints": [
                {"title": "The Sleuth Kit", "content": "Run `fls -r -p disk.img` to view deleted directory entries marked with `*`.", "cost": 35},
            ],
            "writeup": None,
        },

        # 4. Reverse Engineering
        {
            "title": "DEMO_REVERSE_01 — Crack the Binary",
            "category": "Reverse Engineering",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 45,
            "flag": "OWASP_DEMO{reverse_strings_hardcoded_01}",
            "description": (
                "A compiled ELF 64-bit executable validates license activation keys via a naive string comparison. "
                "Disassemble the `main` function using Ghidra, IDA, or Cutter to identify the hardcoded validation string."
            ),
            "hints": [
                {"title": "Ghidra Decompilation", "content": "Look at the `strcmp` call in the decompiled C view of `main`.", "cost": 15},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_REVERSE_02 — Hidden Logic",
            "category": "Reverse Engineering",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 90,
            "flag": "OWASP_DEMO{reverse_xor_key_unravel_02}",
            "description": (
                "The binary encrypts its inner secret using an array of hardcoded byte values XORed with a constant scalar `0x5A`. "
                "Extract the byte array from the `.rodata` section and reconstruct the flag in Python."
            ),
            "hints": [
                {"title": "XOR Symmetry", "content": "Remember that `A ^ K = C` implies `C ^ K = A`. Reversing is identical to encryption.", "cost": 30},
            ],
            "writeup": {
                "title": "XOR Decryption Script",
                "visibility": WriteupVisibility.AFTER_SOLVE,
                "content": (
                    "```python\n"
                    "enc = bytes([0x15, 0x0D, 0x1B, 0x09, 0x0A, ...])\n"
                    "flag = ''.join(chr(b ^ 0x5A) for b in enc)\n"
                    "print(flag)\n"
                    "```"
                ),
            },
        },
        {
            "title": "DEMO_REVERSE_03 — Assembly Trail",
            "category": "Reverse Engineering",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 185,
            "flag": "OWASP_DEMO{assembly_vm_state_machine_03}",
            "description": (
                "Analyze a custom virtual machine bytecode interpreter implemented in x86_64 assembly. "
                "Reverse engineer the custom opcode table (ADD, XOR, JMP, CMP) to decode the virtual machine's target password."
            ),
            "hints": [
                {"title": "Opcode Switch Statement", "content": "Find the dispatcher loop that reads bytecode byte-by-byte and branches through a jump table.", "cost": 50},
            ],
            "writeup": None,
        },

        # 5. Pwn / Binary Exploitation
        {
            "title": "DEMO_PWN_01 — Stack Basics",
            "category": "Pwn / Binary Exploitation",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 50,
            "flag": "OWASP_DEMO{stack_overflow_variable_overwrite_01}",
            "description": (
                "A vulnerable C service uses `gets()` to read operative calls into a 32-byte stack buffer adjacent to a boolean `is_admin` variable. "
                "Overflow the buffer by providing 40 bytes of input to set `is_admin != 0` and trigger the win function."
            ),
            "hints": [
                {"title": "Stack Layout", "content": "32 bytes fill the buffer, the next 4-8 bytes overwrite adjacent stack variables.", "cost": 20},
            ],
            "writeup": {
                "title": "Stack Buffer Overflow Walkthrough",
                "visibility": WriteupVisibility.PUBLIC,
                "content": (
                    "Sending `python3 -c \"print('A'*36)\" | ./vuln` overwrites `is_admin` with non-zero characters (`0x41414141`), triggering `print_flag()`."
                ),
            },
        },
        {
            "title": "DEMO_PWN_02 — Memory Leak",
            "category": "Pwn / Binary Exploitation",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 100,
            "flag": "OWASP_DEMO{format_string_stack_leak_02}",
            "description": (
                "A networked logging daemon passes user-controlled messages directly into `printf(user_input)`. "
                "Exploit the format string vulnerability (`%p %p %p...` or `%12$s`) to leak pointers and dereference the secret flag stored on the stack."
            ),
            "hints": [
                {"title": "Format Specifiers", "content": "Input `%p.%p.%p` to read arbitrary stack words as hexadecimal addresses.", "cost": 30},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_PWN_03 — Control Flow",
            "category": "Pwn / Binary Exploitation",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 200,
            "flag": "OWASP_DEMO{ret2win_rip_hijack_payload_03}",
            "description": (
                "Target application has NX enabled, but ASLR and stack canaries are disabled. "
                "Calculate the exact cyclic pattern offset (72 bytes) to hijack the saved instruction pointer (RIP) and jump directly to `print_flag()`."
            ),
            "hints": [
                {"title": "Pwntools GDB", "content": "Use `cyclic 100` and `cyclic -l 0x...` in pwntools to identify the precise RIP offset.", "cost": 50},
            ],
            "writeup": None,
        },

        # 6. OSINT
        {
            "title": "DEMO_OSINT_01 — Digital Footprint",
            "category": "OSINT",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 30,
            "flag": "OWASP_DEMO{osint_github_commit_leak_01}",
            "description": (
                "An open-source intelligence scenario: An operative pushed an API key to a public GitHub repository, then deleted it in a subsequent commit. "
                "Inspect the commit history and git reflog to uncover the leaked flag."
            ),
            "hints": [
                {"title": "Git Log", "content": "Look at the diff of the commit right before the 'remove secret' commit.", "cost": 10},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_OSINT_02 — Trace the Identity",
            "category": "OSINT",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 65,
            "flag": "OWASP_DEMO{osint_social_persona_recon_02}",
            "description": (
                "Given a pseudonym handle `@NullSpecter99`, pivot across public social platforms, Gravatar hashes, and Keybase profiles "
                "to correlate the pseudonym with the public key fingerprint containing the flag."
            ),
            "hints": [
                {"title": "Email Hash", "content": "MD5 hash of the email address can often be queried against Gravatar profile APIs.", "cost": 25},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_OSINT_03 — Open Source Trail",
            "category": "OSINT",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 130,
            "flag": "OWASP_DEMO{osint_geolocation_flight_radar_03}",
            "description": (
                "A photograph uploaded from an operative shows an aircraft tail number and distinct mountain ridges in the background. "
                "Cross-reference public flight telemetry records and geographical satellite imagery to confirm the airport IATA code and flag."
            ),
            "hints": [
                {"title": "Flight Radar Records", "content": "Look up historical ADS-B transponder data for the tail number on the date specified in EXIF.", "cost": 40},
            ],
            "writeup": None,
        },

        # 7. Steganography
        {
            "title": "DEMO_STEG_01 — Hidden Message",
            "category": "Steganography",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 35,
            "flag": "OWASP_DEMO{steg_exif_metadata_secret_01}",
            "description": (
                "A surveillance image appears ordinary on the surface. "
                "Use `exiftool operative_badge.png` to inspect embedded JPEG/PNG metadata headers, Copyright tags, and user comments."
            ),
            "hints": [
                {"title": "EXIF Inspection", "content": "Check the `Artist`, `Comment`, or `XPComment` fields.", "cost": 10},
            ],
            "writeup": {
                "title": "EXIF Metadata Extraction",
                "visibility": WriteupVisibility.PUBLIC,
                "content": "Running `exiftool image.png | grep -i 'OWASP'` prints `Comment: OWASP_DEMO{steg_exif_metadata_secret_01}`.",
            },
        },
        {
            "title": "DEMO_STEG_02 — Pixels Speak",
            "category": "Steganography",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 75,
            "flag": "OWASP_DEMO{steg_least_significant_bit_02}",
            "description": (
                "A high-resolution tactical map conceals secret instructions within the least significant bit (LSB) of each RGB color channel. "
                "Use `zsteg` or StegSolve to extract the LSB bit plane payload."
            ),
            "hints": [
                {"title": "StegSolve Plane View", "content": "Toggle through Red 0, Green 0, Blue 0 planes to view the encoded ASCII stream.", "cost": 25},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_STEG_03 — Layered Secret",
            "category": "Steganography",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 150,
            "flag": "OWASP_DEMO{steg_outguess_spectrogram_audio_03}",
            "description": (
                "A multi-stage audio recording hides an encrypted OutGuess carrier followed by high-frequency spectral audio tones. "
                "Perform Fourier transform spectrogram analysis in Audacity or Sonic Visualiser to read the embedded visual glyphs."
            ),
            "hints": [
                {"title": "Spectrogram Mode", "content": "Switch track view from Waveform to Spectrogram and increase frequency range to 20kHz.", "cost": 45},
            ],
            "writeup": None,
        },

        # 8. Misc
        {
            "title": "DEMO_MISC_01 — Security Puzzle",
            "category": "Misc",
            "difficulty": ChallengeDifficulty.EASY,
            "points": 25,
            "flag": "OWASP_DEMO{misc_base64_qr_code_01}",
            "description": (
                "A puzzle consisting of concatenated Base64 chunks that assemble into an ASCII QR Code. "
                "Decode the payload and scan the resulting matrix to retrieve the operative passcode."
            ),
            "hints": [
                {"title": "Base64 Decoding", "content": "Run `echo '<base64_data>' | base64 -d` to view the terminal QR code.", "cost": 5},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_MISC_02 — Logic Trap",
            "category": "Misc",
            "difficulty": ChallengeDifficulty.MEDIUM,
            "points": 60,
            "flag": "OWASP_DEMO{misc_regex_crossword_master_02}",
            "description": (
                "Solve a 5x5 regular expression crossword where every row and column satisfies strict POSIX regex patterns. "
                "Concatenate the diagonal characters to formulate the key."
            ),
            "hints": [
                {"title": "Intersection Analysis", "content": "Find rows and columns with uniquely restricted character sets first.", "cost": 20},
            ],
            "writeup": None,
        },
        {
            "title": "DEMO_MISC_03 — Final Clue",
            "category": "Misc",
            "difficulty": ChallengeDifficulty.HARD,
            "points": 120,
            "flag": "OWASP_DEMO{misc_zip_bomb_recursive_tar_03}",
            "description": (
                "A Russian doll archive contains 100 recursively nested bzip2, gzip, and tar layers. "
                "Write an automated Python extraction script that unpacks the archives dynamically until the final flag file is reached."
            ),
            "hints": [
                {"title": "Magic Bytes", "content": "Use the `file` utility or `python-magic` to inspect file signatures at each iteration.", "cost": 30},
            ],
            "writeup": {
                "title": "Recursive Archive Extraction Script",
                "visibility": WriteupVisibility.AFTER_SOLVE,
                "content": (
                    "```python\n"
                    "import os, tarfile, zipfile, bz2, gzip\n"
                    "# Loop unpack until plaintext flag is identified\n"
                    "```"
                ),
            },
        },
    ]

    chall_map = {}
    for spec in challenges_spec:
        category = cats[spec["category"]]
        flag_hashed = hash_flag(spec["flag"])

        chall = db.query(Challenge).filter(Challenge.title == spec["title"]).first()
        if not chall:
            chall = Challenge(
                title=spec["title"],
                description=spec["description"],
                category_id=category.id,
                difficulty=spec["difficulty"],
                points=spec["points"],
                flag_hash=flag_hashed,
                is_active=True,
                challenge_type=ChallengeType.STATIC,
                is_live_instance=False,
            )
            db.add(chall)
            db.commit()
            db.refresh(chall)
            print(f"  + Created Challenge: {chall.title} [{spec['difficulty'].value}, {spec['points']} pts]")
        else:
            chall.description = spec["description"]
            chall.category_id = category.id
            chall.difficulty = spec["difficulty"]
            chall.points = spec["points"]
            chall.flag_hash = flag_hashed
            chall.is_active = True
            db.commit()
            db.refresh(chall)
            print(f"  * Verified Challenge: {chall.title}")

        chall_map[spec["title"]] = chall

        # Seed Hints
        for i, h_info in enumerate(spec.get("hints", []), start=1):
            hint = (
                db.query(ChallengeHint)
                .filter(ChallengeHint.challenge_id == chall.id, ChallengeHint.order == i)
                .first()
            )
            if not hint:
                hint = ChallengeHint(
                    challenge_id=chall.id,
                    title=h_info["title"],
                    content=h_info["content"],
                    point_deduction=h_info["cost"],
                    order=i,
                    is_active=True,
                )
                db.add(hint)
                db.commit()

        # Seed Writeup
        w_info = spec.get("writeup")
        if w_info:
            writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == chall.id).first()
            if not writeup:
                writeup = ChallengeWriteup(
                    challenge_id=chall.id,
                    title=w_info["title"],
                    content=w_info["content"],
                    visibility=w_info["visibility"],
                )
                db.add(writeup)
                db.commit()

    return chall_map


def seed_demo_events(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge], teams: dict[str, Team]
) -> dict[str, Event]:
    print("[4/11] Seeding Demo Events across all lifecycle states...")
    now = utc_now()

    events_spec = [
        {
            "name": "DEMO_EVENT_CYBER_WARFARE",
            "slug": "demo-event-cyber-warfare",
            "description": "Active collegiate battleground simulation. Real-time tactical engagements, jeopardy categories, and dynamic scoreboard.",
            "status": EventStatus.LIVE,
            "start_at": now - timedelta(days=2),
            "end_at": now + timedelta(days=5),
            "reg_start": now - timedelta(days=7),
            "reg_end": now + timedelta(days=4),
            "challenges": [
                "DEMO_WEB_01 — Hidden Parameter",
                "DEMO_WEB_02 — Broken Authentication",
                "DEMO_CRYPTO_01 — Caesar's Shadow",
                "DEMO_FORENSICS_01 — Memory Fragment",
                "DEMO_PWN_01 — Stack Basics",
                "DEMO_MISC_01 — Security Puzzle",
            ],
            "registrations": [
                {"user": users["DEMO_STUDENT_01"], "team": None, "type": "individual"},
                {"user": users["DEMO_STUDENT_02"], "team": None, "type": "individual"},
                {"user": None, "team": teams["DEMO_TEAM_ALPHA"], "type": "team"},
            ],
        },
        {
            "name": "DEMO_EVENT_ZERO_DAY",
            "slug": "demo-event-zero-day",
            "description": "Upcoming collegiate championship. Focuses on advanced reverse engineering and binary exploitation.",
            "status": EventStatus.UPCOMING,
            "start_at": now + timedelta(days=7),
            "end_at": now + timedelta(days=14),
            "reg_start": now - timedelta(days=1),
            "reg_end": now + timedelta(days=6),
            "challenges": [
                "DEMO_REVERSE_02 — Hidden Logic",
                "DEMO_REVERSE_03 — Assembly Trail",
                "DEMO_PWN_02 — Memory Leak",
                "DEMO_PWN_03 — Control Flow",
                "DEMO_CRYPTO_03 — Broken Cipher",
            ],
            "registrations": [
                {"user": users["DEMO_STUDENT_01"], "team": None, "type": "individual"},
            ],
        },
        {
            "name": "DEMO_EVENT_FORENSIC_HUNT",
            "slug": "demo-event-forensic-hunt",
            "description": "Completed collegiate digital forensics and incident response tournament.",
            "status": EventStatus.ENDED,
            "start_at": now - timedelta(days=30),
            "end_at": now - timedelta(days=20),
            "reg_start": now - timedelta(days=35),
            "reg_end": now - timedelta(days=31),
            "challenges": [
                "DEMO_FORENSICS_01 — Memory Fragment",
                "DEMO_FORENSICS_02 — Network Trail",
                "DEMO_FORENSICS_03 — Disk Evidence",
                "DEMO_OSINT_01 — Digital Footprint",
                "DEMO_STEG_01 — Hidden Message",
            ],
            "registrations": [
                {"user": users["DEMO_STUDENT_01"], "team": None, "type": "individual"},
                {"user": users["DEMO_STUDENT_02"], "team": None, "type": "individual"},
                {"user": users["DEMO_STUDENT_03"], "team": None, "type": "individual"},
            ],
        },
        {
            "name": "DEMO_EVENT_BEGINNER_LAB",
            "slug": "demo-event-beginner-lab",
            "description": "Entry-level training lab designed for first-time CTF participants and cybersecurity novices.",
            "status": EventStatus.LIVE,
            "start_at": now - timedelta(days=1),
            "end_at": now + timedelta(days=3),
            "reg_start": now - timedelta(days=3),
            "reg_end": now + timedelta(days=2),
            "challenges": [
                "DEMO_WEB_01 — Hidden Parameter",
                "DEMO_CRYPTO_01 — Caesar's Shadow",
                "DEMO_OSINT_01 — Digital Footprint",
                "DEMO_MISC_01 — Security Puzzle",
            ],
            "registrations": [
                {"user": users["DEMO_STUDENT_03"], "team": None, "type": "individual"},
            ],
        },
    ]

    event_map = {}
    for e_spec in events_spec:
        ev = db.query(Event).filter(Event.name == e_spec["name"]).first()
        if not ev:
            ev = Event(
                name=e_spec["name"],
                slug=e_spec["slug"],
                description=e_spec["description"],
                status=e_spec["status"],
                start_at=e_spec["start_at"],
                end_at=e_spec["end_at"],
                registration_start_at=e_spec["reg_start"],
                registration_end_at=e_spec["reg_end"],
                is_active=True,
                created_by=users["DEMO_ADMIN"].id,
            )
            db.add(ev)
            db.commit()
            db.refresh(ev)
            print(f"  + Created Event: {ev.name} ({ev.status.value})")
        else:
            ev.status = e_spec["status"]
            ev.start_at = e_spec["start_at"]
            ev.end_at = e_spec["end_at"]
            ev.registration_start_at = e_spec["reg_start"]
            ev.registration_end_at = e_spec["reg_end"]
            ev.is_active = True
            db.commit()
            db.refresh(ev)
            print(f"  * Verified Event: {ev.name}")

        event_map[e_spec["name"]] = ev

        # Associate Challenges
        for order, title in enumerate(e_spec["challenges"], start=1):
            ch = challenges.get(title)
            if not ch:
                continue
            # Check existing link in event_challenges table
            res = db.execute(
                text(
                    "SELECT 1 FROM event_challenges WHERE event_id = :eid AND challenge_id = :cid"
                ),
                {"eid": ev.id, "cid": ch.id},
            ).first()
            if not res:
                db.execute(
                    event_challenges.insert().values(
                        event_id=ev.id,
                        challenge_id=ch.id,
                        points_override=ch.points,
                        display_order=order,
                        is_active=True,
                        added_at=now,
                    )
                )
                db.commit()

        # Seed Registrations
        for reg in e_spec["registrations"]:
            user_id = reg["user"].id if reg["user"] else None
            team_id = reg["team"].id if reg["team"] else None
            q = db.query(EventRegistration).filter(EventRegistration.event_id == ev.id)
            if user_id:
                q = q.filter(EventRegistration.user_id == user_id)
            elif team_id:
                q = q.filter(EventRegistration.team_id == team_id)
            existing_reg = q.first()

            if not existing_reg:
                new_reg = EventRegistration(
                    event_id=ev.id,
                    user_id=user_id,
                    team_id=team_id,
                    registration_type=reg["type"],
                    is_active=True,
                    registered_at=now - timedelta(days=1),
                )
                db.add(new_reg)
                db.commit()

    return event_map


def seed_demo_submissions_and_solves(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge], events: dict[str, Event], teams: dict[str, Team]
):
    print("[5/11] Seeding Submissions, Solves, and Activity Heatmap...")
    now = utc_now()

    # Plan solves and attempts per student:
    # DEMO_STUDENT_01: 15 solves, 5 failed attempts across past 14 days
    # DEMO_STUDENT_02: 8 solves, 8 failed attempts across past 10 days
    # DEMO_STUDENT_03: 2 solves, 6 failed attempts
    # DEMO_STUDENT_04: 0 submissions

    active_event = events["DEMO_EVENT_CYBER_WARFARE"]
    ended_event = events["DEMO_EVENT_FORENSIC_HUNT"]

    student_01_solves = [
        ("DEMO_WEB_01 — Hidden Parameter", 14, None, None),
        ("DEMO_WEB_02 — Broken Authentication", 13, None, None),
        ("DEMO_WEB_03 — SQL Injection Lab", 12, None, None),
        ("DEMO_CRYPTO_01 — Caesar's Shadow", 11, None, None),
        ("DEMO_CRYPTO_02 — RSA Mistake", 10, None, None),
        ("DEMO_FORENSICS_01 — Memory Fragment", 9, ended_event, None),
        ("DEMO_FORENSICS_02 — Network Trail", 8, ended_event, None),
        ("DEMO_REVERSE_01 — Crack the Binary", 7, None, None),
        ("DEMO_REVERSE_02 — Hidden Logic", 6, None, None),
        ("DEMO_PWN_01 — Stack Basics", 5, active_event, teams["DEMO_TEAM_ALPHA"]),
        ("DEMO_PWN_02 — Memory Leak", 4, None, None),
        ("DEMO_OSINT_01 — Digital Footprint", 3, None, None),
        ("DEMO_OSINT_02 — Trace the Identity", 2, None, None),
        ("DEMO_STEG_01 — Hidden Message", 1, None, None),
        ("DEMO_MISC_01 — Security Puzzle", 0, None, None),
    ]

    student_01_fails = [
        ("DEMO_PWN_03 — Control Flow", 4, "flag{wrong_rip_offset}"),
        ("DEMO_PWN_03 — Control Flow", 4, "flag{failed_rop}"),
        ("DEMO_CRYPTO_03 — Broken Cipher", 3, "OWASP_DEMO{invalid_ecb_oracle}"),
        ("DEMO_REVERSE_03 — Assembly Trail", 2, "test_key_12345"),
        ("DEMO_FORENSICS_03 — Disk Evidence", 1, "OWASP{not_the_inode}"),
    ]

    student_02_solves = [
        ("DEMO_WEB_01 — Hidden Parameter", 10, None, None),
        ("DEMO_CRYPTO_01 — Caesar's Shadow", 9, None, None),
        ("DEMO_FORENSICS_01 — Memory Fragment", 8, ended_event, None),
        ("DEMO_REVERSE_01 — Crack the Binary", 6, None, None),
        ("DEMO_PWN_01 — Stack Basics", 4, active_event, teams["DEMO_TEAM_ALPHA"]),
        ("DEMO_OSINT_01 — Digital Footprint", 3, None, None),
        ("DEMO_STEG_01 — Hidden Message", 2, None, None),
        ("DEMO_MISC_01 — Security Puzzle", 1, None, None),
    ]

    student_02_fails = [
        ("DEMO_WEB_02 — Broken Authentication", 9, "bad_jwt_token"),
        ("DEMO_WEB_02 — Broken Authentication", 9, "none_alg_failed"),
        ("DEMO_CRYPTO_02 — RSA Mistake", 8, "OWASP{wrong_cube_root}"),
        ("DEMO_CRYPTO_02 — RSA Mistake", 8, "test_rsa_key"),
        ("DEMO_PWN_02 — Memory Leak", 5, "format_string_err"),
        ("DEMO_REVERSE_02 — Hidden Logic", 4, "xor_key_mistake"),
        ("DEMO_OSINT_02 — Trace the Identity", 2, "not_nullspecter"),
        ("DEMO_STEG_02 — Pixels Speak", 1, "wrong_lsb_plane"),
    ]

    student_03_solves = [
        ("DEMO_CRYPTO_01 — Caesar's Shadow", 5, None, None),
        ("DEMO_MISC_01 — Security Puzzle", 2, None, None),
    ]

    student_03_fails = [
        ("DEMO_WEB_01 — Hidden Parameter", 6, "debug_test"),
        ("DEMO_WEB_01 — Hidden Parameter", 6, "test_admin_mode"),
        ("DEMO_FORENSICS_01 — Memory Fragment", 4, "mem_string_fail"),
        ("DEMO_OSINT_01 — Digital Footprint", 3, "github_wrong_token"),
        ("DEMO_OSINT_01 — Digital Footprint", 3, "git_leak_fail"),
        ("DEMO_PWN_01 — Stack Basics", 1, "AAAAA"),
    ]

    all_solves_plan = [
        (users["DEMO_STUDENT_01"], student_01_solves),
        (users["DEMO_STUDENT_02"], student_02_solves),
        (users["DEMO_STUDENT_03"], student_03_solves),
    ]

    all_fails_plan = [
        (users["DEMO_STUDENT_01"], student_01_fails),
        (users["DEMO_STUDENT_02"], student_02_fails),
        (users["DEMO_STUDENT_03"], student_03_fails),
    ]

    # Process Solves
    for user, solve_list in all_solves_plan:
        for title, days_ago, ev, team in solve_list:
            ch = challenges.get(title)
            if not ch:
                continue

            event_id = ev.id if ev else None
            team_id = team.id if team else None
            timestamp = now - timedelta(days=days_ago, hours=days_ago % 12, minutes=days_ago * 7)

            # Check if solve already exists
            existing_solve = (
                db.query(Solve)
                .filter(Solve.user_id == user.id, Solve.challenge_id == ch.id)
                .first()
            )
            if not existing_solve:
                # 1. Create Submission
                sub = Submission(
                    user_id=user.id,
                    challenge_id=ch.id,
                    event_id=event_id,
                    team_id=team_id,
                    submitted_flag_hash=ch.flag_hash,
                    is_correct=True,
                    points_awarded=ch.points,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                db.add(sub)
                db.flush()

                # 2. Create Solve
                solve = Solve(
                    user_id=user.id,
                    challenge_id=ch.id,
                    submission_id=sub.id,
                    points_awarded=ch.points,
                    event_id=event_id,
                    team_id=team_id,
                    created_at=timestamp,
                )
                db.add(solve)

                # 3. Create UserActivity
                act = UserActivity(
                    user_id=user.id,
                    activity_type=ActivityType.CHALLENGE_SOLVED.value,
                    reference_id=ch.id,
                    metadata_json=f'{{"challenge_title": "{ch.title}", "points_awarded": {ch.points}}}',
                    created_at=timestamp,
                )
                db.add(act)
                db.commit()

    # Process Failed Submissions
    for user, fail_list in all_fails_plan:
        for title, days_ago, fake_flag in fail_list:
            ch = challenges.get(title)
            if not ch:
                continue
            timestamp = now - timedelta(days=days_ago, hours=(days_ago + 3) % 12)
            sub = Submission(
                user_id=user.id,
                challenge_id=ch.id,
                event_id=None,
                team_id=None,
                submitted_flag_hash=hash_flag(fake_flag),
                is_correct=False,
                points_awarded=0,
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(sub)
            db.commit()

    print("  + Solves & Submissions successfully committed.")


def seed_demo_hint_usage(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge]
):
    print("[6/11] Seeding Hint Usages...")
    now = utc_now()

    # Student 1 unlocked hint on DEMO_WEB_03 and DEMO_REVERSE_02
    # Student 2 unlocked hint on DEMO_CRYPTO_01
    hint_plans = [
        (users["DEMO_STUDENT_01"], "DEMO_WEB_03 — SQL Injection Lab", 1, 12),
        (users["DEMO_STUDENT_01"], "DEMO_REVERSE_02 — Hidden Logic", 1, 6),
        (users["DEMO_STUDENT_02"], "DEMO_CRYPTO_01 — Caesar's Shadow", 1, 9),
    ]

    for user, chall_title, hint_order, days_ago in hint_plans:
        ch = challenges.get(chall_title)
        if not ch:
            continue
        hint = (
            db.query(ChallengeHint)
            .filter(ChallengeHint.challenge_id == ch.id, ChallengeHint.order == hint_order)
            .first()
        )
        if not hint:
            continue

        usage = (
            db.query(HintUsage)
            .filter(HintUsage.user_id == user.id, HintUsage.hint_id == hint.id)
            .first()
        )
        if not usage:
            timestamp = now - timedelta(days=days_ago, hours=1)
            usage = HintUsage(
                user_id=user.id,
                hint_id=hint.id,
                challenge_id=ch.id,
                points_deducted=hint.point_deduction,
                used_at=timestamp,
            )
            db.add(usage)
            act = UserActivity(
                user_id=user.id,
                activity_type=ActivityType.HINT_USED.value,
                reference_id=hint.id,
                metadata_json=f'{{"challenge_title": "{ch.title}", "deduction": {hint.point_deduction}}}',
                created_at=timestamp,
            )
            db.add(act)
            db.commit()
            print(f"  + Unlocked Hint for {user.username}: {hint.title} (-{hint.point_deduction} pts)")


def seed_demo_badges(db: Session, users: dict[str, User]):
    print("[7/11] Seeding Badge Awards...")
    badges = {b.slug: b for b in db.query(Badge).all()}
    if not badges:
        print("  ! No badges registered in badges table.")
        return

    # Student 1: Veteran collector
    # Student 2: Intermediate
    # Student 3: Novice
    # Student 4: None
    badge_assignments = [
        (users["DEMO_STUDENT_01"], ["first-blood", "novice-hacker", "cyber-explorer", "ctf-grinder", "point-hunter", "weekly-warrior", "event-participant"]),
        (users["DEMO_STUDENT_02"], ["first-blood", "novice-hacker", "streak-starter", "event-participant"]),
        (users["DEMO_STUDENT_03"], ["streak-starter"]),
    ]

    for user, slug_list in badge_assignments:
        for slug in slug_list:
            badge = badges.get(slug)
            if not badge:
                continue
            ub = (
                db.query(UserBadge)
                .filter(UserBadge.user_id == user.id, UserBadge.badge_id == badge.id)
                .first()
            )
            if not ub:
                ub = UserBadge(
                    user_id=user.id,
                    badge_id=badge.id,
                    awarded_at=utc_now() - timedelta(days=3),
                )
                db.add(ub)
                db.commit()
                print(f"  + Awarded Badge to {user.username}: {badge.name}")


def seed_demo_discussions(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge]
):
    print("[8/11] Seeding Discussion Threads and Comments...")
    now = utc_now()

    discussions_data = [
        {
            "challenge_title": "DEMO_WEB_03 — SQL Injection Lab",
            "author": users["DEMO_STUDENT_02"],
            "title": "Query structuring advice for SQLite/Postgres UNION extraction?",
            "content": (
                "When injecting into the student ledger, how do you handle column type mismatches between "
                "the original table and the subquery in `UNION SELECT`? Any tips on formatting payload strings cleanly?"
            ),
            "is_pinned": True,
            "comments": [
                {
                    "author": users["DEMO_STUDENT_01"],
                    "content": "Use `NULL` placeholders for columns where you don't need data, e.g. `' UNION SELECT NULL, table_name, NULL FROM ...`. Works across SQLite and Postgres!",
                },
                {
                    "author": users["DEMO_ADMIN"],
                    "content": "Good explanation @DEMO_STUDENT_01. Remember operatives: avoid posting actual flag hashes in public debriefs.",
                },
            ],
        },
        {
            "challenge_title": "DEMO_CRYPTO_02 — RSA Mistake",
            "author": users["DEMO_STUDENT_01"],
            "title": "Why small e=3 is hazardous without proper padding (OAEP)",
            "content": (
                "Sharing an educational breakdown: If `m^e < N`, modular arithmetic never wraps, turning modular RSA into simple integer exponentiation. "
                "Always enforce OAEP or PSS padding in production systems!"
            ),
            "is_pinned": False,
            "comments": [
                {
                    "author": users["DEMO_STUDENT_03"],
                    "content": "Super clear writeup! I was wondering why my gmpy2 script was getting integer roots immediately. Thanks!",
                }
            ],
        },
        {
            "challenge_title": "DEMO_FORENSICS_01 — Memory Fragment",
            "author": users["DEMO_STUDENT_03"],
            "title": "Beginner recommendations: Strings vs Volatility for memory analysis",
            "content": "Should beginners start with `strings` or dive directly into Volatility 3 plugins like `windows.pslist`?",
            "is_pinned": False,
            "comments": [
                {
                    "author": users["DEMO_STUDENT_02"],
                    "content": "Always run basic `strings` and `grep` first as a triage step! If that fails to yield credentials, spin up Volatility for process tree analysis.",
                }
            ],
        },
    ]

    for d_info in discussions_data:
        ch = challenges.get(d_info["challenge_title"])
        if not ch:
            continue

        disc = (
            db.query(Discussion)
            .filter(Discussion.challenge_id == ch.id, Discussion.title == d_info["title"])
            .first()
        )
        if not disc:
            disc = Discussion(
                challenge_id=ch.id,
                user_id=d_info["author"].id,
                title=d_info["title"],
                content=d_info["content"],
                is_pinned=d_info["is_pinned"],
                is_locked=False,
                is_deleted=False,
                contains_spoiler=False,
                created_at=now - timedelta(days=5),
            )
            db.add(disc)
            db.commit()
            db.refresh(disc)
            print(f"  + Created Discussion: {disc.title}")

        for c_info in d_info["comments"]:
            comment = (
                db.query(DiscussionComment)
                .filter(
                    DiscussionComment.discussion_id == disc.id,
                    DiscussionComment.content == c_info["content"],
                )
                .first()
            )
            if not comment:
                comment = DiscussionComment(
                    discussion_id=disc.id,
                    user_id=c_info["author"].id,
                    content=c_info["content"],
                    is_deleted=False,
                    contains_spoiler=False,
                    created_at=now - timedelta(days=4),
                )
                db.add(comment)
                db.commit()


def seed_demo_notifications(db: Session, users: dict[str, User]):
    print("[9/11] Seeding In-App Notifications...")
    now = utc_now()

    notifications_data = [
        # Student 1: Read and unread notifications
        (
            users["DEMO_STUDENT_01"],
            NotificationType.CHALLENGE_SOLVED.value,
            "Target Neutralized: DEMO_PWN_01 — Stack Basics",
            "You successfully submitted the correct flag and earned 125 Defense Credits.",
            False,
            None,
        ),
        (
            users["DEMO_STUDENT_01"],
            NotificationType.BADGE_AWARDED.value,
            "Tactical Commendation: CTF Grinder",
            "Congratulations! You unlocked the 'CTF Grinder' badge for persistent operational solves.",
            True,
            now - timedelta(days=1),
        ),
        (
            users["DEMO_STUDENT_01"],
            NotificationType.EVENT_STARTED.value,
            "Live Operation Synchronized: DEMO_EVENT_CYBER_WARFARE",
            "Operation CYBER_WARFARE is now live! The arena challenges are unlocked for active engagement.",
            False,
            None,
        ),
        # Student 2
        (
            users["DEMO_STUDENT_02"],
            NotificationType.TEAM_MEMBER_ADDED.value,
            "Squad Update: Joined DEMO_TEAM_ALPHA",
            "You were registered as an active operative in DEMO_TEAM_ALPHA.",
            True,
            now - timedelta(days=3),
        ),
        (
            users["DEMO_STUDENT_02"],
            NotificationType.DISCUSSION_REPLY.value,
            "New Debrief Intel on SQL Injection Lab",
            "DEMO_STUDENT_01 replied to your query regarding UNION extraction placeholders.",
            False,
            None,
        ),
        # Student 3
        (
            users["DEMO_STUDENT_03"],
            NotificationType.EVENT_REGISTERED.value,
            "Enlisted: DEMO_EVENT_BEGINNER_LAB",
            "Your registration for the Beginner Practice Lab was confirmed.",
            True,
            now - timedelta(days=2),
        ),
        # Admin
        (
            users["DEMO_ADMIN"],
            "security_alert",
            "Anti-Cheat Observation Triggered",
            "High rate of failed submissions recorded on challenge DEMO_PWN_03.",
            False,
            None,
        ),
    ]

    for user, n_type, title, msg, is_read, read_at in notifications_data:
        existing_n = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.title == title)
            .first()
        )
        if not existing_n:
            n = Notification(
                user_id=user.id,
                type=n_type,
                title=title,
                message=msg,
                is_read=is_read,
                read_at=read_at,
                created_at=now - timedelta(hours=6),
            )
            db.add(n)
            db.commit()

    print("  + Notifications successfully created.")


def seed_demo_anti_cheat(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge], events: dict[str, Event]
):
    print("[10/11] Seeding Anti-Cheat Telemetry & Review Audits...")
    now = utc_now()

    sec_events_data = [
        {
            "user": users["DEMO_STUDENT_03"],
            "event_type": SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS.value,
            "severity": SecurityEventSeverity.LOW.value,
            "description": "User submitted 6 consecutive invalid flags within 3 minutes on DEMO_WEB_01.",
            "challenge_title": "DEMO_WEB_01 — Hidden Parameter",
            "ip": "10.10.14.55",
            "status": SecurityEventStatus.REVIEWED.value,
            "review_note": "Normal beginner brute-force behavior. No malicious automated fuzzing detected.",
        },
        {
            "user": users["DEMO_STUDENT_02"],
            "event_type": SecurityEventType.SUBMISSION_RATE_EXCEEDED.value,
            "severity": SecurityEventSeverity.MEDIUM.value,
            "description": "Rapid rate limit threshold reached (12 submissions in 60 seconds).",
            "challenge_title": "DEMO_WEB_02 — Broken Authentication",
            "ip": "10.10.14.88",
            "status": SecurityEventStatus.OPEN.value,
            "review_note": None,
        },
        {
            "user": users["DEMO_STUDENT_01"],
            "event_type": SecurityEventType.RAPID_MULTI_CHALLENGE_SOLVING.value,
            "severity": SecurityEventSeverity.HIGH.value,
            "description": "Operative solved 3 high-point challenges within a 90-second window across disparate categories.",
            "challenge_title": "DEMO_PWN_01 — Stack Basics",
            "ip": "10.10.14.12",
            "status": SecurityEventStatus.OPEN.value,
            "review_note": None,
        },
        {
            "user": users["DEMO_STUDENT_03"],
            "event_type": SecurityEventType.REPEATED_CHALLENGE_ATTEMPTS.value,
            "severity": SecurityEventSeverity.CRITICAL.value,
            "description": "Payload signature matched SQLMap automated scanner heuristics in flag submission parameter.",
            "challenge_title": "DEMO_WEB_03 — SQL Injection Lab",
            "ip": "10.10.14.99",
            "status": SecurityEventStatus.ACTIONED.value,
            "review_note": "Automated scanning script detected. Warned operative; rate limit temporarily throttled.",
        },
    ]

    for item in sec_events_data:
        ch = challenges.get(item["challenge_title"])
        existing_se = (
            db.query(SecurityEvent)
            .filter(
                SecurityEvent.user_id == item["user"].id,
                SecurityEvent.event_type == item["event_type"],
                SecurityEvent.severity == item["severity"],
            )
            .first()
        )
        if not existing_se:
            se = SecurityEvent(
                user_id=item["user"].id,
                challenge_id=ch.id if ch else None,
                event_type=item["event_type"],
                severity=item["severity"],
                description=item["description"],
                ip_address=item["ip"],
                status=item["status"],
                created_at=now - timedelta(days=1),
            )
            db.add(se)
            db.commit()
            db.refresh(se)

            if item["review_note"]:
                review = SecurityEventReview(
                    security_event_id=se.id,
                    reviewer_id=users["DEMO_ADMIN"].id,
                    previous_status=SecurityEventStatus.OPEN.value,
                    new_status=item["status"],
                    note=item["review_note"],
                    created_at=now - timedelta(hours=12),
                )
                db.add(review)
                db.commit()

    print("  + Anti-Cheat events & reviews created.")


def seed_demo_live_instances(
    db: Session, users: dict[str, User], challenges: dict[str, Challenge]
):
    print("[11/11] Seeding Live Challenge Sandbox Instances...")
    now = utc_now()

    # Target Web and Pwn challenges for instance states
    ch_web = challenges.get("DEMO_WEB_03 — SQL Injection Lab")
    ch_pwn = challenges.get("DEMO_PWN_01 — Stack Basics")

    if not ch_web or not ch_pwn:
        return

    instances_data = [
        {
            "challenge": ch_web,
            "user": users["DEMO_STUDENT_01"],
            "status": ChallengeInstanceStatus.RUNNING,
            "container_name": "ctf-inst-web03-student01",
            "internal_port": 80,
            "external_port": 31337,
            "url": "http://sandbox.owasp-ctf.local:31337",
            "started_at": now - timedelta(minutes=25),
            "expires_at": now + timedelta(minutes=35),
        },
        {
            "challenge": ch_pwn,
            "user": users["DEMO_STUDENT_02"],
            "status": ChallengeInstanceStatus.EXPIRED,
            "container_name": "ctf-inst-pwn01-student02",
            "internal_port": 1337,
            "external_port": 31338,
            "url": "nc sandbox.owasp-ctf.local 31338",
            "started_at": now - timedelta(hours=2),
            "expires_at": now - timedelta(hours=1),
        },
        {
            "challenge": ch_web,
            "user": users["DEMO_STUDENT_03"],
            "status": ChallengeInstanceStatus.STOPPED,
            "container_name": "ctf-inst-web03-student03",
            "internal_port": 80,
            "external_port": 31339,
            "url": None,
            "started_at": now - timedelta(hours=5),
            "expires_at": now - timedelta(hours=4),
        },
    ]

    for inst in instances_data:
        existing = (
            db.query(ChallengeInstance)
            .filter(ChallengeInstance.container_name == inst["container_name"])
            .first()
        )
        if not existing:
            ci = ChallengeInstance(
                challenge_id=inst["challenge"].id,
                user_id=inst["user"].id,
                container_id=uuid.uuid4().hex[:12],
                container_name=inst["container_name"],
                status=inst["status"],
                internal_port=inst["internal_port"],
                external_port=inst["external_port"],
                external_host="sandbox.owasp-ctf.local",
                url=inst["url"],
                started_at=inst["started_at"],
                expires_at=inst["expires_at"],
            )
            db.add(ci)
            db.commit()

    print("  + Live challenge instances created.")


def main():
    print("=" * 70)
    print(" OWASP CTF Platform — Complete Demo Dataset Seeder")
    print("=" * 70)

    db = SessionLocal()
    try:
        users = seed_demo_users(db)
        teams = seed_demo_teams(db, users)
        challenges = seed_demo_challenges(db)
        events = seed_demo_events(db, users, challenges, teams)
        seed_demo_submissions_and_solves(db, users, challenges, events, teams)
        seed_demo_hint_usage(db, users, challenges)
        seed_demo_badges(db, users)
        seed_demo_discussions(db, users, challenges)
        seed_demo_notifications(db, users)
        seed_demo_anti_cheat(db, users, challenges, events)
        seed_demo_live_instances(db, users, challenges)

        print("=" * 70)
        print(" Demo dataset successfully synchronized and verified!")
        print(f" Demo Credentials: username='DEMO_ADMIN' or 'DEMO_STUDENT_01' (Password: '{DEMO_PASSWORD}')")
        print("=" * 70)
    except Exception as e:
        db.rollback()
        print(f"\n[-] Critical error during seeding: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
