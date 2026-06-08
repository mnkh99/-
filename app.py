import json
import re
import sys
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

try:
    import webview
except Exception:
    webview = None


# 可以直接填 TOKEN，也可以留空并把 token 放到同目录的 token.txt。
TOKEN = ""

HOST = "127.0.0.1"
PORT = 5000
APP_VERSION = "v0.4.3-preview"
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.yaml"
INDEX_PATH = APP_DIR / "index.html"
TOKEN_PATH = APP_DIR / "token.txt"
TITLE_GIF_PATH = APP_DIR / "title.gif"
API_URL = "https://www.warcraftlogs.com/api/v2/client"
PRE_PULL = 10000


def find_available_port(host, preferred_port):
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No available port found from {preferred_port} to {preferred_port + 19}.")


CLASS_COLORS = {
    "DeathKnight": "#c41e3a",
    "DemonHunter": "#a330c9",
    "Druid": "#ff7c0a",
    "Evoker": "#33937f",
    "Hunter": "#aad372",
    "Mage": "#3fc7eb",
    "Monk": "#00ff98",
    "Paladin": "#f48cba",
    "Priest": "#ffffff",
    "Rogue": "#fff468",
    "Shaman": "#0070dd",
    "Warlock": "#8788ee",
    "Warrior": "#c69b6d",
}

DUNGEON_NAME_EN = {
    "pit_of_saron": "Pit of Saron",
    "skyreach": "Skyreach",
    "algethar_academy": "Algeth'ar Academy",
    "tower_of_windrunner": "Tower of Windrunner",
    "magisters_terrace": "Magisters' Terrace",
    "mana_tombs": "Mana-Tombs",
    "the_nexus": "The Nexus",
    "seat_of_the_triumvirate": "The Seat of the Triumvirate",
}

BOSS_NAME_EN = {
    1999: "Forgemaster Garfrost",
    2001: "Ick and Krick",
    2000: "Scourgelord Tyrannus",
    1698: "Ranjit",
    1699: "Araknath",
    1700: "Rukhran",
    1701: "High Sage Viryx",
    2562: "Vexamus",
    2563: "Overgrown Ancient",
    2564: "Crawth",
    2565: "Echo of Doragosa",
    3071: "Arcanotron Custos",
    3072: "Seranel Sunlash",
}


def extract_report_code(log_url_or_code):
    text = (log_url_or_code or "").strip()
    if not text:
        raise ValueError("Report URL is empty.")

    match = re.search(r"/reports/([A-Za-z0-9]+)", text)
    if match:
        return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9]+", text):
        return text

    raise ValueError("Report URL format is invalid. Example: https://cn.warcraftlogs.com/reports/7GjYz81HpQTckBMn")


def extract_fight_id(log_url_or_code, explicit_fight_id):
    if explicit_fight_id not in (None, ""):
        return int(explicit_fight_id)

    text = (log_url_or_code or "").strip()
    match = re.search(r"(?:[?#&]|^)fight=(\d+)", text)
    if match:
        return int(match.group(1))

    raise ValueError("Please choose one fight, or paste a full WCL URL with fight=number.")


def load_token():
    token = TOKEN.strip()

    if not token and TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise ValueError("Token not saved yet. Save a WCL API token in Settings.")

    validate_token_text(token)
    return token


def validate_token_text(token):
    lowered = token.lower()
    if lowered.startswith(("http://", "https://")) or "warcraftlogs.com/reports/" in lowered:
        raise ValueError("Token looks like a report URL. Please paste your WCL API token, not the log link.")

    if any(char.isspace() for char in token):
        raise ValueError("Token should be one continuous string without spaces or line breaks.")

    if len(token) < 20:
        raise ValueError("Token looks too short. Please paste the full WCL API token.")

    try:
        token.encode("latin-1")
    except UnicodeEncodeError:
        raise ValueError("Token contains invalid characters. Paste the WCL API token, not placeholder text.")

def save_token(token_text):
    token = (token_text or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise ValueError("Token is empty.")

    validate_token_text(token)

    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    return app_status()


def app_status():
    status = {
        "version": APP_VERSION,
        "tokenFile": str(TOKEN_PATH.resolve()),
        "tokenFileExists": TOKEN_PATH.exists(),
        "tokenLoaded": False,
        "tokenLength": 0,
        "configFile": str(CONFIG_PATH.resolve()),
        "configExists": CONFIG_PATH.exists(),
        "configLoaded": False,
    }
    try:
        token = load_token()
        status["tokenLoaded"] = True
        status["tokenLength"] = len(token)
    except Exception as exc:
        status["tokenError"] = str(exc)
    try:
        load_config()
        status["configLoaded"] = True
    except Exception as exc:
        status["configError"] = str(exc)
    return status


def config_view():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("找不到 config.yaml，请把它和 app.py、index.html 放在同一目录")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if apply_static_english_names(config):
        write_raw_config(config)

    dungeons = []
    for dungeon in config.get("dungeons", []) or []:
        bosses = []
        for boss in dungeon.get("bosses", []) or []:
            bosses.append({
                "name": boss.get("name", ""),
                "name_en": boss.get("name_en", ""),
                "name_zh": boss.get("name_zh", ""),
                "encounterID": boss.get("encounterID"),
                "aliases": boss.get("aliases") or [],
                "skills": boss.get("skills") or [],
            })
        dungeons.append({
            "id": dungeon.get("id"),
            "name": dungeon.get("name", ""),
            "name_en": dungeon.get("name_en", ""),
            "name_zh": dungeon.get("name_zh", ""),
            "bosses": bosses,
        })

    return {
        "file": str(CONFIG_PATH.resolve()),
        "dungeons": dungeons,
        "flatBossSkills": config.get("boss_skills", []) or [],
        "monkCds": config.get("monk_cds", {}) or {},
        "personalDefensives": config.get("personal_defensives", {}) or {},
        "raidDefensives": config.get("raid_defensives", {}) or {},
        "consumables": config.get("consumables", []) or [],
        "diagnostics": config_diagnostics(config),
    }


def read_raw_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("找不到 config.yaml，请把它和 app.py、index.html 放在同一目录")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_raw_config(config):
    if CONFIG_PATH.exists():
        backup_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".bak")
        backup_path.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)


def config_diagnostics(config):
    flat_ids = {
        int(skill["id"])
        for skill in config.get("boss_skills", []) or []
        if isinstance(skill, dict) and str(skill.get("id", "")).isdigit()
    }
    nested_ids = set()
    missing_english = []
    missing_encounters = []

    for dungeon in config.get("dungeons", []) or []:
        for boss in dungeon.get("bosses", []) or []:
            if not boss.get("encounterID"):
                missing_encounters.append(ensure_entry_name(boss, boss.get("id")))
            for skill in boss.get("skills", []) or []:
                if not isinstance(skill, dict):
                    continue
                if str(skill.get("id", "")).isdigit():
                    nested_ids.add(int(skill["id"]))
                if not skill.get("name_en"):
                    missing_english.append(ensure_entry_name(skill, skill.get("id")))

    for skill in config.get("boss_skills", []) or []:
        if isinstance(skill, dict) and not skill.get("name_en"):
            missing_english.append(ensure_entry_name(skill, skill.get("id")))

    for skill in config.get("consumables", []) or []:
        if isinstance(skill, dict) and not skill.get("name_en"):
            missing_english.append(ensure_entry_name(skill, skill.get("id")))

    for section in ("monk_cds", "personal_defensives", "raid_defensives"):
        for key, value in (config.get(section) or {}).items():
            if str(key).isdigit() and isinstance(value, dict) and not value.get("name_en"):
                missing_english.append(ensure_entry_name(value, key))

    issues = []
    nested_not_flat = sorted(nested_ids - flat_ids)
    flat_not_nested = sorted(flat_ids - nested_ids)
    if nested_not_flat:
        issues.append({
            "code": "nested_not_flat",
            "count": len(nested_not_flat),
            "examples": nested_not_flat[:8],
        })
    if flat_not_nested:
        issues.append({
            "code": "flat_not_nested",
            "count": len(flat_not_nested),
            "examples": flat_not_nested[:8],
        })
    if missing_english:
        issues.append({
            "code": "missing_english",
            "count": len(missing_english),
            "examples": list(dict.fromkeys(missing_english))[:8],
        })
    if missing_encounters:
        issues.append({
            "code": "missing_encounter",
            "count": len(missing_encounters),
            "examples": list(dict.fromkeys(missing_encounters))[:8],
        })

    return issues


def entry_name(entry, default=""):
    if isinstance(entry, dict):
        return entry.get("name") or entry.get("name_zh") or entry.get("name_en") or default
    return str(entry or default)


def ensure_entry_name(entry, skill_id=None):
    name = entry_name(entry, "")
    if name:
        return name
    return f"#{skill_id}" if skill_id else ""


def apply_static_english_names(config):
    changed = False
    for dungeon in config.get("dungeons", []) or []:
        dungeon_en = DUNGEON_NAME_EN.get(str(dungeon.get("id") or ""))
        if dungeon_en and dungeon.get("name_en") != dungeon_en:
            dungeon["name_en"] = dungeon_en
            changed = True
        for boss in dungeon.get("bosses", []) or []:
            try:
                encounter_id = int(boss.get("encounterID"))
            except Exception:
                encounter_id = None
            boss_en = BOSS_NAME_EN.get(encounter_id)
            if boss_en and boss.get("name_en") != boss_en:
                boss["name_en"] = boss_en
                changed = True
    return changed


def set_name_en(entry, english_name):
    if not english_name or not isinstance(entry, dict):
        return False
    if entry.get("name_en") == english_name:
        return False
    entry["name_en"] = english_name
    return True


def enrich_config_from_wcl(ability_map, boss_segments=None):
    config = read_raw_config()
    changed = apply_static_english_names(config)

    for skill in config.get("boss_skills", []) or []:
        changed = set_name_en(skill, ability_map.get(skill.get("id"))) or changed

    for dungeon in config.get("dungeons", []) or []:
        for boss in dungeon.get("bosses", []) or []:
            try:
                encounter_id = int(boss.get("encounterID"))
            except Exception:
                encounter_id = None
            if boss_segments and encounter_id:
                match = next((seg for seg in boss_segments if int(seg.get("encounterID") or -1) == encounter_id), None)
                if match:
                    changed = set_name_en(boss, match.get("name")) or changed
            for skill in boss.get("skills", []) or []:
                changed = set_name_en(skill, ability_map.get(skill.get("id"))) or changed

    for section in ("monk_cds", "personal_defensives", "raid_defensives"):
        mapping = config.get(section) or {}
        for key, value in list(mapping.items()):
            if not str(key).isdigit():
                continue
            english_name = ability_map.get(int(key))
            if not english_name:
                continue
            if isinstance(value, dict):
                changed = set_name_en(value, english_name) or changed
            else:
                mapping[key] = {"name": str(value), "name_en": english_name}
                changed = True

    for skill in config.get("consumables", []) or []:
        changed = set_name_en(skill, ability_map.get(skill.get("id"))) or changed

    if changed:
        write_raw_config(config)
    return changed


def validate_config_structure(config):
    required = [
        "boss_skills",
        "monk_cds",
        "personal_defensives",
        "raid_defensives",
        "consumables",
        "dungeons",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError("Config missing required sections: " + ", ".join(missing))
    if not isinstance(config.get("dungeons"), list):
        raise ValueError("Config section dungeons must be a list.")
    if not isinstance(config.get("boss_skills"), list):
        raise ValueError("Config section boss_skills must be a list.")
    if not isinstance(config.get("consumables"), list):
        raise ValueError("Config section consumables must be a list.")


def export_config_text():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.yaml was not found.")
    return {
        "filename": "config.yaml",
        "text": CONFIG_PATH.read_text(encoding="utf-8"),
    }


def import_config_text(payload):
    text = str(payload.get("text") or "").strip()
    if not text:
        raise ValueError("Imported config is empty.")
    try:
        config = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValueError("Imported config is not valid YAML: " + str(exc))
    validate_config_structure(config)
    write_raw_config(config)
    load_config()
    return config_view()


def restore_config_backup():
    backup_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".bak")
    if not backup_path.exists():
        raise FileNotFoundError("config.yaml.bak was not found.")
    text = backup_path.read_text(encoding="utf-8")
    try:
        config = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValueError("Backup config is not valid YAML: " + str(exc))
    validate_config_structure(config)
    write_raw_config(config)
    load_config()
    return config_view()


def repair_config(payload):
    ability_names = payload.get("abilityNames") or {}
    ability_names = {
        int(key): value
        for key, value in ability_names.items()
        if str(key).isdigit() and value
    }
    config = read_raw_config()
    changed = apply_static_english_names(config)

    flat_by_id = {
        int(skill["id"]): skill
        for skill in config.get("boss_skills", []) or []
        if isinstance(skill, dict) and str(skill.get("id", "")).isdigit()
    }

    added_flat = 0
    filled_names = 0

    def fill_english(entry):
        nonlocal changed, filled_names
        if not isinstance(entry, dict) or not str(entry.get("id", "")).isdigit():
            return
        english_name = ability_names.get(int(entry["id"]))
        if english_name and not entry.get("name_en"):
            entry["name_en"] = english_name
            changed = True
            filled_names += 1

    for dungeon in config.get("dungeons", []) or []:
        for boss in dungeon.get("bosses", []) or []:
            for skill in boss.get("skills", []) or []:
                fill_english(skill)
                if not isinstance(skill, dict) or not str(skill.get("id", "")).isdigit():
                    continue
                skill_id = int(skill["id"])
                if skill_id not in flat_by_id:
                    flat_copy = dict(skill)
                    config.setdefault("boss_skills", []).append(flat_copy)
                    flat_by_id[skill_id] = flat_copy
                    added_flat += 1
                    changed = True

    for skill in config.get("boss_skills", []) or []:
        fill_english(skill)
    for skill in config.get("consumables", []) or []:
        fill_english(skill)

    for section in ("monk_cds", "personal_defensives", "raid_defensives"):
        mapping = config.get(section) or {}
        for key, value in list(mapping.items()):
            if not str(key).isdigit():
                continue
            english_name = ability_names.get(int(key))
            if not english_name:
                continue
            if isinstance(value, dict):
                if not value.get("name_en"):
                    value["name_en"] = english_name
                    changed = True
                    filled_names += 1
            else:
                mapping[key] = {"name": str(value), "name_en": english_name}
                changed = True
                filled_names += 1

    if changed:
        write_raw_config(config)
        load_config()

    view = config_view()
    view["repair"] = {
        "changed": changed,
        "addedFlat": added_flat,
        "filledEnglish": filled_names,
    }
    return view


def add_boss_skill(payload):
    dungeon_index = int(payload.get("dungeonIndex", -1))
    boss_index = int(payload.get("bossIndex", -1))
    name = str(payload.get("name") or "").strip()
    name_en = str(payload.get("nameEn") or "").strip()
    source = str(payload.get("source") or "cast").strip()
    try:
        skill_id = int(payload.get("id"))
    except Exception:
        raise ValueError("Spell ID must be a number.")

    if skill_id <= 0:
        raise ValueError("Spell ID must be greater than 0.")
    if source not in ("cast", "damage"):
        raise ValueError("Boss skill source must be cast or damage.")

    config = read_raw_config()
    dungeons = config.get("dungeons") or []
    if dungeon_index < 0 or dungeon_index >= len(dungeons):
        raise ValueError("Dungeon selection is invalid.")
    bosses = dungeons[dungeon_index].get("bosses") or []
    if boss_index < 0 or boss_index >= len(bosses):
        raise ValueError("Boss selection is invalid.")

    existing_ids = set()
    for dungeon in dungeons:
        for boss in dungeon.get("bosses", []) or []:
            for skill in boss.get("skills", []) or []:
                if skill.get("id") is not None:
                    existing_ids.add(int(skill["id"]))
    for skill in config.get("boss_skills", []) or []:
        if skill.get("id") is not None:
            existing_ids.add(int(skill["id"]))
    if skill_id in existing_ids:
        raise ValueError(f"Spell ID {skill_id} already exists in config.")

    skill = {"id": skill_id, "source": source}
    if name:
        skill["name"] = name
    if name_en:
        skill["name_en"] = name_en
    if source == "damage":
        skill["dedup_ms"] = 10000
        skill["once"] = True
        damage_display = str(payload.get("damageDisplay") or "target").strip()
        if damage_display not in ("target", "interval", "aura"):
            raise ValueError("Damage display must be target, interval, or aura.")
        skill["damage_display"] = damage_display

    bosses[boss_index].setdefault("skills", []).append(skill)
    config.setdefault("boss_skills", []).append(dict(skill))
    write_raw_config(config)
    load_config()
    return config_view()


def update_damage_display(payload):
    try:
        skill_id = int(payload.get("id"))
    except Exception:
        raise ValueError("Spell ID must be a number.")

    damage_display = str(payload.get("damageDisplay") or "").strip()
    if damage_display not in ("target", "interval", "aura"):
        raise ValueError("Damage display must be target, interval, or aura.")

    config = read_raw_config()
    changed = False

    def update_skill(skill):
        nonlocal changed
        if not isinstance(skill, dict) or int(skill.get("id") or 0) != skill_id:
            return
        if skill.get("source") != "damage":
            raise ValueError("Only damage skills can use damage display strategies.")
        if skill.get("damage_display") != damage_display:
            skill["damage_display"] = damage_display
            changed = True

    for skill in config.get("boss_skills", []) or []:
        update_skill(skill)
    for dungeon in config.get("dungeons", []) or []:
        for boss in dungeon.get("bosses", []) or []:
            for skill in boss.get("skills", []) or []:
                update_skill(skill)

    if not changed:
        return config_view()

    write_raw_config(config)
    load_config()
    return config_view()


def collect_config_ids(config):
    ids = set()
    for skill in config.get("boss_skills", []) or []:
        if skill.get("id") is not None:
            ids.add(int(skill["id"]))
    for dungeon in config.get("dungeons", []) or []:
        for boss in dungeon.get("bosses", []) or []:
            for skill in boss.get("skills", []) or []:
                if skill.get("id") is not None:
                    ids.add(int(skill["id"]))
    for section in ("monk_cds", "personal_defensives", "raid_defensives"):
        for key in (config.get(section) or {}).keys():
            if str(key).isdigit():
                ids.add(int(key))
    for skill in config.get("consumables", []) or []:
        if skill.get("id") is not None:
            ids.add(int(skill["id"]))
    return ids


def add_support_skill(payload):
    category = str(payload.get("category") or "").strip()
    name = str(payload.get("name") or "").strip()
    name_en = str(payload.get("nameEn") or "").strip()
    source = str(payload.get("source") or "healing").strip()
    try:
        skill_id = int(payload.get("id"))
    except Exception:
        raise ValueError("Spell ID must be a number.")

    if category not in ("monk_cd", "personal_defensive", "raid_defensive", "consumable"):
        raise ValueError("Skill category is invalid.")
    if skill_id <= 0:
        raise ValueError("Spell ID must be greater than 0.")

    config = read_raw_config()
    if skill_id in collect_config_ids(config):
        raise ValueError(f"Spell ID {skill_id} already exists in config.")

    if category == "monk_cd":
        config.setdefault("monk_cds", {})[skill_id] = {"name": name or f"#{skill_id}", "name_en": name_en} if name_en else name or f"#{skill_id}"
    elif category == "personal_defensive":
        config.setdefault("personal_defensives", {})[skill_id] = {"name": name or f"#{skill_id}", "name_en": name_en} if name_en else name or f"#{skill_id}"
    elif category == "raid_defensive":
        config.setdefault("raid_defensives", {})[skill_id] = {"name": name or f"#{skill_id}", "name_en": name_en} if name_en else name or f"#{skill_id}"
    else:
        if source not in ("healing", "buff", "damage"):
            raise ValueError("Item/Potion source must be healing, buff, or damage.")
        skill = {"id": skill_id, "source": source, "once": False}
        if name:
            skill["name"] = name
        if name_en:
            skill["name_en"] = name_en
        if source == "damage":
            skill["dedup_ms"] = 10000
            skill["once"] = True
        config.setdefault("consumables", []).append(skill)

    write_raw_config(config)
    load_config()
    return config_view()


def remove_from_skill_list(skills, skill_id):
    original_len = len(skills)
    skills[:] = [
        skill for skill in skills
        if int(skill.get("id", -1)) != skill_id
    ]
    return len(skills) != original_len


def remove_map_entry(mapping, key):
    for existing_key in list(mapping.keys()):
        if str(existing_key) == str(key):
            del mapping[existing_key]
            return True
    return False


def delete_config_entry(payload):
    kind = str(payload.get("kind") or "").strip()
    key = str(payload.get("key") or "").strip()
    if not kind or not key:
        raise ValueError("Delete target is missing.")

    config = read_raw_config()
    removed = False

    if kind == "dungeon_boss_skill":
        dungeon_index = int(payload.get("dungeonIndex", -1))
        boss_index = int(payload.get("bossIndex", -1))
        skill_id = int(key)
        dungeons = config.get("dungeons") or []
        if dungeon_index < 0 or dungeon_index >= len(dungeons):
            raise ValueError("Dungeon selection is invalid.")
        bosses = dungeons[dungeon_index].get("bosses") or []
        if boss_index < 0 or boss_index >= len(bosses):
            raise ValueError("Boss selection is invalid.")
        removed = remove_from_skill_list(bosses[boss_index].setdefault("skills", []), skill_id)
        if removed:
            remove_from_skill_list(config.setdefault("boss_skills", []), skill_id)
    elif kind == "flat_boss_skill":
        removed = remove_from_skill_list(config.setdefault("boss_skills", []), int(key))
    elif kind == "monk_cd":
        removed = remove_map_entry(config.setdefault("monk_cds", {}), key)
    elif kind == "personal_defensive":
        removed = remove_map_entry(config.setdefault("personal_defensives", {}), key)
    elif kind == "raid_defensive":
        removed = remove_map_entry(config.setdefault("raid_defensives", {}), key)
    elif kind == "consumable":
        removed = remove_from_skill_list(config.setdefault("consumables", []), int(key))
    else:
        raise ValueError("Delete target type is invalid.")

    if not removed:
        raise ValueError("Entry was not found in config.")

    write_raw_config(config)
    load_config()
    return config_view()


def post_wcl(query):
    token = load_token()
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query},
            timeout=60,
        )
        resp.raise_for_status()
    except requests.Timeout:
        raise RuntimeError("WCL request timed out. Please check your network and try again.")
    except requests.ConnectionError:
        raise RuntimeError("Could not connect to Warcraft Logs. Please check your network or proxy.")
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        if status_code in (401, 403):
            raise RuntimeError("WCL token is invalid, expired, or missing permission for this report.")
        if status_code == 404:
            raise RuntimeError("Warcraft Logs report was not found.")
        raise RuntimeError(f"Warcraft Logs returned HTTP {status_code}. Please try again later.")
    data = resp.json()
    if "errors" in data:
        error_text = json.dumps(data["errors"], ensure_ascii=False)
        lower = error_text.lower()
        if "unauth" in lower or "permission" in lower or "forbidden" in lower:
            raise RuntimeError("WCL token has no permission to read this report, or the report is private.")
        raise RuntimeError(error_text)
    return data


def format_duration_ms(start_time, end_time):
    seconds = max(0, int((end_time - start_time) / 1000))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def fetch_fights(report_code):
    query = f"""
    {{
      reportData {{
        report(code: "{report_code}") {{
          title
          startTime
          fights {{
            id
            name
            startTime
            endTime
            encounterID
            kill
          }}
        }}
      }}
    }}
    """
    data = post_wcl(query)
    report = data["data"]["reportData"]["report"]
    report_start = report.get("startTime", 0)
    fights = []

    for fight in report.get("fights", []):
        start_time = fight.get("startTime", 0)
        end_time = fight.get("endTime", start_time)
        name = fight.get("name") or "未知战斗"
        result = "击杀" if fight.get("kill") else "未击杀"
        duration = format_duration_ms(start_time, end_time)
        offset = format_duration_ms(report_start, start_time)

        fights.append({
            "id": fight["id"],
            "name": name,
            "duration": duration,
            "offset": offset,
            "kill": bool(fight.get("kill")),
            "encounterID": fight.get("encounterID"),
            "label": f"{fight['id']} - {name} / {duration} / {result}",
        })

    return {
        "reportTitle": report.get("title") or report_code,
        "fights": fights,
    }


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("找不到 config.yaml，请把它和 app.py、index.html 放在同一目录")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    boss_skills_by_source = {"cast": [], "damage": []}
    boss_skill_info = {}
    for b in config["boss_skills"]:
        src = b.get("source", "cast")
        boss_skills_by_source[src].append(b["id"])
        boss_skill_info[b["id"]] = {
            "name": ensure_entry_name(b, b.get("id")),
            "once": b.get("once", False),
            "dedup_ms": b.get("dedup_ms"),
            "damage_display": b.get("damage_display"),
            "reset_ms": b.get("reset_ms"),
        }

    all_defensives = {}
    for mapping in (config["personal_defensives"], config["raid_defensives"]):
        for key, value in mapping.items():
            all_defensives[int(key) if str(key).isdigit() else key] = ensure_entry_name(value, key)

    items_by_source = {"healing": [], "buff": [], "damage": []}
    item_info = {}
    for c in config["consumables"]:
        items_by_source[c["source"]].append(c["id"])
        item_info[c["id"]] = {
            "name": ensure_entry_name(c, c.get("id")),
            "once": c["once"],
            "dedup_ms": c.get("dedup_ms"),
        }

    return {
        "boss_skills_by_source": boss_skills_by_source,
        "boss_skill_info": boss_skill_info,
        "dungeons": config.get("dungeons", []),
        "monk_cds": config["monk_cds"],
        "all_defensives": all_defensives,
        "items_by_source": items_by_source,
        "item_info": item_info,
    }


def normalize_name(value):
    return re.sub(r"[\s'’`·\-_:：,，.。()（）]+", "", str(value or "").lower())


def boss_config_matches_segment(boss_config, segment):
    encounter_id = boss_config.get("encounterID")
    if encounter_id and segment.get("encounterID") and int(encounter_id) == int(segment["encounterID"]):
        return True

    names = [boss_config.get("name", "")]
    names.extend(boss_config.get("aliases") or [])
    segment_name = normalize_name(segment.get("name"))
    return any(normalize_name(name) == segment_name for name in names)


def match_dungeon_config(dungeons, boss_segments):
    best_dungeon = None
    best_score = 0

    for dungeon in dungeons:
        score = 0
        for segment in boss_segments:
            for boss in dungeon.get("bosses", []):
                if boss_config_matches_segment(boss, segment):
                    score += 1
                    break

        if score > best_score:
            best_score = score
            best_dungeon = dungeon

    return best_dungeon if best_score > 0 else None


def build_boss_skill_config(cfg, dungeon):
    boss_skills_by_source = {"cast": [], "damage": []}
    boss_skill_info = {}

    if dungeon:
        for boss in dungeon.get("bosses", []):
            for skill in boss.get("skills", []):
                src = skill.get("source", "cast")
                skill_id = skill["id"]
                boss_skills_by_source.setdefault(src, []).append(skill_id)
                boss_skill_info[skill_id] = {
                    "name": ensure_entry_name(skill, skill_id),
                    "once": skill.get("once", False),
                    "dedup_ms": skill.get("dedup_ms"),
                    "damage_display": skill.get("damage_display"),
                    "reset_ms": skill.get("reset_ms"),
                    "boss_name": ensure_entry_name(boss, boss.get("encounterID")),
                    "dungeon_name": ensure_entry_name(dungeon, dungeon.get("id")),
                }
        return boss_skills_by_source, boss_skill_info

    return cfg["boss_skills_by_source"], cfg["boss_skill_info"]


def fetch_base_info(report_code, fight_id):
    query = f"""
    {{
      reportData {{
        report(code: "{report_code}") {{
          fights(fightIDs:[{fight_id}]) {{
            startTime endTime
            dungeonPulls {{ name startTime endTime encounterID }}
          }}
          masterData {{
            actors {{ id name type subType }}
            abilities {{ gameID name icon }}
          }}
        }}
      }}
    }}
    """
    data = post_wcl(query)
    report = data["data"]["reportData"]["report"]
    fights = report["fights"]
    if not fights:
        raise ValueError(f"找不到 Fight ID：{fight_id}")
    return report, fights[0]


def fetch_events_by_id(report_code, fight_id, data_type, hostility_type, ability_id, include_resources=False):
    events = []
    next_page = None

    while True:
        args = (
            f"fightIDs:[{fight_id}], "
            f"dataType:{data_type}, "
            f"hostilityType:{hostility_type}, "
            f"abilityID:{ability_id}"
        )
        if include_resources:
            args += ", includeResources:true"
        if next_page:
            args += f", startTime:{next_page}"

        query = f"""
        {{
          reportData {{
            report(code:"{report_code}") {{
              events({args}) {{
                data
                nextPageTimestamp
              }}
            }}
          }}
        }}
        """

        data = post_wcl(query)
        ev_data = data["data"]["reportData"]["report"]["events"]
        if ev_data and ev_data.get("data"):
            events.extend(ev_data["data"])

        next_page = ev_data.get("nextPageTimestamp")
        if not next_page:
            break

    return events


def fetch_events(report_code, fight_id, data_type, hostility_type, include_resources=False, start_time=None, end_time=None):
    events = []
    next_page = None

    while True:
        args = f"fightIDs:[{fight_id}], dataType:{data_type}, hostilityType:{hostility_type}"
        if include_resources:
            args += ", includeResources:true"
        if next_page:
            args += f", startTime:{next_page}"
        elif start_time is not None:
            args += f", startTime:{int(start_time)}"
        if end_time is not None:
            args += f", endTime:{int(end_time)}"

        query = f"""
        {{
          reportData {{
            report(code:"{report_code}") {{
              events({args}) {{
                data
                nextPageTimestamp
              }}
            }}
          }}
        }}
        """

        data = post_wcl(query)
        ev_data = data["data"]["reportData"]["report"]["events"]
        if ev_data and ev_data.get("data"):
            events.extend(ev_data["data"])

        next_page = ev_data.get("nextPageTimestamp")
        if not next_page:
            break

    return events


def extract_health_percent(event):
    resource_candidates = [
        event.get("targetResources"),
        event.get("resources"),
        event.get("sourceResources"),
    ]
    resources = {}
    for candidate in resource_candidates:
        if isinstance(candidate, dict):
            resources = candidate
            break
        if isinstance(candidate, list) and candidate:
            dict_candidate = next((item for item in candidate if isinstance(item, dict)), None)
            if dict_candidate:
                resources = dict_candidate
                break

    for key in ("hitPointsPercent", "hpPercent", "healthPercent"):
        if resources.get(key) is not None:
            return max(0, min(100, float(resources[key])))
        if event.get(key) is not None:
            return max(0, min(100, float(event[key])))

    hp = (
        resources.get("hitPoints")
        or resources.get("hitpoints")
        or resources.get("currentHitPoints")
        or resources.get("hitPointsRemaining")
        or event.get("hitPoints")
        or event.get("hitpoints")
    )
    max_hp = (
        resources.get("maxHitPoints")
        or resources.get("maxhitPoints")
        or resources.get("maxHitpoints")
        or resources.get("maxHP")
        or event.get("maxHitPoints")
        or event.get("maxhitPoints")
    )

    if hp is None or max_hp in (None, 0):
        return None

    return max(0, min(100, (float(hp) / float(max_hp)) * 100))


def event_ability_id(event):
    ability = event.get("ability") or {}
    if isinstance(ability, dict):
        for key in ("gameID", "id"):
            if ability.get(key) is not None:
                return ability.get(key)
    for key in ("abilityGameID", "abilityID", "_id"):
        if event.get(key) is not None:
            return event.get(key)
    return None


def event_amount(event):
    for key in ("amount", "effectiveAmount", "effectiveHealing", "healing", "total"):
        try:
            if event.get(key) is not None:
                return max(0, float(event.get(key) or 0))
        except Exception:
            continue
    return 0


def normalize_actor_id(value):
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return str(value)


def actor_id_from_value(value):
    if isinstance(value, dict):
        for key in ("id", "actor", "actorID", "actorId", "sourceID", "sourceId", "targetID", "targetId"):
            if value.get(key) is not None:
                return normalize_actor_id(value.get(key))
    if isinstance(value, list):
        for item in value:
            actor_id = actor_id_from_value(item)
            if actor_id is not None:
                return actor_id
    return normalize_actor_id(value)


def event_target_id(event):
    for key in ("targetID", "targetId", "target_id"):
        if event.get(key) is not None:
            return normalize_actor_id(event.get(key))
    for key in ("target", "targetResources", "resources"):
        actor_id = actor_id_from_value(event.get(key))
        if actor_id is not None:
            return actor_id
    return None


def select_damage_timeline_events(events, info):
    sorted_events = sorted(events, key=lambda item: item.get("timestamp", 0))
    if not sorted_events:
        return []

    mode = str(info.get("damage_display") or "target").strip().lower()
    reset_ms = int(info.get("reset_ms") or info.get("dedup_ms") or 10000)

    if mode in ("aura", "field", "global"):
        selected = []
        last_time = None
        for event in sorted_events:
            timestamp = event.get("timestamp", 0)
            if last_time is None or timestamp - last_time > reset_ms:
                selected.append(event)
            last_time = timestamp
        return selected

    if mode in ("interval", "global_interval"):
        selected = []
        last_shown = None
        for event in sorted_events:
            timestamp = event.get("timestamp", 0)
            if last_shown is None or timestamp - last_shown >= reset_ms:
                selected.append(event)
                last_shown = timestamp
        return selected

    selected = []
    last_by_target = {}
    for event in sorted_events:
        timestamp = event.get("timestamp", 0)
        target_key = event_target_id(event) or "__unknown__"
        last_time = last_by_target.get(target_key)
        if last_time is None or timestamp - last_time > reset_ms:
            selected.append(event)
        last_by_target[target_key] = timestamp
    return selected


def dedupe_events(events):
    seen = set()
    result = []
    for event in events:
        key = (
            event.get("timestamp"),
            event.get("type"),
            event.get("sourceID"),
            event.get("targetID"),
            event_ability_id(event),
            event.get("amount"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(event)
    return result


def build_timeline(report_code, fight_id):
    cfg = load_config()
    report, fight = fetch_base_info(report_code, fight_id)

    fight_start = fight["startTime"]
    pulls = fight.get("dungeonPulls") or []
    actors = report["masterData"]["actors"]
    abilities = report["masterData"]["abilities"]

    ability_map = {a["gameID"]: a["name"] for a in abilities}
    ability_icon = {a["gameID"]: a.get("icon") for a in abilities}
    actor_name = {a["id"]: a["name"] for a in actors}
    players = [
        {
            "id": a["id"],
            "name": a["name"],
            "class": a.get("subType") or "Player",
            "color": CLASS_COLORS.get(a.get("subType"), "#dddddd"),
        }
        for a in actors
        if a.get("type") == "Player"
    ]
    players_by_id = {player["id"]: player for player in players}
    player_ids = {player["id"] for player in players}
    player_id_keys = {normalize_actor_id(player["id"]) for player in players}
    monk_ids = {
        a["id"]
        for a in actors
        if a.get("type") == "Player" and a.get("subType") == "Monk"
    }

    boss_segments = []
    for pull in pulls:
        if pull.get("encounterID"):
            boss_segments.append({
                "name": pull["name"],
                "encounterID": pull.get("encounterID"),
                "start": pull["startTime"] - PRE_PULL,
                "end": pull["endTime"],
            })

    if not boss_segments:
        boss_segments.append({
            "name": "整场战斗",
            "encounterID": None,
            "start": fight["startTime"] - PRE_PULL,
            "end": fight["endTime"],
        })

    try:
        enrich_config_from_wcl(ability_map, boss_segments)
        cfg = load_config()
    except Exception:
        pass

    def which_boss(timestamp):
        for index, seg in enumerate(boss_segments):
            if seg["start"] <= timestamp <= seg["end"]:
                return index
        return None

    timeline = []
    dungeon_config = match_dungeon_config(cfg["dungeons"], boss_segments)
    boss_skills_by_source, boss_skill_info = build_boss_skill_config(cfg, dungeon_config)
    monk_cds = cfg["monk_cds"]
    all_defensives = cfg["all_defensives"]
    items_by_source = cfg["items_by_source"]
    item_info = cfg["item_info"]

    for aid in boss_skills_by_source["cast"]:
        for event in fetch_events_by_id(report_code, fight_id, "Casts", "Enemies", aid):
            if event.get("type") != "cast":
                continue
            timeline.append({
                "time": event["timestamp"],
                "kind": "BOSS",
                "name": boss_skill_info[aid]["name"],
                "who": "",
                "_id": aid,
                "_ownerBoss": boss_skill_info[aid].get("boss_name", ""),
                "icon": ability_icon.get(aid),
            })

    for aid in boss_skills_by_source["damage"]:
        info = boss_skill_info[aid]
        raw_events = fetch_events_by_id(report_code, fight_id, "DamageTaken", "Friendlies", aid)
        for event in select_damage_timeline_events(raw_events, info):
            target_id = event_target_id(event)
            target_name = actor_name.get(target_id, "")
            timeline.append({
                "time": event["timestamp"],
                "kind": "BOSS",
                "name": info["name"],
                "who": target_name,
                "_sourceId": target_id,
                "_id": aid,
                "_ownerBoss": info.get("boss_name", ""),
                "icon": ability_icon.get(aid),
            })

    monk_cds_by_id = {
        int(key): ensure_entry_name(value, key)
        for key, value in monk_cds.items()
        if str(key).isdigit()
    }
    monk_cds_by_name = {
        str(key): ensure_entry_name(value, key)
        for key, value in monk_cds.items()
        if not str(key).isdigit()
    }
    monk_cd_ids = set(monk_cds_by_id.keys()).union({
        aid for aid, name in ability_map.items() if name in monk_cds_by_name
    })
    friendly_cast_ids = set(all_defensives.keys()).union(monk_cd_ids)

    for aid in friendly_cast_ids:
        ability_name = ability_map.get(aid, "未知技能")
        for event in fetch_events_by_id(report_code, fight_id, "Casts", "Friendlies", aid):
            if event.get("type") != "cast":
                continue

            source_id = event.get("sourceID")
            who = actor_name.get(source_id, "?")

            monk_cd_name = monk_cds_by_id.get(aid) or monk_cds_by_name.get(ability_name)
            if monk_cd_name and source_id in monk_ids:
                timeline.append({
                    "time": event["timestamp"],
                "kind": "MONK",
                "name": monk_cd_name,
                "who": who,
                "_sourceId": source_id,
                "_id": aid,
                "icon": ability_icon.get(aid),
            })

            if aid in all_defensives:
                timeline.append({
                    "time": event["timestamp"],
                "kind": "DEF",
                "name": all_defensives[aid],
                "who": who,
                "_sourceId": source_id,
                "_id": aid,
                "icon": ability_icon.get(aid),
            })

    for aid in items_by_source["buff"]:
        for event in fetch_events_by_id(report_code, fight_id, "Buffs", "Friendlies", aid):
            if event.get("type") != "applybuff":
                continue
            who = actor_name.get(event.get("sourceID"), "?")
            timeline.append({
                "time": event["timestamp"],
                "kind": "ITEM",
                "name": item_info[aid]["name"],
                "who": who,
                "_sourceId": event.get("sourceID"),
                "_id": aid,
                "icon": ability_icon.get(aid),
            })

    for aid in items_by_source["healing"]:
        for event in fetch_events_by_id(report_code, fight_id, "Healing", "Friendlies", aid):
            who = actor_name.get(event.get("sourceID"), "?")
            timeline.append({
                "time": event["timestamp"],
                "kind": "ITEM",
                "name": item_info[aid]["name"],
                "who": who,
                "_sourceId": event.get("sourceID"),
                "_id": aid,
                "icon": ability_icon.get(aid),
            })

    for aid in items_by_source["damage"]:
        for event in fetch_events_by_id(report_code, fight_id, "DamageDone", "Friendlies", aid):
            who = actor_name.get(event.get("sourceID"), "?")
            timeline.append({
                "time": event["timestamp"],
                "kind": "ITEM",
                "name": item_info[aid]["name"],
                "who": who,
                "_sourceId": event.get("sourceID"),
                "_id": aid,
                "icon": ability_icon.get(aid),
            })

    timeline.sort(key=lambda item: item["time"])
    last_seen = {}
    cleaned = []

    for event in timeline:
        aid = event.get("_id")
        info = item_info.get(aid, {}) or boss_skill_info.get(aid, {})
        dedup_ms = info.get("dedup_ms")
        if dedup_ms is None and info.get("once"):
            dedup_ms = 3000

        if aid is not None and dedup_ms:
            key = (event["who"], aid)
            if key in last_seen and event["time"] - last_seen[key] < dedup_ms:
                continue
            last_seen[key] = event["time"]

        cleaned.append(event)

    buckets = {index: [] for index in range(len(boss_segments))}
    for event in cleaned:
        boss_index = which_boss(event["time"])
        if boss_index is not None:
            buckets[boss_index].append(event)

    death_stats = {
        "total": 0,
        "boss": 0,
        "nonBoss": 0,
    }
    deaths_by_boss = {index: [] for index in range(len(boss_segments))}
    try:
        for event in fetch_events(report_code, fight_id, "Deaths", "Friendlies"):
            player_id = event.get("targetID") if event.get("targetID") in player_ids else event.get("sourceID")
            if player_id not in player_ids:
                continue
            death_stats["total"] += 1
            boss_index = which_boss(event["timestamp"])
            if boss_index is not None:
                death_stats["boss"] += 1
                player = players_by_id.get(player_id, {})
                deaths_by_boss[boss_index].append({
                    "time": event["timestamp"],
                    "playerId": player_id,
                    "name": actor_name.get(player_id, "?"),
                    "class": player.get("class", "Player"),
                    "color": player.get("color", "#dddddd"),
                    "killingBlowId": event_ability_id(event),
                })
            else:
                death_stats["nonBoss"] += 1
    except Exception:
        pass

    health_points = {player["id"]: [] for player in players}
    damage_taken_events = []
    healing_events = []
    try:
        health_events = []
        for seg in boss_segments:
            try:
                damage_taken_events.extend(fetch_events(
                    report_code,
                    fight_id,
                    "DamageTaken",
                    "Friendlies",
                    include_resources=True,
                    start_time=seg["start"],
                    end_time=seg["end"],
                ))
            except Exception:
                pass
            try:
                healing_events.extend(fetch_events(
                    report_code,
                    fight_id,
                    "Healing",
                    "Friendlies",
                    include_resources=True,
                    start_time=seg["start"],
                    end_time=seg["end"],
                ))
            except Exception:
                pass
        damage_taken_events = dedupe_events(damage_taken_events)
        healing_events = dedupe_events(healing_events)
        health_events.extend(damage_taken_events)
        health_events.extend(healing_events)
        for event in health_events:
            resources = event.get("targetResources") or event.get("resources") or {}
            if isinstance(resources, list) and resources:
                resources = next((item for item in resources if isinstance(item, dict)), {}) or {}
            if not isinstance(resources, dict):
                resources = {}
            target_id = event_target_id(event)
            if target_id not in player_id_keys:
                continue
            pct = extract_health_percent(event)
            if pct is None:
                continue
            health_points[target_id].append({
                "time": event["timestamp"],
                "pct": round(pct, 1),
            })
        for points in health_points.values():
            points.sort(key=lambda item: item["time"])
    except Exception:
        health_points = {player["id"]: [] for player in players}

    damage_taken_events.sort(key=lambda item: item.get("timestamp", 0))
    for deaths in deaths_by_boss.values():
        for death in deaths:
            killing = None
            for event in damage_taken_events:
                if event.get("timestamp", 0) > death["time"]:
                    break
                if event.get("targetID") == death["playerId"]:
                    killing = event
            if not killing:
                continue
            ability_id = death.get("killingBlowId") or event_ability_id(killing)
            death["killingBlowId"] = ability_id
            death["killingBlowName"] = ability_map.get(ability_id) or killing.get("abilityName") or killing.get("name")
            death["killingBlowIcon"] = ability_icon.get(ability_id)
            death["killingSource"] = actor_name.get(killing.get("sourceID"), "")

    for deaths in deaths_by_boss.values():
        for death in deaths:
            health_points.setdefault(death["playerId"], []).append({
                "time": death["time"],
                "pct": 0,
            })
    for points in health_points.values():
        points.sort(key=lambda item: item["time"])

    resource_bins_by_boss = {
        index: {"healing": {}, "damage": {}}
        for index in range(len(boss_segments))
    }

    def add_resource_event(event, resource_type, boss_index=None):
        if boss_index is None:
            boss_index = which_boss(event.get("timestamp"))
            if boss_index is None:
                return
        amount = event_amount(event)
        if amount <= 0:
            return
        pull_start = boss_segments[boss_index]["start"] + PRE_PULL
        rel_second = int((event["timestamp"] - pull_start) / 1000)
        bucket = resource_bins_by_boss[boss_index][resource_type]
        bucket[rel_second] = bucket.get(rel_second, 0) + amount

    for boss_index, seg in enumerate(boss_segments):
        try:
            segment_healing_events = fetch_events(
                report_code,
                fight_id,
                "Healing",
                "Friendlies",
                include_resources=False,
                start_time=seg["start"],
                end_time=seg["end"],
            )
        except Exception:
            segment_healing_events = [
                event for event in healing_events
                if seg["start"] <= event.get("timestamp", 0) <= seg["end"]
            ]

        try:
            segment_damage_events = fetch_events(
                report_code,
                fight_id,
                "DamageTaken",
                "Friendlies",
                include_resources=False,
                start_time=seg["start"],
                end_time=seg["end"],
            )
        except Exception:
            segment_damage_events = [
                event for event in damage_taken_events
                if seg["start"] <= event.get("timestamp", 0) <= seg["end"]
            ]

        for event in segment_healing_events:
            if event_target_id(event) in player_id_keys:
                add_resource_event(event, "healing", boss_index)
        for event in segment_damage_events:
            if event_target_id(event) in player_id_keys:
                add_resource_event(event, "damage", boss_index)

    output = {
        "fightStart": fight_start,
        "dungeon": {
            "id": dungeon_config.get("id"),
            "name": dungeon_config.get("name"),
        } if dungeon_config else None,
        "abilityNames": {str(aid): name for aid, name in ability_map.items()},
        "abilityIcons": {str(aid): icon for aid, icon in ability_icon.items() if icon},
        "deathStats": death_stats,
        "players": players,
        "bosses": [],
    }

    for index, seg in enumerate(boss_segments):
        pull_start = seg["start"] + PRE_PULL
        boss_data = {
            "name": seg["name"],
            "encounterID": seg.get("encounterID"),
            "start": seg["start"],
            "end": seg["end"],
            "events": [],
            "health": [],
            "resources": {
                "healing": [],
                "damage": [],
            },
        }

        bins = resource_bins_by_boss.get(index, {"healing": {}, "damage": {}})
        for key in ("healing", "damage"):
            boss_data["resources"][key] = [
                {"relTime": second, "amount": round(amount, 1)}
                for second, amount in sorted(bins.get(key, {}).items())
            ]

        for event in buckets[index]:
            boss_data["events"].append({
                "time": event["time"],
                "relTime": (event["time"] - pull_start) / 1000,
                "kind": event["kind"],
                "name": event["name"],
                "abilityName": ability_map.get(event.get("_id")),
                "who": event["who"],
                "sourceId": event.get("_sourceId"),
                "spellId": event.get("_id"),
                "ownerBoss": event.get("_ownerBoss", ""),
                "icon": event.get("icon"),
            })

        for death in deaths_by_boss.get(index, []):
            boss_data["events"].append({
                "time": death["time"],
                "relTime": (death["time"] - pull_start) / 1000,
                "kind": "DEATH",
                "lane": "BOSS",
                "name": "Death",
                "abilityName": None,
                "who": death["name"],
                "sourceId": death["playerId"],
                "playerId": death["playerId"],
                "playerClass": death.get("class", "Player"),
                "playerColor": death.get("color", "#dddddd"),
                "killingBlowId": death.get("killingBlowId"),
                "killingBlowName": death.get("killingBlowName"),
                "killingBlowIcon": death.get("killingBlowIcon"),
                "killingSource": death.get("killingSource", ""),
                "spellId": None,
                "ownerBoss": "",
                "icon": None,
            })

        boss_data["events"].sort(key=lambda item: item["time"])

        pull_start = seg["start"] + PRE_PULL
        for player in players:
            points = []
            last_before = None
            for point in health_points.get(player["id"], []):
                if point["time"] < seg["start"]:
                    last_before = point
                    continue
                if point["time"] > seg["end"]:
                    break
                if not points:
                    initial_pct = last_before["pct"] if last_before else 100
                    points.append({
                        "relTime": (seg["start"] - pull_start) / 1000,
                        "pct": initial_pct,
                    })
                points.append({
                    "relTime": (point["time"] - pull_start) / 1000,
                    "pct": point["pct"],
                })
            if points:
                boss_data["health"].append({
                    "playerId": player["id"],
                    "name": player["name"],
                    "class": player["class"],
                    "color": player["color"],
                    "points": points,
                })

        output["bosses"].append(boss_data)

    return output


class TimelineHandler(BaseHTTPRequestHandler):
    def send_text(self, status, text, content_type="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send_text(
            status,
            json.dumps(data, ensure_ascii=False),
            "application/json; charset=utf-8",
        )

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/title.gif":
            if not TITLE_GIF_PATH.exists():
                self.send_json(404, {"error": "title.gif not found"})
                return
            body = TITLE_GIF_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path not in ("/", "/index.html"):
            self.send_json(404, {"error": "页面不存在"})
            return

        if not INDEX_PATH.exists():
            self.send_text(500, "找不到 index.html，请把它和 app.py 放在同一目录")
            return

        self.send_text(
            200,
            INDEX_PATH.read_text(encoding="utf-8"),
            "text/html; charset=utf-8",
        )

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw_body or "{}")

            if path == "/api/status":
                self.send_json(200, app_status())
                return

            if path == "/api/token":
                self.send_json(200, save_token(payload.get("token")))
                return

            if path == "/api/config-view":
                self.send_json(200, config_view())
                return

            if path == "/api/config/export":
                self.send_json(200, export_config_text())
                return

            if path == "/api/config/import":
                self.send_json(200, import_config_text(payload))
                return

            if path == "/api/config/restore-backup":
                self.send_json(200, restore_config_backup())
                return

            if path == "/api/config/repair":
                self.send_json(200, repair_config(payload))
                return

            if path == "/api/config/add-boss-skill":
                self.send_json(200, add_boss_skill(payload))
                return

            if path == "/api/config/update-damage-display":
                self.send_json(200, update_damage_display(payload))
                return

            if path == "/api/config/add-support-skill":
                self.send_json(200, add_support_skill(payload))
                return

            if path == "/api/config/delete-entry":
                self.send_json(200, delete_config_entry(payload))
                return

            log_url = payload.get("logUrl")
            report_code = extract_report_code(log_url)

            if path == "/api/fights":
                self.send_json(200, fetch_fights(report_code))
                return

            if path == "/api/timeline":
                fight_id = extract_fight_id(log_url, payload.get("fightId"))
                self.send_json(200, build_timeline(report_code, fight_id))
                return

            self.send_json(404, {"error": "接口不存在"})
        except Exception as exc:
            self.send_json(400, {"error": str(exc)})


def main():
    port = find_available_port(HOST, PORT)
    url = f"http://{HOST}:{port}"
    server = ThreadingHTTPServer((HOST, port), TimelineHandler)
    print(f"服务已启动：{url}")
    print(f"程序目录：{APP_DIR}")
    print("按 Ctrl+C 停止服务")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    if "--browser" in sys.argv or webview is None:
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            server.shutdown()
        return

    try:
        webview.create_window(
            "I Don't Know Less Than You",
            url,
            width=1400,
            height=900,
            min_size=(1100, 720),
        )
        webview.start()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

